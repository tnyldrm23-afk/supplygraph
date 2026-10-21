# SupplyGraph user guide

SupplyGraph answers one question: **if a supplier or facility loses capacity, which
products and stores are affected, and how much of the loss can backup lanes recover?**

- Story page: http://localhost:8080 (a one-page walkthrough of a single failure)
- Simulator: http://localhost:8080/app.html (the full application)

GitHub stores the source code; GitHub Packages stores the deployable Docker image of
the API. The Packages page is not the simulator screen.

## A first run

1. Open the story page and press **Take it offline** in the Atlas Textiles panel.
   Capacity drops in 10% steps and every step shows the solver's real answer.
2. At the bottom, choose a facility and capacity and press **Run in simulator**.
   The simulator opens with that scenario already calculated.
3. In **Disruption**, choose **Atlas Textiles**, leave capacity lost at **100%** and
   press **Run simulation**. Review affected products and unmet daily demand.
4. Switch on **Use backup contracts** (or press **Re-run with backups**) and compare.
5. In **Products**, pick a product to see every lane that carries it.
6. In **Ask the graph**, ask "What happens if Atlas Textiles (SUP-01) shuts down?"
   The answer shows the executed Cypher query and the raw records.

In the verified full Atlas outage, 40 products are affected. An affected product has
not necessarily lost all of its supply: remaining and backup lanes are calculated
separately, and results depend on the selected disruption and backup settings.

## Screens and terms

| Term / screen | Meaning |
|---|---|
| Supplier | Facility where product flow starts |
| Manufacturer | Facility the product passes through; no recipe or bill-of-materials transformation is modeled |
| Distributor | Facility that forwards products to stores |
| Retailer | Store whose demand the network tries to meet |
| SKU | Code that identifies one product |
| Lane | Route between two facilities for one product, with its own capacity and lead time |
| Baseline | Demand met through primary lanes before any disruption |
| Shortfall / unmet demand | Part of demand that cannot be delivered |
| Recovery | Product flow regained when backup contracts are active |
| Service level | Percentage of demand that is delivered |
| Story | One-page walkthrough: network, stages, capacity dial, recovery, products still short |
| Disruption | Scenario controls, world map, network diagram and results |
| Products | Origin, lanes and delivery times of a product |
| Analysis | Network connectivity and facilities that act as bridges |
| Ask the graph | Ask permitted network questions in plain language |

Quantities are average daily units. "112 units/day lost" does not mean 112 companies
or 112 product types. Total unmet demand and the loss *added* by a disruption can
differ, because some demand may already be unmet at baseline.

## How it works inside

**Neo4j** stores facilities, products, lanes and orders as a graph. **FastAPI** serves
the interface and runs the calculations. For each product, a **maximum-flow** algorithm
finds how much can be delivered given lane capacities and store demand; the same stock
is never counted on two routes. Disruption runs never change the stored network, so
scenarios can be rerun freely.

**GDS betweenness** highlights facilities that sit between many shortest routes. A high
score does not prove that closing the facility causes the largest shortage; use the
simulator to measure capacity loss. **WCC** finds which facilities belong to the same
connected group, ignoring direction.

**Ollama** runs the local Qwen2.5:1.5b model. The model interprets the question and picks
one of the permitted Cypher templates; the application checks the query and its
parameters, runs it in Neo4j and returns the results. Disruption quantities are computed
by the solver, not by the language model. If the model is not ready, the assistant is
unavailable while the other screens keep working. Download it once with `make model`;
no paid API key is needed.

**Docker Compose** starts the Neo4j, API, Nginx and Ollama services together. Use
`make docker-stop` to stop and `make docker-run` to start again; stopping keeps the
database and model volumes.

## What is real?

The 118 products and the anonymous historical orders come from the real DataCo dataset.
The 13 facilities, 962 lanes, capacities, lead times and backup relationships are an
explicitly assumed scenario. The application computes the outcome of that scenario; it
does not forecast production or delivery for real companies. An order's recorded
shipping time and the scenario's fastest modeled route are kept separate.

The ML report classifies late deliveries in historical orders; it is not a model that
predicts future disruptions or their impact.

See [DEFENSE.md](DEFENSE.md) for defense preparation, [MODELING.md](MODELING.md) for
modeling decisions and [SIMULATION.md](SIMULATION.md) for calculation details.
