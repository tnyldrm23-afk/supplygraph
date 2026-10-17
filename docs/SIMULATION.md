# Simulation contract

## Units and assumptions
Every product has an observed historical average demand `d` in units/day. Each of
three fictional retailers requests `d/3`. Lane capacity is independent per SKU,
rounded to six decimals. Scenario capacities scale by documented fixed factors of
that demand; organization locations, leads and reserves are assumed, not observed.
There is no inventory, stockpiling, production BOM, price optimization, queue,
calendar or shared cross-product factory capacity.

## Failure mechanics
A Scenario contains 1–5 known facility IDs, a reduction from 0 to 1, exposure depth
1–6, optional SKU and optional reserve activation. A failed facility's incident
lanes have capacity multiplied by `(1-reduction)` exactly once, even when both
endpoints are failed. A complete failure removes those lanes from calculation.
All calculations use fresh local graphs; Neo4j source facts are never removed.

For each SKU, connect a super-source to supplier-role facilities. Its outgoing
capacity is the sum of that supplier's available SKU lanes, ensuring no new stock
is created. Connect each retailer to a super-sink with capacity `d/3`.
Edmonds–Karp maximum flow computes delivered units/day. Conservation prevents
branching paths from duplicating stock; sink caps prevent over-delivery.

Compare:
- **Baseline:** all primary facilities operational, reserve lanes inactive.
- **Scenario:** selected capacity reductions, reserve status as requested.
- **Recovery:** same reductions with all reserve lanes active.

Lost units = `max(0, baseline delivered - scenario delivered)`.
Unmet demand = `max(0, demand - scenario delivered)`.
Recoverable units = `max(0, recovery delivered - scenario delivered)`.
These can differ if a baseline already contains a shortage. No benefit from a
reserve is counted twice or as additional recovery when already active.

Product loss and total service level are primary metrics. Retailer flow allocation
is deterministic, not a fairness or proportional-rationing optimization; multiple
equally optimal maximum-flow allocations can exist. Per-retailer losses should be
read with that limitation. Exposed manufacturer counts are connectivity measures,
not empirically measured manufacturer production losses.

## Bounded traversal and complexity
Exposure uses breadth-first search over **primary organization connectivity**, with
a visited set and depth <=6. Cycles terminate; branching does not enumerate every
possible path. A truncation flag says that the report stopped before all reachable
facilities were shown. This depth bounds exposure reporting only: the end-to-end
flow solver always uses the complete fixed 13-organization scenario. This avoids
incorrectly declaring a distant retailer safe merely because the UI depth is 1.

For a product graph with V nodes and E arcs, Edmonds–Karp is O(V E²). We solve the
baseline once at startup and at most two flows per selected product per scenario.
The current model has 118 SKUs, 13 facilities and at most ten lanes per product;
request work is therefore bounded. A process-local semaphore allows two concurrent
API scenarios (single Uvicorn worker); excess requests receive 429. Moving to a
large production network requires persisted jobs, server-side quotas and tighter
product scoping. The API does not accept user-supplied arbitrary network topology.

## ETA
Dijkstra finds the minimum sum of assumed lane lead days from any active supplier
to the assigned retailer, using only positive-capacity lanes. It is a transit lower
bound, not an order-quantity feasibility check or a dated delivery promise. Orders'
historical actual shipping durations are observed and displayed separately. No
active path returns `available:false`, never a fabricated date.

## GDS interpretation
Directed betweenness ranks bridges in the primary FLOW projection. WCC identifies
weakly connected components, ignoring direction. Both run in Neo4j GDS, not a
Python substitute. Reserve-only facilities may be isolated. Structural bridge
scores are not product loss predictions; product-specific flow simulation provides
the operational scenario quantities.
