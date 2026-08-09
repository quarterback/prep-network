"""
Mascots for the Jefferson schools.

    python3 -m generators.jefferson.mascots [--check]

Three things make a mascot list read as real, and the previous one — 36 names
dealt out uniformly to 840 schools, so the commonest appeared 28 times and
nothing appeared once — had none of them.

**1. The frequency curve is steep and long-tailed.** Massey's national database
is the shape to copy: Eagles 1,229 high schools, Tigers 879, Panthers 827, and
then a tail of *thousands* of names used once. Roughly a fifth of American high
schools share the top dozen names, and roughly a third have a name almost
nobody else has. A uniform draw over a small list produces neither end of that.

**2. The common names are national, the odd ones are LOCAL.** Nobody invents
"Eagles" — it arrives from everywhere. But Hoopeston's Cornjerkers, Jordan's
Beetdiggers, Cairo's Syrupmakers, Tillamook's Cheesemakers and Chinook's
Sugarbeeters are all a town describing its own work, and they exist in exactly
one place each. So the tail here is generated from the *area's* economy — the
mining country gets Orediggers and Highgraders, the port gets Dorymen and
Netmenders, the orchard country gets Appleknockers — and each of those is used
once or twice in the whole state.

**3. Fauna beyond North America.** A state that only knows eagles, bears and
wildcats has a smaller imagination than the schools it is modelling. Species
from South America, Africa, Asia, Europe and Australasia are in the tail, and
they land where a school has some reason to reach for one — metro magnets,
international academies, private schools — rather than being sprinkled evenly
over ranch country. This is a deliberate stretch: a real Oregon 1A school is
not the Pangolins. It is here because variety is the point, and it is kept to
the tail so it never crowds out the names that make the state feel American.

Where the line is on Indigenous names
-------------------------------------
Not a blanket exclusion, because a blanket exclusion is the lazy read and it
throws away a naming layer the region genuinely has.

**Out: a people used as a mascot.** Indians, Braves, Chiefs, Chieftains,
Redskins, Redmen, Savages, Apaches, Mohawks, Seminoles, Sioux, and every tribal
name. They fill the Massey list — Indians alone is 418 high schools, the
eleventh most common name in the country — and they are being retired
nationally, several states by statute. The handful of real programmes that keep
one do it under an explicit agreement with the nation whose name it is; a
fictional state cannot claim a relationship it does not have.

**In: words from the region's Indigenous languages for weather, water, animals
and land.** ``CHINOOK_JARGON`` below is drawn from the Pacific Northwest trade
pidgin and neighbouring languages — *skookum* (strong), *hyak* (swift),
*chinook* (the wind, and the salmon), *kokanee* (landlocked sockeye), *wapiti*
(elk), *sasquatch* (from Halkomelem *sásq'ets*). These name a thing, not a
people, and several are already ordinary English: they are the same layer the
state's own map is built from, since Jefferson's regions are Klamath, Owyhee,
Shasta and Siskiyou. Hyaks, Chinooks, Nanooks, Wapiti, Sasquatch and Kokanee
Salmon are all real, current, uncontroversial school mascots.

The distinction is the one the retirement campaigns themselves draw, and it is
worth getting right rather than flattening.

Assignment is a **post-pass over the finished school records**, keyed on the
school's own name, so it costs the state generator no RNG draws and re-running
it cannot shift a single game result.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RECORDS = ROOT / "records"

# ───────────────────────────────────────────────────────── the national core
#
# Weights are Massey's high-school counts, which gives the real curve for free
# rather than a guess at one. Names carrying Native American imagery are
# removed (see the module docstring); the rest of the ordering is untouched.

COMMON: list[tuple[str, int]] = [
    ("Eagles", 1229), ("Tigers", 879), ("Panthers", 827), ("Bulldogs", 802),
    ("Warriors", 698), ("Wildcats", 702), ("Lions", 571), ("Cougars", 484),
    ("Knights", 444), ("Mustangs", 426), ("Falcons", 381), ("Trojans", 378),
    ("Vikings", 362), ("Rams", 310), ("Spartans", 304), ("Raiders", 299),
    ("Cardinals", 287), ("Patriots", 286), ("Hawks", 242), ("Pirates", 258),
    ("Bears", 235), ("Hornets", 259), ("Crusaders", 234), ("Bobcats", 188),
    ("Titans", 165), ("Saints", 157), ("Rebels", 178), ("Jaguars", 164),
    ("Blue Devils", 172), ("Chargers", 153), ("Wolves", 153), ("Huskies", 148),
    ("Wolverines", 142), ("Dragons", 129), ("Yellowjackets", 150),
    ("Pioneers", 106), ("Lancers", 106), ("Red Devils", 116), ("Rockets", 106),
    ("Cavaliers", 93), ("Golden Eagles", 78), ("Comets", 87), ("Broncos", 81),
    ("Bearcats", 84), ("Rangers", 70), ("Gators", 76), ("Royals", 59),
    ("Bruins", 68), ("Owls", 64), ("Cowboys", 69), ("Grizzlies", 63),
    ("Buccaneers", 56), ("Hurricanes", 62), ("Longhorns", 72),
    ("Red Raiders", 70), ("Generals", 55), ("Coyotes", 53), ("Colts", 57),
    ("Greyhounds", 57), ("Highlanders", 53), ("Mavericks", 45),
    ("Thunderbirds", 42), ("Bluejays", 57), ("Tornadoes", 48), ("Sharks", 40),
    ("Beavers", 41), ("Buffaloes", 47), ("Bison", 41), ("Blazers", 36),
    ("Timberwolves", 42), ("Bombers", 34), ("Mountaineers", 37),
    ("Monarchs", 33), ("Roadrunners", 22), ("Seahawks", 29), ("Flyers", 28),
    ("Phoenix", 31), ("Ravens", 30), ("Leopards", 34), ("Cyclones", 24),
    ("Gladiators", 25), ("Cobras", 29), ("Lynx", 23), ("Golden Bears", 28),
    ("Lumberjacks", 24), ("Miners", 29), ("Stallions", 28), ("Marauders", 28),
    ("Clippers", 25), ("Firebirds", 25), ("Badgers", 26), ("Flames", 18),
    ("Griffins", 23), ("Colonels", 26), ("Green Wave", 31), ("Minutemen", 30),
    ("Trailblazers", 20), ("Dolphins", 18), ("Lobos", 25), ("Maroons", 24),
    ("Scots", 19), ("Nighthawks", 17), ("Cadets", 26), ("Bucks", 23),
    ("Dons", 23), ("Pumas", 22), ("Rattlers", 17), ("Terriers", 18),
    ("Elks", 23), ("Scorpions", 16), ("Polar Bears", 19), ("Shamrocks", 19),
    ("Centurions", 14), ("Defenders", 13), ("Sabers", 15), ("Aztecs", 15),
    ("Gaels", 15), ("Pilots", 12), ("Matadors", 15), ("Foxes", 15),
    ("Mules", 12), ("Norsemen", 9), ("Ducks", 6), ("Kangaroos", 7),
    ("Gophers", 10), ("Marlins", 7), ("Pelicans", 7), ("Jackrabbits", 9),
    ("Whippets", 10), ("Stags", 8), ("Unicorns", 9), ("Antelopes", 7),
    ("Gorillas", 6), ("Penguins", 3), ("Otters", 3), ("Zebras", 7),
    ("Camels", 4), ("Catamounts", 3), ("Ospreys", 2), ("Herons", 1),
    ("Kestrels", 2), ("Sagehens", 1), ("Salukis", 1), ("Wapiti", 1),
]

#: Colour and intensifier prefixes. Massey is full of them — Golden Eagles,
#: Red Devils, Blue Jays, Fighting Irish — and they are a cheap, authentic
#: source of variety because the same animal reads as a different school.
PREFIXES = [
    "Golden", "Red", "Blue", "Green", "Silver", "Crimson", "Purple", "Scarlet",
    "Black", "White", "Grey", "Maroon", "Orange", "Fighting", "Flying",
    "Roaring", "Mighty", "Little", "Big", "Iron", "Wild",
]

# ─────────────────────────────────────────────────── local, by what a place does
#
# The genuinely odd names, invented the way real ones were: a town naming its
# own work, weather or landscape. Each is rare — most appear once in the state.

LOCAL: dict[str, list[str]] = {
    "Halbrook Basin": [            # the big agricultural interior
        "Beetdiggers", "Haybalers", "Threshers", "Grangers", "Sugarbeeters",
        "Combines", "Hopgrowers", "Silos", "Cannery", "Creamery",
        "Beanpickers", "Milkmen", "Dusters", "Plowboys", "Sodbusters",
        "Windrowers", "Grainmen", "Harvesters", "Seeders", "Cornjerkers",
    ],
    "Gold Valley": [               # mining heritage
        "Orediggers", "Hardrockers", "Sluicers", "Highgraders", "Muckers",
        "Assayers", "Nuggets", "Tailings", "Powder Monkeys", "Stampeders",
        "Pickmen", "Quarriers", "Dredgers", "Claimjumpers", "Goldbacks",
        "Sourdoughs", "Prospectors", "Smelters",
    ],
    "Ashbury Metro": [             # the city
        "Streetcars", "Ironworkers", "Machinists", "Foundrymen", "Draftsmen",
        "Skyliners", "Brickies", "Riveters", "Printers", "Signalmen",
        "Trolleys", "Boilermakers", "Cablecars", "Union",
    ],
    "Harborline": [                # the working port
        "Dorymen", "Crabbers", "Netmenders", "Bar Pilots", "Longshore",
        "Lightkeepers", "Fogbells", "Cannerymen", "Tidewater", "Shipwrights",
        "Dredgemen", "Harpooners", "Whalers", "Trollers", "Gillnetters",
        "Baymen", "Wharfmen", "Chandlers",
    ],
    "South Coast": [               # beaches, dunes, small fishing towns
        "Breakers", "Surfriders", "Sandpipers", "Dunerunners", "Tidepools",
        "Combers", "Driftwood", "Conchs", "Seasiders", "Cormorants",
        "Riptide", "Undertow", "Saltdogs", "Kelpers",
    ],
    "Sage Plains": [               # high desert ranching
        "Buckaroos", "Wranglers", "Ropers", "Brandsmen", "Dust Devils",
        "Irrigators", "Windmills", "Alkali", "Jackrabbits", "Tumbleweeds",
        "Drovers", "Horsebreakers", "Waterhaulers", "Rimrockers",
    ],
    "Juniper Highlands": [         # juniper, sage, scattered ranches
        "Junipers", "Sagebrush", "Chukars", "Rockchucks", "Cinderpits",
        "Mesa Riders", "Bunchgrass", "Hawkwatch", "Stonecutters", "Basalt",
    ],
    "Cascade Divide": [            # volcanic peaks, snow
        "Lava Bears", "Cinder Cones", "Snowcats", "Avalanche", "Timberline",
        "Glaciers", "Summiteers", "Icefall", "Cornice", "Pumice",
        "Snowshoes", "Alpenglow", "Crevasse",
    ],
    "Timber Valley": [             # forestry
        "Highclimbers", "Whistle Punks", "Fallers", "Peelers", "Shakesplitters",
        "Choppers", "Tie Hackers", "Riggers", "Sawyers", "Papermakers",
        "Millhands", "Bullbuckers", "Logrollers", "Barkers",
    ],
    "North Range": [               # remote, cold, ranching and rail
        "Brakemen", "Gandy Dancers", "Switchmen", "Roundhouse", "Sheepherders",
        "Linemen", "Snowplows", "Mailriders", "Sectionmen", "Waystation",
    ],
}

# ─────────────────────────────────────── fauna the rest of the world actually has
#
# Grouped by where the animal is from, which is the point: the list exists so
# the state's tail is not one continent's worth of megafauna. Weighted low and
# steered toward metro, magnet and private schools.

WORLD_FAUNA: dict[str, list[str]] = {
    "South America": [
        "Condors", "Capybaras", "Caimans", "Tapirs", "Ocelots", "Maned Wolves",
        "Rheas", "Toucans", "Macaws", "Howlers", "Coatis", "Guanacos",
        "Vicunas", "Anacondas", "Piranhas", "Jacanas", "Hoatzins",
        "Titan Beetles", "Army Ants", "Morpho", "Kinkajous", "Oropendolas",
    ],
    "Africa": [
        "Honey Badgers", "Servals", "Caracals", "Oryx", "Kudu", "Gerenuk",
        "Fennecs", "Pangolins", "Secretarybirds", "Hornbills", "Shoebills",
        "Okapi", "Warthogs", "Meerkats", "Aardvarks", "Cheetahs", "Sitatunga",
        "Springbok", "Bongos", "Scarabs", "Goliath Beetles", "Weaverbirds",
        "Nyala", "Dik-Diks", "Hamerkops",
    ],
    "Asia": [
        "Snow Leopards", "Markhor", "Takin", "Serows", "Binturongs",
        "Sun Bears", "Dholes", "Sarus Cranes", "Kingfishers", "Yaks",
        "Saiga", "Water Buffalo", "Atlas Moths", "Giant Hornets", "Gaur",
        "Clouded Leopards", "Muntjac", "Tahr", "Bharal", "Langurs",
        "Mandarins", "Pheasants",
    ],
    "Europe": [
        "Ibex", "Chamois", "Wisent", "Choughs", "Puffins", "Stoats",
        "Adders", "Stag Beetles", "Boars", "Aurochs", "Griffons", "Pine Martens",
        "Corncrakes", "Capercaillie", "Firecrests", "Mouflon", "Polecats",
    ],
    "Australasia": [
        "Kookaburras", "Quolls", "Wombats", "Cassowaries", "Bilbies",
        "Numbats", "Taipans", "Huntsmen", "Currawongs", "Galahs", "Emus",
        "Dingoes", "Thorny Devils", "Kea", "Tuatara", "Bogongs", "Potoroos",
        "Frilled Lizards", "Lyrebirds", "Wedgetails",
    ],
}

#: Words from Chinook Jargon and neighbouring Pacific Northwest languages, for
#: weather, water, animals and land — never for a people. See the module
#: docstring for where that line sits and why it is not a blanket exclusion.
#: These weight into the mountain, forest, river and coastal areas, which is
#: where the real ones are: Hyaks in the Cascades, Chinooks on the Columbia.
CHINOOK_JARGON = [
    "Chinooks",        # the warm wind, and the king salmon
    "Skookums",        # strong, powerful
    "Hyaks",           # swift
    "Kokanee",         # landlocked sockeye
    "Sasquatch",       # from Halkomelem sásq'ets
    "Wapiti",          # elk
    "Skookumchuck",    # strong water — rapids
    "Tumwater",        # falling water
    "Olallie",         # berry
]

#: Areas whose landscape those words actually describe.
JARGON_AREAS = {
    "Cascade Divide", "Timber Valley", "Harborline", "South Coast",
    "North Range", "Juniper Highlands",
}

#: Insects and other invertebrates, kept as their own group because they are
#: badly under-used — Massey has Hornets 259 and Yellowjackets 150 and then
#: almost nothing until Boll Weevils and Fire Ants in the single digits.
BUGS = [
    "Mantids", "Cicadas", "Fireflies", "Dragonflies", "Locusts", "Hornbeetles",
    "Weevils", "Waterstriders", "Damselflies", "Katydids", "Glowworms",
    "Leafcutters", "Longhorn Beetles", "Skimmers",
]

# ──────────────────────────────────────────────────────────────── assignment

#: Share of schools that get something other than a national-core name. The
#: rest of the curve is the core's own Massey weights.
LOCAL_SHARE = 0.20        # a town naming its own work
WORLD_SHARE = 0.11        # fauna from elsewhere
BUG_SHARE = 0.03
JARGON_SHARE = 0.05       # only in the areas the words describe
PREFIX_CHANCE = 0.16      # "Golden Eagles" rather than "Eagles"


def _pools(area: str, private: bool, metro: bool):
    """The tail a given school can draw from.

    A world-fauna name is much likelier at a metro or private school than at a
    ranch-country 1A, and a local trade name is the reverse — that is what keeps
    the exotic tail from reading as noise sprinkled evenly over the state.
    """
    world_w = WORLD_SHARE * (2.2 if (private or metro) else 0.45)
    local_w = LOCAL_SHARE * (0.5 if metro else 1.25)
    return world_w, local_w


def assign(schools: list[dict], seed: int = 11) -> dict[str, str]:
    """Give every school a mascot. Deterministic, and independent of the state
    generator's RNG — keyed on the school's own name, so adding this cannot
    move a single game result."""
    core_names = [n for n, _ in COMMON]
    core_weights = [w for _, w in COMMON]

    world_flat = [(name, region) for region, names in WORLD_FAUNA.items()
                  for name in names]

    # Local names are consumed, not sampled: each belongs to one town, and two
    # schools calling themselves the Cornjerkers would undo the point of them.
    local_left = {area: list(names) for area, names in LOCAL.items()}
    for names in local_left.values():
        random.Random(seed).shuffle(names)

    out: dict[str, str] = {}
    # Sort so consumption order is stable no matter how the records are listed.
    for s in sorted(schools, key=lambda s: s["name"]):
        rng = random.Random(zlib.crc32(f"{seed}:{s['name']}".encode()))
        area = s.get("area", "")
        metro = "Metro" in area
        world_w, local_w = _pools(area, s.get("private", False), metro)

        roll = rng.random()
        pick = None
        if roll < local_w and local_left.get(area):
            pick = local_left[area].pop()
        elif roll < local_w + world_w:
            pick = rng.choice(world_flat)[0]
        elif roll < local_w + world_w + BUG_SHARE:
            pick = rng.choice(BUGS)
        elif (area in JARGON_AREAS
              and roll < local_w + world_w + BUG_SHARE + JARGON_SHARE):
            pick = rng.choice(CHINOOK_JARGON)
        else:
            pick = rng.choices(core_names, weights=core_weights, k=1)[0]
            # Only the core takes a colour prefix: "Golden Eagles" is a real
            # pattern, "Golden Cornjerkers" is not.
            if rng.random() < PREFIX_CHANCE and " " not in pick:
                pick = f"{rng.choice(PREFIXES)} {pick}"
        out[s["name"]] = pick
    return out


def apply(records_dir: pathlib.Path = RECORDS, seed: int = 11) -> dict[str, str]:
    path = records_dir / "orgs" / "schools.json"
    doc = json.loads(path.read_text())
    mapping = assign(doc["schools"], seed)
    for s in doc["schools"]:
        s["mascot"] = mapping[s["name"]]
    path.write_text(json.dumps(doc, indent=1) + "\n")
    return mapping


def report(mapping: dict[str, str]) -> None:
    import collections

    c = collections.Counter(mapping.values())
    n = len(mapping)
    once = sum(1 for v in c.values() if v == 1)
    twice = sum(1 for v in c.values() if v == 2)
    print(f"{n} schools · {len(c)} distinct mascots "
          f"({len(c) / n:.0%} as many names as schools)")
    print(f"  used once: {once} ({once / len(c):.0%} of names)  ·  twice: {twice}")
    print(f"  most common: {c.most_common(1)[0][1]} schools "
          f"({c.most_common(1)[0][1] / n:.1%})")
    print("  top 12:", ", ".join(f"{k} {v}" for k, v in c.most_common(12)))
    tail = [k for k, v in c.items() if v == 1]
    print("  a few singletons:", ", ".join(sorted(tail)[:14]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default=str(RECORDS))
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--check", action="store_true",
                    help="report the distribution without writing")
    args = ap.parse_args()
    d = pathlib.Path(args.records)
    if args.check:
        doc = json.loads((d / "orgs" / "schools.json").read_text())
        report(assign(doc["schools"], args.seed))
        return 0
    report(apply(d, args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
