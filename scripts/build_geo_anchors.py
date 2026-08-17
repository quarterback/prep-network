#!/usr/bin/env python3
"""
Rebuild `generators/jefferson/data/geo_anchors.json` — the real-world coordinates
Jefferson's cities stand on.

Jefferson's counties each name the real county whose ground they occupy
(`names.COUNTY_GEO`). This script pulls every real populated place inside those
twenty counties out of the GeoNames US dump, ordered by population, and writes
them out as a per-county anchor list.

The generator then places a Jefferson city BY RANK: the largest city in a county
takes the largest real place's coordinates, the second-largest takes the second,
and so on. So Ashbury sits where Medford sits, Port Veles where Coos Bay sits,
and a 4,000-person Antler County mill town lands on a real 4,000-person Douglas
County mill town — on a real valley floor, beside a real river, never in the
Pacific and never on a ridge line. Nothing is scattered or jittered: every
coordinate in the state is a real place's coordinate.

⚠️ Anchors are BAKED IN, on purpose. The generator must run offline and
deterministically, so it reads this file and never the network. Re-run this only
when the county map changes (`names.COUNTY_GEO`) or a county gains more Jefferson
cities than it has anchors — the generator says so loudly when that happens.

County FIPS codes are not hard-coded: each county is identified by looking up its
real county SEAT in the dump and reading the seat's admin2 code, so a typo'd FIPS
can't silently attach a county to the wrong ground.

    python3 scripts/build_geo_anchors.py [--dump /tmp/US.zip] [--per-county 45]

Source: https://download.geonames.org/export/dump/US.zip (~70 MB, all US
populated places, public domain / CC-BY 4.0).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "generators/jefferson/data/geo_anchors.json"
DUMP_URL = "https://download.geonames.org/export/dump/US.zip"

# The county SEAT of each real county Jefferson stands on, used only to resolve
# that county's FIPS code out of the dump. Owyhee County's seat is Murphy
# (pop. ~50), which is in the dump but is not the sort of unambiguous name worth
# matching on — Homedale, the county's largest town, does the same job safely.
SEATS = {
    "Douglas County, OR":    ("Roseburg", "OR"),
    "Coos County, OR":       ("Coquille", "OR"),
    "Curry County, OR":      ("Gold Beach", "OR"),
    "Josephine County, OR":  ("Grants Pass", "OR"),
    "Jackson County, OR":    ("Medford", "OR"),
    "Klamath County, OR":    ("Klamath Falls", "OR"),
    "Lake County, OR":       ("Lakeview", "OR"),
    "Harney County, OR":     ("Burns", "OR"),
    "Malheur County, OR":    ("Vale", "OR"),
    "Del Norte County, CA":  ("Crescent City", "CA"),
    "Siskiyou County, CA":   ("Yreka", "CA"),
    "Modoc County, CA":      ("Alturas", "CA"),
    "Humboldt County, CA":   ("Eureka", "CA"),
    "Trinity County, CA":    ("Weaverville", "CA"),
    "Shasta County, CA":     ("Redding", "CA"),
    "Lassen County, CA":     ("Susanville", "CA"),
    "Washoe County, NV":     ("Reno", "NV"),
    "Humboldt County, NV":   ("Winnemucca", "NV"),
    "Canyon County, ID":     ("Caldwell", "ID"),
    "Owyhee County, ID":     ("Homedale", "ID"),
    # the nine counties the state map claimed before a Jefferson county stood
    # on them (2027-08) — the northern valley, the Siskiyou Valley, and the two
    # that fill out North Range and the Halbrook Basin
    "Butte County, CA":      ("Oroville", "CA"),
    "Tehama County, CA":     ("Red Bluff", "CA"),
    "Glenn County, CA":      ("Willows", "CA"),
    "Colusa County, CA":     ("Colusa", "CA"),
    "Plumas County, CA":     ("Quincy", "CA"),
    "Sierra County, CA":     ("Loyalton", "CA"),
    "Nevada County, CA":     ("Nevada City", "CA"),
    "Pershing County, NV":   ("Lovelock", "NV"),
    "Payette County, ID":    ("Payette", "ID"),
}

# GeoNames feature codes to skip. PPLH is a place that no longer exists, which
# would put a Jefferson town on a ghost site and name it after one.
SKIP_FCODES = {"PPLH", "PPLQ", "PPLW", "PPLCH"}


def _rows(dump: str):
    if not os.path.exists(dump):
        print(f"fetching {DUMP_URL} -> {dump} ...")
        urllib.request.urlretrieve(DUMP_URL, dump)
    member = os.path.basename(DUMP_URL).replace(".zip", ".txt")
    with zipfile.ZipFile(dump) as z:
        if member not in z.namelist():          # a stale cache from another dump
            raise SystemExit(f"{dump} has no {member}: {z.namelist()}")
        for line in z.open(member):
            f = line.decode("utf-8").rstrip("\n").split("\t")
            if f[6] != "P" or f[7] in SKIP_FCODES:
                continue
            yield f[1], f[10], f[11], float(f[4]), float(f[5]), int(f[14] or 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default="/tmp/US.zip")
    ap.add_argument("--per-county", type=int, default=45,
                    help="anchors kept per county; the biggest Jefferson county "
                         "holds ~31 cities, so this leaves real headroom")
    args = ap.parse_args()

    places: list[tuple] = list(_rows(args.dump))
    print(f"{len(places):,} US populated places")

    fips: dict[tuple[str, str], str] = {}
    for real, (seat, st) in SEATS.items():
        hit = [p for p in places if p[0] == seat and p[1] == st]
        if not hit:
            raise SystemExit(f"county seat {seat}, {st} not found in the dump")
        fips[(st, max(hit, key=lambda p: p[5])[2])] = real

    out: dict[str, list] = {real: [] for real in SEATS}
    for name, st, cty, lat, lon, pop in places:
        real = fips.get((st, cty))
        if real:
            out[real].append((name, lat, lon, pop))

    short = []
    for real, rows in out.items():
        rows.sort(key=lambda r: (-r[3], r[0]))
        if len(rows) < args.per_county:
            short.append(f"{real} ({len(rows)})")
        out[real] = [[n, round(la, 4), round(lo, 4)] for n, la, lo, _p in
                     rows[:args.per_county]]
        print(f"  {real:24} {len(out[real]):3}  {out[real][0][0]}")
    if short:
        print("under the per-county target (fine unless Jefferson outgrows it): "
              + ", ".join(short))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "_doc": [
            "Real populated places, largest first, in the twenty real counties",
            "Jefferson stands on. The generator assigns a Jefferson city the",
            "coordinates of the real place at its own population rank within its",
            "county -- see generators/jefferson/gen.py::write_gazetteer and",
            "scripts/build_geo_anchors.py. Regenerate with that script; do not",
            "hand-edit. Source: GeoNames (CC-BY 4.0).",
        ],
        "counties": out,
    }, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
