"""Neo4j persistence, idempotent ingestion and named GDS projections."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase, unit_of_work
from app.config import Settings

CONSTRAINTS = [
    f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
    for label in ("Organization", "Product", "Category", "Location", "Lane", "Order")
]
INDEXES = [
    "CREATE INDEX organization_kind IF NOT EXISTS FOR (n:Organization) ON (n.kind)",
    "CREATE INDEX product_name IF NOT EXISTS FOR (n:Product) ON (n.name)",
    "CREATE INDEX order_date IF NOT EXISTS FOR (n:Order) ON (n.ordered_at)",
    "CREATE INDEX lane_sku IF NOT EXISTS FOR (n:Lane) ON (n.sku)",
]


class Database:
    """Own a driver with bounded reads and serialized GDS projection creation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=20,
            connection_timeout=10,
        )
        self._projection_lock = threading.Lock()

    def close(self):
        """Release the connection pool."""
        self.driver.close()

    def read(self, cypher: str, parameters: dict | None = None) -> list[dict]:
        """Execute a bounded read transaction, returning detached Python values."""
        with self.driver.session(
            database=self.settings.neo4j_database, default_access_mode="READ"
        ) as session:

            @unit_of_work(timeout=self.settings.query_timeout)
            def execute(tx):
                return tx.run(cypher, parameters or {}).data()

            return session.execute_read(execute)

    def write(self, cypher: str, parameters: dict | None = None):
        """Execute internal trusted writes; never exposed to the NL endpoint."""
        with self.driver.session(database=self.settings.neo4j_database) as session:
            session.execute_write(lambda tx: tx.run(cypher, parameters or {}).consume())

    def seed(self, payload: dict):
        """MERGE source-derived nodes and scenario nodes in deterministic batches."""
        for statement in CONSTRAINTS + INDEXES:
            self.write(statement)
        tables = {
            "Organization": "organizations",
            "Product": "products",
            "Category": "categories",
            "Location": "locations",
            "Lane": "lanes",
        }
        for label, table in tables.items():
            self.write(
                f"UNWIND $rows AS row MERGE (n:{label} {{id:row.id}}) SET n += row",
                {"rows": payload[table]},
            )
        self.write(
            """MATCH (o:Organization), (l:Location {id:o.location_id})
                       MERGE (o)-[:LOCATED_IN]->(l)"""
        )
        self.write(
            """MATCH (p:Product), (c:Category {id:p.category_id})
                       MERGE (p)-[:IN_CATEGORY]->(c)"""
        )
        self.write(
            """MATCH (l:Lane), (a:Organization {id:l.origin}),
                       (b:Organization {id:l.destination}), (p:Product {id:l.sku})
                       MERGE (l)-[:ORIGIN]->(a) MERGE (l)-[:DESTINATION]->(b)
                       MERGE (l)-[:CARRIES]->(p)"""
        )
        # FLOW is an explicit analytics projection, never a product-capacity relation.
        self.write(
            """MATCH (l:Lane)-[:ORIGIN]->(a:Organization),
                       (l)-[:DESTINATION]->(b:Organization)
                       WHERE l.backup = false
                       WITH a,b,min(l.lead_days) AS lead_days
                       MERGE (a)-[r:FLOW]->(b)
                       SET r.lead_days=lead_days, r.provenance='derived-assumed',
                           r.meaning='unweighted organization connectivity' """
        )
        for start in range(0, len(payload["orders"]), 500):
            batch = payload["orders"][start : start + 500]
            self.write(
                """UNWIND $rows AS row
                           MERGE (o:Order {id:row.id}) SET o += row.properties
                           WITH o,row MATCH (r:Organization {id:row.retailer_id})
                           MERGE (o)-[:DELIVERS_TO {provenance:'assumed'}]->(r)
                           WITH o,row UNWIND row.items AS item
                           MATCH (p:Product {id:item.sku})
                           MERGE (o)-[q:REQUESTS]->(p) SET q.quantity=item.quantity""",
                {
                    "rows": [
                        {
                            "id": o["id"],
                            "properties": {k: v for k, v in o.items() if k != "items"},
                            "retailer_id": o["retailer_id"],
                            "items": o["items"],
                        }
                        for o in batch
                    ]
                },
            )
        self.write(
            'MERGE (d:Dataset {id:"DataCo-v5"}) SET d.metadata=$metadata',
            {"metadata": json.dumps(payload["metadata"])},
        )
        self.write("CALL db.awaitIndexes(60)")

    def snapshot(self) -> dict[str, Any]:
        """Load scenario facts from Neo4j for the deterministic flow solver."""
        payload = {}
        for label, key in [
            ("Organization", "organizations"),
            ("Product", "products"),
            ("Lane", "lanes"),
            ("Location", "locations"),
            ("Category", "categories"),
        ]:
            payload[key] = [
                r["data"] for r in self.read(f"MATCH (n:{label}) RETURN properties(n) AS data")
            ]
        result = self.read('MATCH (d:Dataset {id:"DataCo-v5"}) RETURN d.metadata AS metadata')
        payload["metadata"] = json.loads(result[0]["metadata"]) if result else {}
        return payload

    def gds(self, algorithm: str, limit: int = 20) -> dict:
        """Run one of two explicit, allowlisted GDS algorithms on a named projection."""
        if algorithm not in ("betweenness", "wcc"):
            raise ValueError("Unsupported GDS algorithm")
        with self._projection_lock:
            exists = self.read('CALL gds.graph.exists("supplyflow") YIELD exists RETURN exists')[0][
                "exists"
            ]
            if not exists:
                self.read(
                    """CALL gds.graph.project('supplyflow', 'Organization',
                             {FLOW: {orientation:'NATURAL'}})
                             YIELD graphName RETURN graphName"""
                )
        if algorithm == "betweenness":
            query = """CALL gds.betweenness.stream('supplyflow', {concurrency:1})
                       YIELD nodeId, score WITH gds.util.asNode(nodeId) AS n, score
                       RETURN n.id AS id, n.name AS name, n.kind AS kind, score
                       ORDER BY score DESC, id LIMIT $limit"""
        else:
            query = """CALL gds.wcc.stream('supplyflow', {concurrency:1})
                       YIELD nodeId, componentId
                       WITH componentId, collect(gds.util.asNode(nodeId).id) AS members
                       RETURN componentId AS component_id, members, size(members) AS size
                       ORDER BY size DESC, component_id LIMIT $limit"""
        return {
            "algorithm": algorithm,
            "projection": "supplyflow",
            "orientation": "directed for betweenness; direction ignored by WCC",
            "provenance": "assumed topology, derived FLOW edges",
            "results": self.read(query, {"limit": limit}),
        }


def load_payload(path: str) -> dict:
    """Read the committed sanitized DataCo derivative."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
