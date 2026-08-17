#!/usr/bin/env python3
"""
Render the state map — `docs/jefferson-map.svg` — and the county layer that
backs it, `records/orgs/jefferson_counties.geojson`.

Everything here is derived, never drawn by hand:

  * county shapes are the REAL counties' Census boundaries
    (`generators/jefferson/data/real_counties.geojson`), tagged with the
    Jefferson county and area standing on them (`names.COUNTY_GEO`);
  * city positions are the coordinates in `records/orgs/cities.json`, which are
    themselves real places' coordinates (see `gen.py::write_gazetteer`);
  * the state outline is `records/orgs/jefferson_boundary.geojson`.

⚠️ The owner's map claims 29 real counties; only 20 carry a Jefferson county.
The nine unassigned ones are drawn as claimed ground and listed in the legend
rather than quietly dropped — a map that hides the gap is how the gazetteer and
the map drifted apart in the first place.

Output is a plain SVG with no external references, so it renders anywhere.

    python3 scripts/build_jefferson_map.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generators.jefferson import names as N   # noqa: E402

REAL = ROOT / "generators/jefferson/data/real_counties.geojson"
CITIES = ROOT / "records/orgs/cities.json"
# ⚠️ NOT under records/orgs — Gen.run() rmtree's that directory every run,
# which silently deleted both map layers. Source data lives with the
# generator; the derived layer is written to docs/ beside the map.
BOUNDARY = ROOT / "generators/jefferson/data/jefferson_boundary.geojson"
OUT_SVG = ROOT / "docs/jefferson-map.svg"
OUT_GEO = ROOT / "docs/jefferson-counties.geojson"

W, H, PAD = 1400, 1380, 34
PAD_L = 150          # coastal towns hang their labels out over the ocean
LABEL_MIN = 60_000          # cities named on the map
DOT_MIN, DOT_MAX = 2.2, 17.0

AREA_COLOR = {
    "Harborline":        "#2E6F8E",
    "South Coast":       "#4EA0A8",
    "Timber Valley":     "#2F6B4F",
    "Cascade Divide":    "#6B7F3A",
    "Gold Valley":       "#C08A2E",
    "Ashbury Metro":     "#9B3B4E",
    "Halbrook Basin":    "#7A4E9B",
    "Sage Plains":       "#A9752F",
    "Juniper Highlands": "#8C6B4A",
    "North Range":       "#4A5A72",
    "Vermilion Valley":  "#B0492F",
    "Siskiyou Valley":       "#8A7B2E",
}
UNASSIGNED = "#D8D5CE"


def _rings(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


def _centroid(geom):
    """Area-weighted centroid of the largest ring. A mean of the ring's own
    vertices is pulled hard toward whichever edge has the most detail, which on
    these counties is always the coastline or a river — so coastal county names
    ended up in the Pacific."""
    ring = max(_rings(geom), key=len)
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-12:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    return (cx / (3 * a), cy / (3 * a))


class _Boxes:
    """Greedy label collision. Labels are offered in importance order and any
    that cannot find a clear slot is dropped — a map with 40 readable names
    beats one with 90 stacked on top of each other."""

    def __init__(self):
        self.taken: list[tuple[float, float, float, float]] = []

    def place(self, w, h, slots, bounds):
        for x, y in slots:
            box = (x, y - h, x + w, y)
            if not (bounds[0] <= box[0] and box[2] <= bounds[2]
                    and bounds[1] <= box[1] and box[3] <= bounds[3]):
                continue                        # never hang a label off the canvas
            if all(box[2] <= t[0] or box[0] >= t[2] or box[3] <= t[1] or box[1] >= t[3]
                   for t in self.taken):
                self.taken.append(box)
                return x, y
        return None


def main() -> int:
    counties = json.loads(REAL.read_text())["features"]
    cities = json.loads(CITIES.read_text())["cities"]
    boundary = json.loads(BOUNDARY.read_text())["features"][0]["geometry"]

    # real county -> (Jefferson county, area)
    geo = {real: (c, area) for area, lst in N.COUNTY_GEO.items() for c, real in lst}
    for f in counties:
        c, a = geo.get(f["properties"]["real_county"], (None, None))
        f["properties"]["county"] = c
        f["properties"]["area"] = a
    OUT_GEO.write_text(json.dumps(
        {"type": "FeatureCollection",
         "_doc": ["Jefferson's counties as map shapes: the real county boundary each",
                  "one stands on, tagged with its Jefferson county and area. Built by",
                  "scripts/build_jefferson_map.py; do not hand-edit.",
                  "A null county/area means ground the state map claims that no",
                  "Jefferson county has been drawn onto yet."],
         "features": counties}, indent=1) + "\n")

    # ---- projection: equirectangular, longitude squeezed at the mean latitude
    pts = [(c["lon"], c["lat"]) for c in cities]
    pts += [(x, y) for f in counties for r in _rings(f["geometry"]) for x, y in r]
    lo0, lo1 = min(p[0] for p in pts), max(p[0] for p in pts)
    la0, la1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((la0 + la1) / 2))
    sx = (W - PAD_L - PAD) / ((lo1 - lo0) * k)
    sy = (H - 2 * PAD - 150) / (la1 - la0)
    s = min(sx, sy)
    ox = PAD_L + ((W - PAD_L - PAD) - (lo1 - lo0) * k * s) / 2
    oy = PAD

    def xy(lon, lat):
        return (ox + (lon - lo0) * k * s, oy + (la1 - lat) * s)

    def path(geom):
        out = []
        for ring in _rings(geom):
            out.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in
                                      (xy(a, b) for a, b in ring)) + "Z")
        return "".join(out)

    svg = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' "
           f"viewBox='0 0 {W} {H}' font-family='Helvetica,Arial,sans-serif'>",
           f"<rect width='{W}' height='{H}' fill='#F7F5F0'/>"]

    for f in counties:
        a = f["properties"]["area"]
        fill = AREA_COLOR.get(a, UNASSIGNED) if a else UNASSIGNED
        op = "0.42" if a else "0.5"
        svg.append(f"<path d='{path(f['geometry'])}' fill='{fill}' fill-opacity='{op}' "
                   f"stroke='#FFF' stroke-width='1.1'/>")
    # ⚠️ The supplied outline is a hull over the claimed counties and does not
    # trace them exactly (it bulges past the Glenn/Colusa corner). Drawn light,
    # so the county mosaic is what reads as the state and the outline is a hint.
    svg.append(f"<path d='{path(boundary)}' fill='none' stroke='#4A463F' "
               f"stroke-width='1.8' stroke-opacity='0.7' stroke-linejoin='round'/>")

    # A county name is context and a city name is the lookup, so the county is
    # placed first and never moved -- but it is DRAWN after the dots, with the
    # paper colour haloed behind it, or a metro's cluster of circles swallows it.
    county_boxes, county_svg = [], []
    for f in counties:
        c = f["properties"]["county"]
        x, y = xy(*_centroid(f["geometry"]))
        label = c.upper() if c else f["properties"]["real_county"].split(" County")[0].upper()
        col = "#3A3630" if c else "#8E8A82"
        x = min(max(x, PAD_L + 60), W - PAD - 60)
        county_boxes.append((x - len(label) * 4.9, y - 13, x + len(label) * 4.9, y + 4))
        county_svg.append(
            f"<text x='{x:.0f}' y='{y:.0f}' text-anchor='middle' font-size='13' "
            f"font-weight='700' letter-spacing='1.4' fill='{col}' "
            f"opacity='{0.85 if c else 0.6}' stroke='#F7F5F0' stroke-width='3.2' "
            f"stroke-linejoin='round' paint-order='stroke'>{label}</text>")

    pmax = max(c["population"] for c in cities)
    rad = {c["name"]: DOT_MIN + (DOT_MAX - DOT_MIN) * math.sqrt(c["population"] / pmax)
           for c in cities}
    for c in sorted(cities, key=lambda c: c["population"]):
        x, y = xy(c["lon"], c["lat"])
        svg.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{rad[c['name']]:.1f}' "
                   f"fill='{AREA_COLOR[c['area']]}' fill-opacity='0.92' "
                   f"stroke='#FFF' stroke-width='0.9'/>")

    svg.extend(county_svg)

    boxes = _Boxes()
    boxes.taken.extend(county_boxes)       # a county name is never overprinted
    bounds = (6, PAD - 10, W - 6, oy + (la1 - la0) * s + 24)
    for c in cities:                       # reserve the dots themselves
        x, y = xy(c["lon"], c["lat"])
        r = rad[c["name"]]
        boxes.taken.append((x - r, y - r, x + r, y + r))
    named = dropped = 0
    for c in sorted(cities, key=lambda c: -c["population"]):
        if c["population"] < LABEL_MIN:
            continue
        x, y = xy(c["lon"], c["lat"])
        r, nm = rad[c["name"]], c["name"]
        w, h = len(nm) * 6.9 + 5, 15
        spot = boxes.place(w, h, [(x + r + 4, y + 5), (x - r - 4 - w, y + 5),
                                  (x - w / 2, y - r - 4), (x - w / 2, y + r + 18),
                                  (x + r + 4, y - r - 6), (x - r - 4 - w, y + r + 18)],
                          bounds)
        if not spot:
            dropped += 1
            continue
        named += 1
        tx, ty = spot
        svg.append(f"<text x='{tx:.0f}' y='{ty:.0f}' font-size='12.5' font-weight='700' "
                   f"fill='#1B1917' stroke='#F7F5F0' stroke-width='3.4' "
                   f"stroke-linejoin='round' paint-order='stroke'>"
                   f"{nm.replace('&', '&amp;')}</text>")
    print(f"  labels: {named} placed, {dropped} dropped for want of room")

    # ---- legend
    ly = H - 158
    svg.append(f"<text x='{PAD}' y='{ly - 46}' font-size='25' font-weight='800' "
               f"fill='#1B1917'>State of Jefferson</text>")
    svg.append(f"<text x='{PAD}' y='{ly - 25}' font-size='13' fill='#57534E'>"
               f"{len(cities)} cities and towns · {len([f for f in counties if f['properties']['county']])} "
               f"counties · 10 areas · every position a real place's coordinates</text>")
    for i, (a, col) in enumerate(AREA_COLOR.items()):
        cx = PAD + (i % 4) * 300
        cy = ly + (i // 4) * 26
        svg.append(f"<circle cx='{cx + 6}' cy='{cy}' r='6' fill='{col}'/>"
                   f"<text x='{cx + 18}' y='{cy + 4}' font-size='13' fill='#3A3630'>{a}</text>")
    unass = [f["properties"]["real_county"] for f in counties if not f["properties"]["county"]]
    if unass:
      svg.append(f"<circle cx='{PAD + 6}' cy='{ly + 86}' r='6' fill='{UNASSIGNED}' "
               f"stroke='#B5B1A9'/>"
               f"<text x='{PAD + 18}' y='{ly + 90}' font-size='12.5' fill='#77726A'>"
               f"claimed ground with no Jefferson county drawn on it yet — "
               f"{', '.join(u.split(' County')[0] for u in unass)}</text>")
    svg.append("</svg>")

    OUT_SVG.write_text("\n".join(svg) + "\n")
    print(f"{OUT_SVG.relative_to(ROOT)}  ({len(cities)} cities, {len(counties)} counties, "
          f"{len(unass)} unassigned)")
    print(f"{OUT_GEO.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
