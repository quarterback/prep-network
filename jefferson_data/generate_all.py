#!/usr/bin/env python3
"""Jefferson State Complete Dataset Generator - All-in-one script"""
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

def get_class(enr):
    if enr >= 1800: return "6A"
    if enr >= 1400: return "5A"
    if enr >= 1000: return "4A"
    if enr >= 700: return "3A"
    if enr >= 400: return "2A"
    return "1A"

SCHOOLS = []
def add(sid, nm, sn, city, enr, typ="Public"):
    st = get_settlement(city)
    if not st: return
    SCHOOLS.append({"school_id": sid, "name": nm, "short_name": sn, "city": city, "region": st["region"], "type": typ, "enrollment": enr, "classification": get_class(enr), "conference": None})

# ASHFORD (24 schools)
add("SCH001","Ashford High School","Ashford HS","Ashford",2150)
add("SCH002","North Ashford High School","North Ashford","Ashford",1980)
add("SCH003","South Ashford High School","South Ashford","Ashford",1890)
add("SCH004","East Ashford High School","East Ashford","Ashford",1820)
add("SCH005","West Ashford High School","West Ashford","Ashford",1780)
add("SCH006","Central High School","Central","Ashford",1850)
add("SCH007","Ashford Memorial High School","Memorial","Ashford",1720)
add("SCH008","Washington High School","Washington","Ashford",1650)
add("SCH009","Lincoln High School","Lincoln","Ashford",1590)
add("SCH010","Roosevelt High School","Roosevelt","Ashford",1540)
add("SCH011","Kennedy High School","Kennedy","Ashford",1480)
add("SCH012","Hamilton High School","Hamilton","Ashford",1420)
add("SCH013","Franklin High School","Franklin","Ashford",1380)
add("SCH014","Valley View High School","Valley View","Ashford",1320)
add("SCH015","Cascade High School","Cascade","Ashford",1260)
add("SCH016","Pioneer High School","Pioneer","Ashford",1200)
add("SCH017","Heritage High School","Heritage","Ashford",1150)
add("SCH018","Ashford Technical High School","Ashford Tech","Ashford",980)
add("SCH019","Ashford Arts Academy","Arts Academy","Ashford",850)
add("SCH020","St. Mary's Academy","St. Mary's","Ashford",620,"Private")
add("SCH021","Trinity Preparatory School","Trinity Prep","Ashford",540,"Private")
add("SCH022","Ashford Christian Academy","Christian Academy","Ashford",480,"Private")
add("SCH023","Sacred Heart High School","Sacred Heart","Ashford",420,"Private")
add("SCH024","Jefferson Leadership Academy","Leadership Academy","Ashford",380,"Private")

# PORT VALDEZ (8)
add("SCH025","Port Valdez High School","Port Valdez HS","Port Valdez",1680)
add("SCH026","North Port High School","North Port","Port Valdez",1450)
add("SCH027","South Port High School","South Port","Port Valdez",1380)
add("SCH028","Coastal High School","Coastal","Port Valdez",1220)
add("SCH029","Redwood High School","Redwood","Port Valdez",1150)
add("SCH030","Maritime Academy","Maritime","Port Valdez",920)
add("SCH031","Valdez Memorial High School","Valdez Memorial","Port Valdez",1080)
add("SCH032","St. Joseph's High School","St. Joseph's","Port Valdez",450,"Private")

# NEWBRIDGE (8)
add("SCH033","Newbridge High School","Newbridge HS","Newbridge",1620)
add("SCH034","East Newbridge High School","East Newbridge","Newbridge",1350)
add("SCH035","West Newbridge High School","West Newbridge","Newbridge",1280)
add("SCH036","Frontier High School","Frontier","Newbridge",1180)
add("SCH037","Boise Valley High School","Boise Valley","Newbridge",1050)
add("SCH038","Interstate High School","Interstate","Newbridge",950)
add("SCH039","Canyon View High School","Canyon View","Newbridge",880)
add("SCH040","Bethel Christian School","Bethel","Newbridge",420,"Private")

# TIMBERLAKE (6)
add("SCH041","Timberlake High School","Timberlake HS","Timberlake",1520)
add("SCH042","North Timberlake High School","N. Timberlake","Timberlake",1250)
add("SCH043","South Timberlake High School","S. Timberlake","Timberlake",1180)
add("SCH044","University High School","University","Timberlake",1020)
add("SCH045","Tech Valley High School","Tech Valley","Timberlake",880)
add("SCH046","Lake County High School","Lake County","Timberlake",720)

# REDHAVEN (5)
add("SCH047","Redhaven High School","Redhaven HS","Redhaven",1380)
add("SCH048","Pacific High School","Pacific","Redhaven",1120)
add("SCH049","Harbor High School","Harbor","Redhaven",980)
add("SCH050","Ocean View High School","Ocean View","Redhaven",850)
add("SCH051","Sequoia High School","Sequoia","Redhaven",720)

# VOLCANO RIDGE (4)
add("SCH052","Volcano Ridge High School","Volcano Ridge HS","Volcano Ridge",1280)
add("SCH053","Summit High School","Summit","Volcano Ridge",1050)
add("SCH054","Crater High School","Crater","Volcano Ridge",820)
add("SCH055","Lava Ridge High School","Lava Ridge","Volcano Ridge",680)

# SILVERTON (3)
add("SCH056","Silverton High School","Silverton HS","Silverton",1120)
add("SCH057","Basin High School","Basin","Silverton",880)
add("SCH058","Desert Edge High School","Desert Edge","Silverton",720)

# CANYON CREEK (3)
add("SCH059","Canyon Creek High School","Canyon Creek HS","Canyon Creek",980)
add("SCH060","Snake River High School","Snake River","Canyon Creek",820)
add("SCH061","Frontier Valley High School","Frontier Valley","Canyon Creek",680)

# KLAMATH JUNCTION (3)
add("SCH062","Klamath Junction High School","Klamath Junction HS","Klamath Junction",920)
add("SCH063","Uplands High School","Uplands","Klamath Junction",750)
add("SCH064","Railroad Union High School","Railroad Union","Klamath Junction",620)

# MENDOTA (3)
add("SCH065","Mendota High School","Mendota HS","Mendota",880)
add("SCH066","Delta High School","Delta","Mendota",720)
add("SCH067","Bay View High School","Bay View","Mendota",580)

# DESERT SPRINGS (3)
add("SCH068","Desert Springs High School","Desert Springs HS","Desert Springs",850)
add("SCH069","Geothermal High School","Geothermal","Desert Springs",680)
add("SCH070","Oasis High School","Oasis","Desert Springs",550)

# OAKMERE (3)
add("SCH071","Oakmere High School","Oakmere HS","Oakmere",780)
add("SCH072","Valley Oak High School","Valley Oak","Oakmere",650)
add("SCH073","Mere Creek High School","Mere Creek","Oakmere",520)

# CASCADE HEIGHTS (2)
add("SCH074","Cascade Heights High School","Cascade Heights HS","Cascade Heights",720)
add("SCH075","Heights View High School","Heights View","Cascade Heights",580)

# FORT BRAGGTON (2)
add("SCH076","Fort Braggton High School","Fort Braggton HS","Fort Braggton",650)
add("SCH077","Headland High School","Headland","Fort Braggton",520)

# LASSEN PEAK (2)
add("SCH078","Lassen Peak High School","Lassen Peak HS","Lassen Peak",580)
add("SCH079","Ski Valley High School","Ski Valley","Lassen Peak",450)

# PAYETTE CROSSING (2)
add("SCH080","Payette Crossing High School","Payette Crossing HS","Payette Crossing",550)
add("SCH081","River Crossing High School","River Crossing","Payette Crossing",420)

# WILLOWBROOK (2)
add("SCH082","Willowbrook High School","Willowbrook HS","Willowbrook",520)
add("SCH083","Brookside High School","Brookside","Willowbrook",400)

# TRINITY MINE (2)
add("SCH084","Trinity Mine High School","Trinity Mine HS","Trinity Mine",480)
add("SCH085","Miners Union High School","Miners Union","Trinity Mine",380)

# MODOC FLATS (2)
add("SCH086","Modoc Flats High School","Modoc Flats HS","Modoc Flats",450)
add("SCH087","Flatlands High School","Flatlands","Modoc Flats",350)

# OWYHEE CANYON (2)
add("SCH088","Owyhee Canyon High School","Owyhee Canyon HS","Owyhee Canyon",420)
add("SCH089","Canyon Rim High School","Canyon Rim","Owyhee Canyon",320)

# LAKEVIEW TERRACE (1)
add("SCH090","Lakeview Terrace High School","Lakeview Terrace HS","Lakeview Terrace",400)

# Remaining towns (1 each through SCH139)
towns_1sch = [
    ("SCH091","Douglasville HS","Douglasville",380),("SCH092","Curry Landing HS","Curry Landing",350),
    ("SCH093","Jackson Point HS","Jackson Point",320),("SCH094","Washoe Junction HS","Washoe Junction",300),
    ("SCH095","Siskiyou Pass HS","Siskiyou Pass",280),("SCH096","Malheur Center HS","Malheur Center",260),
    ("SCH097","Humboldt Bay HS","Humboldt Bay",240),("SCH098","Glenn HS","Glenn",220),
    ("SCH099","Plumas Grove HS","Plumas Grove",200),("SCH100","Tehama Bridge HS","Tehama Bridge",180),
    ("SCH101","Del Norte Head HS","Del Norte Head",160),("SCH102","Butte Valley HS","Butte Valley",150),
    ("SCH103","Grainfield HS","Grainfield",140),("SCH104","Orchardale HS","Orchardale",130),
    ("SCH105","Ranchero HS","Ranchero",120),("SCH106","Vineyard Mesa HS","Vineyard Mesa",110),
    ("SCH107","Dairy Hollow HS","Dairy Hollow",100),("SCH108","Alfalfa Springs HS","Alfalfa Springs",95),
    ("SCH109","Cornerville HS","Cornerville",90),("SCH110","Sheep Camp HS","Sheep Camp",85),
    ("SCH111","Summit Lodge HS","Summit Lodge",110),("SCH112","Crystal Lake HS","Crystal Lake",95),
    ("SCH113","Pine Haven HS","Pine Haven",80),("SCH114","Hot Springs HS","Hot Springs",70),
    ("SCH115","Eagle Nest HS","Eagle Nest",60),("SCH116","Deer Park HS","Deer Park",50),
    ("SCH117","Seabright HS","Seabright",85),("SCH118","Rockport HS","Rockport",70),
    ("SCH119","Moonstone Beach HS","Moonstone Beach",60),("SCH120","Capetown HS","Capetown",50),
    ("SCH121","Sandbar HS","Sandbar",40),("SCH122","Lighthouse Point HS","Lighthouse Point",35),
    ("SCH123","Crossroads HS","Crossroads",30),("SCH124","Whispering Pines HS","Whispering Pines",28),
    ("SCH125","Dry Creek HS","Dry Creek",26),("SCH126","Ghost Rock HS","Ghost Rock",24),
    ("SCH127","Prairie Home HS","Prairie Home",22),("SCH128","Milltown HS","Milltown",20),
    ("SCH129","Basin View HS","Basin View",18),("SCH130","Iron Springs HS","Iron Springs",16),
    ("SCH131","Cedar Flat HS","Cedar Flat",14),("SCH132","Sunset Mesa HS","Sunset Mesa",12),
    ("SCH133","Willow Creek HS","Willow Creek",11),("SCH134","Black Rock HS","Black Rock",10),
    ("SCH135","Morning Star HS","Morning Star",9),("SCH136","Fox Gulch HS","Fox Gulch",8),
    ("SCH137","Antelope Run HS","Antelope Run",7),("SCH138","Stone Bridge HS","Stone Bridge",6),
    ("SCH139","Lost Valley HS","Lost Valley",5),
]
for sid,sn,city,enr in towns_1sch: add(sid,city+" High School",sn,city,enr)

# Union/rural schools (SCH140-SCH155)
union_schools = [
    ("SCH140","Harney County Union High School","Harney Union","Malheur Center",180),
    ("SCH141","Silver Basin Union High School","Silver Basin Union","Silverton",220),
    ("SCH142","Trinity Mountain Union High School","Trinity Union","Trinity Mine",160),
    ("SCH143","Owyhee Rim Union High School","Owyhee Union","Owyhee Canyon",140),
    ("SCH144","Klamath Uplands Union High School","Klamath Union","Klamath Junction",200),
    ("SCH145","Redwood Coast Union High School","Redwood Union","Redhaven",180),
    ("SCH146","Shasta Highlands Union High School","Shasta Union","Volcano Ridge",170),
    ("SCH147","Humboldt Delta Union High School","Humboldt Union","Mendota",150),
    ("SCH148","Boise Frontier Union High School","Frontier Union","Newbridge",190),
    ("SCH149","Cascadia Valley Union High School","Valley Union","Ashford",210),
    ("SCH150","Great Basin Union High School","Basin Union","Desert Springs",130),
    ("SCH151","East County High School","East County","Modoc Flats",180),
    ("SCH152","West County High School","West County","Douglasville",190),
    ("SCH153","North County High School","North County","Glenn",170),
    ("SCH154","South County High School","South County","Jackson Point",160),
    ("SCH155","Central County High School","Central County","Tehama Bridge",150),
]
for sid,nm,sn,city,enr in union_schools: add(sid,nm,sn,city,enr)

# More rural schools to reach ~255
more_rural = [
    ("SCH156","Mountain View High School","Mountain View","Siskiyou Pass",140),
    ("SCH157","Valley Center High School","Valley Center","Butte Valley",130),
    ("SCH158","River Valley High School","River Valley","Payette Crossing",170),
    ("SCH159","Lake County Union High School","Lake Union","Lakeview Terrace",160),
    ("SCH160","Coastal Union High School","Coastal Union","Curry Landing",150),
    ("SCH161","Border High School","Border HS","Del Norte Head",120),
    ("SCH162","Washoe County High School","Washoe County","Washoe Junction",140),
    ("SCH163","Humboldt County High School","Humboldt County","Humboldt Bay",130),
    ("SCH164","Plumas County High School","Plumas County","Plumas Grove",120),
    ("SCH165","High Desert High School","High Desert","Alfalfa Springs",110),
    ("SCH166","Orchard County High School","Orchard County","Orchardale",140),
    ("SCH167","Vineyard County High School","Vineyard County","Vineyard Mesa",130),
    ("SCH168","Dairy County High School","Dairy County","Dairy Hollow",120),
    ("SCH169","Grain County High School","Grain County","Grainfield",130),
    ("SCH170","Corn County High School","Corn County","Cornerville",110),
    ("SCH171","Sheep County High School","Sheep County","Sheep Camp",100),
    ("SCH172","Ranch County High School","Ranch County","Ranchero",120),
    ("SCH173","Summit County High School","Summit County","Summit Lodge",100),
    ("SCH174","Crystal County High School","Crystal County","Crystal Lake",90),
    ("SCH175","Pine County High School","Pine County","Pine Haven",80),
    ("SCH176","Eagle County High School","Eagle County","Eagle Nest",70),
    ("SCH177","Deer County High School","Deer County","Deer Park",60),
    ("SCH178","Seabright County High School","Seabright County","Seabright",80),
    ("SCH179","Rock County High School","Rock County","Rockport",70),
    ("SCH180","Moonstone County High School","Moonstone County","Moonstone Beach",60),
    ("SCH181","Cape County High School","Cape County","Capetown",50),
    ("SCH182","Sand County High School","Sand County","Sandbar",40),
    ("SCH183","Light County High School","Light County","Lighthouse Point",35),
    ("SCH184","Cross County High School","Cross County","Crossroads",30),
    ("SCH185","Whisper County High School","Whisper County","Whispering Pines",28),
    ("SCH186","Dry County High School","Dry County","Dry Creek",26),
    ("SCH187","Ghost County High School","Ghost County","Ghost Rock",24),
    ("SCH188","Prairie County High School","Prairie County","Prairie Home",22),
    ("SCH189","Mill County High School","Mill County","Milltown",20),
    ("SCH190","View County High School","View County","Basin View",18),
    ("SCH191","Iron County High School","Iron County","Iron Springs",16),
    ("SCH192","Cedar County High School","Cedar County","Cedar Flat",14),
    ("SCH193","Sunset County High School","Sunset County","Sunset Mesa",12),
    ("SCH194","Creek County High School","Creek County","Willow Creek",11),
    ("SCH195","Black Rock County High School","Black Rock County","Black Rock",10),
    ("SCH196","Star County High School","Star County","Morning Star",9),
    ("SCH197","Fox County High School","Fox County","Fox Gulch",8),
    ("SCH198","Antelope County High School","Antelope County","Antelope Run",7),
    ("SCH199","Bridge County High School","Bridge County","Stone Bridge",6),
    ("SCH200","Lost County High School","Lost County","Lost Valley",5),
]
for sid,nm,sn,city,enr in more_rural: add(sid,nm,sn,city,enr)

# Additional schools to reach 255
for i in range(201, 256):
    idx = (i - 201) % len(SETTLEMENTS)
    city = SETTLEMENTS[idx]["name"]
    enr = random.randint(5, 50)
    add(f"SCH{i}", f"Jefferson Rural High School {i-200}", f"JRHS {i-200}", city, enr)

# CONFERENCES (32 total)
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

# Assign schools to conferences based on region
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

# Output stats
print(f"Total population: {sum(s['population'] for s in SETTLEMENTS):,}")
print(f"Settlements: {len(SETTLEMENTS)}")
print(f"Schools: {len(SCHOOLS)}")
class_counts = {}
for s in SCHOOLS:
    class_counts[s["classification"]] = class_counts.get(s["classification"], 0) + 1
print(f"Classifications: {class_counts}")
print(f"Conferences: {len(CONFERENCES)}")

# Save JSON files
with open("/workspace/jefferson_data/regions.json", "w") as f: json.dump(REGIONS, f, indent=2)
with open("/workspace/jefferson_data/settlements.json", "w") as f: json.dump(SETTLEMENTS, f, indent=2)
with open("/workspace/jefferson_data/schools.json", "w") as f: json.dump(SCHOOLS, f, indent=2)
with open("/workspace/jefferson_data/conferences.json", "w") as f: json.dump(CONFERENCES, f, indent=2)

# Generate human-readable reference
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

### Primary Metro: Ashford Metropolitan Area
- Ashford (587k) - State capital
- Timberlake (168k) - University town
- Oakmere (58k) - Suburban manufacturing
- Cascade Heights (52k) - Commuter suburb
- Willowbrook (39k) - Food processing
- Douglasville (24.5k) - County seat
- Glenn (15k) - Farm service
- Tehama Bridge (13k) - Historic bridge town
- Butte Valley (11k) - Rice farming

### Port Valdez Metro
- Port Valdez (234k) - Deep-water port
- Redhaven (152k) - Fishing fleet
- Fort Braggton (47k) - Historic fort
- Humboldt Bay (16k) - Small port
- Seabright (5.9k) - Artist colony

### Greater Boise-Jefferson Metro
- Newbridge (198k) - Boise bedroom/employment
- Canyon Creek (82k) - Suburban residential
- Payette Crossing (41k) - Logistics hub

## Secondary Regional Cities
- Volcano Ridge (112k) - Mountain recreation
- Silverton (94k) - Agricultural processing
- Klamath Junction (76k) - Rail hub
- Mendota (72k) - University town
- Desert Springs (68k) - Geothermal energy

## School/Classification Distribution
Target: ~255 schools across 6A-1A classifications
- 6A: Large metro schools (1800+ enrollment)
- 5A: Major city schools (1400-1799)
- 4A: Regional city schools (1000-1399)
- 3A: Small city/town schools (700-999)
- 2A: Town/rural schools (400-699)
- 1A: Small rural schools (<400)

## Conference Areas (32)
Conferences are geographically-based regular-season groupings, mixing classifications:
- Cascadia Metro/Central Valley leagues serve Ashford metro
- Redwood Coast/Pacific Maritime serve coastal areas
- Shasta Mountain/Volcanic Peaks serve highlands
- Silver Basin/Ranch Country serve eastern desert
- Boise Frontier/Snake River serve Boise-edge corridor
- Harney/Frontier Rural serve vast high desert
- Trinity/Mining Heritage serve mountain mining areas
- Owyhee/Canyon Lands serve canyon ranching country

## Transportation/Settlement Corridors
1. Central Valley Corridor: Ashford-Timberlake-Oakmere axis
2. Coastal Corridor: Port Valdez-Redhaven-Fort Braggton
3. Boise Frontier Corridor: Newbridge-Canyon Creek-Payette Crossing
4. Mountain Corridor: Volcano Ridge-Summit Lodge-Lassen Peak
5. Desert Corridor: Silverton-Desert Springs-Malheur Center
"""

with open("/workspace/jefferson_data/REFERENCE.md", "w") as f: f.write(ref)
print("\nFiles generated successfully!")
