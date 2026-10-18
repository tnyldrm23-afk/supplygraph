# Data attribution and license

**Original:** Constante, Fabian; Silva, Fernando; Pereira, António (2019),
“DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS”, Mendeley Data, V5,
https://doi.org/10.17632/8gx2fvg2k6.5.

**Source license:** Creative Commons Attribution 4.0 International (CC BY 4.0),
https://creativecommons.org/licenses/by/4.0/ (verified in original publisher metadata).

**Derivative:** `data/processed/supplygraph.json` retains product/category facts,
aggregates historical units/daily averages, aggregates repeated order/SKU line
quantities, and selects 6000 anonymous orders at evenly spaced chronological
indices. Customer identifiers, contact details, addresses, passwords and exact
customer coordinates are excluded. These transformations were made by SupplyGraph.
The derivative's original observed content remains under CC BY 4.0.

**Added scenario:** all fictional companies/facilities, supply relationships,
capacities, lead times, backup contracts and retailer assignments are original
illustrative assumptions. They do not imply actual DataCo supplier relationships.
The project's code and original scenario definitions are MIT licensed.

SHA-256 of original CSV:
`fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6`.

Raw files are downloaded locally, ignored by Git and excluded from Docker images.
The source dictionary is used for interpretation and is downloadable with the
reproducible source-data script. No rights over original DataCo content are claimed.

**Map backdrop:** `app/static/land.svg` is projected from Natural Earth 1:50m land
(public domain, https://www.naturalearthdata.com/) via the world-atlas package
(ISC license) with `scripts/create_land_map.py`. City placements on the map are
the scenario's assumed facility locations.
