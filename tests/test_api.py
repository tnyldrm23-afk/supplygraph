"""Public validation, resource errors, overload behavior and honest LLM failures."""

from types import SimpleNamespace

import pytest
from app.agent import GuardrailError, LLMUnavailable
from app.main import app


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/health",
        "/api/overview",
        "/api/organizations",
        "/api/organizations?kind=supplier",
        "/api/products?search=Widget",
        "/api/graph",
        "/api/graph?sku=SKU-1",
        "/api/products/SKU-1/provenance",
        "/api/supply/bottlenecks",
        "/api/supply/bottlenecks?product=SKU-1",
        "/api/suppliers/SUP-01/impact?depth=2",
        "/api/suppliers/SUP-01/alternatives",
        "/api/orders",
        "/api/orders/ORD-1/eta",
        "/api/orders/ORD-1/eta?failed=SUP-01",
        "/api/orders/ORD-1/eta?failed=SUP-01&backups=true",
        "/api/analytics/betweenness",
        "/api/analytics/wcc",
        "/openapi.json",
    ],
)
def test_read_endpoints(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/products/SKU-999/provenance",
        "/api/graph?sku=SKU-999",
        "/api/supply/bottlenecks?product=SKU-999",
        "/api/suppliers/SUP-99/alternatives",
        "/api/suppliers/SUP-99/impact",
        "/api/orders/ORD-999/eta",
        "/api/orders/ORD-1/eta?failed=SUP-99",
    ],
)
def test_resource_not_found(client, endpoint):
    assert client.get(endpoint).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"supplier_ids": []},
        {"supplier_ids": ["SUP-01"], "depth": 7},
        {"supplier_ids": ["SUP-01"], "reduction": 1.1},
        {"supplier_ids": ["SUP-01"], "reduction": -1},
        {"supplier_ids": ["SUP-01", "SUP-01"]},
        {"supplier_ids": ["bad"]},
        {"supplier_ids": ["SUP-01"], "unexpected": 1},
    ],
)
def test_scenario_rejects_invalid_inputs(client, body):
    assert client.post("/api/scenarios", json=body).status_code == 422


def test_scenario_flow(client):
    result = client.post("/api/scenarios", json={"supplier_ids": ["SUP-01"]})
    assert result.status_code == 200
    assert result.json()["data"]["totals"]["scenario_delivered"] == 0


def test_concurrency_limit(client):
    slots = app.state.simulation_slots
    slots.acquire()
    slots.acquire()
    try:
        response = client.post("/api/scenarios", json={"supplier_ids": ["SUP-01"]})
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "2"
    finally:
        slots.release()
        slots.release()


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/products?limit=201",
        "/api/products?offset=-1",
        "/api/suppliers/SUP-01/impact?depth=100",
        "/api/analytics/unsupported",
    ],
)
def test_query_bounds(client, endpoint):
    assert client.get(endpoint).status_code == 422


def test_ask_contract(client):
    assert client.post("/api/ask", json={"question": "Show suppliers"}).status_code == 200
    assert client.post("/api/ask", json={"question": "Hi"}).status_code == 422


@pytest.mark.parametrize(
    "exception,status", [(GuardrailError("write rejected"), 422), (LLMUnavailable("offline"), 503)]
)
def test_ask_errors(client, exception, status):
    def fail(_question):
        raise exception

    app.state.assistant = SimpleNamespace(ask=fail)
    response = client.post("/api/ask", json={"question": "Show suppliers"})
    assert response.status_code == status
    assert response.json()["detail"] == str(exception)
