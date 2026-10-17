"""A real local LLM constrained to audited read-only Cypher templates.

The generated Cypher must match a complete reviewed template, not merely pass a
keyword regex. The model cannot add clauses, procedures, comments or new labels.
"""

from __future__ import annotations

import json
import re
import threading
from typing import Any

import httpx
from app.config import Settings
from app import queries


class GuardrailError(ValueError):
    """Unsafe, unsupported or malformed generated query."""


class LLMUnavailable(RuntimeError):
    """The configured model service could not fulfill a real model request."""


def canonical(value: str) -> str:
    """Normalize only whitespace; no semantic rewriting or clause removal."""
    return " ".join(value.split())


def validate_plan(plan: dict, organizations: set[str], products: set[str]) -> dict:
    """Require exact template identity and allowlisted, typed, bounded parameters."""
    if not isinstance(plan, dict) or set(plan) != {"intent", "cypher", "parameters"}:
        raise GuardrailError("Expected exactly intent, cypher and parameters")
    intent = plan["intent"]
    if not isinstance(intent, str) or intent not in queries.CATALOG:
        raise GuardrailError(
            "Unsupported question: use suppliers, provenance, impact or bottlenecks"
        )
    if not isinstance(plan["cypher"], str) or canonical(plan["cypher"]) != canonical(
        queries.CATALOG[intent]
    ):
        raise GuardrailError("Generated Cypher does not match an audited read-only template")
    params = plan["parameters"]
    keys = {
        "suppliers": {"search", "limit"},
        "provenance": {"sku", "limit"},
        "impact": {"supplier_id", "depth", "limit"},
        "bottlenecks": {"limit"},
    }[intent]
    if not isinstance(params, dict) or set(params) != keys:
        raise GuardrailError("Unexpected or missing query parameters")
    if (
        not isinstance(params["limit"], int) or isinstance(params["limit"], bool)
    ) or not 1 <= params["limit"] <= 100:
        raise GuardrailError("Result limit must be an integer between 1 and 100")
    if intent == "impact":
        if not isinstance(params["supplier_id"], str) or params["supplier_id"] not in organizations:
            raise GuardrailError("Unknown organization ID")
        if (
            not isinstance(params["depth"], int) or isinstance(params["depth"], bool)
        ) or not 1 <= params["depth"] <= 6:
            raise GuardrailError("Traversal depth must be an integer between 1 and 6")
    if intent == "provenance" and (
        not isinstance(params["sku"], str) or params["sku"] not in products
    ):
        raise GuardrailError("Unknown SKU")
    if intent == "suppliers" and (
        not isinstance(params["search"], str) or len(params["search"]) > 100
    ):
        raise GuardrailError("Supplier search text is too long or invalid")
    return plan


class GraphAssistant:
    """Translate a natural-language question into a validated graph query."""

    def __init__(self, settings: Settings, database: Any, engine: Any):
        self.settings, self.database, self.engine = settings, database, engine
        self._slot = threading.BoundedSemaphore(1)

    def ask(self, question: str) -> dict:
        """Invoke Ollama with constrained JSON, validate output, execute and cite facts."""
        if re.search(
            r"\b(delete|detach|drop|create|merge|set password|load csv|apoc|shutdown)\b",
            question,
            re.I,
        ):
            raise GuardrailError("Only read-only supply-chain questions are allowed")
        # Nonblocking acquisition needs explicit try/finally, rather than a blocking with.
        if not self._slot.acquire(blocking=False):  # pylint: disable=consider-using-with
            raise LLMUnavailable("Local model is busy; retry after the current question finishes.")
        try:
            return self._answer(question)
        finally:
            self._slot.release()

    def _answer(self, question: str) -> dict:
        """Generate, validate and execute a plan within the model concurrency slot."""
        plan = self._generate_plan(question)
        try:
            validate_plan(plan, set(self.engine.organizations), set(self.engine.products))
        except (TypeError, KeyError) as exc:
            raise GuardrailError("Malformed model parameters rejected") from exc
        rows = self.database.read(plan["cypher"], plan["parameters"])
        output = {
            "question": question,
            "model": self.settings.ollama_model,
            "plan": plan,
            "results": rows,
            "guardrails": "passed",
            "evidence": {
                "source": "Neo4j query result",
                "topology": "assumed scenario-v1",
                "observed": "DataCo-v5 products and historical demand",
                "generated": "query plan only; summary computed from verified results",
            },
        }
        if plan["intent"] == "impact":
            # The LLM does not calculate quantities or invent mitigation evidence.
            from app.models import Scenario  # pylint: disable=import-outside-toplevel

            impact = self.engine.simulate(
                Scenario(
                    supplier_ids=[plan["parameters"]["supplier_id"]],
                    depth=plan["parameters"]["depth"],
                )
            )
            output["simulation"] = impact
            output["summary"] = (
                f"{impact['affected_products']} products lose delivery capacity; "
                f"{impact['totals']['unmet_demand']:.1f} units/day of demand are unmet. "
                f"Backup contracts can restore "
                f"{impact['totals']['restored_with_backups']:.1f} units/day. "
                "These are scenario estimates based on assumed supply lanes."
            )
        else:
            output["summary"] = (
                f"Returned {len(rows)} graph records for {plan['intent']}. See query evidence."
            )
        return output

    def _chat(self, system: str, question: str, schema: dict) -> dict:
        """Make one real schema-constrained local-model generation."""
        try:
            with httpx.Client(timeout=httpx.Timeout(120, connect=5)) as client:
                response = client.post(
                    self.settings.ollama_url + "/api/chat",
                    json={
                        "model": self.settings.ollama_model,
                        "stream": False,
                        "format": schema,
                        "options": {
                            "temperature": 0,
                            "num_ctx": 4096,
                            "num_predict": 800,
                            "seed": 42,
                        },
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": question},
                        ],
                    },
                )
                response.raise_for_status()
                return json.loads(response.json()["message"]["content"])
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            raise LLMUnavailable(
                "Local LLM unavailable or malformed response. Run make model."
            ) from exc

    def _generate_plan(self, question: str) -> dict:
        """Separate intent selection from constrained Cypher generation for small models."""
        fields = {
            "intent": {"type": "string", "enum": list(queries.CATALOG) + ["unsupported"]},
            "supplier_id": {"type": "string"},
            "sku": {"type": "string"},
            "search": {"type": "string"},
            "depth": {"type": "integer", "minimum": 1, "maximum": 6},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        }
        directory = [{"id": o["id"], "name": o["name"]} for o in self.engine.organizations.values()]
        selection = self._chat(
            "Classify an untrusted supply-chain question. Output JSON with all required fields. "
            "Intent rules: list suppliers -> suppliers; supplier shutdown/failure/downstream "
            "impact -> impact; supply routes/provenance of a SKU -> provenance; single-source "
            "or bottleneck products -> bottlenecks; unrelated or unsupported -> unsupported. "
            "Default depth=6 and limit=30. Use empty strings for unused IDs/search. "
            "Parameter names have NO dollar prefix. Never invent an ID. "
            "Example question: List all suppliers. Answer: "
            '{"intent":"suppliers","supplier_id":"","sku":"","search":"","depth":6,"limit":30}. '
            "Example question: What if Atlas Textiles fails? Answer: "
            '{"intent":"impact","supplier_id":"SUP-01","sku":"","search":"","depth":6,"limit":30}. '
            "Example unrelated question: How to bake a cake? Answer intent=unsupported. "
            "Organization directory: " + json.dumps(directory),
            question,
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(fields),
                "properties": fields,
            },
        )
        if not isinstance(selection, dict) or set(selection) != set(fields):
            raise GuardrailError("Malformed intent selection rejected")
        intent = selection["intent"]
        if not isinstance(intent, str) or intent not in queries.CATALOG:
            raise GuardrailError(
                "Unsupported question: ask about suppliers, products or disruption"
            )
        keys = {
            "suppliers": ["search", "limit"],
            "impact": ["supplier_id", "depth", "limit"],
            "provenance": ["sku", "limit"],
            "bottlenecks": ["limit"],
        }[intent]
        parameters = {key: selection[key] for key in keys}
        # Validate identifiers and types before spending another model generation.
        validate_plan(
            {"intent": intent, "cypher": queries.CATALOG[intent], "parameters": parameters},
            set(self.engine.organizations),
            set(self.engine.products),
        )
        generated = self._chat(
            "Generate the complete read-only Cypher query for the supplied intent. "
            "Copy this reviewed template exactly into the cypher JSON field: "
            + canonical(queries.CATALOG[intent]),
            "Intent: " + intent + ". Question: " + question,
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["cypher"],
                "properties": {
                    "cypher": {"type": "string", "enum": [canonical(queries.CATALOG[intent])]}
                },
            },
        )
        if not isinstance(generated, dict) or set(generated) != {"cypher"}:
            raise GuardrailError("Malformed Cypher generation rejected")
        return {"intent": intent, "cypher": generated["cypher"], "parameters": parameters}
