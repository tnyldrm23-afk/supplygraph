"""Committed derivative provenance, identity and quantity invariants."""

from pathlib import Path
import json

DATA = Path(__file__).resolve().parents[1] / "data/processed/supplygraph.json"


def test_sanitized_source_integrity():
    """The distributable contains no customer personal fields or repeated order/SKU edges."""
    payload = json.loads(DATA.read_text())
    assert len(payload["products"]) == 118
    assert len(payload["orders"]) == 6000
    assert len({o["id"] for o in payload["orders"]}) == 6000
    for order in payload["orders"]:
        assert len({i["sku"] for i in order["items"]}) == len(order["items"])
        assert all(i["quantity"] > 0 for i in order["items"])
        assert not any("customer" in key.lower() or "password" in key.lower() for key in order)
    assert payload["orders"][0]["ordered_at"] == payload["metadata"]["period_start"]
    assert payload["orders"][-1]["ordered_at"] == payload["metadata"]["period_end"]
    for product in payload["products"]:
        assert abs(product["daily_demand"] - product["historical_units"] / 1127) < 0.000051
        assert product["provenance"] == "observed"


def test_assumed_lanes_have_valid_product_identity_and_capacity():
    """No invented real supplier relationship or dangling contractual endpoint is published."""
    payload = json.loads(DATA.read_text())
    products = {p["id"] for p in payload["products"]}
    organizations = {o["id"] for o in payload["organizations"]}
    assert len({l["id"] for l in payload["lanes"]}) == 962
    for lane in payload["lanes"]:
        assert lane["sku"] in products
        assert lane["origin"] in organizations and lane["destination"] in organizations
        assert lane["capacity"] > 0 and lane["lead_days"] > 0
        assert lane["provenance"] == "assumed"
    assert all(o["provenance"] == "assumed" for o in payload["organizations"])
