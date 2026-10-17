"""Auditable, bounded Cypher queries; user text is never interpolated."""

SUPPLIERS = """
MATCH (o:Organization)
WHERE o.kind = 'supplier' AND (toLower(o.name) CONTAINS toLower($search) OR o.id = $search)
RETURN o.id AS id, o.name AS name, o.provenance AS provenance
ORDER BY o.id LIMIT $limit
"""
PROVENANCE = """
MATCH (l:Lane)-[:CARRIES]->(p:Product {id: $sku})
MATCH (l)-[:ORIGIN]->(a:Organization), (l)-[:DESTINATION]->(b:Organization)
RETURN l.id AS id, a.id AS origin, b.id AS destination, p.id AS sku,
       l.capacity AS capacity, l.lead_days AS lead_days, l.backup AS backup,
       l.provenance AS provenance
ORDER BY l.id LIMIT $limit
"""
IMPACT = """
MATCH p=(s:Organization {id: $supplier_id})-[:FLOW*1..6]->(o:Organization)
WHERE length(p) <= $depth
WITH o, min(length(p)) AS hops
RETURN o.id AS id, o.name AS name, o.kind AS kind, hops
ORDER BY hops, id LIMIT $limit
"""
BOTTLENECKS = """
MATCH (s:Organization)-[:ORIGIN]-(l:Lane)-[:CARRIES]->(p:Product)
WHERE s.kind = 'supplier' AND l.backup = false
WITH p, collect(DISTINCT s.id) AS suppliers
WHERE size(suppliers) = 1
RETURN p.id AS sku, p.name AS name, suppliers[0] AS supplier_id,
       p.daily_demand AS daily_demand
ORDER BY daily_demand DESC, sku LIMIT $limit
"""
ALTERNATIVES = """
MATCH (failed:Organization {id: $supplier_id})<-[:ORIGIN]-(current:Lane)-[:CARRIES]->(p:Product)
MATCH (alternate:Lane)-[:CARRIES]->(p), (alternate)-[:ORIGIN]->(s:Organization)
WHERE s.kind = 'supplier' AND s.id <> failed.id
MATCH (alternate)-[:DESTINATION]->(target:Organization)
RETURN DISTINCT s.id AS supplier_id, s.name AS name, p.id AS sku,
       target.id AS destination, alternate.capacity AS capacity,
       alternate.lead_days AS lead_days, alternate.backup AS backup,
       alternate.provenance AS provenance
ORDER BY sku, lead_days LIMIT $limit
"""
ORDER = """
MATCH (o:Order {id: $order_id})- [r:REQUESTS]->(p:Product)
RETURN properties(o) AS order, collect({sku: p.id, name:p.name, quantity:r.quantity}) AS items
"""
CATALOG = {
    "suppliers": SUPPLIERS,
    "provenance": PROVENANCE,
    "impact": IMPACT,
    "bottlenecks": BOTTLENECKS,
}
