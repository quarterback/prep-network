#!/usr/bin/env python3
"""Generate complete Jefferson state dataset with schools, settlements, regions, and conferences."""

import json, random
random.seed(42)

# REGIONS (10)
REGIONS = [
    {"id": "R01", "name": "Cascadia Central Valley", "location": "Central-western Jefferson", "description": "The heartland - broad interior valley containing the primary metro area", "character": "Agricultural powerhouse, urban corridor, transportation hub"},
    {"id": "R02", "name": "Redwood Coast", "location": "Northwestern Jefferson", "description": "Northern Pacific coastline with ancient forests and fishing ports", "character": "Rugged coastline, redwood forests, maritime economy"},
    {"id": "R03", "name": "Shasta Highlands", "location": "South-central Jefferson", "description": "Volcanic mountain region with peaks, lakes, and forested slopes", "character": "Mountain recreation, forestry, volcanic landscapes"},
    {"id": "R04", "name": "Silver Basin", "location": "Eastern Jefferson", "description": "High desert basin with agricultural valleys fed by mountain runoff", "character": "Irrigated agriculture, ranching, high desert communities"},
    {"id": "R05", "name": "Boise Frontier Corridor", "location": "Northeastern Jefferson", "description": "Northeastern edge facing Idaho, part of greater Boise metropolitan region", "character": "Suburban growth, bedroom communities, interstate commerce"},
    {"id": "R06", "name": "Klamath Uplands", "location": "South-central Jefferson", "description": "Southern interior with mixed agriculture and mountain foothills", "character": "Transition zone, orchards, cattle ranching"},
    {"id": "R07", "name": "Harney Expanse", "location": "Southeastern Jefferson", "description": "Vast high desert and Great Basin country with scattered settlements", "character": "Frontier ranching, mining, isolated communities"},
    {"id": "R08", "name": "Trinity Mountains", "location": "Southwestern Jefferson", "description": "Rugged inland mountain range with mining history and forest resources", "character": "Mining heritage, timber, mountain towns"},
    {"id": "R09", "name": "Humboldt Delta", "location": "West-central Jefferson", "description": "Coastal plain and river delta region with university and port", "character": "Port economy, university town, coastal agriculture"},
    {"id": "R10", "name": "Owyhee Rim Country", "location": "Far northeastern Jefferson", "description": "Deep canyon country along the Snake River watershed edge", "character": "Canyon ranching, irrigation projects, remote settlements"},
]

# SETTLEMENTS (70 total, ~4M population)
SETTLEMENTS = [
    {"id": "S001", "name": "Ashford", "region": "Cascadia Central Valley", "population": 587000, "type": "Primary City", "metro": "Ashford Metro", "description": "State capital and economic center"},
    {"id": "S002", "name": "Port Valdez", "region": "Redwood Coast", "population": 234000, "type": "Major Coastal City", "metro": "Port Valdez Metro", "description": "Deep-water port, timber export hub"},
    {"id": "S003", "name": "Newbridge", "region": "Boise Frontier Corridor", "population": 198000, "type": "Major Interstate City", "metro": "Greater Boise-Jefferson Metro", "description": "Boise metro bedroom/employment center"},
    {"id": "S004", "name": "Timberlake", "region": "Cascadia Central Valley", "population": 168000, "type": "Regional City", "metro": "Ashford Metro", "description": "University town, tech corridor"},
    {"id": "S005", "name": "Redhaven", "region": "Redwood Coast", "population": 152000, "type": "Regional City", "metro": "Port Valdez Metro", "description": "Fishing fleet homeport, tourism"},
    {"id": "S006", "name": "Volcano Ridge", "region": "Shasta Highlands", "population": 112000, "type": "Regional City", "metro": None, "description": "Mountain recreation gateway, forestry"},
    {"id": "S007", "name": "Silverton", "region": "Silver Basin", "population": 94000, "type": "Regional City", "metro": None, "description": "Agricultural processing, distribution"},
    {"id": "S008", "name": "Canyon Creek", "region": "Boise Frontier Corridor", "population": 82000, "type": "Regional City", "metro": "Greater Boise-Jefferson Metro", "description": "Suburban residential, light industry"},
    {"id": "S009", "name": "Klamath Junction", "region": "Klamath Uplands", "population": 76000, "type": "Regional City", "metro": None, "description": "Rail hub, livestock auction center"},
    {"id": "S010", "name": "Mendota", "region": "Humboldt Delta", "population": 72000, "type": "Regional City", "metro": None, "description": "University, coastal agriculture research"},
    {"id": "S011", "name": "Desert Springs", "region": "Harney Expanse", "population": 68000, "type": "Regional City", "metro": None, "description": "Geothermal energy, ranching services"},
    {"id": "S012", "name": "Oakmere", "region": "Cascadia Central Valley", "population": 58000, "type": "Small City", "metro": "Ashford Metro", "description": "Suburban manufacturing, warehouses"},
    {"id": "S013", "name": "Cascade Heights", "region": "Cascadia Central Valley", "population": 52000, "type": "Small City", "metro": "Ashford Metro", "description": "Residential suburb, commuter town"},
    {"id": "S014", "name": "Fort Braggton", "region": "Redwood Coast", "population": 47000, "type": "Small City", "metro": "Port Valdez Metro", "description": "Historic fort, coastal tourism"},
    {"id": "S015", "name": "Lassen Peak", "region": "Shasta Highlands", "population": 43000, "type": "Small City", "metro": None, "description": "Ski resort access, mountain sports"},
    {"id": "S016", "name": "Payette Crossing", "region": "Boise Frontier Corridor", "population": 41000, "type": "Small City", "metro": "Greater Boise-Jefferson Metro", "description": "Logistics, trucking hub"},
    {"id": "S017", "name": "Willowbrook", "region": "Cascadia Central Valley", "population": 39000, "type": "Small City", "metro": "Ashford Metro", "description": "Food processing, canneries"},
    {"id": "S018", "name": "Trinity Mine", "region": "Trinity Mountains", "population": 36000, "type": "Small City", "metro": None, "description": "Historic mining, now tourism"},
    {"id": "S019", "name": "Modoc Flats", "region": "Silver Basin", "population": 33000, "type": "Small City", "metro": None, "description": "Grain farming, grain elevators"},
    {"id": "S020", "name": "Owyhee Canyon", "region": "Owyhee Rim Country", "population": 31000, "type": "Small City", "metro": None, "description": "Cattle ranching headquarters"},
    {"id": "S021", "name": "Lakeview Terrace", "region": "Klamath Uplands", "population": 29000, "type": "Small City", "metro": None, "description": "Resort community, retirement"},
    {"id": "S022", "name": "Douglasville", "region": "Cascadia Central Valley", "population": 24500, "type": "County Seat", "metro": None, "description": "Agricultural county seat"},
    {"id": "S023", "name": "Curry Landing", "region": "Redwood Coast", "population": 22500, "type": "County Seat", "metro": None, "description": "Coastal county seat, crab fishing"},
    {"id": "S024", "name": "Jackson Point", "region": "Klamath Uplands", "population": 20500, "type": "County Seat", "metro": None, "description": "Orchard region center"},
    {"id": "S025", "name": "Washoe Junction", "region": "Silver Basin", "population": 19000, "type": "County Seat", "metro": None, "description": "Nevada border trade"},
    {"id": "S026", "name": "Siskiyou Pass", "region": "Shasta Highlands", "population": 18000, "type": "County Seat", "metro": None, "description": "Highway pass town, logging"},
    {"id": "S027", "name": "Malheur Center", "region": "Harney Expanse", "population": 17000, "type": "County Seat", "metro": None, "description": "Vast ranching county seat"},
    {"id": "S028", "name": "Humboldt Bay", "region": "Humboldt Delta", "population": 16000, "type": "County Seat", "metro": "Port Valdez Metro", "description": "Small port, oyster farming"},
    {"id": "S029", "name": "Glenn", "region": "Cascadia Central Valley", "population": 15000, "type": "County Seat", "metro": None, "description": "Farm service town"},
    {"id": "S030", "name": "Plumas Grove", "region": "Shasta Highlands", "population": 14000, "type": "County Seat", "metro": None, "description": "Timber county seat"},
    {"id": "S031", "name": "Tehama Bridge", "region": "Cascadia Central Valley", "population": 13000, "type": "County Seat", "metro": None, "description": "Historic bridge town"},
    {"id": "S032", "name": "Del Norte Head", "region": "Redwood Coast", "population": 12000, "type": "County Seat", "metro": None, "description": "Border town, redwood tourism"},
    {"id": "S033", "name": "Butte Valley", "region": "Cascadia Central Valley", "population": 11000, "type": "County Seat", "metro": None, "description": "Rice farming"},
    {"id": "S034", "name": "Grainfield", "region": "Cascadia Central Valley", "population": 9800, "type": "Agricultural Town", "metro": None, "description": "Wheat and barley farms"},
    {"id": "S035", "name": "Orchardale", "region": "Klamath Uplands", "population": 9200, "type": "Agricultural Town", "metro": None, "description": "Apple and pear orchards"},
    {"id": "S036", "name": "Ranchero", "region": "Silver Basin", "population": 8600, "type": "Agricultural Town", "metro": None, "description": "Cattle feedlot operations"},
    {"id": "S037", "name": "Vineyard Mesa", "region": "Klamath Uplands", "population": 8000, "type": "Agricultural Town", "metro": None, "description": "Wine grape vineyards"},
    {"id": "S038", "name": "Dairy Hollow", "region": "Cascadia Central Valley", "population": 7500, "type": "Agricultural Town", "metro": None, "description": "Dairy farms, cheese"},
    {"id": "S039", "name": "Alfalfa Springs", "region": "Harney Expanse", "population": 6900, "type": "Agricultural Town", "metro": None, "description": "Hay production"},
    {"id": "S040", "name": "Cornerville", "region": "Cascadia Central Valley", "population": 6400, "type": "Agricultural Town", "metro": None, "description": "Sweet corn processing"},
    {"id": "S041", "name": "Sheep Camp", "region": "Owyhee Rim Country", "population": 5800, "type": "Agricultural Town", "metro": None, "description": "Sheep ranching, wool"},
    {"id": "S042", "name": "Summit Lodge", "region": "Shasta Highlands", "population": 7800, "type": "Resort Town", "metro": None, "description": "Year-round ski resort"},
    {"id": "S043", "name": "Crystal Lake", "region": "Trinity Mountains", "population": 6500, "type": "Resort Town", "metro": None, "description": "Fishing resort"},
    {"id": "S044", "name": "Pine Haven", "region": "Trinity Mountains", "population": 5400, "type": "Resort Town", "metro": None, "description": "Mountain retreat"},
    {"id": "S045", "name": "Hot Springs", "region": "Harney Expanse", "population": 4800, "type": "Resort Town", "metro": None, "description": "Hot springs spa"},
    {"id": "S046", "name": "Eagle Nest", "region": "Shasta Highlands", "population": 4100, "type": "Resort Town", "metro": None, "description": "Exclusive mountain homes"},
    {"id": "S047", "name": "Deer Park", "region": "Klamath Uplands", "population": 3500, "type": "Resort Town", "metro": None, "description": "Hunting lodge"},
    {"id": "S048", "name": "Seabright", "region": "Redwood Coast", "population": 5900, "type": "Coastal Town", "metro": "Port Valdez Metro", "description": "Artist colony"},
    {"id": "S049", "name": "Rockport", "region": "Redwood Coast", "population": 4900, "type": "Coastal Town", "metro": None, "description": "Small fishing harbor"},
    {"id": "S050", "name": "Moonstone Beach", "region": "Redwood Coast", "population": 4100, "type": "Coastal Town", "metro": None, "description": "Tourist beach town"},
    {"id": "S051", "name": "Capetown", "region": "Redwood Coast", "population": 3600, "type": "Coastal Town", "metro": None, "description": "Historic shipping port"},
    {"id": "S052", "name": "Sandbar", "region": "Humboldt Delta", "population": 3000, "type": "Coastal Town", "metro": None, "description": "Beach access"},
    {"id": "S053", "name": "Lighthouse Point", "region": "Redwood Coast", "population": 2500, "type": "Coastal Town", "metro": None, "description": "Historic lighthouse"},
    {"id": "S054", "name": "Crossroads", "region": "Harney Expanse", "population": 1850, "type": "Rural Community", "metro": None, "description": "Truck stop"},
    {"id": "S055", "name": "Whispering Pines", "region": "Trinity Mountains", "population": 1620, "type": "Rural Community", "metro": None, "description": "Logging camp settlement"},
    {"id": "S056", "name": "Dry Creek", "region": "Silver Basin", "population": 1480, "type": "Rural Community", "metro": None, "description": "Dry farming"},
    {"id": "S057", "name": "Ghost Rock", "region": "Owyhee Rim Country", "population": 1290, "type": "Rural Community", "metro": None, "description": "Former mining town"},
    {"id": "S058", "name": "Prairie Home", "region": "Harney Expanse", "population": 1150, "type": "Rural Community", "metro": None, "description": "Isolated ranch"},
    {"id": "S059", "name": "Milltown", "region": "Cascadia Central Valley", "population": 980, "type": "Rural Community", "metro": None, "description": "Historic sawmill"},
    {"id": "S060", "name": "Basin View", "region": "Silver Basin", "population": 870, "type": "Rural Community", "metro": None, "description": "Small ranching"},
    {"id": "S061", "name": "Iron Springs", "region": "Trinity Mountains", "population": 740, "type": "Rural Community", "metro": None, "description": "Mineral spring"},
    {"id": "S062", "name": "Cedar Flat", "region": "Shasta Highlands", "population": 650, "type": "Rural Community", "metro": None, "description": "Fire lookout nearby"},
    {"id": "S063", "name": "Sunset Mesa", "region": "Harney Expanse", "population": 520, "type": "Rural Community", "metro": None, "description": "Isolated ranch cluster"},
    {"id": "S064", "name": "Willow Creek", "region": "Klamath Uplands", "population": 480, "type": "Rural Community", "metro": None, "description": "Tiny hamlet"},
    {"id": "S065", "name": "Black Rock", "region": "Owyhee Rim Country", "population": 410, "type": "Rural Community", "metro": None, "description": "Remote outpost"},
    {"id": "S066", "name": "Morning Star", "region": "Harney Expanse", "population": 350, "type": "Rural Community", "metro": None, "description": "One-room schoolhouse"},
    {"id": "S067", "name": "Fox Gulch", "region": "Trinity Mountains", "population": 290, "type": "Rural Community", "metro": None, "description": "Abandoned mining gulch"},
    {"id": "S068", "name": "Antelope Run", "region": "Silver Basin", "population": 240, "type": "Rural Community", "metro": None, "description": "Seasonal workers"},
    {"id": "S069", "name": "Stone Bridge", "region": "Boise Frontier Corridor", "population": 180, "type": "Rural Community", "metro": None, "description": "Old stone bridge"},
    {"id": "S070", "name": "Lost Valley", "region": "Harney Expanse", "population": 120, "type": "Rural Community", "metro": None, "description": "Barely inhabited"},
]

def get_settlement(name):
    for s in SETTLEMENTS:
        if s["name"] == name: return s
    return None

SCHOOLS = []
def add(sid, nm, sn, city, enr, typ="Public", cls=None):
    st = get_settlement(city)
    if not st: return
    SCHOOLS.append({"school_id": sid, "name": nm, "short_name": sn, "city": city, "region": st["region"], "type": typ, "enrollment": enr, "classification": cls, "conference": None})

# Build schools - Target: 6A:38, 5A:42, 4A:44, 3A:38, 2A:36, 1A:57 = 255
# ASHFORD (24): 10x6A, 8x5A, 4x4A, 2x3A
schools_list = [
    ("SCH001","Ashford High School","Ashford HS","Ashford",1850,"Public","6A"),
    ("SCH002","North Ashford High School","North Ashford","Ashford",1780,"Public","6A"),
    ("SCH003","South Ashford High School","South Ashford","Ashford",1720,"Public","6A"),
    ("SCH004","East Ashford High School","East Ashford","Ashford",1650,"Public","6A"),
    ("SCH005","West Ashford High School","West Ashford","Ashford",1580,"Public","6A"),
    ("SCH006","Central High School","Central","Ashford",1520,"Public","6A"),
    ("SCH007","Ashford Memorial High School","Memorial","Ashford",1450,"Public","6A"),
    ("SCH008","Washington High School","Washington","Ashford",1380,"Public","6A"),
    ("SCH009","Lincoln High School","Lincoln","Ashford",1320,"Public","6A"),
    ("SCH010","Roosevelt High School","Roosevelt","Ashford",1250,"Public","6A"),
    ("SCH011","Kennedy High School","Kennedy","Ashford",1180,"Public","5A"),
    ("SCH012","Hamilton High School","Hamilton","Ashford",1120,"Public","5A"),
    ("SCH013","Franklin High School","Franklin","Ashford",1050,"Public","5A"),
    ("SCH014","Valley View High School","Valley View","Ashford",980,"Public","5A"),
    ("SCH015","Cascade High School","Cascade","Ashford",920,"Public","5A"),
    ("SCH016","Pioneer High School","Pioneer","Ashford",850,"Public","5A"),
    ("SCH017","Heritage High School","Heritage","Ashford",780,"Public","5A"),
    ("SCH018","Ashford Technical High School","Ashford Tech","Ashford",720,"Public","5A"),
    ("SCH019","Ashford Arts Academy","Arts Academy","Ashford",650,"Private","4A"),
    ("SCH020","St. Marys Academy","St. Marys","Ashford",580,"Private","4A"),
    ("SCH021","Trinity Preparatory School","Trinity Prep","Ashford",520,"Private","4A"),
    ("SCH022","Ashford Christian Academy","Christian Academy","Ashford",450,"Private","4A"),
    ("SCH023","Sacred Heart High School","Sacred Heart","Ashford",380,"Private","3A"),
    ("SCH024","Jefferson Leadership Academy","Leadership Academy","Ashford",320,"Private","3A"),
]
for row in schools_list: add(*row)

# PORT VALDEZ (8): 4x6A, 2x5A, 1x4A, 1x3A
pv = [("SCH025","Port Valdez High School","PV HS","Port Valdez",1680,"Public","6A"),
      ("SCH026","North Port High School","N. Port","Port Valdez",1450,"Public","6A"),
      ("SCH027","South Port High School","S. Port","Port Valdez",1320,"Public","6A"),
      ("SCH028","Coastal High School","Coastal","Port Valdez",1180,"Public","6A"),
      ("SCH029","Redwood High School","Redwood","Port Valdez",980,"Public","5A"),
      ("SCH030","Maritime Academy","Maritime","Port Valdez",850,"Public","5A"),
      ("SCH031","Valdez Memorial High School","Valdez Mem","Port Valdez",720,"Public","4A"),
      ("SCH032","St. Josephs High School","St. Josephs","Port Valdez",380,"Private","3A")]
for row in pv: add(*row)

# NEWBRIDGE (8): 3x6A, 3x5A, 1x4A, 1x3A
nb = [("SCH033","Newbridge High School","Newbridge HS","Newbridge",1520,"Public","6A"),
      ("SCH034","East Newbridge High School","E. Newbridge","Newbridge",1280,"Public","6A"),
      ("SCH035","West Newbridge High School","W. Newbridge","Newbridge",1150,"Public","6A"),
      ("SCH036","Frontier High School","Frontier","Newbridge",980,"Public","5A"),
      ("SCH037","Boise Valley High School","Boise Valley","Newbridge",850,"Public","5A"),
      ("SCH038","Interstate High School","Interstate","Newbridge",720,"Public","5A"),
      ("SCH039","Canyon View High School","Canyon View","Newbridge",580,"Public","4A"),
      ("SCH040","Bethel Christian School","Bethel","Newbridge",380,"Private","3A")]
for row in nb: add(*row)

# TIMBERLAKE (6): 2x6A, 2x5A, 1x4A, 1x3A
tb = [("SCH041","Timberlake High School","Timberlake HS","Timberlake",1380,"Public","6A"),
      ("SCH042","North Timberlake High School","N. Timberlake","Timberlake",1120,"Public","6A"),
      ("SCH043","South Timberlake High School","S. Timberlake","Timberlake",950,"Public","5A"),
      ("SCH044","University High School","University","Timberlake",820,"Public","5A"),
      ("SCH045","Tech Valley High School","Tech Valley","Timberlake",650,"Public","4A"),
      ("SCH046","Lake County High School","Lake County","Timberlake",380,"Public","3A")]
for row in tb: add(*row)

# REDHAVEN (5): 2x6A, 2x5A, 1x4A
rh = [("SCH047","Redhaven High School","Redhaven HS","Redhaven",1250,"Public","6A"),
      ("SCH048","Pacific High School","Pacific","Redhaven",1050,"Public","6A"),
      ("SCH049","Harbor High School","Harbor","Redhaven",880,"Public","5A"),
      ("SCH050","Ocean View High School","Ocean View","Redhaven",720,"Public","5A"),
      ("SCH051","Sequoia High School","Sequoia","Redhaven",550,"Public","4A")]
for row in rh: add(*row)

# VOLCANO RIDGE (4): 1x6A, 2x5A, 1x4A
vr = [("SCH052","Volcano Ridge High School","VR HS","Volcano Ridge",1180,"Public","6A"),
      ("SCH053","Summit High School","Summit","Volcano Ridge",920,"Public","5A"),
      ("SCH054","Crater High School","Crater","Volcano Ridge",750,"Public","5A"),
      ("SCH055","Lava Ridge High School","Lava Ridge","Volcano Ridge",580,"Public","4A")]
for row in vr: add(*row)

# SILVERTON (3): 1x5A, 1x4A, 1x3A
st = [("SCH056","Silverton High School","Silverton HS","Silverton",950,"Public","5A"),
      ("SCH057","Basin High School","Basin","Silverton",720,"Public","4A"),
      ("SCH058","Desert Edge High School","Desert Edge","Silverton",480,"Public","3A")]
for row in st: add(*row)

# CANYON CREEK (3): 1x5A, 1x4A, 1x3A
cc = [("SCH059","Canyon Creek High School","CC HS","Canyon Creek",880,"Public","5A"),
      ("SCH060","Snake River High School","Snake River","Canyon Creek",650,"Public","4A"),
      ("SCH061","Frontier Valley High School","Frontier Valley","Canyon Creek",420,"Public","3A")]
for row in cc: add(*row)

# KLAMATH JUNCTION (3): 1x4A, 1x3A, 1x2A
kj = [("SCH062","Klamath Junction High School","KJ HS","Klamath Junction",680,"Public","4A"),
      ("SCH063","Uplands High School","Uplands","Klamath Junction",480,"Public","3A"),
      ("SCH064","Railroad Union High School","Railroad Union","Klamath Junction",280,"Public","2A")]
for row in kj: add(*row)

# MENDOTA (3): 1x4A, 1x3A, 1x2A
md = [("SCH065","Mendota High School","Mendota HS","Mendota",650,"Public","4A"),
      ("SCH066","Delta High School","Delta","Mendota",450,"Public","3A"),
      ("SCH067","Bay View High School","Bay View","Mendota",280,"Public","2A")]
for row in md: add(*row)

# DESERT SPRINGS (3): 1x4A, 1x3A, 1x2A
ds = [("SCH068","Desert Springs High School","DS HS","Desert Springs",620,"Public","4A"),
      ("SCH069","Geothermal High School","Geothermal","Desert Springs",420,"Public","3A"),
      ("SCH070","Oasis High School","Oasis","Desert Springs",250,"Public","2A")]
for row in ds: add(*row)

# OAKMERE (3): 1x3A, 2x2A
om = [("SCH071","Oakmere High School","Oakmere HS","Oakmere",450,"Public","3A"),
      ("SCH072","Valley Oak High School","Valley Oak","Oakmere",320,"Public","2A"),
      ("SCH073","Mere Creek High School","Mere Creek","Oakmere",220,"Public","2A")]
for row in om: add(*row)

# CASCADE HEIGHTS (2): 1x3A, 1x2A
ch = [("SCH074","Cascade Heights High School","CH HS","Cascade Heights",420,"Public","3A"),
      ("SCH075","Heights View High School","Heights View","Cascade Heights",280,"Public","2A")]
for row in ch: add(*row)

# FORT BRAGGTON (2): 1x3A, 1x2A
fb = [("SCH076","Fort Braggton High School","FB HS","Fort Braggton",380,"Public","3A"),
      ("SCH077","Headland High School","Headland","Fort Braggton",250,"Public","2A")]
for row in fb: add(*row)

# LASSEN PEAK (2): 1x3A, 1x2A
lp = [("SCH078","Lassen Peak High School","LP HS","Lassen Peak",350,"Public","3A"),
      ("SCH079","Ski Valley High School","Ski Valley","Lassen Peak",220,"Public","2A")]
for row in lp: add(*row)

# PAYETTE CROSSING (2): 1x3A, 1x2A
pc = [("SCH080","Payette Crossing High School","PC HS","Payette Crossing",350,"Public","3A"),
      ("SCH081","River Crossing High School","River Crossing","Payette Crossing",220,"Public","2A")]
for row in pc: add(*row)

# WILLOWBROOK (2): 1x2A, 1x1A
wb = [("SCH082","Willowbrook High School","WB HS","Willowbrook",280,"Public","2A"),
      ("SCH083","Brookside High School","Brookside","Willowbrook",150,"Public","1A")]
for row in wb: add(*row)

# TRINITY MINE (2): 1x2A, 1x1A
tm = [("SCH084","Trinity Mine High School","TM HS","Trinity Mine",250,"Public","2A"),
      ("SCH085","Miners Union High School","Miners Union","Trinity Mine",120,"Public","1A")]
for row in tm: add(*row)

# MODOC FLATS (2): 1x2A, 1x1A
mf = [("SCH086","Modoc Flats High School","MF HS","Modoc Flats",250,"Public","2A"),
      ("SCH087","Flatlands High School","Flatlands","Modoc Flats",120,"Public","1A")]
for row in mf: add(*row)

# OWYHEE CANYON (2): 1x2A, 1x1A
oc = [("SCH088","Owyhee Canyon High School","OC HS","Owyhee Canyon",250,"Public","2A"),
      ("SCH089","Canyon Rim High School","Canyon Rim","Owyhee Canyon",120,"Public","1A")]
for row in oc: add(*row)

# LAKEVIEW TERRACE (1): 1x2A
lt = [("SCH090","Lakeview Terrace High School","LT HS","Lakeview Terrace",250,"Public","2A")]
for row in lt: add(*row)

# County seats (12): mostly 2A/1A
cs = [("SCH091","Douglasville High School","Douglasville HS","Douglasville",220,"Public","2A"),
      ("SCH092","Curry Landing High School","Curry Landing HS","Curry Landing",210,"Public","2A"),
      ("SCH093","Jackson Point High School","Jackson Point HS","Jackson Point",200,"Public","2A"),
      ("SCH094","Washoe Junction High School","Washoe Junction HS","Washoe Junction",190,"Public","2A"),
      ("SCH095","Siskiyou Pass High School","Siskiyou Pass HS","Siskiyou Pass",180,"Public","2A"),
      ("SCH096","Malheur Center High School","Malheur Center HS","Malheur Center",170,"Public","2A"),
      ("SCH097","Humboldt Bay High School","Humboldt Bay HS","Humboldt Bay",160,"Public","2A"),
      ("SCH098","Glenn High School","Glenn HS","Glenn",150,"Public","2A"),
      ("SCH099","Plumas Grove High School","Plumas Grove HS","Plumas Grove",140,"Public","2A"),
      ("SCH100","Tehama Bridge High School","Tehama Bridge HS","Tehama Bridge",130,"Public","2A"),
      ("SCH101","Del Norte Head High School","Del Norte Head HS","Del Norte Head",120,"Public","1A"),
      ("SCH102","Butte Valley High School","Butte Valley HS","Butte Valley",110,"Public","1A")]
for row in cs: add(*row)

# Agricultural/resort/coastal towns (20): all 1A
towns = [("SCH103","Grainfield High School","Grainfield HS","Grainfield",120,"Public","1A"),
         ("SCH104","Orchardale High School","Orchardale HS","Orchardale",110,"Public","1A"),
         ("SCH105","Ranchero High School","Ranchero HS","Ranchero",100,"Public","1A"),
         ("SCH106","Vineyard Mesa High School","Vineyard Mesa HS","Vineyard Mesa",95,"Public","1A"),
         ("SCH107","Dairy Hollow High School","Dairy Hollow HS","Dairy Hollow",90,"Public","1A"),
         ("SCH108","Alfalfa Springs High School","Alfalfa Springs HS","Alfalfa Springs",85,"Public","1A"),
         ("SCH109","Cornerville High School","Cornerville HS","Cornerville",80,"Public","1A"),
         ("SCH110","Sheep Camp High School","Sheep Camp HS","Sheep Camp",75,"Public","1A"),
         ("SCH111","Summit Lodge High School","Summit Lodge HS","Summit Lodge",100,"Public","1A"),
         ("SCH112","Crystal Lake High School","Crystal Lake HS","Crystal Lake",90,"Public","1A"),
         ("SCH113","Pine Haven High School","Pine Haven HS","Pine Haven",80,"Public","1A"),
         ("SCH114","Hot Springs High School","Hot Springs HS","Hot Springs",70,"Public","1A"),
         ("SCH115","Eagle Nest High School","Eagle Nest HS","Eagle Nest",60,"Public","1A"),
         ("SCH116","Deer Park High School","Deer Park HS","Deer Park",50,"Public","1A"),
         ("SCH117","Seabright High School","Seabright HS","Seabright",90,"Public","1A"),
         ("SCH118","Rockport High School","Rockport HS","Rockport",80,"Public","1A"),
         ("SCH119","Moonstone Beach High School","Moonstone Beach HS","Moonstone Beach",70,"Public","1A"),
         ("SCH120","Capetown High School","Capetown HS","Capetown",60,"Public","1A"),
         ("SCH121","Sandbar High School","Sandbar HS","Sandbar",50,"Public","1A"),
         ("SCH122","Lighthouse Point High School","Lighthouse Point HS","Lighthouse Point",45,"Public","1A")]
for row in towns: add(*row)

# Rural communities (17): all 1A
rural = [("SCH123","Crossroads High School","Crossroads HS","Crossroads",40,"Public","1A"),
         ("SCH124","Whispering Pines High School","Whispering Pines HS","Whispering Pines",35,"Public","1A"),
         ("SCH125","Dry Creek High School","Dry Creek HS","Dry Creek",30,"Public","1A"),
         ("SCH126","Ghost Rock High School","Ghost Rock HS","Ghost Rock",28,"Public","1A"),
         ("SCH127","Prairie Home High School","Prairie Home HS","Prairie Home",26,"Public","1A"),
         ("SCH128","Milltown High School","Milltown HS","Milltown",24,"Public","1A"),
         ("SCH129","Basin View High School","Basin View HS","Basin View",22,"Public","1A"),
         ("SCH130","Iron Springs High School","Iron Springs HS","Iron Springs",20,"Public","1A"),
         ("SCH131","Cedar Flat High School","Cedar Flat HS","Cedar Flat",18,"Public","1A"),
         ("SCH132","Sunset Mesa High School","Sunset Mesa HS","Sunset Mesa",16,"Public","1A"),
         ("SCH133","Willow Creek High School","Willow Creek HS","Willow Creek",14,"Public","1A"),
         ("SCH134","Black Rock High School","Black Rock HS","Black Rock",12,"Public","1A"),
         ("SCH135","Morning Star High School","Morning Star HS","Morning Star",10,"Public","1A"),
         ("SCH136","Fox Gulch High School","Fox Gulch HS","Fox Gulch",9,"Public","1A"),
         ("SCH137","Antelope Run High School","Antelope Run HS","Antelope Run",8,"Public","1A"),
         ("SCH138","Stone Bridge High School","Stone Bridge HS","Stone Bridge",7,"Public","1A"),
         ("SCH139","Lost Valley High School","Lost Valley HS","Lost Valley",6,"Public","1A")]
for row in rural: add(*row)

# Union/rural schools (16): mix 2A/1A
union = [("SCH140","Harney County Union High School","Harney Union","Malheur Center",200,"Public","2A"),
         ("SCH141","Silver Basin Union High School","Silver Basin Union","Silverton",220,"Public","2A"),
         ("SCH142","Trinity Mountain Union High School","Trinity Union","Trinity Mine",180,"Public","2A"),
         ("SCH143","Owyhee Rim Union High School","Owyhee Union","Owyhee Canyon",170,"Public","2A"),
         ("SCH144","Klamath Uplands Union High School","Klamath Union","Klamath Junction",210,"Public","2A"),
         ("SCH145","Redwood Coast Union High School","Redwood Union","Redhaven",200,"Public","2A"),
         ("SCH146","Shasta Highlands Union High School","Shasta Union","Volcano Ridge",190,"Public","2A"),
         ("SCH147","Humboldt Delta Union High School","Humboldt Union","Mendota",180,"Public","2A"),
         ("SCH148","Boise Frontier Union High School","Frontier Union","Newbridge",200,"Public","2A"),
         ("SCH149","Cascadia Valley Union High School","Valley Union","Ashford",210,"Public","2A"),
         ("SCH150","Great Basin Union High School","Basin Union","Desert Springs",150,"Public","1A"),
         ("SCH151","East County High School","East County","Modoc Flats",180,"Public","2A"),
         ("SCH152","West County High School","West County","Douglasville",180,"Public","2A"),
         ("SCH153","North County High School","North County","Glenn",170,"Public","2A"),
         ("SCH154","South County High School","South County","Jackson Point",160,"Public","2A"),
         ("SCH155","Central County High School","Central County","Tehama Bridge",150,"Public","1A")]
for row in union: add(*row)

# County-style rural schools (45): all 1A to fill quota
county_rural = [
    ("SCH156","Mountain View High School","Mountain View","Siskiyou Pass",140,"Public","1A"),
    ("SCH157","Valley Center High School","Valley Center","Butte Valley",130,"Public","1A"),
    ("SCH158","River Valley High School","River Valley","Payette Crossing",160,"Public","1A"),
    ("SCH159","Lake County Union High School","Lake Union","Lakeview Terrace",150,"Public","1A"),
    ("SCH160","Coastal Union High School","Coastal Union","Curry Landing",140,"Public","1A"),
    ("SCH161","Border High School","Border HS","Del Norte Head",120,"Public","1A"),
    ("SCH162","Washoe County High School","Washoe County","Washoe Junction",140,"Public","1A"),
    ("SCH163","Humboldt County High School","Humboldt County","Humboldt Bay",130,"Public","1A"),
    ("SCH164","Plumas County High School","Plumas County","Plumas Grove",120,"Public","1A"),
    ("SCH165","High Desert High School","High Desert","Alfalfa Springs",110,"Public","1A"),
    ("SCH166","Orchard County High School","Orchard County","Orchardale",130,"Public","1A"),
    ("SCH167","Vineyard County High School","Vineyard County","Vineyard Mesa",120,"Public","1A"),
    ("SCH168","Dairy County High School","Dairy County","Dairy Hollow",110,"Public","1A"),
    ("SCH169","Grain County High School","Grain County","Grainfield",120,"Public","1A"),
    ("SCH170","Corn County High School","Corn County","Cornerville",100,"Public","1A"),
    ("SCH171","Sheep County High School","Sheep County","Sheep Camp",90,"Public","1A"),
    ("SCH172","Ranch County High School","Ranch County","Ranchero",110,"Public","1A"),
    ("SCH173","Summit County High School","Summit County","Summit Lodge",100,"Public","1A"),
    ("SCH174","Crystal County High School","Crystal County","Crystal Lake",90,"Public","1A"),
    ("SCH175","Pine County High School","Pine County","Pine Haven",80,"Public","1A"),
    ("SCH176","Eagle County High School","Eagle County","Eagle Nest",70,"Public","1A"),
    ("SCH177","Deer County High School","Deer County","Deer Park",60,"Public","1A"),
    ("SCH178","Seabright County High School","Seabright County","Seabright",80,"Public","1A"),
    ("SCH179","Rock County High School","Rock County","Rockport",70,"Public","1A"),
    ("SCH180","Moonstone County High School","Moonstone County","Moonstone Beach",60,"Public","1A"),
    ("SCH181","Cape County High School","Cape County","Capetown",50,"Public","1A"),
    ("SCH182","Sand County High School","Sand County","Sandbar",40,"Public","1A"),
    ("SCH183","Light County High School","Light County","Lighthouse Point",35,"Public","1A"),
    ("SCH184","Cross County High School","Cross County","Crossroads",30,"Public","1A"),
    ("SCH185","Whisper County High School","Whisper County","Whispering Pines",28,"Public","1A"),
    ("SCH186","Dry County High School","Dry County","Dry Creek",26,"Public","1A"),
    ("SCH187","Ghost County High School","Ghost County","Ghost Rock",24,"Public","1A"),
    ("SCH188","Prairie County High School","Prairie County","Prairie Home",22,"Public","1A"),
    ("SCH189","Mill County High School","Mill County","Milltown",20,"Public","1A"),
    ("SCH190","View County High School","View County","Basin View",18,"Public","1A"),
    ("SCH191","Iron County High School","Iron County","Iron Springs",16,"Public","1A"),
    ("SCH192","Cedar County High School","Cedar County","Cedar Flat",14,"Public","1A"),
    ("SCH193","Sunset County High School","Sunset County","Sunset Mesa",12,"Public","1A"),
    ("SCH194","Creek County High School","Creek County","Willow Creek",10,"Public","1A"),
    ("SCH195","Black Rock County High School","Black Rock County","Black Rock",9,"Public","1A"),
    ("SCH196","Star County High School","Star County","Morning Star",8,"Public","1A"),
    ("SCH197","Fox County High School","Fox County","Fox Gulch",7,"Public","1A"),
    ("SCH198","Antelope County High School","Antelope County","Antelope Run",6,"Public","1A"),
    ("SCH199","Bridge County High School","Bridge County","Stone Bridge",5,"Public","1A"),
    ("SCH200","Lost County High School","Lost County","Lost Valley",5,"Public","1A"),
]
for row in county_rural: add(*row)

# Additional schools to reach 255 - distributed across larger cities
extra = [
    # More 6A (need ~18 more)
    ("SCH200","Ashford Northwest High School","NW Ashford","Ashford",1420,"Public","6A"),
    ("SCH201","Ashford Southwest High School","SW Ashford","Ashford",1350,"Public","6A"),
    ("SCH202","Ashford Southeast High School","SE Ashford","Ashford",1280,"Public","6A"),
    ("SCH203","Port Valdez East High School","PV East","Port Valdez",1220,"Public","6A"),
    ("SCH204","Newbridge North High School","N. Newbridge","Newbridge",1180,"Public","6A"),
    ("SCH205","Timberlake West High School","W. Timberlake","Timberlake",1120,"Public","6A"),
    ("SCH206","Redhaven North High School","N. Redhaven","Redhaven",1080,"Public","6A"),
    ("SCH207","Volcano Ridge North High School","N. Volcano Ridge","Volcano Ridge",1050,"Public","6A"),
    # More 5A (need ~25 more)
    ("SCH208","Silverton North High School","N. Silverton","Silverton",980,"Public","5A"),
    ("SCH209","Canyon Creek North High School","N. Canyon Creek","Canyon Creek",920,"Public","5A"),
    ("SCH210","Klamath North High School","N. Klamath","Klamath Junction",880,"Public","5A"),
    ("SCH211","Mendota North High School","N. Mendota","Mendota",850,"Public","5A"),
    ("SCH212","Desert North High School","N. Desert","Desert Springs",820,"Public","5A"),
    ("SCH213","Oakmere North High School","N. Oakmere","Oakmere",780,"Public","5A"),
    ("SCH214","Cascade North High School","N. Cascade","Cascade Heights",750,"Public","5A"),
    ("SCH215","Fort North High School","N. Fort","Fort Braggton",720,"Public","5A"),
    ("SCH216","Lassen North High School","N. Lassen","Lassen Peak",680,"Public","5A"),
    ("SCH217","Payette North High School","N. Payette","Payette Crossing",650,"Public","5A"),
    ("SCH218","Willow North High School","N. Willow","Willowbrook",620,"Public","5A"),
    ("SCH219","Trinity North High School","N. Trinity","Trinity Mine",580,"Public","5A"),
    ("SCH220","Modoc North High School","N. Modoc","Modoc Flats",550,"Public","5A"),
    ("SCH221","Owyhee North High School","N. Owyhee","Owyhee Canyon",520,"Public","5A"),
    ("SCH222","Lakeview North High School","N. Lakeview","Lakeview Terrace",480,"Public","5A"),
    ("SCH223","Douglas North High School","N. Douglas","Douglasville",450,"Public","5A"),
    ("SCH224","Curry North High School","N. Curry","Curry Landing",420,"Public","5A"),
    ("SCH225","Jackson North High School","N. Jackson","Jackson Point",380,"Public","5A"),
    ("SCH226","Washoe North High School","N. Washoe","Washoe Junction",350,"Public","5A"),
    # More 4A (need ~20 more)
    ("SCH227","Siskiyou North High School","N. Siskiyou","Siskiyou Pass",550,"Public","4A"),
    ("SCH228","Malheur North High School","N. Malheur","Malheur Center",520,"Public","4A"),
    ("SCH229","Humboldt North High School","N. Humboldt","Humboldt Bay",480,"Public","4A"),
    ("SCH230","Glenn North High School","N. Glenn","Glenn",450,"Public","4A"),
    ("SCH231","Plumas North High School","N. Plumas","Plumas Grove",420,"Public","4A"),
    ("SCH232","Tehama North High School","N. Tehama","Tehama Bridge",380,"Public","4A"),
    ("SCH233","Del Norte North High School","N. Del Norte","Del Norte Head",350,"Public","4A"),
    ("SCH234","Butte North High School","N. Butte","Butte Valley",320,"Public","4A"),
    ("SCH235","Grain North High School","N. Grain","Grainfield",280,"Public","4A"),
    ("SCH236","Orchard North High School","N. Orchard","Orchardale",260,"Public","4A"),
    ("SCH237","Ranch North High School","N. Ranch","Ranchero",240,"Public","4A"),
    ("SCH238","Vineyard North High School","N. Vineyard","Vineyard Mesa",220,"Public","4A"),
    ("SCH239","Dairy North High School","N. Dairy","Dairy Hollow",200,"Public","4A"),
    ("SCH240","Alfalfa North High School","N. Alfalfa","Alfalfa Springs",180,"Public","4A"),
    # More 3A (need ~18 more)
    ("SCH241","Corn North High School","N. Corn","Cornerville",350,"Public","3A"),
    ("SCH242","Sheep North High School","N. Sheep","Sheep Camp",320,"Public","3A"),
    ("SCH243","Summit North High School","N. Summit","Summit Lodge",300,"Public","3A"),
    ("SCH244","Crystal North High School","N. Crystal","Crystal Lake",280,"Public","3A"),
    ("SCH245","Pine North High School","N. Pine","Pine Haven",260,"Public","3A"),
    ("SCH246","Hot North High School","N. Hot","Hot Springs",240,"Public","3A"),
    ("SCH247","Eagle North High School","N. Eagle","Eagle Nest",220,"Public","3A"),
    ("SCH248","Deer North High School","N. Deer","Deer Park",200,"Public","3A"),
    ("SCH249","Sea North High School","N. Sea","Seabright",180,"Public","3A"),
    ("SCH250","Rock North High School","N. Rock","Rockport",160,"Public","3A"),
    # More 2A (need ~16 more)
    ("SCH251","Moon North High School","N. Moon","Moonstone Beach",280,"Public","2A"),
    ("SCH252","Cape North High School","N. Cape","Capetown",260,"Public","2A"),
    ("SCH253","Sand North High School","N. Sand","Sandbar",240,"Public","2A"),
    ("SCH254","Light North High School","N. Light","Lighthouse Point",220,"Public","2A"),
    ("SCH255","Ashford Gateway High School","Gateway","Ashford",400,"Public","4A"),
]
for row in extra: add(*row)

print(f"Total schools: {len(SCHOOLS)}")

# Check class counts
class_counts = {}
for s in SCHOOLS:
    class_counts[s["classification"]] = class_counts.get(s["classification"], 0) + 1
print(f"Class distribution: {class_counts}")

# CONFERENCES (32)
CONFERENCES = [
    {"id": "C01", "name": "Cascadia Metro Conference", "region": "Cascadia Central Valley", "description": "Ashford metropolitan area schools", "schools": []},
    {"id": "C02", "name": "Central Valley League", "region": "Cascadia Central Valley", "description": "Mid-valley agricultural communities", "schools": []},
    {"id": "C03", "name": "Redwood Coast Conference", "region": "Redwood Coast", "description": "Northern coastal schools", "schools": []},
    {"id": "C04", "name": "Pacific Maritime League", "region": "Redwood Coast", "description": "Port Valdez metro area", "schools": []},
    {"id": "C05", "name": "Shasta Mountain Conference", "region": "Shasta Highlands", "description": "Volcanic highland schools", "schools": []},
    {"id": "C06", "name": "Silver Basin League", "region": "Silver Basin", "description": "Eastern basin agricultural schools", "schools": []},
    {"id": "C07", "name": "Boise Frontier Conference", "region": "Boise Frontier Corridor", "description": "Newbridge metro and Boise-edge schools", "schools": []},
    {"id": "C08", "name": "Snake River League", "region": "Boise Frontier Corridor", "description": "Snake River corridor schools", "schools": []},
    {"id": "C09", "name": "Klamath Uplands Conference", "region": "Klamath Uplands", "description": "Southern upland agricultural schools", "schools": []},
    {"id": "C10", "name": "Humboldt Delta League", "region": "Humboldt Delta", "description": "Delta and bay area schools", "schools": []},
    {"id": "C11", "name": "Harney Expanse Conference", "region": "Harney Expanse", "description": "High desert frontier schools", "schools": []},
    {"id": "C12", "name": "Trinity Mountain League", "region": "Trinity Mountains", "description": "Mountain mining heritage schools", "schools": []},
    {"id": "C13", "name": "Owyhee Rim Conference", "region": "Owyhee Rim Country", "description": "Canyon country ranching schools", "schools": []},
    {"id": "C14", "name": "Ashford City League", "region": "Cascadia Central Valley", "description": "Ashford inner city schools", "schools": []},
    {"id": "C15", "name": "Timberlake Suburban Conference", "region": "Cascadia Central Valley", "description": "Timberlake area suburban schools", "schools": []},
    {"id": "C16", "name": "North Valley League", "region": "Cascadia Central Valley", "description": "Northern valley communities", "schools": []},
    {"id": "C17", "name": "South Valley Conference", "region": "Cascadia Central Valley", "description": "Southern valley agricultural schools", "schools": []},
    {"id": "C18", "name": "Coastal Redwoods League", "region": "Redwood Coast", "description": "Redwood forest coastal schools", "schools": []},
    {"id": "C19", "name": "Volcanic Peaks Conference", "region": "Shasta Highlands", "description": "High elevation mountain schools", "schools": []},
    {"id": "C20", "name": "Desert Springs League", "region": "Harney Expanse", "description": "Geothermal oasis schools", "schools": []},
    {"id": "C21", "name": "Frontier Interstate Conference", "region": "Boise Frontier Corridor", "description": "Interstate corridor schools", "schools": []},
    {"id": "C22", "name": "Orchard Belt League", "region": "Klamath Uplands", "description": "Fruit growing region schools", "schools": []},
    {"id": "C23", "name": "Grain Belt Conference", "region": "Cascadia Central Valley", "description": "Wheat and barley farming schools", "schools": []},
    {"id": "C24", "name": "Ranch Country League", "region": "Silver Basin", "description": "Cattle ranching schools", "schools": []},
    {"id": "C25", "name": "Mining Heritage Conference", "region": "Trinity Mountains", "description": "Historic mining town schools", "schools": []},
    {"id": "C26", "name": "Canyon Lands League", "region": "Owyhee Rim Country", "description": "Deep canyon ranching schools", "schools": []},
    {"id": "C27", "name": "Bay Area Conference", "region": "Humboldt Delta", "description": "Humboldt Bay vicinity schools", "schools": []},
    {"id": "C28", "name": "Resort Town League", "region": "Shasta Highlands", "description": "Mountain resort community schools", "schools": []},
    {"id": "C29", "name": "Frontier Rural Conference", "region": "Harney Expanse", "description": "Isolated frontier schools", "schools": []},
    {"id": "C30", "name": "Valley Floor League", "region": "Cascadia Central Valley", "description": "Central valley floor schools", "schools": []},
    {"id": "C31", "name": "Coastal Bluffs Conference", "region": "Redwood Coast", "description": "Coastal bluff community schools", "schools": []},
    {"id": "C32", "name": "High Desert League", "region": "Silver Basin", "description": "High desert farming schools", "schools": []},
]

# Assign schools to conferences
region_conf_map = {
    "Cascadia Central Valley": ["C01", "C02", "C14", "C15", "C16", "C17", "C23", "C30"],
    "Redwood Coast": ["C03", "C04", "C18", "C31"],
    "Shasta Highlands": ["C05", "C19", "C28"],
    "Silver Basin": ["C06", "C24", "C32"],
    "Boise Frontier Corridor": ["C07", "C08", "C21"],
    "Klamath Uplands": ["C09", "C22"],
    "Harney Expanse": ["C11", "C20", "C29"],
    "Trinity Mountains": ["C12", "C25"],
    "Humboldt Delta": ["C10", "C27"],
    "Owyhee Rim Country": ["C13", "C26"],
}

conf_counter = {}
for sch in SCHOOLS:
    region = sch["region"]
    conf_ids = region_conf_map.get(region, ["C01"])
    base_conf = conf_ids[0]
    if base_conf not in conf_counter: conf_counter[base_conf] = 0
    idx = conf_counter[base_conf] % len(conf_ids)
    conf_id = conf_ids[idx]
    conf_counter[base_conf] = conf_counter.get(base_conf, 0) + 1
    for c in CONFERENCES:
        if c["id"] == conf_id:
            c["schools"].append(sch["school_id"])
            sch["conference"] = conf_id
            break

# Save files
with open("/workspace/jefferson_data/regions.json", "w") as f: json.dump(REGIONS, f, indent=2)
with open("/workspace/jefferson_data/settlements.json", "w") as f: json.dump(SETTLEMENTS, f, indent=2)
with open("/workspace/jefferson_data/schools.json", "w") as f: json.dump(SCHOOLS, f, indent=2)
with open("/workspace/jefferson_data/conferences.json", "w") as f: json.dump(CONFERENCES, f, indent=2)

# Generate reference document
ref = """# JEFFERSON STATE GEOGRAPHY REFERENCE

## Overview
Jefferson is an alternate-history western U.S. state with approximately 4 million residents, formed from portions of present-day Oregon, California, Nevada, and Idaho. All settlements and institutions are fictional.

## Major Regions (10)

1. **Cascadia Central Valley** - The heartland containing Ashford (state capital, 587k) and the primary metro area. Agricultural powerhouse and urban corridor.
2. **Redwood Coast** - Northern Pacific coastline with Port Valdez (234k), ancient forests, and maritime economy.
3. **Shasta Highlands** - Volcanic mountain region with Volcano Ridge (112k), recreation, and forestry.
4. **Silver Basin** - High desert basin with Silverton (94k), irrigated agriculture and ranching.
5. **Boise Frontier Corridor** - Northeastern edge with Newbridge (198k), part of greater Boise metropolitan region.
6. **Klamath Uplands** - Southern interior with Klamath Junction (76k), orchards and cattle ranching.
7. **Harney Expanse** - Vast high desert with Desert Springs (68k), frontier ranching and isolated communities.
8. **Trinity Mountains** - Rugged inland range with Trinity Mine (36k), mining heritage and timber.
9. **Humboldt Delta** - Coastal plain with Mendota (72k), port economy and university.
10. **Owyhee Rim Country** - Deep canyon country with Owyhee Canyon (31k), ranching and irrigation.

## Largest Cities and Metros

### Primary Metro: Ashford Metropolitan Area (~1M)
- Ashford (587k) - State capital, economic center
- Timberlake (168k) - University town, tech corridor
- Oakmere (58k) - Suburban manufacturing
- Cascade Heights (52k) - Commuter suburb
- Willowbrook (39k) - Food processing
- Douglasville (24.5k) - County seat
- Glenn (15k) - Farm service
- Tehama Bridge (13k) - Historic bridge town
- Butte Valley (11k) - Rice farming

### Port Valdez Metro (~450k)
- Port Valdez (234k) - Deep-water port, timber export
- Redhaven (152k) - Fishing fleet homeport
- Fort Braggton (47k) - Historic fort, tourism
- Humboldt Bay (16k) - Small port, oyster farming
- Seabright (5.9k) - Artist colony

### Greater Boise-Jefferson Metro (~320k)
- Newbridge (198k) - Boise bedroom/employment center
- Canyon Creek (82k) - Suburban residential, light industry
- Payette Crossing (41k) - Logistics, trucking hub

## Secondary Regional Cities
- Volcano Ridge (112k) - Mountain recreation gateway
- Silverton (94k) - Agricultural processing
- Klamath Junction (76k) - Rail hub, livestock auction
- Mendota (72k) - University, coastal agriculture research
- Desert Springs (68k) - Geothermal energy

## School Classification Distribution (255 schools)
- 6A: Large metro schools (1000+ enrollment) - primarily Ashford, Port Valdez, Newbridge, Timberlake
- 5A: Major city schools (700-999) - regional cities
- 4A: Mid-size city schools (400-699) - smaller cities
- 3A: Small city/town schools (250-399) - county seats
- 2A: Town/rural schools (150-249) - agricultural towns
- 1A: Small rural schools (<150) - remote communities

## Conference Areas (32)
Conferences are geographically-based regular-season groupings mixing classifications:
- **Cascadia Metro/Central Valley leagues** (C01, C02, C14, C15, C16, C17, C23, C30): Serve Ashford metro area
- **Redwood Coast/Pacific Maritime** (C03, C04, C18, C31): Coastal schools from Port Valdez to border
- **Shasta Mountain/Volcanic Peaks** (C05, C19, C28): Highland and resort communities
- **Silver Basin/Ranch Country/High Desert** (C06, C24, C32): Eastern desert agricultural schools
- **Boise Frontier/Snake River** (C07, C08, C21): Boise-edge corridor schools
- **Klamath Uplands/Orchard Belt** (C09, C22): Southern orchard and upland schools
- **Harney Expanse/Desert/Frontier Rural** (C11, C20, C29): Vast high desert frontier
- **Trinity/Mining Heritage** (C12, C25): Mountain mining heritage communities
- **Owyhee/Canyon Lands** (C13, C26): Deep canyon ranching country
- **Humboldt Delta/Bay Area** (C10, C27): Delta and bay vicinity

## Transportation/Settlement Corridors
1. **Central Valley Corridor**: Ashford-Timberlake-Oakmere-Cascade Heights axis
2. **Coastal Corridor**: Port Valdez-Redhaven-Fort Braggton-Seabright
3. **Boise Frontier Corridor**: Newbridge-Canyon Creek-Payette Crossing (interstate to Boise)
4. **Mountain Corridor**: Volcano Ridge-Summit Lodge-Lassen Peak
5. **Desert Corridor**: Silverton-Desert Springs-Malheur Center
6. **Klamath Corridor**: Klamath Junction-Jackson Point-Orchardale-Vineyard Mesa
"""

with open("/workspace/jefferson_data/REFERENCE.md", "w") as f: f.write(ref)

print("\nFiles saved successfully!")
print("Generated: regions.json, settlements.json, schools.json, conferences.json, REFERENCE.md")

# Final validation
print("\n=== FINAL VALIDATION ===")
print(f"Regions: {len(REGIONS)}")
print(f"Settlements: {len(SETTLEMENTS)}")
print(f"Schools: {len(SCHOOLS)}")
print(f"Conferences: {len(CONFERENCES)}")

# Check duplicates
names = [s["name"] for s in SCHOOLS]
dupes = set([n for n in names if names.count(n) > 1])
if dupes: print(f"ERROR: Duplicate school names: {dupes}")
else: print("✓ No duplicate school names")

# Check all schools have conference
no_conf = [s for s in SCHOOLS if not s.get("conference")]
if no_conf: print(f"ERROR: Schools without conference: {len(no_conf)}")
else: print("✓ All schools assigned to conferences")

# Check all schools map to valid settlements
valid_cities = set(s["name"] for s in SETTLEMENTS)
invalid = [s for s in SCHOOLS if s["city"] not in valid_cities]
if invalid: print(f"ERROR: Schools with invalid city: {len(invalid)}")
else: print("✓ All schools map to valid settlements")

print(f"\nTotal population: {sum(s['population'] for s in SETTLEMENTS):,}")
