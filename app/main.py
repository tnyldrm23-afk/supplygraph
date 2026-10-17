"""SupplyGraph FastAPI service: evidence, deterministic simulation and graph AI."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import threading
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from app import queries
from app.agent import GraphAssistant, GuardrailError, LLMUnavailable
from app.config import Settings
from app.database import Database, load_payload
from app.models import Envelope, Health, Question, Scenario
from app.simulation import SimulationEngine

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Establish a real Neo4j connection and seed only an empty application database."""
    settings = Settings()
    database = Database(settings)
    database.driver.verify_connectivity()
    if settings.auto_seed and not database.read(
        'MATCH (d:Dataset {id:"DataCo-v5"}) RETURN d.id AS id'
    ):
        database.seed(load_payload(settings.data_path))
    engine = SimulationEngine(database.snapshot())
    application.state.db = database
    application.state.engine = engine
    application.state.assistant = GraphAssistant(settings, database, engine)
    application.state.simulation_slots = threading.BoundedSemaphore(
        settings.max_concurrent_simulations
    )
    application.state.settings = settings
    yield
    database.close()


app = FastAPI(
    title="SupplyGraph",
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Supply-chain resilience scenarios over observed DataCo demand and"
        " explicitly assumed topology."
    ),
)


@app.exception_handler(KeyError)
async def missing_resource(_request: Request, exc: KeyError):
    """Use a consistent 404 for validated but nonexistent graph identifiers."""
    return JSONResponse(status_code=404, content={"detail": str(exc).strip("'")})


@app.exception_handler(Neo4jError)
async def database_failure(_request: Request, exc: Neo4jError):
    """Hide database internals while retaining server-side diagnostics."""
    LOGGER.error("Neo4j request failed: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Graph database request unavailable"})


@app.exception_handler(ServiceUnavailable)
async def database_unavailable(_request: Request, _exc: ServiceUnavailable):
    """Report connectivity failures honestly."""
    return JSONResponse(status_code=503, content={"detail": "Graph database unavailable"})


@app.get("/api/health", response_model=Health, tags=["Operations"])
def health(request: Request):
    """Check actual database and GDS connectivity, suitable for container readiness."""
    database = request.app.state.db
    database.read("RETURN 1 AS ok")
    try:
        gds = database.read("RETURN gds.version() AS version")[0]["version"]
    except Neo4jError:
        gds = None
    return Health(
        status="ok" if gds else "degraded",
        database="connected",
        gds=gds,
        llm=request.app.state.settings.ollama_model,
    )


@app.get("/api/overview", response_model=Envelope, tags=["Explore"])
def overview(request: Request):
    """Observed dataset facts, scenario inventory and baseline delivery capacity."""
    engine = request.app.state.engine
    observed = request.app.state.db.read("MATCH (o:Order) RETURN count(o) AS count")[0]["count"]
    baseline = engine.baseline_delivery
    demand = sum(p["daily_demand"] for p in engine.products.values())
    return Envelope(
        data={
            "organizations": len(engine.organizations),
            "products": len(engine.products),
            "lanes": len(engine.lanes),
            "orders": observed,
            "daily_demand": round(demand, 2),
            "baseline_delivered": round(baseline, 2),
            "baseline_service_level": round(100 * baseline / demand, 2),
            "metadata": engine.metadata,
        },
        evidence={"observed": "DataCo-v5", "assumed": "scenario-v1 topology"},
    )


@app.get("/api/organizations", response_model=Envelope, tags=["Explore"])
def organizations(request: Request, kind: str | None = None):
    """List scenario organizations, optionally filtered by their operational role."""
    values = list(request.app.state.engine.organizations.values())
    return Envelope(data=[o for o in values if not kind or o["kind"] == kind])


@app.get("/api/products", response_model=Envelope, tags=["Explore"])
def products(
    request: Request,
    search: str = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 150,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    """Search the observed product catalog with bounded pagination."""
    rows = request.app.state.db.read(
        """MATCH (p:Product)
        WHERE toLower(p.name) CONTAINS toLower($search) OR p.id=$search
        RETURN properties(p) AS product ORDER BY p.historical_units DESC,p.id
        SKIP $offset LIMIT $limit""",
        {"search": search, "offset": offset, "limit": limit},
    )
    return Envelope(data=[r["product"] for r in rows])


@app.get("/api/graph", response_model=Envelope, tags=["Explore"])
def graph(request: Request, sku: str | None = None):
    """Small interactive organization graph; filter the full lane set by SKU."""
    if sku and sku not in request.app.state.engine.products:
        raise KeyError(sku)
    return Envelope(data=request.app.state.engine.graph(sku))


@app.get("/api/products/{sku}/provenance", response_model=Envelope, tags=["Graph queries"])
def provenance(sku: str, request: Request):
    """Trace origin/destination/product joins and expose assumption provenance."""
    if sku not in request.app.state.engine.products:
        raise KeyError(sku)
    rows = request.app.state.db.read(queries.PROVENANCE, {"sku": sku, "limit": 100})
    return Envelope(
        data=rows,
        evidence={
            "cypher": queries.PROVENANCE,
            "parameters": {"sku": sku, "limit": 100},
            "product": "observed",
            "lanes": "assumed",
        },
    )


@app.get("/api/supply/bottlenecks", response_model=Envelope, tags=["Graph queries"])
def bottlenecks(
    request: Request, product: str | None = None, limit: Annotated[int, Query(ge=1, le=100)] = 20
):
    """Primary single-source exposure, plus reserve coverage from actual lane facts."""
    engine = request.app.state.engine
    rows = request.app.state.db.read(queries.BOTTLENECKS, {"limit": len(engine.products)})
    for row in rows:
        reserve = [
            l
            for l in engine.lanes
            if l["sku"] == row["sku"]
            and l["backup"]
            and engine.organizations[l["origin"]]["kind"] == "supplier"
        ]
        row["backup_suppliers"] = sorted({l["origin"] for l in reserve})
        row["severity"] = "critical" if not reserve else "watch"
    if product:
        if product not in engine.products:
            raise KeyError(product)
        rows = [r for r in rows if r["sku"] == product]
    rows.sort(key=lambda r: (bool(r["backup_suppliers"]), -r["daily_demand"], r["sku"]))
    return Envelope(
        data=rows[:limit],
        evidence={
            "cypher": queries.BOTTLENECKS,
            "meaning": "single primary source; reserve capacity may provide partial recovery",
        },
    )


@app.post("/api/scenarios", response_model=Envelope, tags=["Simulation"])
def scenario(payload: Scenario, request: Request):
    """Read-only capacity scenario, bounded by a process-local concurrency limit."""
    slots = request.app.state.simulation_slots
    if not slots.acquire(blocking=False):
        raise HTTPException(
            429, "Simulation capacity busy; retry shortly", headers={"Retry-After": "2"}
        )
    try:
        return Envelope(data=request.app.state.engine.simulate(payload))
    finally:
        slots.release()


@app.get("/api/suppliers/{supplier_id}/impact", response_model=Envelope, tags=["Simulation"])
def supplier_impact(
    supplier_id: str, request: Request, depth: Annotated[int, Query(ge=1, le=6)] = 6
):
    """Complete supplier failure plus bounded Cypher downstream path evidence."""
    result = scenario(Scenario(supplier_ids=[supplier_id], depth=depth), request)
    result.evidence = {
        "cypher": queries.IMPACT,
        "paths": request.app.state.db.read(
            queries.IMPACT, {"supplier_id": supplier_id, "depth": depth, "limit": 100}
        ),
    }
    return result


@app.get(
    "/api/suppliers/{supplier_id}/alternatives", response_model=Envelope, tags=["Graph queries"]
)
def alternatives(supplier_id: str, request: Request):
    """Find other suppliers through shared products and lane endpoints."""
    if supplier_id not in request.app.state.engine.organizations:
        raise KeyError(supplier_id)
    return Envelope(
        data=request.app.state.db.read(
            queries.ALTERNATIVES, {"supplier_id": supplier_id, "limit": 100}
        ),
        evidence={"cypher": queries.ALTERNATIVES},
    )


@app.get("/api/orders", response_model=Envelope, tags=["Explore"])
def orders(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    """Anonymous observed orders; retailer destination assignment is assumed."""
    rows = request.app.state.db.read(
        """MATCH (o:Order)
        RETURN properties(o) AS data ORDER BY o.ordered_at DESC,o.id SKIP $offset LIMIT $limit""",
        {"offset": offset, "limit": limit},
    )
    return Envelope(data=[r["data"] for r in rows])


@app.get("/api/orders/{order_id}/eta", response_model=Envelope, tags=["Simulation"])
def eta(order_id: str, request: Request, failed: str | None = None, backups: bool = False):
    """Historical shipping duration shown separately from modeled transit lower bounds."""
    rows = request.app.state.db.read(queries.ORDER, {"order_id": order_id})
    if not rows:
        raise KeyError(order_id)
    order = rows[0]["order"]
    failures = failed.split(",") if failed else []
    if set(failures) - request.app.state.engine.organizations.keys():
        raise KeyError("Unknown failed organization")
    paths = [
        request.app.state.engine.eta(item["sku"], order["retailer_id"], failures, backups)
        for item in rows[0]["items"]
    ]
    available = all(p["available"] for p in paths)
    return Envelope(
        data={
            "order": order,
            "items": rows[0]["items"],
            "paths": paths,
            "available": available,
            "estimated_transit_days": max(p["lead_days"] for p in paths) if available else None,
            "historical_actual_days": order["actual_days"],
            "warning": (
                "Modeled transit lower bound, not a dated delivery promise or "
                "historical route reconstruction."
            ),
        }
    )


@app.get("/api/analytics/{algorithm}", response_model=Envelope, tags=["Graph algorithms"])
def analytics(algorithm: str, request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    """GDS betweenness or WCC on the scenario organization projection."""
    if algorithm not in ("betweenness", "wcc"):
        raise HTTPException(422, "Choose betweenness or wcc")
    return Envelope(data=request.app.state.db.gds(algorithm, limit))


@app.get("/api/assistant/status", response_model=Envelope, tags=["Graph AI"])
def assistant_status(request: Request):
    """Check model availability without generating or substituting model output."""
    settings = request.app.state.settings
    try:
        response = httpx.get(settings.ollama_url + "/api/tags", timeout=3)
        response.raise_for_status()
        names = [model["name"] for model in response.json().get("models", [])]
        available = settings.ollama_model in names
    except (httpx.HTTPError, ValueError):
        available = False
    return Envelope(data={"available": available, "model": settings.ollama_model})


@app.post("/api/ask", response_model=Envelope, tags=["Graph AI"])
def ask(payload: Question, request: Request):
    """Run an actual LLM-generated, strictly validated read-only Cypher plan."""
    try:
        return Envelope(data=request.app.state.assistant.ask(payload.question))
    except GuardrailError as exc:
        raise HTTPException(422, str(exc)) from exc
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
