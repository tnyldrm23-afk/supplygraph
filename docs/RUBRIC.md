# Instructor rubric → implementation and evidence

Source: [GraphDB Projects Specification — AIDAMS 3A](https://gist.github.com/bdallard/2ada69b40c3abfe3a7b3f6ed402b4b51#file-projects_spec-md).
Project 3, Supply Chain Resilience & Impact Simulator, Level 2.
No self-assigned grade is claimed. Published checks and instructor judgment remain separate.

| Criterion | Points | Implementation / verification evidence |
|---|---:|---|
| Compose >=3 services | 2 | Four services in docker-compose.yml: Neo4j, API, Nginx, Ollama |
| Dockerfiles / official images | 2 | Non-root API Dockerfile; official supporting images |
| Environment examples / no secrets | 2 | .env.example, random local setup, Git/Docker ignore rules |
| Public registry image | 2 | Public multi-architecture GHCR image; reports/registry-verification.json proves anonymous pull and real-service smoke test |
| Clean Compose startup | 1 | make docker-run with readiness wait; container health records |
| >=3 labels / relation types | 3 | Organization, Lane, Product, Order, Category, Location; eight domain/derived relation types |
| >=2 constraints | 2 | Six unique-ID constraints in app/database.py |
| Appropriate indexes | 2 | Identity constraints + kind, date, name, SKU indexes; PROFILE notes unused/non-sargable cases |
| Dataset ingestion | 2 | scripts/download_data.py, prepare_data.py, seed_data.py; batched UNWIND/MERGE |
| Documented dataset source | 1 | DATA_LICENSE.md, source hash, reports/data-audit.json |
| >=4 endpoints / >=3 advanced queries | 2 | Provenance joins, bounded exposure paths, aggregation, shared-product alternatives; 15 API routes |
| Pydantic validation | 2 | Scenario/Question/Envelope/Health schemas + query bounds |
| Swagger /docs | 1 | Actual FastAPI OpenAPI, direct and proxied Swagger |
| Error handling | 1 | 404/422/429/503 contracts and API tests |
| Graph/pathfinding >=2 endpoints | 4 | Supplier impact (flow + path evidence), order ETA (Dijkstra), GDS algorithm endpoints |
| Complex graph patterns | 3 | Lane/product/origin/destination joins, common-product alternate supplier pattern |
| WITH / UNWIND / aggregation / subqueries | 2 | Import UNWIND; impact min(length); collect/size bottlenecks; documented query plans |
| Optimization / benchmarks | 5 | reports/query-benchmarks.json, actual PROFILE operators, 5 warmups + 30 consumed measurements |
| GDS projection + >=2 algorithms | 2 | supplyflow projection; real betweenness + WCC; integration tests |
| ML workflow | 3 | Order node classification, chronological holdout, prior baseline, reports/ml-evaluation.json |
| NL-to-Cypher / agent | 4 | Actual local Qwen via Ollama, two-stage constrained query generation, structured graph evidence |
| LLM guardrails and reliability | 4 | Full query allowlist, typed params, ID/depth/limit/timeout checks; adversarial + actual model evaluation |
| Neo4j diagram | 2 | docs/diagrams/schema.drawio + SVG |
| System architecture diagram | 2 | docs/diagrams/architecture.drawio + SVG, service ports/data flows |
| Modeling / anti-genericity | 3 | docs/MODELING.md and source-er.drawio |
| README + screenshots | 3 | Root README; docs/screenshots/ contains actual browser captures |
| Demonstration notebook | 2 | demo.ipynb; make demo executes real API/GDS/model examples |
| .pylintrc / pylint >=9.5 / make lint | 2 | Versioned rules, release verification report; no broad warning suppression |
| PEP8 / clean structure | 1 | Black-formatted Python; API, persistence, solver and agent separated |
| Docstrings | 1 | Public modules, classes and functions documented |
| Make targets | 1 | help/install/run/docker-run/test/lint/clean and domain verification tools |
| Functional targets | 1 | Release gate runs required commands |
| Make usage documented | 1 | README and make help |
| Unit/API/Neo4j tests | 3 | tests/test_simulation.py, test_api.py, test_agent.py, test_integration.py |
| Container health tests | 2 | Four Compose health checks + real API/database connectivity |
| Cypher tests | 2 | Five actual graph queries in integration suite; unit contracts explicitly use labeled doubles |
| >=60% coverage | 2 | make test fail-under=60; reports/coverage.xml and final verification |
| All tests pass | 1 | Final local results in reports/verification.json; remote CI tracked separately |
| Lint workflow | 1 | .github/workflows/quality.yml |
| Test / coverage workflow | 1 | Unit/API job + real Docker integration job; coverage artifact |
| README badges | 1 | Quality, container and labeled local-coverage badges |
| Code reviews, >=2 comments per PR | 1 | Two constructive, explicitly labeled solo self-review comments on merged PR #1; docs/SELF_REVIEW.md |
| Reverse proxy or auth | 3 | Nginx reverse proxy, headers, CSP and loopback binding |
| EXPLAIN/PROFILE | 2 | Captured PROFILE operators show scan → unique seek |
| Branch workflow | 2 | main + feat/supplygraph; substantial PR and recorded self-review |
| .gitignore | 1 | Raw files, .env, virtualenv, caches excluded |
| Balanced team contributions | 3 | Solo author; team distribution requirement needs instructor interpretation, not fake collaborators |
| >=1 substantial merged PR/member | 3 | One real author; substantial merged PR #1: https://github.com/tnyldrm23-afk/supplygraph/pull/1 |
| Clear commits | 1 | Conventional prefixes and milestone commits |

## Level 2-specific choices
NL-to-Cypher is sufficient according to the instructor's common Levels 1–2 section.
The supplier-scenario assistant executes graph queries and produces a deterministic
evidence-grounded summary without claiming a Level 3 LangGraph autonomous agent.
The shared rubric also allocates ML points; a small real-data node-classification
experiment is included even though the core project remains Level 2.

## Honest exclusions and external gates
No team members or peer reviews are invented for this solo submission. Registry
publication and anonymous download, remote quality/container CI, merged PR #1 and
release v1.0.0 were observed; links are recorded in reports/verification.json. The live model evaluation separately records initial failed design
iterations and final outcomes. Check STATUS.md and verification.json for current gates.
