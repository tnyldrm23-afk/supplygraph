# Solo implementation review

Author: Tan YILDIRIM — B00822334. AI-assisted implementation and verification.
This is a documented self-review, not an independent teammate review.
The final GitHub PR should link this review and the verification evidence.

## Comment 1 — Preserve quantity across repeated order/SKU lines
**Finding:** Source order IDs repeat and distinct line IDs can share the same SKU.
A MERGE of REQUESTS followed by `SET quantity=line.quantity` would silently retain
only the last line quantity. In the selected source sample, 1644 orders initially
had repeated SKU lines before aggregation.

**Requested change:** Aggregate quantity by `(order_id, sku)` before persistence.
Use the same aggregated facts in ML features and the notebook; retain original
source line counts separately in the audit.

**Resolution:** prepare_data sums quantities with Counter; the derivative has one
item per SKU per order. Data invariant tests verify uniqueness and positive totals.
The original 180519 lines remain the input to historical product-demand aggregation.

## Comment 2 — Do not confuse reachable exposure with lost supply
**Finding:** Removing a supplier can leave an alternative route. Pure reachability
propagation would label every downstream product unavailable, while summing every
alternative path would duplicate shared stock or overfill retailer demand.

**Requested change:** Separate BFS exposure from per-SKU capacitated maximum-flow
loss. Demand-cap the retailer sinks and compute recovery jointly on the network.

**Resolution:** SimulationEngine conserves flow and compares baseline/scenario/
recovery. Counterexample fixtures cover shared downstream bottlenecks, surplus
source capacity, partial loss, reserve activation, simultaneous failures and cycles.
Depth explicitly bounds exposure only; complete small-network flows are still solved.

## Comment 3 — Model constraints must be enforced after generation
**Finding:** The first small-model design emitted mismatched or empty Cypher. A
second iteration exposed a multiline enum/JSON control-character issue in the local
model service. Treating either as a successful model response would be misleading.

**Requested change:** Retain strict validation, reduce ambiguity, constrain the
actual generated query and keep failed evaluation evidence.

**Resolution:** Two actual model calls separate intent/parameters from canonical
single-line Cypher generation. Exact intent/template identity and typed parameters
are still checked. Initial and intermediate reports are preserved; final actual
model evaluation records 6/6 expected outcomes. No malformed plan is executed.

## Comment 4 — Verify health, not just process existence
**Finding:** Nginx served the UI correctly, but BusyBox wget resolved `localhost` to
IPv6 while Nginx listened on IPv4, making the container unhealthy. Merely checking
`docker compose ps` exit status would have missed the issue.

**Requested change:** Use an explicit IPv4 health URL and assert each required
service's actual State and Health fields. Test proxied Swagger and API as well as
the direct API port.

**Resolution:** Compose health uses 127.0.0.1. check_containers validates all four
services are running and healthy. Integration tests now cover Nginx, proxy health,
static assets and proxied Swagger CSP. The final clean-start check is recorded.
