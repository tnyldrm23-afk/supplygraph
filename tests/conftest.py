"""Explicit test doubles and small independently understandable flow fixtures."""

from copy import deepcopy
from types import SimpleNamespace
import threading

import pytest
from fastapi.testclient import TestClient
from app import queries
from app.main import app
from app.models import Scenario
from app.simulation import SimulationEngine


@pytest.fixture
def payload():
    """Two suppliers, a shared manufacturer and two retailer demand sinks."""
    orgs = [
        {"id": "SUP-01", "name": "Primary", "kind": "supplier", "provenance": "assumed"},
        {"id": "SUP-02", "name": "Reserve", "kind": "supplier", "provenance": "assumed"},
        {"id": "MFG-01", "name": "Factory", "kind": "manufacturer", "provenance": "assumed"},
        {"id": "RET-01", "name": "Retail one", "kind": "retailer", "provenance": "assumed"},
        {"id": "RET-02", "name": "Retail two", "kind": "retailer", "provenance": "assumed"},
    ]
    specs = [
        ("SUP-01", "MFG-01", 12, 2, False),
        ("SUP-02", "MFG-01", 6, 5, True),
        ("MFG-01", "RET-01", 8, 1, False),
        ("MFG-01", "RET-02", 8, 3, False),
    ]
    lanes = [
        dict(
            id=f"L{i}",
            origin=a,
            destination=b,
            capacity=c,
            lead_days=d,
            backup=e,
            sku="SKU-1",
            provenance="assumed",
        )
        for i, (a, b, c, d, e) in enumerate(specs)
    ]
    return {
        "products": [
            {
                "id": "SKU-1",
                "name": "Widget",
                "daily_demand": 12,
                "historical_units": 1200,
                "price": 10,
                "provenance": "observed",
            }
        ],
        "organizations": orgs,
        "lanes": lanes,
        "locations": [],
        "metadata": {"source": "test-fixture"},
    }


@pytest.fixture
def engine(payload):
    """Use the real solver on a tiny graph with analytically known capacities."""
    return SimulationEngine(payload)


class FakeDatabase:
    """Test-only deterministic repository; integration tests never use this class."""

    def __init__(self, engine):
        self.engine = engine
        self.calls = []

    def read(self, cypher, parameters=None):
        """Return known records for exercising API contracts without a Docker dependency."""
        self.calls.append((cypher, parameters))
        if "gds.version" in cypher:
            return [{"version": "test-only"}]
        if "RETURN 1 AS ok" in cypher:
            return [{"ok": 1}]
        if "count(o)" in cypher:
            return [{"count": 1}]
        if cypher == queries.PROVENANCE:
            return deepcopy(self.engine.lanes)
        if cypher == queries.BOTTLENECKS:
            return [{"sku": "SKU-1", "name": "Widget", "supplier_id": "SUP-01", "daily_demand": 12}]
        if cypher == queries.ALTERNATIVES:
            return [{"supplier_id": "SUP-02", "sku": "SKU-1"}]
        if cypher == queries.IMPACT:
            return [{"id": "MFG-01", "hops": 1}]
        if cypher == queries.ORDER:
            if parameters["order_id"] != "ORD-1":
                return []
            return [
                {
                    "order": {"id": "ORD-1", "retailer_id": "RET-01", "actual_days": 3},
                    "items": [{"sku": "SKU-1", "name": "Widget", "quantity": 2}],
                }
            ]
        if "MATCH (p:Product)" in cypher:
            return [{"product": p} for p in self.engine.products.values()]
        if "MATCH (o:Order)" in cypher:
            return [{"data": {"id": "ORD-1"}}]
        return []

    def gds(self, algorithm, limit):
        """Clearly label a test stub rather than pretending it ran GDS."""
        return {"algorithm": algorithm, "results": [], "test_stub": True, "limit": limit}


@pytest.fixture
def client(engine):
    """Inject test state; real lifespan is exercised separately by Docker integration."""
    app.state.db = FakeDatabase(engine)
    app.state.engine = engine
    app.state.settings = SimpleNamespace(ollama_model="test-only", ollama_url="http://unused")
    app.state.simulation_slots = threading.BoundedSemaphore(2)
    app.state.assistant = SimpleNamespace(ask=lambda _: {"summary": "test result"})
    return TestClient(app)
