# Modeling rationale and anti-genericity appendix

## Deliberate scope
SupplyGraph is a Level 2 distribution-resilience laboratory. Real DataCo product,
category and anonymous order observations ground the catalog, demand and historical
classifier. DataCo does not contain a trustworthy multi-tier supplier/company graph.
Every organization and supply lane is therefore an explicitly fictional scenario.
This is visible in the UI, API evidence, importer, diagrams and dataset report.
We do not claim these organizations supplied DataCo or that historical shipments
followed the modeled routes. Products pass unchanged through manufacturer-role
facilities: this is not a bill-of-materials transformation model.

## Source to graph
The CSV is an order-line fact table. `Order Item Id` identifies a line, while
`Order Id` repeats across lines. Multiple lines in the same order can reference the
same SKU; sum their quantities before creating one REQUESTS edge. Treating a row as
an order would overcount orders; MERGE with last-value quantity would lose demand.
The source audit is in `reports/data-audit.json`; the reconstructed source ER model
is `docs/diagrams/source-er.drawio` (SVG preview alongside it).

All 118 products and 51 categories are retained. Demand is total source quantity
per SKU divided by the full 1127-day observation window, rounded to four decimal
places. This historical daily average is not a current demand forecast. 6000 evenly
spaced order indices across the complete sorted source period form the small,
reproducible graph/ML sample. Identifiers refer to anonymous source orders, not people.
No customer names, passwords, emails, addresses or exact customer coordinates survive
sanitization. The 95.9 MB raw file is ignored in Git and Docker images.

## Why reify a lane?
A naive `Company-[:SUPPLIES]->Company` edge loses product identity, independent
capacity, contractual lead time and standby status. A Lane node gives each
product-specific route a stable ID, uniqueness constraint and inspectable evidence.
ORIGIN and DESTINATION point from Lane to Organization; CARRIES points to Product.
Organization.kind avoids duplication of a company that could perform multiple roles
in future; the current scenario assigns one role per facility.

Alternatives rejected:
- A single SUPPLIES edge with `products:[...]`: capacities and lead times differ by SKU.
- Separate Supplier, Manufacturer, Distributor and Retailer label-specific APIs:
  duplicates common identity, location and scenario rules. A constrained role property
  plus common Organization label is clearer for GDS and downstream traversal.
- Product as a string property only: no reliable catalog identity, category joins,
  shared-product alternative discovery or observed/assumed separation.
- Location as free text: loses reusable facility geography and normalized country identity.
  Facility coordinates are assumed; customer coordinates are never imported.
- Embedding orders inside products: destroys order-level identity and temporal splits.
- OrderLine as a persistent node: unnecessary for this scope after quantity-preserving
  aggregation; original per-line profitability is not analyzed. Reintroduce it if line
  auditability or per-line discount queries become requirements.

## FLOW is not inventory
FLOW is a derived, directed organization-connectivity relation for bounded Cypher
exposure and GDS. It collapses primary product lanes and excludes reserves. Its
`lead_days` is descriptive; betweenness is explicitly unweighted. FLOW must never
be used to compute product availability, quantities or manufacturing conversion.
Product-level maximum flow uses the full Lane facts instead.

## Constraints and indexes
Six uniqueness constraints protect IDs for Organization, Product, Lane, Order,
Category and Location and provide unique lookup indexes. Extra indexes cover
Organization.kind, Product.name, Order.ordered_at and Lane.sku. Not every index is
used by every query: the `toLower(name) CONTAINS` product search is not served by
an ordinary name index. At this tiny catalog size a scan is acceptable; larger
catalogs should use a full-text index. PROFILE demonstrates a real unique ID seek
versus a non-sargable `toLower(id)` scan without dropping production constraints.

## Anti-genericity appendix
The initial AI-style baseline would be:
`Supplier -> Manufacturer -> Distributor -> Retailer`, with Product properties,
shortest-path disruption propagation and a free-form LLM mitigation paragraph.

Our model deliberately differs:
1. Reified product-specific Lane nodes preserve capacity, standby status and evidence.
2. Real observations and assumed topology carry distinct provenance; no fictional
   supplier network is presented as recovered empirical truth.
3. Quantity-preserving order aggregation handles repeated order/SKU line items.
4. A reachable retailer is only *exposed*. A product is disrupted only when actual
   demand-constrained maximum delivered flow falls below its baseline.
5. Alternatives are OR supply routes. Multiple upstream inputs are not incorrectly
   treated as interchangeable BOM components; BOM semantics are explicitly excluded.
6. The LLM cannot invent an arbitrary graph relation or mitigation number. Entire
   query templates and typed parameters are validated before execution. Numerical
   summaries are computed from graph/solver results.
7. A temporal classifier uses observed pre-shipment order features, never invented
   topology or post-outcome delivery fields.

These are recorded design decisions, not a claim that an AI-generated draft proves
correctness. The accompanying counterexample tests demonstrate why they matter.
