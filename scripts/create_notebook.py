"""Author an executable defense notebook, with actual API and graph evidence."""

from pathlib import Path
import nbformat as nbf

nb = nbf.v4.new_notebook()
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
nb.cells = [
    md(
        """# SupplyGraph — resilience through connected thinking
**Tan YILDIRIM · B00822334 · AIDAMS · Level 2**

Run `make docker-run`, `make model`, `make ml` and `make benchmark`, then `make demo`.
The notebook uses the actual local FastAPI/Neo4j/GDS services. No fixture is substituted.

Observed: DataCo v5 product/order facts. Assumed: all companies, lanes, capacities,
lead times and retailer assignments. These scenarios do not reconstruct DataCo's real suppliers."""
    ),
    code(
        """import json, os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd()/".cache/matplotlib"))
import httpx
import matplotlib.pyplot as plt
import networkx as nx
from IPython.display import display, Markdown
client = httpx.Client(base_url="http://localhost:8000", timeout=240)
def get(path):
    response = client.get(path)
    response.raise_for_status()
    return response.json().get("data", response.json())
health = get("/api/health")
assert health["database"] == "connected" and health["gds"]
health"""
    ),
    md(
        """## 1. Source audit and graph inventory
The original CSV is verified by SHA-256. All source products/categories are retained,
while 6000 anonymous orders are selected at evenly spaced chronological indices.
Repeated order/SKU lines are aggregated so REQUESTS quantities are not overwritten."""
    ),
    code(
        """overview = get("/api/overview")
audit = json.loads(Path("reports/data-audit.json").read_text())
{key: audit[key] for key in ["source_rows", "unique_orders", "unique_products", "unique_categories", "selected_orders", "license", "sampling"]}"""
    ),
    md(
        """## 2. Explore the assumed primary network
This plot is an actual API graph, but the topology itself is a constructed scenario.
Reserve-only facilities can be isolated in the primary-lane projection."""
    ),
    code(
        """graph = get("/api/graph")
g = nx.DiGraph()
kinds = {"supplier":0,"manufacturer":1,"distributor":2,"retailer":3}
for node in graph["nodes"]:
    g.add_node(node["id"], name=node["name"], kind=node["kind"])
for edge in graph["edges"]:
    if not edge["backup"]:
        g.add_edge(edge["origin"], edge["destination"])
pos = {}
for kind,col in kinds.items():
    members = [n for n,d in g.nodes(data=True) if d["kind"]==kind]
    for row,node in enumerate(members): pos[node]=(col,-row)
plt.figure(figsize=(13,5))
nx.draw_networkx(g,pos,labels={n:d["name"] for n,d in g.nodes(data=True)},node_size=2700,
                 node_color=["#d9edbd","#e7eddd","#f5e6cf","#e2ebec"][0],font_size=8,
                 edge_color="#9bad8e",arrows=True,node_shape="s")
plt.title("Primary organization connectivity — all edges assumed")
plt.axis("off"); plt.tight_layout(); plt.show()"""
    ),
    md(
        """## 3. Failure, recovery and stock conservation
Maximum flow is computed separately per SKU. Super-sink retailer capacities cap
fulfillment; flow conservation prevents branching routes from multiplying stock.
The depth setting bounds exposure reporting, while flows use the complete small network."""
    ),
    code(
        """scenarios = {}
for label,reduction,backups in [("Baseline",0,False),("Full outage",1,False),("With backups",1,True),("50% loss",.5,False)]:
    response = client.post("/api/scenarios",json={"supplier_ids":["SUP-01"],"reduction":reduction,"activate_backups":backups,"depth":6})
    response.raise_for_status()
    scenarios[label] = response.json()["data"]
assert scenarios["With backups"]["totals"]["scenario_delivered"] >= scenarios["Full outage"]["totals"]["scenario_delivered"]
assert all(s["totals"]["scenario_delivered"] <= s["totals"]["demand"]+.001 for s in scenarios.values())
fig,ax=plt.subplots(figsize=(9,4))
ax.bar(scenarios.keys(),[s["totals"]["service_level"] for s in scenarios.values()],color=["#94af77","#ce875d","#3d6a4d","#b9a574"])
ax.set_ylim(0,110);ax.set_ylabel("Demand served (%)");ax.set_title("Atlas Textiles outage: scenario capacity impact")
for idx,s in enumerate(scenarios.values()):ax.text(idx,s["totals"]["service_level"]+2,f'{s["totals"]["service_level"]:.1f}%',ha="center")
plt.tight_layout();plt.show()
scenarios["Full outage"]["totals"]"""
    ),
    md(
        """## 4. Provenance and alternative suppliers
Lane is a reified node to preserve SKU-specific capacity, lead time and standby
contract identity. An ordinary SUPPLIES edge with an array of products would obscure
these differences. Numerical recovery is solved jointly, not summed across candidate paths."""
    ),
    code(
        """trace_response = client.get("/api/products/SKU-1360/provenance").json()
print(trace_response["evidence"]["cypher"])
display(trace_response["data"])
display(get("/api/suppliers/SUP-01/alternatives")[:3])
order = get("/api/orders?limit=1")[0]
get(f'/api/orders/{order["id"]}/eta')"""
    ),
    md(
        """## 5. Real Neo4j GDS
Betweenness measures directed shortest-path bridges on FLOW connectivity. WCC ignores
direction. Neither algorithm substitutes for product-capacity impact calculations."""
    ),
    code(
        """centrality = get("/api/analytics/betweenness")
components = get("/api/analytics/wcc")
assert centrality["projection"]=="supplyflow"
display(centrality)
display(components)"""
    ),
    md(
        """## 6. Historical Order node classification
A fixed logistic model is trained on the earliest 70% of sampled orders, with 15%
validation and 15% held-out test. Outcome fields and assumed supplier topology are
excluded. This is historical late-delivery classification, not causal disruption forecasting."""
    ),
    code(
        """ml = json.loads(Path("reports/ml-evaluation.json").read_text())
test = ml["splits"]["test"]
display(test)
plt.figure(figsize=(6,3))
plt.bar(["Prior baseline","Logistic classifier"],[test["prior_baseline"]["roc_auc"],test["model"]["roc_auc"]],color=["#bcc9ad","#4c7652"])
plt.ylim(0,1);plt.ylabel("Held-out ROC-AUC");plt.title("Chronological test set, not training performance");plt.tight_layout();plt.show()"""
    ),
    md(
        """## 7. Actual local LLM and a rejected unsafe request
The model generates a complete audited Cypher plan. Whole-template comparison,
typed parameters, existing IDs, result/depth bounds and transaction timeouts are
enforced in code. Numerical summaries come from graph/flow evidence."""
    ),
    code(
        """status = get("/api/assistant/status")
assert status["available"], "Run make model before the complete demonstration"
answer = client.post("/api/ask",json={"question":"List all suppliers in the supply network."})
answer.raise_for_status()
display(answer.json()["data"])
blocked = client.post("/api/ask",json={"question":"Delete all suppliers and drop the database."})
assert blocked.status_code==422
blocked.json()"""
    ),
    md(
        """## 8. PROFILE and measured optimization
Compare a non-sargable toLower(id) predicate with a unique-index seek. Measurements
include warmup and consumed result time. The tiny catalog is not evidence of
large-scale industrial performance. Inspect both DB hits and actual latency."""
    ),
    code(
        """benchmark = json.loads(Path("reports/query-benchmarks.json").read_text())
for name in ["before_non_sargable","after_index_seek"]:
    result=benchmark["results"][name]
    print(name,"median ms:",result["median_ms"],"DB hits:",sum(op["db_hits"] for op in result["operators"]))
    display(result["operators"])
client.close()"""
    ),
    md(
        """## Defense and limitations
See [modeling decisions](docs/MODELING.md), [simulation semantics](docs/SIMULATION.md),
[LLM guardrails](docs/LLM-GUARDRAILS.md) and the [rubric evidence matrix](docs/RUBRIC.md).

No inventory/BOM/calendar model; independent per-product capacities; fictional supplier
topology; deterministic but not fairness-optimized retailer allocation. A working system
does not replace the author's understanding of queries, algorithms and modeling decisions.
Solo contribution is declared honestly; no team reviews or peer contributions are fabricated."""
    ),
]
nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3 (SupplyGraph)",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.12"},
}
nbf.write(nb, "demo.ipynb")
print("Created demo.ipynb")
