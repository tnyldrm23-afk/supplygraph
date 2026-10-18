# Delivery status

Updated: 2026-10-18 (Europe/Paris). Backend baseline release: **v1.0.0**. Visual interface refinement: **1.1**.
Solo author: **Tan YILDIRIM — B00822334**. Level 2, project 3.

## Verified implementation
- Complete instructor source read; tracked roadmap and rubric-to-evidence matrix supplied.
- Real DataCo v5 source hash verified; CC BY 4.0 attribution and sanitized derivative.
- 180519 source lines, 65752 source orders, 118 products, 51 categories; 6000 sampled anonymous orders.
- All 13 facilities and 962 lanes are explicitly assumed, with visible provenance.
- Neo4j 5.26.12 and GDS 2.13.7; constraints, indexes, real betweenness/WCC.
- Four-service Compose application with responsive dashboard, product trace, analytics and assistant.
- 95 unit/API/adversarial/data tests and 10 real integration tests passed.
- Fresh isolated-volume startup passed all 10 integration tests; disposable volumes removed.
- Branch-inclusive coverage 84.69%; pylint 10.00/10; Black checks passed.
- Actual PROFILE comparison: 237 DB hits for scan vs 2 for unique seek.
- Chronological ML holdout: ROC-AUC .7104 vs .5 prior baseline; 900 test orders.
- Actual local Qwen evaluation: 6/6 expected outcomes; Turkish UI question also passed.
- Initial failed model evaluation iterations retained as evidence.
- All 9 code cells of demo.ipynb executed successfully against real API/GDS/Ollama.
- Editable draw.io + SVG schema, architecture and source ER diagrams.
- README, modeling, guardrails, simulation, operations, defense and Turkish usage guides.

## Verified public delivery
- Repository: https://github.com/tnyldrm23-afk/supplygraph
- Substantial merged implementation PR, with two explicitly labeled solo review comments:
  https://github.com/tnyldrm23-afk/supplygraph/pull/1
- Release: https://github.com/tnyldrm23-afk/supplygraph/releases/tag/v1.0.0
- Implementation commit: `5ca22493815e0a9c079bede74da536b26ac91ff9`.
- Main Quality CI succeeded: https://github.com/tnyldrm23-afk/supplygraph/actions/runs/39075935717
- Main Container CI succeeded: https://github.com/tnyldrm23-afk/supplygraph/actions/runs/39075935782
- Versioned Container CI succeeded: https://github.com/tnyldrm23-afk/supplygraph/actions/runs/39076581710
- Public package: https://github.com/tnyldrm23-afk/supplygraph/pkgs/container/supplygraph
- Multi-architecture image supports linux/amd64 and linux/arm64. Anonymous download
  used an empty Docker credential configuration. Published-image health, catalog,
  outage and actual GDS queries passed; see reports/registry-verification.json.
- Final documentation/evidence follow-up preserves the released application runtime.

Source was published through the authorized GitHub browser session. No new CLI
account grant or token was needed; no browser credentials were extracted.

## Evidence locations
`reports/verification.json`, `fresh-start.json`, `browser-qa.json`,
`registry-verification.json`, `llm-evaluation.json`, `query-benchmarks.json`,
`ml-evaluation.json`, `coverage.xml`, executed `demo.ipynb`, and screenshots.

## Interpretation limits and defense responsibility
This is a fictional distribution scenario, not a real DataCo multi-tier supplier map
or BOM/inventory model. Capacities are independent per SKU. Exposure depth bounds BFS;
flow solves the complete small network. Retailer allocation is deterministic, not
fairness optimized. ML classifies historical order lateness, not causal disruption.
Solo work and AI assistance are disclosed. Team contribution/review criteria remain
for the instructor to interpret for a solo submission; no collaborators are invented.
Tan must be able to explain the submitted choices; docs/DEFENSE.md provides practice.
No deadline was supplied. No paid API, hosting or cloud deployment is required.

## Owner-requested visual refinement
Larger readable typography, navy/blue palette, consistent vector icons, visible
mobile navigation, full-width map and mobile facility list are implemented.
Twenty application-layout checks passed across 321/376/768/1024/1440 px and all
four screens. Eight sampled text/control contrast ratios exceeded 4.5:1. Real
scenario, reserve recovery, filtering, depth, reset, keyboard selection, local
model answer and blocked-write interactions were checked. Browser report and
refreshed screenshots are tracked. Publication of this refinement is the current
final delivery step; the baseline release evidence above remains historical.
