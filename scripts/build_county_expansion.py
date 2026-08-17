#!/usr/bin/env python3
"""
Populate the nine counties added to the map in 2027-08 — towns, schools and
leagues for ground the state claimed but never settled.

    python3 scripts/build_county_expansion.py [--seed 4127] [--dry-run]

Writes `generators/jefferson/data/expansion_counties.csv`, in the same columns
as `expansion_schools.csv`, which `gen.load_expansion` reads alongside it.

⚠️ WHY A FILE AND NOT A GENERATOR PASS. `Gen.build_schools` is one RNG stream:
every name, classification and enrollment in the founding state comes out of it
in order, and the season is drawn downstream of that. Adding towns inside it
would re-deal the entire state — the mascot draw in that loop carries a comment
saying exactly this, and it is why the 7A roster is a CSV too. So the new ground
is generated HERE, against its own seed, and loaded afterwards. The founding
state stays byte-stable and this file is reviewable as data.

Names are checked against every school and city that already exists — including
the other expansion roster — so nothing collides and no real western place is
reproduced (`names.BLOCKLIST`).

The nine counties, and what they are:

  Vermilion Valley  the rice, orchard and olive country in the far south, on
                    the northern Sacramento Valley floor -- Kernwood (Butte),
                    Olivet (Tehama), Paddock (Glenn), Bardsley (Colusa)
  Siskiyou Valley       the northern Sierra gold country -- Goldbank (Nevada),
                    Featherstone (Plumas), Highgrade (Sierra)
  Scheelite         the Humboldt Sink's tungsten and hay country, filling out
                    North Range (Pershing)
  Barlowe           the orchard bench above the Snake, filling out the Halbrook
                    Basin (Payette)
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.sports import classify              # noqa: E402
from generators.jefferson import names as N   # noqa: E402

OUT = ROOT / "generators/jefferson/data/expansion_counties.csv"
COLUMNS = ["school", "city", "county", "area", "city_population", "enrollment",
           "classification", "private", "naming_type", "mascot", "conference",
           "status"]

# county -> (area, towns, county population, conference)
COUNTIES = [
    ("Kernwood",     "Vermilion Valley", 12, 420_000, "Vermilion Valley Conference"),
    ("Olivet",       "Vermilion Valley",  9, 180_000, "Olive Belt League"),
    ("Paddock",      "Vermilion Valley", 11, 140_000, "Paddock County League"),
    ("Bardsley",     "Vermilion Valley",  6,  70_000, "Bardsley Union League"),
    ("Goldbank",     "Siskiyou Valley",      10, 300_000, "Siskiyou Valley Conference"),
    ("Featherstone", "Siskiyou Valley",       7, 105_000, "Feather River League"),
    ("Highgrade",    "Siskiyou Valley",       4,  38_000, "High Sierra League"),
    ("Scheelite",    "North Range",       5,  52_000, "Sink Valley League"),
    ("Barlowe",      "Halbrook Basin",    7, 190_000, "Barlowe Bench League"),
]

# Town grammar for the new country, in the register names.py already uses:
# stems x endings, fused plat compounds, settler surnames, railroad stops.
STEMS = {
    "Vermilion Valley": ["Levee", "Almond", "Olive", "Vermilion", "Harvest", "Rice",
                         "Walnut", "Grange", "Tule", "Sutter", "Marsh", "Clover",
                         "Bidwell", "Prune", "Chaff", "Canal", "Barley", "Fig"],
    "Siskiyou Valley":      ["Quartz", "Nugget", "Sluice", "Cradle", "Ravine", "Gulch",
                         "Bullion", "Tailing", "Assay", "Cinnabar", "Hydraulic",
                         "Ditch", "Lode", "Feather", "Summit", "Tunnel"],
    "North Range":      ["Alkali", "Tungsten", "Sink", "Borax", "Playa", "Hay",
                         "Saltbush", "Dry", "Sage", "Mirage"],
    "Halbrook Basin":   ["Orchard", "Bench", "Cider", "Snake", "Pear", "Weiser",
                         "Furrow", "Onion", "Hop", "Bramble"],
}
ENDINGS = ["Flat", "Bar", "Crossing", "Bend", "Landing", "Slough", "Diggings",
           "Ferry", "Gap", "Basin", "Springs", "Bluff", "Fork", "Camp", "Wells",
           "Grade", "Reach", "Siding", "Cut", "Head"]
SURNAMES = ["Ainsworth", "Bardsley", "Caverly", "Denholm", "Ewart", "Fenimore",
            "Garrow", "Haddon", "Ingels", "Jessup", "Kilbride", "Lanphere",
            "Mowbray", "Nesbit", "Orkney", "Prescod", "Quill", "Renfrew",
            "Slocum", "Thackeray", "Urquhart", "Vessey", "Wardlow", "Yarrow",
            "Bracken", "Corliss", "Dunmore", "Elverson", "Fairbank", "Gilhooly"]
TAILS = ["Junction", "Siding", "Spur", "Depot", "Switch", "Yard"]

# ⚠️ NOT names.DIRECTIONS — that list carries "Union" and "Heights", which are
# not directions. A Union is two towns that merged their high schools (owner
# rule 2027-08); using it as a compass point produced "Canal Depot Union" in a
# town that had merged with nobody.
DIRECTIONS = ["North", "South", "East", "West", "Central", "Northwest",
              "Southeast", "Northeast", "Southwest"]

# School-name material. The spec asks for the full real-world spread, not just
# place names: directional publics in quantity, people, religious schools across
# denominations, and academies among ordinary publics.
# ⚠️ NO INVENTED PEOPLE (owner rule 2027-08). Schools here are named the way
# real ones are: for the town, for a geographic feature, for a dead president or
# vice president, or — once a town is big enough to need a second school — for
# the town plus a direction ("Bellows Lake North").
#
# Presidents and vice presidents are DEAD ONES ONLY, and the list deliberately
# omits three that no district names a school after any more (Calhoun and
# Breckinridge for the Confederacy, Agnew for resigning in disgrace), plus
# Jefferson itself — the state is called Jefferson and a Jefferson High here
# would read as the state's school, not a president's.
PRESIDENTS = [
    "Washington", "John Adams", "Madison", "Monroe", "John Quincy Adams",
    "Van Buren", "William Henry Harrison", "Tyler", "Polk", "Zachary Taylor",
    "Fillmore", "Franklin Pierce", "Buchanan", "Lincoln", "Ulysses S. Grant",
    "Rutherford Hayes", "Garfield", "Chester Arthur", "Grover Cleveland",
    "Benjamin Harrison", "Theodore Roosevelt", "Taft", "Woodrow Wilson",
    "Coolidge", "Herbert Hoover", "Franklin Roosevelt", "Harry Truman",
    "Eisenhower", "John F. Kennedy", "Lyndon Johnson", "Gerald Ford",
    "Ronald Reagan", "Jimmy Carter", "George H. W. Bush",
]
VICE_PRESIDENTS = [
    "Aaron Burr", "George Clinton", "Elbridge Gerry", "Daniel Tompkins",
    "Richard Mentor Johnson", "George Dallas", "William Rufus King",
    "Hannibal Hamlin", "Schuyler Colfax", "Henry Wilson", "William Wheeler",
    "Thomas Hendricks", "Levi Morton", "Adlai Stevenson", "Garret Hobart",
    "Charles Fairbanks", "James Sherman", "Thomas Marshall", "Charles Dawes",
    "Charles Curtis", "John Nance Garner", "Henry Wallace", "Alben Barkley",
    "Hubert Humphrey", "Nelson Rockefeller", "Walter Mondale",
]

# Geographic features a school gets named for — built from the region's own
# stems, so a Siskiyou Valley school is named for Siskiyou Valley ground.
FEATURE_TAILS = ["Lake", "Ridge", "Butte", "Mesa", "Creek", "Falls", "Bend",
                 "Peak", "Slough", "Bar", "Hollow", "Rim", "Meadows", "Point",
                 "Narrows", "Divide", "Canyon", "Marsh", "Bluffs", "Draw"]
FEATURE_STEMS = ["Bellows", "Kettle", "Antelope", "Willow", "Sandhill", "Heron",
                 "Cinnabar", "Manzanita", "Buckeye", "Sycamore", "Blackbird",
                 "Deer", "Sulphur", "Cottonrock", "Indigo", "Vernal", "Poorman",
                 "Whiskey", "Lonepine", "Redbank", "Coyote", "Steelhead",
                 "Chinook", "Foxtail", "Bittern", "Gravel", "Cathedral"]

# ── FREEDMEN'S SETTLEMENTS ──────────────────────────────────────────────────
# Paddock County is the state's Freedmen's country (owner rule 2027-08), and its
# towns are named the way the real ones were. California had exactly this:
# Allensworth, in the San Joaquin Valley, was founded in 1908 as a Black farming
# colony, and Paddock is the Sacramento-Valley analogue — irrigated ground,
# bought and worked in common.
#
# Three strands, all of them real practice: scripture read as liberation
# (Shiloh, Zion, Canaan, Beulah, Goshen, Promise Land, Free Hill — the impulse
# behind Mound Bayou and Boley); the founders' and leaders' own names (Fort Bardsley,
# Rentie, Tatum, Lyles, Roberts, Douglass, Dunbar, Minnesota City, Langston); and the
# eastern town people had left, carried west (New Piscataway, Camden, Trenton —
# the pattern of New Philadelphia, Illinois).
#
# The first five are the owner's own, by name.
FREEDMEN_TOWNS = [
    "Welsh Plains", "New Piscataway", "Fort Bardsley", "Shiloh", "Zion Hill",
    "Canaan Bend", "Beulah Landing", "Free Hill", "Promise Land", "Camden Flat",
    "Jamaica", "Tatum Station", "Lyles Crossing", "Roberts Settlement",
    "Douglass Grove", "Dunbar Wells", "Minnesota City Bend", "Langston Bar",
    "Mount Olive Flat", "New Trenton",
]
FREEDMEN_COUNTY = "Paddock"

# ── PRIVATE SCHOOLS ─────────────────────────────────────────────────────────
# Built on the naming patterns real American private schools actually use, so
# the set reads like a region's independent sector rather than one idea repeated.
# Catholic schools are the largest and most varied strand, as they are in life:
# saints, but also Bishop/Cardinal/Archbishop, the devotional titles (Sacred
# Heart, Holy Cross, Our Lady of X), and the teaching orders (Jesuit, Marist,
# Salesian, De La Salle, Presentation). Then the evangelical and denominational
# schools, the historic independents (Country Day, Hall, Academy, Friends), a
# classical school and a military academy.
#
# No "High School" or "School" suffix — the association writes a school's name
# the way people say it (owner rule 2027-08).
SAINT_NAMES = ["Aloysius", "Bede", "Brendan", "Cecilia", "Clement", "Dominic",
               "Fiacre", "Genevieve", "Hilary", "Jerome", "Kateri", "Lucy",
               "Monica", "Perpetua", "Rose of Lima", "Sebastian", "Thomas More",
               "Ursula", "Veronica"]
PRELATES = ["Bishop Ryan", "Bishop Kelleher", "Bishop Amat", "Bishop Ferraro",
            "Cardinal Newman", "Cardinal Doyle", "Archbishop Blanchet",
            "Archbishop Quinlan", "Monsignor Barrow"]
DEVOTIONS = ["Sacred Heart", "Holy Cross", "Holy Family", "Immaculate Heart",
             "Christ the King", "Mater Dei", "Our Lady of the Snows",
             "Our Lady of Lourdes", "Notre Dame", "Resurrection", "Corpus Christi"]
ORDERS = ["Jesuit", "Marist", "Salesian", "De La Salle", "Presentation",
          "Carmel", "Serra", "Loyola", "Regis", "Bellarmine", "Xavier"]
EVANGELICAL = ["{} Christian", "{} Baptist", "Grace Christian", "Faith Christian",
               "Calvary Chapel {}", "Bethel Christian", "Cornerstone Christian",
               "Heritage Christian", "Liberty Christian", "Trinity Christian",
               "Victory Christian", "Foothills Christian", "New Hope Christian"]
DENOMINATIONAL = ["{} Lutheran", "Concordia", "Martin Luther", "{} Episcopal",
                  "Trinity Episcopal", "All Saints Episcopal", "{} Adventist Academy",
                  "{} Seventh-day Adventist", "Wesley Methodist", "{} Friends School"]
INDEPENDENT = ["{} Country Day", "{} Day", "{} Preparatory", "{} Collegiate",
               "{} Latin", "{} Academy", "The {} School", "{} Hall",
               "{} Classical Academy", "Veritas Academy", "{} Institute",
               "{} Military Academy", "{} Seminary"]

# Mascots with a reason to be where they are, in the register the state uses.
MASCOTS = {
    "Vermilion Valley": ["Ricebirds", "Olive Pickers", "Levee Rats", "Almond Blossoms",
                         "Threshers", "Sandhill Cranes", "Canal Diggers", "Grangers",
                         "Snow Geese", "Harvesters", "Tule Elk", "Prune Packers",
                         "Combines", "Egrets", "Ditchriders", "Balers"],
    "Siskiyou Valley":      ["Argonauts", "Hydraulickers", "Stampmillers", "Nuggets",
                         "Quartz Hounds", "Highgraders", "Cradlers", "Powder Monkeys",
                         "Tunnel Rats", "Assayers", "River Otters", "Sluicers",
                         "Snowshoers", "Ravens", "Bullion", "Pack Mules"],
    "North Range":      ["Tungsten", "Alkali Cats", "Playa Dogs", "Haywagons",
                         "Sinkholes", "Borax Teams", "Dust Devils", "Pronghorns"],
    "Halbrook Basin":   ["Orchardists", "Cider Pressers", "Benchriders", "Onion Toppers",
                         "Hop Pickers", "Pear Packers", "Furrows", "Bramblers"],
}

# Enrollment comes from the town, not from a band: about 5.2% of a place's
# people are of high-school age, split across its schools. Classification is
# then whatever app.sports.classify() says that enrollment is — one ladder, and
# the size of a school follows from the size of its town rather than the other
# way round.
HS_SHARE = 0.052


def existing_names() -> tuple[set[str], set[str]]:
    """Every school and place already spoken for, so nothing collides."""
    schools, places = set(), set()
    orgs = json.loads((ROOT / "records/orgs/schools.json").read_text())
    for s in (orgs["schools"] if isinstance(orgs, dict) else orgs):
        schools.add(s["name"].lower())
        places.add(s["city"].lower())
    for c in json.loads((ROOT / "records/orgs/cities.json").read_text())["cities"]:
        places.add(c["name"].lower())
    with open(ROOT / "generators/jefferson/data/expansion_schools.csv") as fh:
        for r in csv.DictReader(fh):
            schools.add(r["school"].lower())
            places.add(r["city"].lower())
    places |= {p.lower() for p in N.BLOCKLIST}
    schools |= {p.lower() for p in N.BLOCKLIST}
    return schools, places


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=4127)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    used_schools, used_places = existing_names()

    statesmen = list(PRESIDENTS) + list(VICE_PRESIDENTS)
    rng.shuffle(statesmen)
    features = [f"{a} {b}" for a in FEATURE_STEMS for b in FEATURE_TAILS]
    rng.shuffle(features)

    def town_name(area, big=False) -> str:
        """`big` is a county's largest towns — they read as cities, so they take
        the settler-surname and stem-and-ending forms and never the fused plat
        compounds, which sound like the hamlets they are ("Prunehaven")."""
        stems = STEMS[area]
        while True:
            roll = rng.random() * (0.88 if big else 1.0)
            if roll < 0.40:
                n = f"{rng.choice(stems)} {rng.choice(ENDINGS)}"
            elif roll < 0.70:
                base = rng.choice(SURNAMES)
                tails = ["ville", " City", " Bar"] + \
                    ([] if base.endswith("s") else ["s Landing"])
                n = base if rng.random() < 0.55 else base + rng.choice(tails)
            elif roll < 0.88:
                n = f"{rng.choice(SURNAMES + stems)} {rng.choice(TAILS)}"
            else:
                n = rng.choice(stems) + rng.choice(["wood", "ford", "mont", "burg",
                                                    "ton", "field", "haven"]).lower()
            if n.lower() not in used_places:
                used_places.add(n.lower())
                return n

    def private_name(city, county):
        """One private school, drawn from the strand weights an American region
        actually shows: Catholic largest and most varied, then evangelical, the
        older denominations, and the independents."""
        for _ in range(40):
            r = rng.random()
            if r < 0.20:
                nm = f"St. {rng.choice(SAINT_NAMES)}"
                if rng.random() < 0.45:
                    nm += rng.choice([" Academy", " Preparatory", " Catholic"])
            elif r < 0.30:
                nm = rng.choice(PRELATES)
            elif r < 0.40:
                nm = rng.choice(DEVOTIONS)
            elif r < 0.48:
                base = rng.choice(ORDERS)
                nm = f"{base} {city}" if rng.random() < 0.5 else f"{base} Academy"
            elif r < 0.53:
                # the owner's ask: some county-flavoured religious schools
                nm = f"{county} County {rng.choice(['Catholic', 'Christian'])}"
            elif r < 0.72:
                nm = rng.choice(EVANGELICAL).format(rng.choice([city, county]))
            elif r < 0.84:
                nm = rng.choice(DENOMINATIONAL).format(rng.choice([city, county]))
            else:
                nm = rng.choice(INDEPENDENT).format(
                    rng.choice([city, county, rng.choice(SURNAMES)]))
            if nm.lower() not in used_schools:
                return nm
        return None

    def unique(name: str, city: str = "", county: str = "") -> str:
        """⚠️ Never disambiguate with "Union" (owner rule 2027-08): a Union is
        two towns that merged their high schools, not a suffix for a name
        already taken. A clash falls back to the plainest real answer — the
        town, then the town and a direction."""
        if name.lower() not in used_schools:
            used_schools.add(name.lower())
            return name
        for alt in [city] + [f"{city} {d}" for d in DIRECTIONS] + \
                   [f"{county} County {d}" for d in DIRECTIONS]:
            if alt and alt.lower() not in used_schools:
                used_schools.add(alt.lower())
                return alt
        raise SystemExit(f"cannot disambiguate {name!r} in {city}")

    rows = []
    for county, area, n_towns, county_pop, conference in COUNTIES:
        county_school_left = 1     # a county has ONE school named for it
        # One town carries a third of the county, the rest fall away on a curve
        # -- which is how a rural county's seat actually sits against its towns.
        shares = [1 / (i + 1) ** 1.35 for i in range(n_towns)]
        tot = sum(shares)
        named = list(FREEDMEN_TOWNS) if county == FREEDMEN_COUNTY else []
        towns = []
        for i in range(n_towns):
            pop = max(400, int(round(county_pop * shares[i] / tot, -2)))
            if named:
                nm = named.pop(0)
                used_places.add(nm.lower())
            else:
                nm = town_name(area, big=i < 2)
            towns.append((nm, pop))

        for city, pop in towns:
            k = max(1, min(8, round(pop / 22_000)))
            dirs = list(DIRECTIONS)
            rng.shuffle(dirs)
            for i in range(k):
                if (i == 0 and k == 1 and len(towns) > 3 and city == towns[-1][0]
                        and rng.random() < 0.55):
                    # the two smallest towns in the county merged their schools
                    nm, kind = f"{towns[-2][0]}-{city} Union", "union district"
                elif i == 0 and k == 1 and county_school_left and rng.random() < 0.28:
                    county_school_left = 0
                    # rural consolidations carry the county, not the town
                    nm, kind = f"{county} County", "county consolidation"
                elif i == 0:
                    nm, kind = city, "city flagship"
                else:
                    roll = rng.random()
                    if roll < 0.38 and dirs:
                        nm, kind = f"{city} {dirs.pop()}", "directional"
                    elif roll < 0.72 and statesmen:
                        nm, kind = statesmen.pop(), "president/vice president"
                    elif features:
                        nm, kind = features.pop(), "geographic feature"
                    else:
                        nm, kind = (f"{city} {dirs.pop()}" if dirs else city), \
                            "directional"
                # a school's students are its share of the town's teenagers,
                # the flagship taking the larger cut
                share = pop / max(1, k) * (1.18 if i == 0 else 0.88)
                enroll = max(58, min(2_500,
                                     int(share * HS_SHARE * rng.uniform(0.82, 1.18))))
                rows.append(dict(
                    school=unique(nm, city, county), city=city, county=county, area=area,
                    city_population=pop, enrollment=enroll,
                    classification=classify(enroll), private=False, naming_type=kind,
                    mascot=rng.choice(MASCOTS[area]), conference=conference,
                    status="new"))

            # Private schools take a real share of a town's students, which is
            # how a place of 90,000 supports several schools instead of one
            # enormous one — the owner's rule that you open another school
            # before a public reaches 3,000. Roughly one per 30,000 people,
            # and none in a town too small to fill one.
            for _ in range(int(pop // 30_000) + (1 if pop > 12_000
                                                 and rng.random() < 0.45 else 0)):
                nm = private_name(city, county)
                if nm is None:
                    break
                enroll = max(58, int(pop * HS_SHARE * rng.uniform(0.03, 0.10)))
                rows.append(dict(
                    school=unique(nm, city, county), city=city, county=county, area=area,
                    city_population=pop, enrollment=enroll,
                    classification=classify(enroll), private=True,
                    naming_type="private/independent",
                    mascot=rng.choice(MASCOTS[area]), conference=conference,
                    status="new"))

    import collections
    print(f"{len(rows)} schools · {len({r['city'] for r in rows})} towns · "
          f"{len(COUNTIES)} counties · "
          f"{sum(p for _c, _a, _t, p, _f in COUNTIES):,} people")
    for county, area, _t, pop, _f in COUNTIES:
        mine = [r for r in rows if r["county"] == county]
        print(f"  {county:13} {area:17} {len({r['city'] for r in mine}):2} towns "
              f"{len(mine):3} schools  {pop:>8,}")
    print("  classes:", dict(sorted(collections.Counter(
        r["classification"] for r in rows).items())))

    if args.dry_run:
        return 0
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
