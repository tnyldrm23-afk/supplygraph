"""Flow conservation, OR routes, capacity reduction and scenario immutability."""

from copy import deepcopy

import pytest
from app.models import Scenario
from app.simulation import SimulationEngine


def test_baseline_conserves_stock(engine):
    result = engine.simulate(Scenario(supplier_ids=["SUP-01"], reduction=0))
    assert result["totals"]["scenario_delivered"] == 12
    assert result["totals"]["service_level"] == 100
    assert result["affected_products"] == 0


def test_full_failure_and_backup(engine):
    failed = engine.simulate(Scenario(supplier_ids=["SUP-01"]))
    assert failed["totals"]["scenario_delivered"] == 0
    assert failed["totals"]["unmet_demand"] == 12
    assert failed["totals"]["restored_with_backups"] == 6
    assert failed["affected_retailers"] == 2
    assert failed["exposed_manufacturers"] == 1
    assert len(failed["alternatives"]) == 1
    recovered = engine.simulate(Scenario(supplier_ids=["SUP-01"], activate_backups=True))
    assert recovered["totals"]["scenario_delivered"] == 6
    assert recovered["totals"]["service_level"] == 50
    assert recovered["totals"]["restored_with_backups"] == 0


def test_partial_loss_and_demand_cap(engine):
    result = engine.simulate(
        Scenario(supplier_ids=["SUP-01"], reduction=0.25, activate_backups=False)
    )
    assert result["totals"]["scenario_delivered"] == 9
    assert result["totals"]["unmet_demand"] == 3
    result = engine.simulate(Scenario(supplier_ids=["SUP-01"], reduction=0, activate_backups=True))
    assert result["totals"]["scenario_delivered"] == 12  # 18 available, 12 demanded


def test_multiple_failures_cannot_restore_failed_reserve(engine):
    result = engine.simulate(Scenario(supplier_ids=["SUP-01", "SUP-02"], activate_backups=True))
    assert result["totals"]["scenario_delivered"] == 0
    assert result["totals"]["restored_with_backups"] == 0


def test_shared_downstream_bottleneck_not_double_counted(payload):
    payload["lanes"].append(
        dict(
            id="EXTRA",
            origin="SUP-02",
            destination="MFG-01",
            sku="SKU-1",
            capacity=100,
            lead_days=1,
            backup=False,
        )
    )
    payload["lanes"][2]["capacity"] = 2
    payload["lanes"][3]["capacity"] = 2
    engine = SimulationEngine(payload)
    result = engine.simulate(Scenario(supplier_ids=["SUP-01"], reduction=0))
    assert result["totals"]["scenario_delivered"] == 4  # NOT sum of source capacity


def test_cycle_safe_depth_bound_and_distinct_flow_scope(payload):
    payload["lanes"].append(
        dict(
            id="CYCLE",
            origin="RET-01",
            destination="MFG-01",
            sku="SKU-1",
            capacity=5,
            lead_days=1,
            backup=False,
        )
    )
    engine = SimulationEngine(payload)
    result = engine.simulate(Scenario(supplier_ids=["SUP-01"], depth=1))
    assert result["traversal_truncated"] is True
    assert {o["id"] for o in result["exposed_organizations"]} == {"SUP-01", "MFG-01"}
    assert result["totals"]["scenario_delivered"] == 0
    assert "flow uses" in result["evidence"]["depth_scope"]


def test_scenarios_never_mutate_source_or_baseline(payload):
    original = deepcopy(payload)
    engine = SimulationEngine(payload)
    first = engine.simulate(Scenario(supplier_ids=["SUP-01"]))
    engine.simulate(Scenario(supplier_ids=["MFG-01"], reduction=0.5, activate_backups=True))
    again = engine.simulate(Scenario(supplier_ids=["SUP-01"]))
    assert first == again
    assert payload == original


@pytest.mark.parametrize(
    "missing", [{"supplier_ids": ["SUP-99"]}, {"supplier_ids": ["SUP-01"], "sku": "SKU-999"}]
)
def test_missing_resources(engine, missing):
    with pytest.raises(KeyError):
        engine.simulate(Scenario(**missing))


def test_eta_and_no_path(engine):
    eta = engine.eta("SKU-1", "RET-01")
    assert eta["lead_days"] == 3
    assert eta["path"] == ["SUP-01", "MFG-01", "RET-01"]
    assert engine.eta("SKU-1", "RET-01", ["SUP-01"])["available"] is False
    assert engine.eta("SKU-1", "RET-01", ["SUP-01"], True)["lead_days"] == 6
    with pytest.raises(KeyError):
        engine.eta("SKU-2", "RET-01")


def test_graph_product_filter(engine):
    assert len(engine.graph()["edges"]) == 4
    assert len(engine.graph("SKU-1")["nodes"]) == 5
    assert engine.graph("SKU-999")["edges"] == []
