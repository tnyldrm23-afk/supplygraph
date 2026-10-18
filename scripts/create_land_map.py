"""Project Natural Earth land into the dotted world backdrop at app/static/land.svg.

Input: land-50m.json from the world-atlas npm package (v2.0.2), e.g.
https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-50m.json

Usage: python scripts/create_land_map.py land-50m.json app/static/land.svg

The projection constants must match GEO and project() in app/static/app.js.
"""
import json
import math
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
W = 1060
LON0, LON1, LAT_TOP, LAT_BOTTOM = -84.0, 124.0, 60.0, 5.0
K = W / math.radians(LON1 - LON0)


def merc(lat):
    lat = max(-80.0, min(84.0, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


Y0 = merc(LAT_TOP)
H = round(K * (Y0 - merc(LAT_BOTTOM)))


def project(lon, lat):
    return K * math.radians(lon - LON0), K * (Y0 - merc(lat))


topo = json.load(open(SRC, encoding="utf-8"))
sx, sy = topo["transform"]["scale"]
tx, ty = topo["transform"]["translate"]
arcs = []
for arc in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx
        y += dy
        pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)


def ring_points(ring):
    pts = []
    for index in ring:
        arc = arcs[index] if index >= 0 else arcs[~index][::-1]
        pts.extend(arc if not pts else arc[1:])
    return pts


parts = []
for geometry in topo["objects"]["land"]["geometries"]:
    polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]
    for polygon in polygons:
        for ring in polygon:
            pts = [project(lon, lat) for lon, lat in ring_points(ring)]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < -20 or min(xs) > W + 20 or max(ys) < -20 or min(ys) > H + 20:
                continue
            if (max(xs) - min(xs)) < 2 and (max(ys) - min(ys)) < 2:
                continue
            simplified = [pts[0]]
            for p in pts[1:]:
                if abs(p[0] - simplified[-1][0]) + abs(p[1] - simplified[-1][1]) >= 1.6:
                    simplified.append(p)
            if len(simplified) < 3:
                continue
            parts.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in simplified) + "Z")

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
    '<defs><pattern id="d" width="5" height="5" patternUnits="userSpaceOnUse">'
    '<circle cx="2.5" cy="2.5" r="1.05" fill="#9fc3bd"/></pattern></defs>'
    f'<path fill="url(#d)" d="{"".join(parts)}"/></svg>\n'
)
open(OUT, "w", encoding="utf-8").write(svg)
print("height", H, "bytes", len(svg), "K", K, "Y0", Y0)
