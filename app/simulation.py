"""Deterministic product-specific flow simulation over explicitly assumed lanes.

Stock is conserved by maximum flow, retailer demand is capped, and backup capacity
is activated only when requested. This is a distribution model, not a BOM model.
"""

from __future__ import annotations

from collections import deque
import hashlib
import json
from typing import Any

import networkx as nx
from app.models import Scenario

EPSILON = 1e-6
SOURCE = "__source__"
SINK = "__sink__"


class SimulationEngine:
    """Immutable snapshot with bounded graph work and reproducible scenarios."""

    def __init__(self, payload: dict):
        self.products = {p["id"]: p for p in payload["products"]}
        self.organizations = {o["id"]: o for o in payload["organizations"]}
        self.lanes = sorted(payload["lanes"], key=lambda lane: lane["id"])
        self.locations = {loc["id"]: loc for loc in payload.get("locations", [])}
        self.metadata = payload.get("metadata", {})
        self._by_sku: dict[str, list] = {}
        for lane in self.lanes:
            self._by_sku.setdefault(lane["sku"], []).append(lane)
        self._baseline = {sku: self._flow(sku, (), 0, False) for sku in self.products}

    @property
    def baseline_delivery(self) -> float:
        """Total baseline units/day, exposed without leaking the mutable cache."""
        return sum(row["delivered"] for row in self._baseline.values())

    def _network(
        self, sku: str, failures: tuple | list, reduction: float, backups: bool
    ) -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_nodes_from(self.organizations)
        demand = self.products[sku]["daily_demand"]
        for lane in self._by_sku.get(sku, []):
            if lane["backup"] and not backups:
                continue
            capacity = lane["capacity"]
            if lane["origin"] in failures or lane["destination"] in failures:
                capacity *= 1 - reduction
            if capacity <= EPSILON:
                continue
            a, b = lane["origin"], lane["destination"]
            previous = graph.get_edge_data(a, b, default={})
            graph.add_edge(
                a,
                b,
                capacity=capacity + previous.get("capacity", 0),
                lead_days=min(lane["lead_days"], previous.get("lead_days", float("inf"))),
            )
        graph.add_nodes_from([SOURCE, SINK])
        retailers = sorted(oid for oid, o in self.organizations.items() if o["kind"] == "retailer")
        for oid, org in self.organizations.items():
            if org["kind"] == "supplier":
                capacity = sum(e["capacity"] for _, _, e in graph.out_edges(oid, data=True))
                graph.add_edge(SOURCE, oid, capacity=capacity, lead_days=0)
        for oid in retailers:
            graph.add_edge(oid, SINK, capacity=demand / len(retailers), lead_days=0)
        return graph

    def _flow(self, sku: str, failures: tuple | list, reduction: float, backups: bool) -> dict:
        graph = self._network(sku, failures, reduction, backups)
        value, flow = nx.maximum_flow(
            graph, SOURCE, SINK, flow_func=nx.algorithms.flow.edmonds_karp
        )
        retailers = {
            oid: flow[oid].get(SINK, 0)
            for oid, o in self.organizations.items()
            if o["kind"] == "retailer"
        }
        return {"delivered": value, "retailers": retailers}

    def _exposure(self, failures: list[str], depth: int, sku: str | None) -> tuple[dict, bool]:
        edges: dict[str, set] = {}
        for lane in self.lanes:
            if (sku and lane["sku"] != sku) or lane["backup"]:
                continue
            edges.setdefault(lane["origin"], set()).add(lane["destination"])
        distances = dict.fromkeys(failures, 0)
        queue = deque(failures)
        truncated = False
        while queue:
            origin = queue.popleft()
            for target in sorted(edges.get(origin, ())):
                if distances[origin] >= depth:
                    truncated = truncated or target not in distances
                elif target not in distances:
                    distances[target] = distances[origin] + 1
                    queue.append(target)
        return distances, truncated

    def simulate(self, scenario: Scenario) -> dict[str, Any]:
        """Compare demand-constrained baseline and disrupted flows without writes."""
        missing = set(scenario.supplier_ids) - self.organizations.keys()
        if missing:
            raise KeyError("Unknown organizations: " + ", ".join(sorted(missing)))
        if scenario.sku and scenario.sku not in self.products:
            raise KeyError("Unknown SKU: " + scenario.sku)
        exposed, truncated = self._exposure(scenario.supplier_ids, scenario.depth, scenario.sku)
        skus = [scenario.sku] if scenario.sku else sorted(self.products)
        rows, alternatives = [], []
        totals = {
            "demand": 0.0,
            "baseline_delivered": 0.0,
            "scenario_delivered": 0.0,
            "restored_with_backups": 0.0,
            "unmet_demand": 0.0,
        }
        retailer_losses = dict.fromkeys(
            (i for i, o in self.organizations.items() if o["kind"] == "retailer"), 0.0
        )
        for sku in skus:
            product = self.products[sku]
            baseline = self._baseline[sku]
            current = self._flow(
                sku, scenario.supplier_ids, scenario.reduction, scenario.activate_backups
            )
            recovery = self._flow(sku, scenario.supplier_ids, scenario.reduction, True)
            demand = product["daily_demand"]
            loss = max(0.0, baseline["delivered"] - current["delivered"])
            additional = max(0.0, recovery["delivered"] - current["delivered"])
            totals["demand"] += demand
            totals["baseline_delivered"] += baseline["delivered"]
            totals["scenario_delivered"] += current["delivered"]
            totals["restored_with_backups"] += additional
            totals["unmet_demand"] += max(0.0, demand - current["delivered"])
            for retailer in retailer_losses:
                retailer_losses[retailer] += max(
                    0, baseline["retailers"][retailer] - current["retailers"][retailer]
                )
            rows.append(
                {
                    "sku": sku,
                    "name": product["name"],
                    "demand": round(demand, 3),
                    "baseline_delivered": round(baseline["delivered"], 3),
                    "scenario_delivered": round(current["delivered"], 3),
                    "lost_units": round(loss, 3),
                    "recoverable_units": round(additional, 3),
                    "recovery_delivered": round(recovery["delivered"], 3),
                    "status": "disrupted" if loss > EPSILON else "stable",
                }
            )
            if loss > EPSILON:
                for lane in self._by_sku[sku]:
                    if lane["backup"] and lane["origin"] not in scenario.supplier_ids:
                        alternatives.append(
                            {
                                **lane,
                                "supplier_name": self.organizations[lane["origin"]]["name"],
                                "note": (
                                    "Candidate capacity; shared recovery solved jointly " "per SKU."
                                ),
                            }
                        )
        rows.sort(key=lambda row: (-row["lost_units"], row["sku"]))
        totals = {key: round(value, 3) for key, value in totals.items()}
        totals["service_level"] = (
            round(totals["scenario_delivered"] / totals["demand"] * 100, 2)
            if totals["demand"]
            else 100
        )
        totals["baseline_service_level"] = (
            round(totals["baseline_delivered"] / totals["demand"] * 100, 2)
            if totals["demand"]
            else 100
        )
        canonical = json.dumps(scenario.model_dump(), sort_keys=True)
        return {
            "scenario_id": hashlib.sha256(canonical.encode()).hexdigest()[:12],
            "scenario": scenario.model_dump(),
            "totals": totals,
            "affected_products": sum(row["lost_units"] > EPSILON for row in rows),
            "exposed_manufacturers": sum(
                self.organizations[oid]["kind"] == "manufacturer" for oid in exposed
            ),
            "affected_retailers": sum(loss > EPSILON for loss in retailer_losses.values()),
            "retailer_losses": {key: round(value, 3) for key, value in retailer_losses.items()},
            "exposed_organizations": [
                {**self.organizations[oid], "hops": hops}
                for oid, hops in sorted(exposed.items(), key=lambda item: (item[1], item[0]))
            ],
            "products": rows,
            "alternatives": alternatives,
            "traversal_truncated": truncated,
            "evidence": {
                "observations": "DataCo-v5 product catalog and historical daily demand",
                "assumptions": (
                    "scenario-v1 topology, capacities, lead times and equal retailer "
                    "demand shares"
                ),
                "method": (
                    "per-SKU capacitated maximum flow, Edmonds–Karp; no "
                    "inventory/BOM/substitution"
                ),
                "units": "units/day",
                "depth_scope": (
                    "bounds exposure BFS only; flow uses the complete 13-organization " "scenario"
                ),
                "uncertainty": "Scenario estimate, not a prediction of actual DataCo operations.",
                "allocation": (
                    "retailer flow allocation is deterministic but not a fairness " "optimization"
                ),
            },
        }

    def eta(
        self, sku: str, retailer: str, failures: list[str] | None = None, backups: bool = False
    ) -> dict:
        """Shortest feasible lane lead time; a lower bound, not promised delivery."""
        if sku not in self.products or retailer not in self.organizations:
            raise KeyError("Unknown SKU or retailer")
        graph = self._network(sku, failures or [], 1.0, backups)
        try:
            path = nx.shortest_path(graph, SOURCE, retailer, weight="lead_days")
        except nx.NetworkXNoPath:
            return {
                "sku": sku,
                "available": False,
                "lead_days": None,
                "path": [],
                "provenance": "assumed",
                "method": "no active supply path",
            }
        lead = sum(graph[a][b]["lead_days"] for a, b in zip(path, path[1:]))
        return {
            "sku": sku,
            "available": True,
            "lead_days": lead,
            "path": path[1:],
            "provenance": "assumed",
            "method": (
                "Dijkstra on active positive-capacity lanes; excludes queue, stock"
                " and calendar effects"
            ),
        }

    def graph(self, sku: str | None = None) -> dict:
        """Expose small aggregate graph with product-aware inspectable lane facts."""
        selected = [lane for lane in self.lanes if not sku or lane["sku"] == sku]
        groups: dict[tuple, list] = {}
        for lane in selected:
            groups.setdefault((lane["origin"], lane["destination"], lane["backup"]), []).append(
                lane
            )
        edges = [
            {
                "origin": key[0],
                "destination": key[1],
                "backup": key[2],
                "product_count": len({x["sku"] for x in values}),
                "lane_count": len(values),
                "min_lead_days": min(x["lead_days"] for x in values),
                "provenance": "assumed",
            }
            for key, values in groups.items()
        ]
        return {
            "nodes": list(self.organizations.values()),
            "edges": edges,
            "locations": list(self.locations.values()),
            "sku": sku,
            "warning": "All organization connections are constructed scenario assumptions.",
        }
