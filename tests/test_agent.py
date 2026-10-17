"""Adversarial generated plans cannot escape the full-template query allowlist."""

import json
from types import SimpleNamespace

import httpx
import pytest
from app import queries
from app.agent import GraphAssistant, GuardrailError, LLMUnavailable, validate_plan
from app.config import Settings
from tests.conftest import FakeDatabase


def plan(intent="impact", **params):
    """Create an explicit test-model response."""
    defaults = {
        "impact": {"supplier_id": "SUP-01", "depth": 6, "limit": 30},
        "suppliers": {"search": "", "limit": 30},
        "provenance": {"sku": "SKU-1", "limit": 30},
        "bottlenecks": {"limit": 30},
    }
    return {
        "intent": intent,
        "cypher": queries.CATALOG[intent],
        "parameters": defaults[intent] | params,
    }


@pytest.mark.parametrize("intent", list(queries.CATALOG))
def test_audited_plans_pass(intent):
    assert validate_plan(plan(intent), {"SUP-01"}, {"SKU-1"})["intent"] == intent


@pytest.mark.parametrize(
    "suffix",
    [
        " DETACH DELETE s",
        "; MATCH (x) DELETE x",
        " // comment",
        " UNION MATCH (secret) RETURN secret",
        " CALL dbms.listConfig()",
        ' LOAD CSV FROM "https://example.org" AS line RETURN line',
    ],
)
def test_any_added_clause_is_rejected(suffix):
    value = plan()
    value["cypher"] += suffix
    with pytest.raises(GuardrailError):
        validate_plan(value, {"SUP-01"}, {"SKU-1"})


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"limit": "10"},
        {"depth": 7},
        {"depth": 0},
        {"depth": False},
        {"depth": 1.5},
        {"supplier_id": "SUP-99"},
        {"extra": "value"},
    ],
)
def test_untrusted_parameter_shape_and_bounds(params):
    with pytest.raises(GuardrailError):
        validate_plan(plan(**params), {"SUP-01"}, {"SKU-1"})


def test_wrong_intent_query_pair():
    value = plan()
    value["cypher"] = queries.SUPPLIERS
    with pytest.raises(GuardrailError):
        validate_plan(value, {"SUP-01"}, {"SKU-1"})


@pytest.mark.parametrize(
    "value", [None, [], {"intent": "other"}, {"intent": "impact", "cypher": None, "parameters": {}}]
)
def test_malformed_plan(value):
    with pytest.raises(GuardrailError):
        validate_plan(value, {"SUP-01"}, {"SKU-1"})


def test_unknown_product_and_long_search():
    for value in (plan("provenance", sku="SKU-2"), plan("suppliers", search="x" * 101)):
        with pytest.raises(GuardrailError):
            validate_plan(value, {"SUP-01"}, {"SKU-1"})


class ModelClient:
    """Test-only HTTP response; does not claim a real LLM was invoked."""

    output = None
    error = None

    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, *_args, **kwargs):
        if self.error:
            raise self.error
        schema = kwargs["json"]["format"]
        if "intent" in schema["properties"]:
            output = {
                "intent": self.output["intent"],
                "supplier_id": "",
                "sku": "",
                "search": "",
                "depth": 6,
                "limit": 30,
            }
            output.update(self.output["parameters"])
        else:
            output = {"cypher": self.output["cypher"]}
        return SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: {"message": {"content": json.dumps(output)}}
        )


@pytest.mark.parametrize("intent", list(queries.CATALOG))
def test_assistant_execution_and_evidence(engine, monkeypatch, intent):
    monkeypatch.setattr(httpx, "Client", ModelClient)
    monkeypatch.setattr(ModelClient, "output", plan(intent))
    database = FakeDatabase(engine)
    assistant = GraphAssistant(Settings(_env_file=None), database, engine)
    result = assistant.ask("Which supply chain records are relevant?")
    assert result["guardrails"] == "passed"
    assert database.calls[-1][0] == queries.CATALOG[intent]
    assert "assumed" in result["evidence"]["topology"]
    if intent == "impact":
        assert result["simulation"]["affected_products"] == 1


def test_model_unavailable_no_fake_answer(engine, monkeypatch):
    monkeypatch.setattr(httpx, "Client", ModelClient)
    monkeypatch.setattr(ModelClient, "error", httpx.ConnectError("offline"))
    with pytest.raises(LLMUnavailable):
        GraphAssistant(Settings(_env_file=None), FakeDatabase(engine), engine).ask(
            "Show all suppliers"
        )


def test_write_rejected_before_model_or_db(engine):
    database = FakeDatabase(engine)
    with pytest.raises(GuardrailError):
        GraphAssistant(Settings(_env_file=None), database, engine).ask("Delete all suppliers")
    assert not database.calls


def test_model_concurrency_bound(engine):
    assistant = GraphAssistant(Settings(_env_file=None), FakeDatabase(engine), engine)
    assistant._slot.acquire()
    try:
        with pytest.raises(LLMUnavailable, match="busy"):
            assistant.ask("List all suppliers")
    finally:
        assistant._slot.release()


@pytest.mark.parametrize(
    "output",
    [
        None,
        {},
        {
            "intent": "unsupported",
            "supplier_id": "",
            "sku": "",
            "search": "",
            "depth": 6,
            "limit": 30,
        },
    ],
)
def test_malformed_or_unsupported_selection(engine, monkeypatch, output):
    assistant = GraphAssistant(Settings(_env_file=None), FakeDatabase(engine), engine)
    monkeypatch.setattr(assistant, "_chat", lambda *args: output)
    with pytest.raises(GuardrailError):
        assistant.ask("A question that should not execute")
    assert not assistant.database.calls


def test_malformed_generated_query(engine, monkeypatch):
    assistant = GraphAssistant(Settings(_env_file=None), FakeDatabase(engine), engine)
    outputs = iter(
        [
            {
                "intent": "suppliers",
                "supplier_id": "",
                "sku": "",
                "search": "",
                "depth": 6,
                "limit": 30,
            },
            {},
        ]
    )
    monkeypatch.setattr(assistant, "_chat", lambda *args: next(outputs))
    with pytest.raises(GuardrailError):
        assistant.ask("List all suppliers")
    assert not assistant.database.calls


@pytest.mark.parametrize(
    "key,value", [("supplier_id", []), ("supplier_id", {}), ("supplier_id", 2)]
)
def test_invalid_identifier_types_are_rejected(key, value):
    with pytest.raises(GuardrailError):
        validate_plan(plan(**{key: value}), {"SUP-01"}, {"SKU-1"})
