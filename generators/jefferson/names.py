"""
Naming material for Jefferson. Pools + grammar, not hand-invention.

School names deliberately span the full real-world spread: directional publics
(North/South/East/West/Central + city), people (surname schools), religious
schools across denominations (Catholic saints, Baptist, Episcopal, Methodist,
Lutheran, nondenominational Christian), colors, places, and things, plus
academies and preps. Everything runs through collision checks and a blocklist
of real western cities and schools.
"""

# town-name grammar
STEMS = [
    "Alder", "Juniper", "Cedar", "Granite", "Copper", "Silver", "Summit", "Sage",
    "Pine", "Fox", "Eagle", "Clear", "Black", "Red", "Elk", "Bear", "Lost", "High",
    "North", "South", "Gold", "Iron", "Aspen", "Willow", "Hawk", "Stone", "Deer",
    "Antler", "Basalt", "Madrone", "Manzanita", "Obsidian", "Tamarack", "Larch",
    "Camas", "Bitter", "Wolf", "Raven", "Osprey", "Trout", "Salmonberry", "Huckle",
]
ENDINGS = [
    "Bay", "Falls", "Ridge", "Valley", "Basin", "Creek", "Springs", "Junction",
    "Pass", "Harbor", "Point", "Prairie", "Fork", "Lake", "Mesa", "Bluff",
    "Crossing", "Glen", "Hollow", "Flat", "Landing", "Meadows", "Gap", "Butte",
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
}

# handpicked anchors (all fictional; checked against the blocklist by eye)
ANCHORS = {
    "inland_metro": ("Ashbury", 470_000),        # major inland city, ~900k metro
    "coastal_metro": ("Port Meridian", 205_000),  # coastal city, ~330k metro
    "boise_side": ("Halbrook", 185_000),          # Jefferson side of the Boise metro
    "secondary": [
        ("Juniper Mesa", 118_000), ("Cedarport", 96_000), ("Blackpine", 84_000),
        ("Eagle Prairie", 71_000), ("Redfork", 58_000), ("Silver Junction", 46_000),
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
    "St. Norbert", "St. Perpetua", "Our Lady of the Pines", "Bishop Merrick",
    "Archbishop Doyle", "Holy Cross", "Sacred Heart",
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

FIRST_NAMES = [
    "Aiden", "Alexis", "Amara", "Anders", "Annika", "Beau", "Bianca", "Bodie",
    "Brynn", "Caleb", "Camila", "Carson", "Cecilia", "Colt", "Dahlia", "Dante",
    "Delaney", "Diego", "Eleanor", "Elias", "Emery", "Esme", "Ezra", "Fiona",
    "Gideon", "Gracelyn", "Harlan", "Hazel", "Hector", "Imogen", "Ira", "Isla",
    "Jasper", "Joaquin", "Jubilee", "Kai", "Katriel", "Lachlan", "Lucia", "Magnus",
    "Maren", "Mateo", "Mireya", "Nash", "Noelle", "Odessa", "Orion", "Paloma",
    "Phoenix", "Priya", "Quinn", "Rafael", "Ramona", "Rhett", "Rosalind", "Rowan",
    "Sable", "Santiago", "Saoirse", "Silas", "Sonora", "Tallulah", "Teodoro",
    "Tessa", "Ulises", "Vera", "Waylon", "Willa", "Xiomara", "Yusuf", "Zadie", "Zeke",
]
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
