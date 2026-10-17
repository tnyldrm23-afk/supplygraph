"""Generate self-contained SVG previews and editable draw.io diagrams."""

from pathlib import Path
from html import escape
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "docs/diagrams"


def diagram(name, title, nodes, edges, width=1100, height=660):
    """Render explicit node positions to both SVG and diagrams.net XML."""
    colors = {
        "observed": ("#eff5e9", "#6f8b56"),
        "assumed": ("#fcf0e4", "#bb8b57"),
        "service": ("#edf3ef", "#456e5a"),
        "meta": ("#f3f4f1", "#8b9981"),
    }
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="none" stroke="#8b9981"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#fafbf8"/>',
        f'<text x="35" y="42" font-family="sans-serif" font-size="24" fill="#19352a">{escape(title)}</text>',
    ]
    mapping = {n[0]: n for n in nodes}
    mx = ET.Element("mxfile", host="app.diagrams.net")
    d = ET.SubElement(mx, "diagram", name=title, id=name)
    model = ET.SubElement(
        d,
        "mxGraphModel",
        dx=str(width),
        dy=str(height),
        grid="1",
        page="1",
        pageWidth=str(width),
        pageHeight=str(height),
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    for idx, (src, dst, label) in enumerate(edges):
        a, b = mapping[src], mapping[dst]
        x1, y1 = a[2] + a[4] / 2, a[3] + a[5] / 2
        x2, y2 = b[2] + b[4] / 2, b[3] + b[5] / 2
        if abs(x2 - x1) > abs(y2 - y1):
            x1 = a[2] + a[4] if x2 > x1 else a[2]
            x2 = b[2] if x2 > x1 else b[2] + b[4]
        else:
            y1 = a[3] + a[5] if y2 > y1 else a[3]
            y2 = b[3] if y2 > y1 else b[3] + b[5]
        svg.append(
            f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#94a18b" stroke-width="1.5" marker-end="url(#arrow)"/>'
        )
        tx = (x1 + x2) / 2
        ty = (y1 + y2) / 2 - 8
        svg.append(
            f'<text x="{tx}" y="{ty}" font-family="monospace" font-size="10" text-anchor="middle" fill="#5b7051">{escape(label)}</text>'
        )
        cell = ET.SubElement(
            root,
            "mxCell",
            id="edge" + str(idx),
            value=label,
            style="edgeStyle=orthogonalEdgeStyle;rounded=1;endArrow=block;html=1;",
            edge="1",
            parent="1",
            source=src,
            target=dst,
        )
        ET.SubElement(cell, "mxGeometry", relative="1", attrib={"as": "geometry"})
    for ident, label, x, y, w, h, kind, detail in nodes:
        fill, stroke = colors[kind]
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}"/>'
        )
        svg.append(
            f'<text x="{x+16}" y="{y+27}" font-family="sans-serif" font-size="15" font-weight="600" fill="#254634">{escape(label)}</text>'
        )
        for idx, line in enumerate(detail.split("\n")):
            svg.append(
                f'<text x="{x+16}" y="{y+49+idx*16}" font-family="monospace" font-size="10" fill="#718466">{escape(line)}</text>'
            )
        cell = ET.SubElement(
            root,
            "mxCell",
            id=ident,
            value=label + "\n" + detail,
            style=f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontFamily=Helvetica;",
            vertex="1",
            parent="1",
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            x=str(x),
            y=str(y),
            width=str(w),
            height=str(h),
            attrib={"as": "geometry"},
        )
    svg.append(
        '<text x="35" y="'
        + str(height - 25)
        + '" font-family="sans-serif" font-size="11" fill="#829475">SupplyGraph · Green: observed / service · Orange: assumed scenario · Tan YILDIRIM, B00822334</text></svg>'
    )
    (ROOT / (name + ".svg")).write_text("\n".join(svg))
    ET.ElementTree(mx).write(ROOT / (name + ".drawio"), encoding="utf-8", xml_declaration=True)


diagram(
    "schema",
    "Graph schema — observed facts and assumed supply lanes",
    [
        (
            "org",
            "Organization",
            70,
            140,
            230,
            115,
            "assumed",
            "id UNIQUE · name · kind\nSupplier / manufacturer /\ndistributor / retailer",
        ),
        (
            "lane",
            "Lane",
            430,
            130,
            245,
            145,
            "assumed",
            "id UNIQUE · sku\ncapacity: units/day\nlead_days · backup\nprovenance = assumed",
        ),
        (
            "prod",
            "Product",
            810,
            140,
            230,
            115,
            "observed",
            "id UNIQUE · category_id\nname · price\ndaily_demand (derived)",
        ),
        (
            "loc",
            "Location",
            70,
            410,
            230,
            105,
            "assumed",
            "id UNIQUE\nname · country\nscenario facility coordinates",
        ),
        (
            "order",
            "Order",
            430,
            410,
            245,
            125,
            "observed",
            "id UNIQUE · ordered_at\nscheduled_days · actual_days\nshipping_mode · late\nML score + holdout split",
        ),
        (
            "cat",
            "Category",
            810,
            410,
            230,
            105,
            "observed",
            "id UNIQUE\nname\nDataCo category catalog",
        ),
    ],
    [
        ("lane", "org", "ORIGIN + DESTINATION"),
        ("lane", "prod", "CARRIES"),
        ("org", "loc", "LOCATED_IN"),
        ("order", "prod", "REQUESTS {quantity}"),
        ("prod", "cat", "IN_CATEGORY"),
        ("order", "org", "DELIVERS_TO (assumed)"),
    ],
    height=650,
)

diagram(
    "architecture",
    "System architecture — four local Docker Compose services",
    [
        (
            "web",
            "Nginx + static UI",
            50,
            120,
            240,
            125,
            "service",
            "127.0.0.1:8080\nHTML / CSS / SVG / JS\nreverse proxy + CSP",
        ),
        (
            "api",
            "FastAPI",
            420,
            120,
            255,
            145,
            "service",
            "127.0.0.1:8000 /docs\nPydantic + exact-template guard\nimmutable flow solver\nquery timeout + concurrency cap",
        ),
        (
            "neo",
            "Neo4j 5.26 + GDS",
            810,
            120,
            240,
            145,
            "service",
            "127.0.0.1:7474 / :7687\nconstraints + indexes\nFLOW projection\nbetweenness / WCC",
        ),
        (
            "data",
            "Sanitized DataCo v5",
            50,
            410,
            240,
            115,
            "observed",
            "118 products · 6000 orders\nsource hash verified\nCC BY 4.0 attribution",
        ),
        (
            "ollama",
            "Ollama / Qwen",
            420,
            410,
            255,
            115,
            "service",
            "127.0.0.1:11434\nqwen2.5:1.5b\nreal local model generation",
        ),
        (
            "ml",
            "Offline ML + benchmarks",
            810,
            410,
            240,
            115,
            "meta",
            "temporal node classification\nPROFILE + 30-run latency\nreports + demo.ipynb",
        ),
    ],
    [
        ("web", "api", "HTTP /api/*"),
        ("api", "neo", "Bolt / bounded Cypher"),
        ("api", "ollama", "JSON query plan"),
        ("data", "api", "idempotent ingestion"),
        ("ml", "neo", "scores + PROFILE"),
    ],
)

diagram(
    "source-er",
    "Source ER model — reconstruction from DataCo order-line records",
    [
        (
            "line",
            "Order line",
            420,
            250,
            250,
            130,
            "observed",
            "Order Item Id (source PK)\nOrder Id (FK)\nProduct Card Id (FK)\nquantity / item price",
        ),
        (
            "order",
            "Order",
            70,
            110,
            230,
            115,
            "observed",
            "Order Id (source PK)\norder date\nshipping mode / durations",
        ),
        (
            "product",
            "Product",
            800,
            110,
            240,
            115,
            "observed",
            "Product Card Id (source PK)\nname / catalog price\nProduct Category Id (FK)",
        ),
        (
            "category",
            "Category",
            800,
            420,
            240,
            100,
            "observed",
            "Category Id (source PK)\nCategory Name",
        ),
        (
            "derivative",
            "Sanitized graph mapping",
            70,
            420,
            250,
            130,
            "meta",
            "Repeated order/SKU lines\naggregate to REQUESTS quantity\ncustomer personal fields omitted\nNo real supplier topology",
        ),
    ],
    [
        ("order", "line", "1 → many"),
        ("product", "line", "1 → many"),
        ("product", "category", "many → 1"),
        ("line", "derivative", "aggregate + sanitize"),
    ],
)
print("Wrote three editable draw.io diagrams and SVG previews.")
