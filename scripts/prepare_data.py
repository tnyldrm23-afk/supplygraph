"""Create a sanitized, deterministic derivative of the original DataCo dataset."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6"
CITATION = "Constante, Silva & Pereira (2019), DataCo, Mendeley Data V5, doi:10.17632/8gx2fvg2k6.5"


def build() -> dict:
    """Aggregate all rows, keep anonymous order facts, and add explicit scenario lanes."""
    path = ROOT / "data/raw/DataCoSupplyChainDataset.csv"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOURCE_SHA:
        raise ValueError("Original DataCo SHA-256 mismatch. Refusing unverified input.")
    products, orders, categories = {}, {}, {}
    demand = Counter()
    countries = Counter()
    missing = Counter()
    item_ids = set()
    duplicates = 0
    first, last = None, None
    with path.open(encoding="latin-1", newline="") as handle:
        reader = csv.DictReader(handle)
        for count, row in enumerate(reader, 1):
            for key, value in row.items():
                if not value:
                    missing[key] += 1
            if row["Order Item Id"] in item_ids:
                duplicates += 1
                continue
            item_ids.add(row["Order Item Id"])
            sku = "SKU-" + row["Product Card Id"]
            cat = "CAT-" + row["Category Id"]
            categories[cat] = {"id": cat, "name": row["Category Name"].strip()}
            products[sku] = {
                "id": sku,
                "name": row["Product Name"].strip(),
                "category_id": cat,
                "price": float(row["Product Price"]),
                "provenance": "observed",
                "source": "DataCo-v5",
            }
            quantity = int(row["Order Item Quantity"])
            demand[sku] += quantity
            date = datetime.strptime(row["order date (DateOrders)"], "%m/%d/%Y %H:%M")
            first = min(first or date, date)
            last = max(last or date, date)
            oid = "ORD-" + row["Order Id"]
            if oid not in orders:
                orders[oid] = {
                    "id": oid,
                    "ordered_at": date.isoformat(),
                    "scheduled_days": int(row["Days for shipment (scheduled)"]),
                    "actual_days": int(row["Days for shipping (real)"]),
                    "shipping_mode": row["Shipping Mode"],
                    "market": row["Market"],
                    "late": int(row["Late_delivery_risk"]),
                    "items": [],
                    "destination_country": row["Order Country"],
                    "provenance": "observed",
                    "source": "DataCo-v5",
                }
            orders[oid]["items"].append({"sku": sku, "quantity": quantity})
            countries[row["Order Country"]] += 1
    days = (last - first).days + 1
    for sku, product in products.items():
        product["historical_units"] = demand[sku]
        product["daily_demand"] = round(demand[sku] / days, 4)
    # This is NOT an inferred real-world company network. All organization names,
    # locations, capacities, edges and lead times below are constructed scenarios.
    locations = [
        ("LOC-PT", "Porto", "Portugal", 41.15, -8.61),
        ("LOC-TR", "Istanbul", "Türkiye", 41.01, 28.98),
        ("LOC-VN", "Ho Chi Minh City", "Vietnam", 10.82, 106.63),
        ("LOC-NL", "Rotterdam", "Netherlands", 51.92, 4.48),
        ("LOC-DE", "Hamburg", "Germany", 53.55, 9.99),
        ("LOC-FR", "Paris", "France", 48.86, 2.35),
        ("LOC-GB", "London", "United Kingdom", 51.51, -0.13),
        ("LOC-US", "New York", "United States", 40.71, -74.01),
    ]
    organizations = [
        ("SUP-01", "Atlas Textiles", "supplier", "LOC-PT"),
        ("SUP-02", "Bosphorus Materials", "supplier", "LOC-TR"),
        ("SUP-03", "Mekong Components", "supplier", "LOC-VN"),
        ("SUP-04", "Lusitania Reserve", "supplier", "LOC-PT"),
        ("MFG-01", "Porto Works", "manufacturer", "LOC-PT"),
        ("MFG-02", "Istanbul Assembly", "manufacturer", "LOC-TR"),
        ("MFG-03", "Saigon Works", "manufacturer", "LOC-VN"),
        ("DST-01", "Rotterdam Gateway", "distributor", "LOC-NL"),
        ("DST-02", "Hamburg Hub", "distributor", "LOC-DE"),
        ("DST-03", "Atlantic Distribution", "distributor", "LOC-US"),
        ("RET-01", "Paris Retail", "retailer", "LOC-FR"),
        ("RET-02", "London Retail", "retailer", "LOC-GB"),
        ("RET-03", "New York Retail", "retailer", "LOC-US"),
    ]
    orgs = [
        dict(
            id=oid,
            name=name,
            kind=kind,
            location_id=loc,
            provenance="assumed",
            source="scenario-v1",
        )
        for oid, name, kind, loc in organizations
    ]
    lanes = []
    for idx, sku in enumerate(sorted(products)):
        group = idx % 3 + 1
        manufacturer = f"MFG-{group:02d}"
        daily = products[sku]["daily_demand"]
        # Three retailer sinks each request 1/3 of the source-product daily demand.
        # Share-constrained max-flow prevents counting the same stock three times.
        specs = [
            (f"SUP-{group:02d}", manufacturer, 1.15, 2 + group, False),
            (manufacturer, "DST-01", 0.8, 2, False),
            (manufacturer, "DST-02", 0.5, 3, False),
            ("DST-01", "RET-01", 0.45, 1, False),
            ("DST-01", "RET-02", 0.40, 2, False),
            ("DST-02", "RET-03", 0.45, 3, False),
            ("DST-02", "RET-02", 0.20, 2, False),
        ]
        if idx % 4 != 0:
            specs += [("SUP-04", manufacturer, 0.65, 6, True)]
        if idx % 5 == 0:
            specs += [(manufacturer, "DST-03", 0.4, 4, True), ("DST-03", "RET-03", 0.4, 1, True)]
        for src, dst, factor, lead, backup in specs:
            lanes.append(
                dict(
                    id=f"LANE-{len(lanes)+1:04d}",
                    origin=src,
                    destination=dst,
                    sku=sku,
                    capacity=round(daily * factor, 6),
                    lead_days=lead,
                    backup=backup,
                    provenance="assumed",
                    source="scenario-v1",
                    units="units/day",
                )
            )
    # Chronological, deterministic order-level sample across the entire time range.
    ordered = sorted(orders.values(), key=lambda x: (x["ordered_at"], x["id"]))
    sample_size = min(6000, len(ordered))
    selected = [
        ordered[i * (len(ordered) - 1) // max(1, sample_size - 1)] for i in range(sample_size)
    ]
    for order in selected:
        # One order can contain several distinct line items for the same SKU.
        # Aggregate before MERGE to preserve observed quantity rather than overwrite it.
        quantities = Counter()
        for item in order["items"]:
            quantities[item["sku"]] += item["quantity"]
        order["items"] = [{"sku": sku, "quantity": qty} for sku, qty in sorted(quantities.items())]
    for idx, order in enumerate(selected):
        order["retailer_id"] = f"RET-{idx % 3 + 1:02d}"
        order["retailer_assignment_provenance"] = "assumed"
    report = {
        "citation": CITATION,
        "license": "CC BY 4.0",
        "sha256": digest,
        "source_rows": count,
        "unique_orders": len(orders),
        "unique_products": len(products),
        "unique_categories": len(categories),
        "duplicate_item_ids": duplicates,
        "period_start": first.isoformat(),
        "period_end": last.isoformat(),
        "period_days": days,
        "source_missing_values": dict(missing),
        "selected_orders": len(selected),
        "sampling": "6000 evenly spaced order indices across the full chronological range",
        "observed_fields": [
            "product IDs/names/prices/categories",
            "historical quantities",
            "anonymous order IDs/dates",
            "shipping durations/modes",
            "markets",
            "late label",
        ],
        "assumed_fields": [
            "all organizations",
            "all lanes",
            "capacities",
            "lead times",
            "backup contracts",
            "retailer assignment",
            "equal retailer demand split",
        ],
        "excluded_fields": [
            "customer names",
            "emails",
            "passwords",
            "addresses",
            "customer IDs",
            "customer coordinates",
            "customer postcodes",
        ],
        "country_line_counts_top10": countries.most_common(10),
        "demand_method": "historical units divided by the complete 1127-day observation window; not a forecast",
        "warning": "DataCo does not supply multi-tier supplier topology. Scenario graph is fictional.",
    }
    payload = dict(
        products=list(products.values()),
        categories=list(categories.values()),
        organizations=orgs,
        locations=[
            dict(
                id=x[0],
                name=x[1],
                country=x[2],
                latitude=x[3],
                longitude=x[4],
                provenance="assumed",
            )
            for x in locations
        ],
        lanes=lanes,
        orders=selected,
        metadata=report,
    )
    (ROOT / "data/processed/supplygraph.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (ROOT / "reports/data-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
