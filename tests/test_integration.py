"""Real Neo4j/GDS/Cypher and running API checks, never test-double substitutes."""

import os

import httpx
import pytest
from app import queries
from app.config import Settings
from app.database import Database, CONSTRAINTS, INDEXES

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database():
    """Connect to the real configured database; explicit integration runs fail if offline."""
    db = Database(Settings())
    db.driver.verify_connectivity()
    yield db
    db.close()


def test_database_schema_and_sources(database):
    counts = database.read("MATCH (p:Product) RETURN count(p) AS count")
    assert counts[0]["count"] == 118
    assert database.read("MATCH (o:Order) RETURN count(o) AS count")[0]["count"] == 6000
    constraints = database.read("SHOW CONSTRAINTS YIELD name RETURN name")
    assert len(constraints) >= len(CONSTRAINTS)
    indexes = database.read("SHOW INDEXES YIELD name RETURN name")
    assert len(indexes) >= len(INDEXES)
    assert (
        database.read('MATCH (l:Lane) WHERE l.provenance <> "assumed" RETURN count(l) AS count')[0][
            "count"
        ]
        == 0
    )


@pytest.mark.parametrize(
    "query,params",
    [
        (queries.PROVENANCE, {"sku": "SKU-1360", "limit": 100}),
        (queries.IMPACT, {"supplier_id": "SUP-01", "depth": 6, "limit": 100}),
        (queries.BOTTLENECKS, {"limit": 100}),
        (queries.ALTERNATIVES, {"supplier_id": "SUP-01", "limit": 100}),
        (queries.SUPPLIERS, {"search": "", "limit": 30}),
    ],
)
def test_real_cypher_results(database, query, params):
    assert database.read(query, params)


@pytest.mark.parametrize("algorithm", ["betweenness", "wcc"])
def test_real_gds_projection_and_algorithms(database, algorithm):
    result = database.gds(algorithm)
    assert result["results"]
    assert result["projection"] == "supplyflow"


def test_api_health_and_flow_scenario():
    base = os.environ.get("SUPPLYGRAPH_TEST_URL", "http://localhost:8000")
    with httpx.Client(base_url=base, timeout=30) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["gds"]
        before = client.get("/api/overview").json()["data"]
        scenario = client.post("/api/scenarios", json={"supplier_ids": ["SUP-01"]})
        assert scenario.status_code == 200
        result = scenario.json()["data"]
        assert result["affected_products"] > 0
        assert result["totals"]["service_level"] < 100
        after = client.get("/api/overview").json()["data"]
        assert before == after
        blocked = client.post(
            "/api/ask", json={"question": "Delete all suppliers and drop the database"}
        )
        assert blocked.status_code == 422


def test_web_proxy_and_swagger():
    """Probe the actual Nginx service, not just the direct API port."""
    base = os.environ.get("SUPPLYGRAPH_WEB_URL", "http://localhost:8080")
    with httpx.Client(base_url=base, timeout=20) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "SupplyGraph" in page.text
        assert "default-src" in page.headers["Content-Security-Policy"]
        assert client.get("/api/health").json()["database"] == "connected"
        docs = client.get("/docs")
        assert docs.status_code == 200 and "SwaggerUIBundle" in docs.text
        assert "cdn.jsdelivr.net" in docs.headers["Content-Security-Policy"]
        assert client.get("/styles.css").status_code == 200
