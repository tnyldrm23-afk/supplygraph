# SupplyGraph delivery roadmap

Owner: Tan YILDIRIM — B00822334. Solo submission. Level 2, project 3.
Source: instructor-spec.md, retrieved 2026-10-17. Repository: https://github.com/tnyldrm23-afk/supplygraph

## Working contract
- Keep this file and STATUS.md current after each milestone and verification cycle.
- Distinguish implemented, verified, externally blocked and deliberately excluded work.
- Never claim successful Docker, GDS, LLM, CI or publication without observed evidence.
- Real DataCo observations and constructed supply-network assumptions have separate provenance.
- Preserve primary data; disruption runs are read-only, bounded scenario calculations.
- Every important modeling decision has an ADR and a defense explanation.
- No invented collaborators, commit distribution, PR reviews, performance measurements or ML scores.

## M0 — Requirements and access
- [x] Read entire instructor specification and evaluation checklist.
- [x] Record solo author identity and Level 2 selection.
- [x] Inspect empty workspace, Python, Docker and Git authentication.
- [x] Create authorized public GitHub repository.
- [x] Save instructor source, derive rubric-to-evidence matrix.
- [x] Establish authenticated browser Git publishing and reproducible local environment.

## M1 — Data audit and scope freeze
- [x] Download original DataCo v5 and dictionary; verify source SHA-256.
- [x] Profile row counts, unique identifiers, dates, nulls, inconsistent keys and duplicates.
- [x] Confirm no actual multi-tier supplier topology exists in DataCo.
- [x] Strip customer names, credentials, contact details and exact customer coordinates.
- [x] Build deterministic sanitized derived dataset with provenance and source citation.
- [x] Define explicit fictional supply network grounded in observed product/category/demand data.
- [x] Record sampling, product coverage, capacity units and assumed lead times.

## M2 — Domain model and simulation correctness
- [x] Define Organization, Product, Category, Location, Lane, Order and evidence properties.
- [x] Document nodes versus properties, lane reification, directionality and alternatives.
- [x] Model product-specific capacity and AND/OR semantics explicitly; no unsupported BOM claims.
- [x] Establish immutable scenarios, bounded depth, cycle-safe traversal, deterministic ordering.
- [x] Compute baseline versus disrupted maximum delivered flow per SKU and sink.
- [x] Report affected manufacturers/retailers/products, unmet demand, alternatives and paths.
- [x] Validate disconnected nodes, alternative routes, multiple failures, cycles and truncation.
- [x] Define ETA honestly as scenario estimate, distinct from historical actual shipping time.

## M3 — Neo4j and ingestion
- [x] Neo4j 5.x, compatible GDS, official image; persistent named volume.
- [x] At least 3 labels, 3 relationship types, 2 uniqueness constraints and useful indexes.
- [x] Idempotent batched UNWIND import with explicit source version.
- [x] Query repository with parameterized, bounded Cypher and transaction timeouts.
- [x] Real provenance, bottlenecks, reachability, alternatives and order ETA queries.
- [x] EXPLAIN/PROFILE evidence including before/after plans and measured latencies.

## M4 — API and operations
- [x] FastAPI, Pydantic request/response validation, OpenAPI /docs.
- [x] Versioned API, health/readiness, meaningful errors, pagination and limits.
- [x] At least four useful domain endpoints and three advanced graph queries.
- [x] Disruption, provenance, bottlenecks, alternatives, ETA and graph analytics.
- [x] Read-only health/diagnostic endpoints; no ingestion or mutation endpoint exposed.
- [x] Docker Compose >=3 services, health checks, dependency readiness, .env.example.
- [x] Public registry image published via GitHub Actions; anonymous pull and runtime verified.

## M5 — Graph algorithms and ML
- [x] Explicit organization FLOW projection derived only from scenario-active lanes.
- [x] GDS betweenness and WCC with documented direction and limitations.
- [x] At least two graph-algorithm API endpoints; distinguish centrality from causal impact.
- [x] Real-data order node-classification experiment with chronological order-level split.
- [x] Exclude label leakage: actual shipping duration, delivery status, late-risk flag, future dates.
- [x] Baseline comparison, metrics, split counts, class balance and limitations.
- [x] Reproducible report; no claim of industrial generalization or calibrated causal forecast.

## M6 — LLM over graph
- [x] Local Ollama model or explicitly configured provider; actual LLM invocation.
- [x] Schema-bound natural language -> structured Cypher plan -> validation -> execution.
- [x] Allowlisted read queries, bounded result sizes and timeouts; reject arbitrary writes/CALL.
- [x] Avoid regex-only security: exact query template validation and typed parameters.
- [x] Natural-language supplier failure scenario and evidence-grounded summary.
- [x] Show Cypher, parameters, graph evidence and verified/simulated status.
- [x] Evaluate successful questions, unsupported questions and malicious outputs.
- [x] Display unavailable LLM honestly; never silently substitute a fake LLM.

## M7 — Product interface
- [x] Polished responsive dashboard with coherent visual system and accessible controls.
- [x] Baseline KPIs, product filters, supplier selector and disruption severity.
- [x] Interactive graph, impact highlighting, bottleneck ranking and evidence inspector.
- [x] Baseline/scenario comparison, mitigation and ETA views.
- [x] Natural language panel showing guardrails and evidence.
- [x] Loading, errors, empty results, keyboard use and small-screen layout.
- [x] Real browser smoke test and final screenshots.

## M8 — Quality and reproducibility
- [x] Meaningful pytest unit/API/Cypher/Neo4j integration tests, >=60% coverage.
- [x] Container health checks and fresh Compose startup tested.
- [x] .pylintrc, pylint >=9.5, PEP8, docstrings and formatting.
- [x] make help/install/run/docker-run/test/lint/clean and additional data/demo commands.
- [x] Dependency locks or pinned tested dependencies; clean install validation.
- [x] GitHub Actions lint/test/integration, badges and container publishing; remote runs succeeded.
- [x] No credentials or customer personal data tracked; inspect final git diff.

## M9 — Documentation and defense
- [x] Comprehensive README: setup, ports, API examples, screenshots, limitations and data.
- [x] Graph schema, source ER model, system architecture (editable diagrams + previews).
- [x] Modeling rationale, rejected alternatives and anti-genericity appendix.
- [x] Executable demo.ipynb with exploration, graphs, requests and results.
- [x] Simulation method, complexity bounds and interpretation guide.
- [x] LLM guardrail docs and evaluation report.
- [x] Defense guide: explain every major query, index, algorithm and engineering decision.
- [x] Solo contribution statement; no fabricated team collaboration evidence.

## M10 — Release and evidence audit
- [x] Feature branch, substantial merged PR #1, two honest solo self-review comments and screenshot.
- [x] Final required Make targets pass locally; verification evidence recorded.
- [x] Final browser verification and exported screenshots.
- [x] Remote implementation tree hash checked, main CI passed and public image ran successfully.
- [x] Release tag v1.0.0 published; local application left running and healthy.
- [x] Final evidence bundle prepared for publication; release and implementation history retained.
- [x] Rubric audit distinguishes implemented, locally verified and externally pending evidence.

## Acceptance gates
1. Data gate: source verified, sanitized derivative reproducible, topology assumptions visible.
2. Correctness gate: flow impact and path evidence pass adversarial graph fixtures.
3. Runtime gate: fresh Compose, real Neo4j/GDS, real LLM and UI all exercised.
4. Quality gate: coverage >=60%, pylint >=9.5 and required make targets succeed.
5. Release gate: GitHub code + reproducible docs + registry image + honest evidence.

## Scope decisions
A product-specific distribution network, not a bill-of-materials manufacturing planner.
No live supplier feeds, commercial ETA promises, purchasing or financial transactions.
English application and delivery docs for AIDAMS; Turkish explanations for the owner.
Deterministic NetworkX algorithms may serve tests/reference comparisons, never be presented as GDS.

## M11 — Visual refinement requested by the owner
- [x] Replace the small pale typography with a readable navy/blue interface and stronger contrast.
- [x] Keep navigation labels visible on narrow screens; provide consistent native vector icons.
- [x] Separate scenario configuration, network inspection, impact and recovery into clear sections.
- [x] Give the network full content width; provide a readable facility-list alternative on mobile.
- [x] Replace internal scenario IDs in the main result with a useful quantity summary.
- [x] Verify all four screens, map/list selection, recovery, filtering and keyboard use in the browser.
- [x] Twenty layout checks across five widths; eight contrast samples passed 4.5:1; no application-body overflow.
- [ ] Refresh screenshots and owner documentation, publish through a reviewed feature PR.
- [ ] Verify final public image and leave the redesigned application running.
