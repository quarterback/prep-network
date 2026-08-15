"""
Naming material for Jefferson. Pools + grammar, not hand-invention.

School names deliberately span the full real-world spread: directional publics
(North/South/East/West/Central + city), people (surname schools), religious
schools across denominations (Catholic saints, Baptist, Episcopal, Methodist,
Lutheran, nondenominational Christian), colors, places, and things, plus
academies and preps. Everything runs through collision checks and a blocklist
of real western cities and schools.
"""

# ---- town naming ------------------------------------------------------------
# A real western map is not one grammar. Its towns came from different decades
# and different actors: fused compounds platted by land companies (Ashford,
# Silverton), settler surnames left by homesteads and post offices (Glenn,
# Merrill), names the railroad assigned (Doyle Junction), and one-word oddities
# nobody can fully explain (Keno, Bly, Drain). One two-word template produces a
# fantasy map; the mix below produces a state.

STEMS = [
    "Alder", "Juniper", "Cedar", "Granite", "Copper", "Silver", "Summit", "Sage",
    "Pine", "Fox", "Eagle", "Clear", "Black", "Red", "Elk", "Bear", "Lost", "High",
    "Gold", "Iron", "Aspen", "Willow", "Hawk", "Stone", "Deer",
    "Antler", "Basalt", "Madrone", "Manzanita", "Obsidian", "Tamarack", "Larch",
    "Camas", "Bitter", "Wolf", "Raven", "Osprey", "Trout", "Salmonberry", "Huckle",
]
ENDINGS = [
    "Bay", "Falls", "Ridge", "Valley", "Basin", "Creek", "Springs",
    "Pass", "Harbor", "Point", "Prairie", "Fork", "Lake", "Mesa", "Bluff",
    "Glen", "Hollow", "Flat", "Landing", "Meadows", "Gap", "Butte",
]

# fused plat-map compounds: stem + suffix as ONE word (Alderton, Copperfield)
FUSE_STEMS = [
    "Alder", "Ash", "Brack", "Carver", "Cole", "Copper", "Dray", "Elm", "Farley",
    "Garner", "Gray", "Hale", "Kel", "Lin", "Marsh", "Mill", "Nor", "Oak", "Pell",
    "Quar", "Ren", "Sil", "Stan", "Thorn", "Wal", "Wick", "Win", "Yar",
]
FUSE_SUFFIXES = ["ton", "ford", "dale", "burg", "field", "mont", "wood", "view",
                 "vale", "port", "mere", "brook", "stead", "well"]

# settler-surname towns (a post office named for whoever ran it)
TOWN_SURNAMES = [
    "Averill", "Bidwell", "Colby", "Doyle", "Ferris", "Garrity", "Harmon",
    "Kendrick", "Loomis", "Mabry", "Merrick", "Naylor", "Odell", "Purcell",
    "Ransom", "Selby", "Tindall", "Ulery", "Vance", "Weller", "Yandell",
    "Etchart", "Ansotegui",   # Basque ranching country, SE corner — real heritage
]

# what the railroad called the stop
RAIL_TAILS = ["Junction", "Crossing", "Siding", "Spur", "Bar"]

# one-word towns with no surviving explanation
ODDITIES = [
    "Galena", "Cinder", "Tule", "Windrow", "Fiddletown", "Placer", "Assay",
    "Rimrock", "Lodestone", "Cutbank", "Sixes", "Halfway House", "Tallow",
    "Whistle Stop", "Ninemile", "Rye", "Flume", "Cinnabar", "Stovepipe",
]

# real western places the grammar must never produce (city or school)
BLOCKLIST = {
    "medford", "ashland", "klamath falls", "grants pass", "roseburg", "coos bay",
    "redding", "eureka", "arcata", "chico", "red bluff", "susanville", "alturas",
    "yreka", "weed", "mount shasta", "crescent city", "brookings", "lakeview",
    "burns", "ontario", "vale", "nyssa", "reno", "sparks", "winnemucca", "nampa",
    "caldwell", "meridian", "eagle point", "shady cove", "talent", "phoenix",
    "gold beach", "bandon", "florence", "fortuna", "ukiah", "willits", "quincy",
    "chester", "westwood", "paradise", "oroville", "corning", "orland", "willows",
    "bend", "eugene", "silverton", "lostine", "sisters", "prineville", "payette",
    "fruitland", "weiser", "marsing", "homedale", "elko", "cascade", "skyline",
    "ashton", "ashford", "silverdale", "oakdale", "ferndale", "cedarville",
    "greenfield", "fairfield", "goldendale", "oakland", "oakridge", "glendale",
    "millbrook", "linton", "walton", "stanfield", "stanwood", "renton", "colton",
    "halfway", "granger", "loomis", "colby", "odell", "merrill", "doyle", "vance",
    "bly", "keno", "dairy", "bonanza", "drain", "glenn", "malin", "dorris",
}

# owner-specified cities (2027-08): place, population, region, and — where
# given — the exact school list. Plainfield's three schools appear exactly as
# written: the city is their location, not part of their names.
NAMED_CITIES = [
    ("Plainfield", 84_323, "Timber Valley",
     ["George Washington Carver", "Benjamin F. Harding", "Plainfield Science"]),
    ("Leidesdorff", 56_304, "Gold Valley", ["Leidesdorff"]),
    ("Newark River", 60_029, "Harborline", None),
    ("Santa Laura", 58_650, "South Coast", None),
    ("Hetfield", 17_340, "North Range", None),
    ("New Leiden", 35_738, "Cascade Divide", None),
    ("Annie Springs", 24_420, "Cascade Divide", None),
    ("Latgaway", 28_411, "Sage Plains", None),
    ("Netherwood", 31_754, "Timber Valley", None),
]

# ---- counties ---------------------------------------------------------------
# Jefferson sits on a real footprint (southern Oregon, far-northern California,
# NW Nevada, the SW Idaho corner). Counties are fictional; each maps to the
# real county whose ground it stands on. The school-name pool's county schools
# (Marlow County, Sablewood Regional) come from these, so a county school sits
# in its own county.
COUNTY_GEO = {
    "Ashbury Metro":     [("Marlow", "Jackson County, OR"),
                          ("Camas", "Josephine County, OR")],
    "Harborline":        [("Bidwell", "Coos County, OR"),
                          ("Weller", "Curry County, OR")],
    "South Coast":       [("Ostrander", "Del Norte County, CA"),
                          ("San Marcos", "Humboldt County, CA")],
    "Halbrook Basin":    [("Halbrook", "Canyon County, ID"),
                          ("Vance", "Owyhee County, ID")],
    "Cascade Divide":    [("Tamarack", "Klamath County, OR"),
                          ("Cinder", "Siskiyou County, CA")],
    "Juniper Highlands": [("Rimrock", "Lake County, OR"),
                          ("Juniper", "Modoc County, CA")],
    "Sage Plains":       [("Emigrant", "Harney County, OR"),
                          ("Stagewater", "Malheur County, OR")],
    "Timber Valley":     [("Antler", "Douglas County, OR")],
    "Gold Valley":       [("Sablewood", "Trinity County, CA"),
                          ("Ferris", "Shasta County, CA")],
    "North Range":       [("Windrow", "Lassen County, CA"),
                          ("Lodestone", "Humboldt County, NV"),
                          ("Galena", "Washoe County, NV"),
                          ("Scheelite", "Pershing County, NV")],
    # ── the 2027-08 expansion ────────────────────────────────────────────────
    # The state map claimed twenty-nine real counties and only twenty carried a
    # Jefferson county; these are the other nine. Two are fill-ins for areas
    # that already existed (Scheelite above, Barlowe below); the other seven
    # are genuinely new country and get two new areas of their own — the
    # rice-and-orchard valley in the far south, and the gold country in the
    # northern Sierra.
    "Vermilion Valley":  [("Kernwood", "Butte County, CA"),
                          ("Olivet", "Tehama County, CA"),
                          ("Paddock", "Glenn County, CA"),
                          ("Bardsley", "Colusa County, CA")],
    "Mother Lode":       [("Goldbank", "Nevada County, CA"),
                          ("Featherstone", "Plumas County, CA"),
                          ("Highgrade", "Sierra County, CA")],
}
COUNTY_GEO["Halbrook Basin"].append(("Barlowe", "Payette County, ID"))

# metro/anchor cities pinned to their county (the rest hash into their area's)
COUNTY_PINS = {
    "Ashbury": "Marlow", "Port Meridian": "Bidwell", "Halbrook": "Halbrook",
    "Plainfield": "Antler", "Leidesdorff": "Sablewood", "Newark River": "Weller",
    "Santa Laura": "San Marcos", "Hetfield": "Windrow", "New Leiden": "Tamarack",
    "Annie Springs": "Cinder", "San Aurelio": "San Marcos",
    "Puerto Alma": "San Marcos", "Mesa Dorada": "Ostrander",
    "Latgaway": "Stagewater", "Netherwood": "Antler",
}

# ---- named private schools (owner list, 2027-08) ---------------------------
# Placed city by city, most in the metros — where private schools actually
# cluster. Secular independents and the Catholic/religious tradition together;
# tier sets the classification weight band (metro privates run bigger).
PRIVATE_NAMED = [
    # (name, city, tier)  tier: "metro" | "secondary" | "town"
    ("Romero-Finniski", "Ashbury", "metro"),
    ("Condotti Vanguard Academy", "Ashbury", "metro"),
    ("Metropolitan Country Day School", "Ashbury", "metro"),
    ("Chaminade", "Ashbury", "metro"),
    ("Sisters of Mercy", "Ashbury", "metro"),
    ("St. Norbert Abbey", "Ashbury", "metro"),
    ("Fletcher-Garrison Hall", "Port Meridian", "metro"),
    ("Saint Francis", "Port Meridian", "metro"),
    ("Abbey Prep", "Port Meridian", "metro"),
    ("Wheeler Academy", "Halbrook", "metro"),
    ("Delbarton", "Halbrook", "metro"),
    ("Pinecrest School", "Averill", "secondary"),
    ("Calderwood School", "Cedarport", "secondary"),
    ("Evans Western Institute", "Redfork", "secondary"),
    ("Calasanz Prep", "Plainfield", "secondary"),
    ("Ryken", "Newark River", "secondary"),
    ("Jefferson Methodist School", "Leidesdorff", "secondary"),
]

# ---- Christian schools dotted around the state ------------------------------
# Directional/geographic names, the way these schools actually name
# themselves. One is just Baptist HS — some schools never needed more.
CHRISTIAN_SCHOOLS = [
    ("Northside Christian", "Halbrook", "metro"),
    ("Westside Christian", "Port Meridian", "metro"),
    ("Southridge Christian", "Ashbury", "metro"),
    ("Eastmont Christian", "Cedarport", "secondary"),
    ("Western Slope Christian", "Redfork", "secondary"),
    ("High Desert Christian", "Doyle Junction", "secondary"),
    ("Central Christian", "Summervale", "secondary"),
    ("Coastal Christian", "Santa Laura", "town"),
    ("North Valley Christian", "Netherwood", "town"),
    ("Valley Christian", "New Leiden", "town"),
    ("Southern Jefferson Christian", "Latgaway", "town"),
    ("Baptist HS", "Hetfield", "town"),
]

# Santa Laura anchors a Spanish-derived naming layer on the southern coast;
# these settle around it as single-school towns.
SPANISH_TOWNS = ["San Aurelio", "Puerto Alma", "Mesa Dorada"]

# handpicked anchors (all fictional; checked against the blocklist by eye)
ANCHORS = {
    "inland_metro": ("Ashbury", 470_000),        # major inland city, ~900k metro
    "coastal_metro": ("Port Meridian", 205_000),  # coastal city, ~330k metro
    "boise_side": ("Halbrook", 185_000),          # Jefferson side of the Boise metro
    "secondary": [
        ("Averill", 118_000), ("Cedarport", 96_000), ("Blackpine", 84_000),
        ("Kelford", 71_000), ("Redfork", 58_000), ("Doyle Junction", 46_000),
        ("Summervale", 43_000),
    ],
}

SURNAMES_SCHOOL = [
    "Whitfield", "Ellsworth", "Merritt", "Hargrove", "Bellamy", "Dawes", "Fenwick",
    "Granger", "Holloway", "Kessler", "Latimer", "Prescott", "Redmond", "Thorne",
    "Winslow", "Abernathy", "Calloway", "Marbury", "Ostrander", "Pemberton",
    "Quennell", "Sablewood", "Tanager", "Vandermeer", "Wickham", "Yarrow",
]
SAINTS = [
    "St. Anselm", "St. Brigid", "St. Callistus", "St. Isidore", "St. Monica",
    "St. Norbert", "St. Perpetua", "St. Sebastian Prep", "Our Lady of the Pines",
    "Bishop Merrick", "Bishop Delaney", "Archbishop Doyle", "Holy Cross",
    "Sacred Heart", "Mercy Academy", "Trinity Catholic", "Providence Academy",
]

# secular private tradition: founders, benefactors, classical preps
PREPS = [
    "Hawthorne Preparatory", "Barrett Academy", "Pacific Friends School",
    "Ashbury Country Day", "Whittaker Hall", "The Meridian School",
    "Copley Academy", "Jefferson Lutheran", "Sherwood Friends",
]

# ---- person-named schools ---------------------------------------------------
# Jefferson's own civic history: territorial governors, educators, ranchers,
# newspaper editors. In sports contexts these schools go by surname alone —
# "Mercer at Talltree, Friday" — so the surname IS the school name; a couple
# keep the full name the way a district that never shortened it would.
CIVIC_FIGURES = [
    "Mercer", "Talltree", "Navarro", "Whitcomb", "Bell", "Matsuda", "Okafor",
    "Delgado", "Ashworth", "Crane", "Iwasaki", "Barlow", "Reyes", "Tanaka",
    "McAllister", "Vasquez", "Littlefeather", "Grady", "Nakamura", "Soto",
]
CIVIC_FULL = ["Augustus Mercer", "Lena Talltree", "Ida Crane"]
# national figures, used sparingly so Jefferson keeps its own history
NATIONAL_FIGURES = ["Lincoln", "Roosevelt", "Douglass", "Tubman", "Marshall",
                    "King", "Chavez", "Parks", "Wells", "Grant"]

# ---- neighborhood schools (metros identify by neighborhood, not compass) ----
NEIGHBORHOODS = [
    "Woodlawn", "Parkside", "Eastgate", "Laurel Heights", "Crown Hill",
    "Mission Terrace", "Fairhaven", "Millrow", "Brookmont", "Garfield Park",
    "Cannon Hill", "Steelbridge", "Old Harbor", "Vista Terrace", "Maple Row",
    "Kingsline", "Riverbend", "Northgate", "Southgate", "Terrace Park",
]

# ---- geographic-feature schools (the landscape already on the map) ----------
GEO_SCHOOLS = [
    "Twin Rivers", "Cascade View", "North Fork", "Granite Basin", "Rimrock",
    "Bear Flat", "Silver Lake", "Timberline", "High Prairie", "Redwood Glen",
    "Bluewater", "Sage Summit", "Owl Canyon", "Larchmont Ridge",
]

# ---- rural consolidations ---------------------------------------------------
COUNTIES = ["Marlow", "Tamarack", "Bidwell", "Sablewood", "Ostrander", "Camas",
            "Weller", "Antler", "Halbrook", "Meridian"]
REGIONAL_FORMS = ["{} County", "Upper {} Union", "{} Regional", "{} Union"]

# ---- magnet / technical / specialty (metros only) ---------------------------
MAGNETS = [
    "Jefferson School of Science and Technology", "Port Meridian North",
    "Academy of Arts and Communication", "Ashbury Health Sciences",
    "Port Meridian Maritime", "Ashbury Technical",
]
PROTESTANT = [
    "Grace Baptist", "First Baptist", "Trinity Episcopal", "Wesley Methodist",
    "Asbury Methodist", "Cornerstone Christian", "Covenant Christian",
    "Providence Christian", "Redeemer Lutheran", "Zion Lutheran", "Calvary",
    "Emmanuel", "Faith Baptist", "Living Word", "Grace Episcopal",
]
CIVIC_WORDS = [
    "Frontier", "Pioneer", "Overland", "Prospect", "Pinnacle", "Liberty",
    "Independence", "Enterprise", "Harmony", "Unity", "Golden Valley",
    "Scarlet Oak", "Blue Spruce", "Silverleaf", "Crimson Ridge",
]
DIRECTIONS = ["North", "South", "East", "West", "Central", "Northwest", "Southeast", "Union", "Heights"]

MASCOTS = [
    "Loggers", "Miners", "Mustangs", "Timberwolves", "Ospreys", "Steelheads",
    "Vaqueros", "Prospectors", "Sandpipers", "Renegades", "Falcons", "Badgers",
    "Bighorns", "Wranglers", "Mariners", "Lumberjacks", "Rattlers", "Kestrels",
    "Stampede", "Gold Diggers", "Pioneers", "Owls", "Cougars", "Grizzlies",
    "Huckleberries", "Thunderbirds", "Axemen", "Drifters", "Coyotes", "Herons",
    "Marmots", "Firebirds", "Ridgerunners", "Salmonbacks", "Whalers", "Sagehens",
]

# Given names are split by gender because the rosters are. One shared list
# put Vera and Imogen in a boys wrestling dual and Rafael and Hector in a
# girls tennis lineup, on every page of the site at once — the single most
# visible thing separating "a demo of a results system" from "a results
# system". A sport's gender is already in the catalog; the roster just has to
# honour it. UNISEX names are drawn for either, which is what keeps the split
# from reading as two sealed name universes.
BOYS_FIRST = [
    "Aiden", "Anders", "Beau", "Bodie", "Caleb", "Colt", "Dante", "Diego",
    "Elias", "Ezra", "Gideon", "Harlan", "Hector", "Jasper", "Joaquin",
    "Lachlan", "Magnus", "Mateo", "Nash", "Orion", "Rafael", "Rhett",
    "Santiago", "Silas", "Teodoro", "Ulises", "Waylon", "Yusuf", "Zeke",
    "Abel", "Bennett", "Cormac", "Desmond", "Emiliano", "Ferris", "Gustav",
    "Hollis", "Ignatius", "Jericho", "Kepler", "Leland", "Malachi", "Nikolai",
    "Oskar", "Porter", "Quentin", "Ronan", "Soren", "Tobias", "Vicente",
    "Wendell", "Xavier", "Yannick", "Zephyr", "Amos", "Cyrus", "Dashiell",
    "Everett", "Gabriel", "Hamza", "Isandro", "Kofi", "Lucian", "Mikael",
]
GIRLS_FIRST = [
    "Amara", "Annika", "Bianca", "Brynn", "Camila", "Cecilia", "Dahlia",
    "Delaney", "Eleanor", "Esme", "Fiona", "Gracelyn", "Hazel", "Imogen",
    "Isla", "Jubilee", "Lucia", "Maren", "Mireya", "Noelle", "Odessa",
    "Paloma", "Priya", "Ramona", "Rosalind", "Sable", "Saoirse", "Sonora",
    "Tallulah", "Tessa", "Vera", "Willa", "Xiomara", "Zadie",
    "Adaeze", "Beatriz", "Clementine", "Dagny", "Elowen", "Fernanda",
    "Giselle", "Halina", "Ingrid", "Juniper", "Kalinda", "Linnea", "Marisol",
    "Nadia", "Oriana", "Perpetua", "Rhiannon", "Siobhan", "Thandiwe",
    "Ursula", "Valentina", "Wren", "Yasmin", "Zora", "Anneke", "Cordelia",
    "Devorah", "Freya", "Ileana", "Magnolia", "Solveig",
]
#: Drawn for either roster.
UNISEX_FIRST = [
    "Alexis", "Carson", "Emery", "Ira", "Kai", "Katriel", "Phoenix", "Quinn",
    "Rowan", "Aspen", "Blaise", "Ellis", "Marlowe", "Sasha", "Tatum",
]
#: Kept for anything that wants a name without caring whose it is.
FIRST_NAMES = BOYS_FIRST + GIRLS_FIRST + UNISEX_FIRST
LAST_NAMES = [
    "Abbott", "Acevedo", "Aldridge", "Barajas", "Beckett", "Bergstrom", "Blackwood",
    "Bravo", "Callahan", "Castellanos", "Chavarria", "Coombs", "Crowfoot", "Dahl",
    "Delgadillo", "Eastman", "Ferreira", "Finch", "Gallego", "Gustafson", "Halvorsen",
    "Herrera", "Hollis", "Ivanov", "Jansen", "Katagiri", "Kowalski", "Lachance",
    "Ledoux", "Lindqvist", "Maldonado", "McAllister", "Nakagawa", "Nguyen", "Novak",
    "Okafor", "Ortega", "Paulsen", "Pham", "Quintana", "Rasmussen", "Renteria",
    "Saelee", "Sandoval", "Schuster", "Singh", "Sorensen", "Takahashi", "Thibodeaux",
    "Ulrich", "Vasquez", "Villanueva", "Whitehorse", "Wynn", "Xiong", "Ybarra",
    "Zamora", "Zielinski", "Arreola", "Brandt", "Cardenas", "Duffy", "Ellison",
    "Fontaine", "Grimaldi", "Hutchins", "Iverson", "Jimenez", "Keller", "Lucero",
]


# ---- conference naming ------------------------------------------------------
# Modeled on how American high-school conferences are actually named: regional
# geography, rivers and valleys, metro identity, county identity, historic and
# cultural terms, corridors, and the occasional numeric league whose name
# outlives its membership count. Curated per area from Jefferson's own map so
# the list reads as institutions accumulated over decades of realignment, not
# output of one template. Order matters: the generator takes them in sequence,
# so the strongest names land on the areas' first leagues.

CONF_NAMES = {
    "Ashbury Metro": [
        "Capital City League", "Greater Ashbury Conference",
        "Metro Six", "Ashbury Suburban League", "Overland Conference",
    ],
    "Harborline": [
        "Seaboard League", "Harborline Conference", "Cannery Athletic League",
        "Pacific Eight",
    ],
    "South Coast": [
        "Driftwood League", "South Coast Conference", "Tidewater Athletic League",
    ],
    "Halbrook Basin": [
        "Basin Athletic Conference", "Border League", "Halbrook City League",
        "Snake Plain Conference",
    ],
    "Cascade Divide": [
        "Cascade Eight", "Timberline League", "Divide Conference",
    ],
    "Juniper Highlands": [
        "High Desert League", "Juniper Athletic Conference", "Rimrock League",
    ],
    "Sage Plains": [
        "Sagebrush Conference", "Frontier Ten", "Emigrant Trail League",
    ],
    "Timber Valley": [
        "Timber Valley Conference", "Millrace League", "Big Trees Conference",
        "Valley Heritage League",
    ],
    "Gold Valley": [
        "Mother Lode League", "Gold Valley Conference", "Stagecoach League",
    ],
    "North Range": [
        "North Range League", "Territorial Conference", "Short Line League",
    ],
}

# statewide pool when an area outgrows its list — realignment leftovers
CONF_EXTRA = [
    "Mid-State Conference", "Jefferson Heritage Conference", "Pioneer League",
    "Crossroads Conference", "Interstate League", "Mid-Southern Conference",
    "Foothills Athletic Conference", "Twin Rivers League", "Federal League",
    "Northern Ten", "Prospectors League", "Homestead Conference",
]


# ---- athletic colors --------------------------------------------------------
# Curated school-color pairs (primary dark enough to carry a white monogram,
# secondary as the accent). A school's colors are fixed identity — they do not
# follow the site theme, exactly as a real athletic mark doesn't.
SCHOOL_COLORS = [
    ("#7b1e2b", "#e8c46b"),  # maroon / gold
    ("#14294e", "#c8ccd4"),  # navy / silver
    ("#1e5631", "#f2f2ee"),  # forest / white
    ("#8c1d40", "#f0b323"),  # cardinal / sun gold
    ("#4b2e83", "#b7a57a"),  # purple / vegas gold
    ("#0f6a70", "#f4f1ea"),  # teal / cream
    ("#1d1d1f", "#d97706"),  # black / orange
    ("#1d4e9e", "#f2f2ee"),  # royal / white
    ("#92400e", "#1d1d1f"),  # burnt orange / black
    ("#167339", "#e8e6df"),  # kelly / stone
    ("#6d1a36", "#9fb4c7"),  # garnet / powder
    ("#14532d", "#e8c46b"),  # hunter / gold
    ("#1e2a4a", "#c05621"),  # midnight / rust
    ("#5b2a86", "#e5e7eb"),  # plum / grey
    ("#3a5a78", "#f5e9d0"),  # steel / cream
    ("#204e39", "#c8a24a"),  # pine / old gold
    ("#7f1d1d", "#d4d4d8"),  # brick red / silver
    ("#0e7490", "#fbbf24"),  # cyan-deep / amber
    ("#3f2a56", "#3ba55d"),  # eggplant / green
    ("#333d29", "#d97706"),  # olive drab / orange
]
