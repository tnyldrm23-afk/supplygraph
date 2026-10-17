# Defense guide — Tan YILDIRIM, B00822334

## Demonstration order (about 10 minutes)
1. `make help`, `make lint`, `make test`, `make docker-run`.
2. Show four healthy containers (`docker compose ps`), Nginx app and `/docs`.
3. Show the graph schema and original source ER model. Explain why suppliers are
   fictional while products/order facts are real, with visible provenance.
4. Run Atlas Textiles full outage; compare reserve activation. Explain stock
   conservation, equal retailer demand caps and residual shortage.
5. Filter to a product and inspect its Lane records, capacity and lead times.
6. Show bounded Cypher impact paths, shared-product alternative supplier pattern,
   and bottleneck aggregation. Distinguish exposure from computed capacity loss.
7. Show GDS betweenness and WCC. Reserve-only nodes may be disconnected by design.
8. Show an order's actual historical shipping days beside its assumed route lower bound.
9. Ask a natural-language supply question; inspect model-generated Cypher and real
   graph evidence. Submit a write request and show rejection before execution.
10. Show held-out ML metrics, before/after PROFILE operators, test report, Makefile,
    contribution history and substantial PR. Explain solo self-review honestly.

## Questions to be ready for

**Why Neo4j instead of just SQL?**
Relationships are first-class; bounded multi-hop exposure and shared-product
supplier patterns are natural traversals. SQL can represent this graph with joins
and recursive CTEs; we do not claim relational modeling is impossible. The project
compares a source order-line ER model with the traversal-oriented graph model.

**Why does a lane deserve a node?**
A stable per-product contract identity needs SKU, capacity, lead time, backup status
and provenance. A generic company-to-company edge with product arrays obscures
independent capacities and is harder to constrain and inspect.

**How does failure propagate?**
Primary connectivity supplies bounded BFS exposure. Actual quantity loss is a
separate per-SKU maximum-flow comparison after scaling incident capacities. Merely
being reachable does not imply a shortage if another route supplies enough stock.

**Why not remove nodes from Neo4j?**
Scenarios must be reversible, comparable and concurrent. Mutating shared facts
would corrupt the baseline and cause cross-user race conditions. The snapshot is
immutable; each solver graph is local to the request.

**Why maximum flow instead of shortest path?**
Shortest path selects a route, not a feasible distribution of shared supply across
several demand sinks. Maximum flow conserves units and respects all lane and retailer
caps. Dijkstra is appropriate for a different question: minimum assumed transit.

**What are the computational limits?**
BFS is O(V+E), visited-set cycle-safe, capped at six exposure hops. Edmonds–Karp is
O(VE²) per SKU. The fixed scenario has thirteen facilities and at most ten SKU lanes;
118 SKUs are bounded and two concurrent API scenarios are allowed. Cypher uses
indexed starting IDs, fixed 1..6 traversal bounds, LIMIT and transaction timeouts.
Depth limits exposure reporting only, not global end-to-end flow.

**What does GDS betweenness mean here?**
Unweighted directed primary organization FLOW shortest-path bridge counts. A bridge
need not carry much product volume, so centrality is not loss or risk probability.
WCC ignores direction and reveals primary-network connectivity and isolates.

**What makes the LLM safe?**
A real local model first selects intent/parameters, then emits only that reviewed
Cypher template. Every generated query is compared against the complete audited
string; typed bounded parameters and known identifiers are checked before reads.
The regex denylist is not the security boundary. No arbitrary CALL/UNION/write can
be appended. Community edition is not falsely described as enforcing Enterprise RBAC.

**Can the LLM still be wrong?**
Yes. It may misunderstand intent, choose the wrong valid SKU or emit malformed
output. Structured constraints reduce the surface, and invalid output is rejected.
Small actual-model evaluations and adversarial tests document practical limits.
Observed results, assumed relationships and generated plans remain distinct.

**Does ML predict disruptions?**
No. It classifies historical late-delivery Order nodes using booking-time features.
Train/validation/test are chronological order-level partitions. Actual shipment
outcomes and assumed graph relations are excluded. Held-out ROC-AUC is 0.7104;
results are not a causal disruption model or calibrated industrial forecast.

**Where is the index evidence?**
`reports/query-benchmarks.json`: toLower(id) scan versus parameterized unique-ID
lookup. Inspect the complete PROFILE operators and DB hits (237 vs 2) alongside
thirty-run latency measurements. Small local timings are not universal guarantees.

**What did AI assistance contribute?**
Implementation assistance, debugging and documentation, disclosed openly. The author
must understand the final design and its counterexamples. The anti-genericity appendix
shows deliberate choices, not a claim that every generated schema is acceptable.

## Practical troubleshooting
- API unavailable: `docker compose ps` then `docker compose logs --tail=100 api neo4j`.
- First empty database: wait for idempotent ingestion and health checks.
- Model missing: `make model`; assistant status must report ready before demonstrating.
- Changed source data: `make data`, `make seed`, `docker compose restart api`.
- Changed topology: drop only the `supplyflow` GDS projection and rebuild it; do not
  delete source data as a routine troubleshooting step.
- Credentials: inspect your own local `.env`; never paste it into chat, commits or screenshots.
