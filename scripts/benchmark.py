"""Capture actual PROFILE plans and warm latency comparisons without dropping indexes."""

import json
import statistics
import time
from pathlib import Path
from neo4j import Query
from app.config import Settings
from app.database import Database
from app import queries


def flatten(plan):
    """Detach operator measurements recursively for reproducible review."""
    if not plan:
        return []
    return [
        {
            "operator": plan["operatorType"],
            "db_hits": plan.get("dbHits", 0),
            "rows": plan.get("rows", 0),
            "arguments": plan.get("args", {}),
        }
    ] + [row for child in plan.get("children", []) for row in flatten(child)]


def main():
    """Measure non-sargable versus indexed lookups and representative graph queries."""
    settings = Settings()
    database = Database(settings)
    cases = {
        "before_non_sargable": (
            "MATCH (p:Product) WHERE toLower(p.id)=toLower($sku) RETURN p.id",
            {"sku": "SKU-1360"},
        ),
        "after_index_seek": ("MATCH (p:Product {id:$sku}) RETURN p.id", {"sku": "SKU-1360"}),
        "product_provenance": (queries.PROVENANCE, {"sku": "SKU-1360", "limit": 100}),
        "bounded_impact": (queries.IMPACT, {"supplier_id": "SUP-01", "depth": 6, "limit": 100}),
        "bottleneck_aggregation": (queries.BOTTLENECKS, {"limit": 100}),
    }
    results = {}
    try:
        with database.driver.session(database=settings.neo4j_database) as session:
            for name, (query, params) in cases.items():
                for _ in range(5):
                    session.run(Query(query, timeout=8), params).consume()
                latencies = []
                for _ in range(30):
                    begin = time.perf_counter()
                    session.run(Query(query, timeout=8), params).consume()
                    latencies.append((time.perf_counter() - begin) * 1000)
                profile = session.run("PROFILE " + query, params).consume().profile
                results[name] = {
                    "query": query,
                    "parameters": params,
                    "repetitions": 30,
                    "median_ms": round(statistics.median(latencies), 3),
                    "p95_ms": round(sorted(latencies)[28], 3),
                    "min_ms": round(min(latencies), 3),
                    "operators": flatten(profile),
                }
        report = {
            "environment": "Local Docker Neo4j 5.26.12, 118 products, 962 scenario lanes",
            "method": "5 warmups + 30 timed consumed queries; sequential; Python perf_counter",
            "caution": "Tiny catalog favors plan/DB-hit evidence; no guaranteed latency speedup claimed.",
            "results": results,
        }
        Path("reports/query-benchmarks.json").write_text(json.dumps(report, indent=2, default=str))
        print(json.dumps(report, indent=2, default=str))
    finally:
        database.close()


if __name__ == "__main__":
    main()
