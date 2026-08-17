"""
Jefferson (JHSAA): a full fictional 2026-27 season as records.

    python3 -m generators.jefferson.gen

Pipeline per the owner's spec: regions -> towns -> schools -> classifications ->
conferences -> offered sports -> teams -> schedules -> completed/upcoming
contests -> postseason. Deterministic from SEED; two runs are byte-identical.

Demo "today" is mid-January: fall complete with championships, winter
mid-season (the dense rail), spring scheduled.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import random
import re
import shutil
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app import records_io  # noqa: E402
from app.shapes import (  # noqa: E402
    LOWER_IS_BETTER, Competitor, Dual, Entry, Event, Game, Line, MarkType, Meet,
    Period, TeamScore, parse_mark,
)
from app.sports import (  # noqa: E402
    BY_KEY, CATALOG, CLASSES, Sport, meet_family, meet_scoring,
)
from generators.jefferson import names as N  # noqa: E402

SEED = 5
SEASON = "2026-27"
#: The demo clock. Everything on or before this date is PLAYED; everything
#: after is scheduled. It is a single constant on purpose — the season is
#: generated against it, so moving it and re-running is how the demo advances.
#: Note that scoring happens inline with scheduling, so a different date is a
#: different season, not the same season further along.
TODAY = dt.date(2027, 5, 13)
RECORDS = ROOT / "records"

# The founding 256 keep their classes; 7A exists only via the expansion roster
CLASS_TARGETS = {"9A": 0, "8A": 0, "7A": 0, "6A": 38, "5A": 42, "4A": 44, "3A": 38, "2A": 36, "1A": 58}
#: ⚠️ The FOUNDING draw only. Classification is decided afterwards by
#: app.sports.classify() on the enrollment this produces — these bands stay
#: as they are because changing them re-deals the founding RNG stream.
ENROLL = {"9A": (2600, 4300), "8A": (2600, 4300), "7A": (2600, 4300),
          "6A": (1800, 3200), "5A": (1200, 1799), "4A": (700, 1199),
          "3A": (400, 699), "2A": (220, 399), "1A": (60, 219)}
OFFER_RANGE = {"9A": (24, 32), "8A": (24, 32), "7A": (24, 32), "6A": (20, 28), "5A": (17, 24), "4A": (14, 20),
               "3A": (11, 15), "2A": (8, 12), "1A": (6, 10)}
POOL = {"9A": 84, "8A": 84, "7A": 84, "6A": 72, "5A": 60, "4A": 48, "3A": 38, "2A": 30, "1A": 22}

#: State championship weekend for the MEET sports, by season. These mirror the
#: bracket sports' finals in ``generators.jefferson.postseason``, so a title
#: decided by a meet and one decided by a final are crowned the same weekend.
#:
#: Only fall used to get a championship date at all, which is why every winter
#: meet title — swimming, skiing, bowling, gymnastics, spirit, winter track,
#: debate — read as "upcoming" on a page dated the following MAY. Half the
#: postseason was permanently pending because half of it was never scheduled.
MEET_FINALS = {"fall": dt.date(2026, 11, 14), "winter": dt.date(2027, 2, 27),
               "spring": dt.date(2027, 5, 22)}
#: …and the late-spring exception, which keeps an unplayed championship in the
#: state at the demo clock so "the field is set, nothing is contested" is a
#: page the site actually has to render.
LATE_SPRING_MEETS = {"boys-track", "girls-track"}
LATE_SPRING_FINAL = dt.date(2027, 6, 12)


def champ_date(sport) -> dt.date:
    if sport.key in LATE_SPRING_MEETS:
        return LATE_SPRING_FINAL
    return MEET_FINALS[sport.season]

AREAS = [
    ("Ashbury Metro", "metro"), ("Harborline", "coast"), ("South Coast", "coast"),
    ("Halbrook Basin", "metro"), ("Cascade Divide", "mountain"),
    ("Juniper Highlands", "desert"), ("Sage Plains", "desert"),
    ("Timber Valley", "valley"), ("Gold Valley", "valley"), ("North Range", "remote"),
]
OUT_OF_STATE = ["Boise Vista (ID)", "Silver Sage (NV)", "Bidwell Grove (CA)",
                "Owyhee Bench (ID)", "Pyramid Peak (NV)"]


def slugify(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "x"


def _competition_ranks(values: list[float]) -> list[int]:
    """Standard competition ranking over an already-sorted list: 1, 2, 2, 4.

    Golf and bowling are scored in whole strokes and pinfall, so ties are not
    an edge case — a 3A field of eighty had three golfers on 79 and printed
    them as first, second and third. Equal marks share a place and the next
    one skips, which is how every results sheet in the sport prints it.
    """
    out, last, place = [], None, 0
    for i, v in enumerate(values, 1):
        if v != last:
            place, last = i, v
        out.append(place)
    return out


def _flip_set(score: str) -> str:
    """Turn a scoreline round: ``6-3, 7-6 (5)`` -> ``3-6, 6-7 (5)``.

    A dual line is generated from the winner's point of view and then flipped
    for the loser, which is the only way the printed score and the recorded
    winner can be guaranteed to agree.
    """
    out = []
    for part in score.split(","):
        m = re.match(r"\s*(\d+)-(\d+)(.*)$", part)
        out.append(f"{m.group(2)}-{m.group(1)}{m.group(3)}" if m else part.strip())
    return ", ".join(out)


class Gen:
    def __init__(self):
        self.rng = random.Random(SEED)
        self.used_places: set[str] = set(N.BLOCKLIST)
        self.used_schools: set[str] = set()
        self.contests: list = []
        self.expansion_city_data: dict = {}
        self.rosters: dict = {}
        self.pools: dict = {}

    # ---------------------------------------------------------- geography
    def town_name(self) -> str:
        """One draw from the mixed map: fused plat compounds, settler surnames,
        the old two-word nature names (now a minority), railroad stops, and the
        occasional unexplained one-worder. See names.py for why the mix."""
        rng = self.rng
        while True:
            roll = rng.random()
            if roll < 0.32:
                n = rng.choice(N.FUSE_STEMS) + rng.choice(N.FUSE_SUFFIXES)
            elif roll < 0.52:
                n = f"{rng.choice(N.STEMS)} {rng.choice(N.ENDINGS)}"
            elif roll < 0.72:
                base = rng.choice(N.TOWN_SURNAMES)
                n = base if rng.random() < 0.6 else \
                    base + rng.choice(["ville", " City", "s Landing"])
            elif roll < 0.85:
                n = f"{rng.choice(N.TOWN_SURNAMES + N.STEMS)} {rng.choice(N.RAIL_TAILS)}"
            else:
                n = rng.choice(N.ODDITIES)
            if n.lower() not in self.used_places:
                self.used_places.add(n.lower())
                return n

    def build_schools(self) -> list[dict]:
        rng = self.rng

        # Name pools are popped, not sampled, so a name appears once statewide.
        # Naming history per the owner's spec: metro cores carry people and
        # compass points (the schools that predate expansion), later rings
        # carry neighborhoods and landscape, small towns carry their own name,
        # rural consolidations carry county/union names.
        person = list(N.CIVIC_FIGURES) + list(N.CIVIC_FULL)
        rng.shuffle(person)
        national = list(N.NATIONAL_FIGURES)
        rng.shuffle(national)
        person = person[:14] + national[:4]     # national figures used sparingly
        rng.shuffle(person)
        hoods = list(N.NEIGHBORHOODS); rng.shuffle(hoods)
        geo = list(N.GEO_SCHOOLS); rng.shuffle(geo)
        magnets = {"Ashbury": ["Jefferson School of Science and Technology",
                               "Academy of Arts and Communication"],
                   "Port Meridian": ["Port Meridian North",
                                     "Port Meridian Maritime"],
                   "Halbrook": ["Halbrook East"]}

        def draw(pool, fallback):
            return pool.pop() if pool else fallback()

        # Anchor cities are reserved before any random draw — town_name()
        # produced a suburb "Averill" once, then the secondary city Averill was
        # added on top of it: two towns, one name, in different leagues.
        for key, val in N.ANCHORS.items():
            if key == "secondary":
                for city, _pop in val:
                    self.used_places.add(city.lower())
            else:
                self.used_places.add(val[0].lower())
        for city, _pop, _area, _spec in N.NAMED_CITIES:
            self.used_places.add(city.lower())
        for city in N.SPANISH_TOWNS:
            self.used_places.add(city.lower())

        slots: list[dict] = []  # {city, area, weight, private, name}

        def metro_plan(city, k):
            """k public-school names for a metro. Ashbury pins the rivalry
            pair the newsroom already covers."""
            names = ["Ashbury Central", "Ashbury Heights"] if city == "Ashbury" else [city]
            dirs = [d for d in N.DIRECTIONS if d not in ("Central", "Heights")]
            rng.shuffle(dirs)
            mag = list(magnets.get(city, []))
            while len(names) < k:
                roll = rng.random()
                if mag and len(names) >= k - len(mag):
                    names.append(mag.pop(0))       # specialty schools last
                elif roll < 0.34:
                    names.append(draw(hoods, lambda: f"{city} {dirs.pop()}"))
                elif roll < 0.62:
                    names.append(draw(person, lambda: f"{city} {dirs.pop()}"))
                elif roll < 0.80 and dirs:
                    names.append(f"{city} {dirs.pop()}")
                else:
                    names.append(draw(geo, lambda: f"{city} {dirs.pop()}"))
            return names

        def add_city(city, area, publics, privates, weight, kind="town"):
            self.used_places.add(city.lower())
            if kind == "metro":
                names = metro_plan(city, publics)
            else:
                dirs = [d for d in N.DIRECTIONS]
                rng.shuffle(dirs)
                names = []
                for i in range(publics):
                    if i == 0:
                        names.append(city)
                    elif kind == "suburb" and rng.random() < 0.5:
                        # newer suburban schools name for the neighborhood
                        names.append(draw(hoods, lambda: f"{city} {dirs[i % len(dirs)]}"))
                    elif kind == "secondary" and i == 1 and rng.random() < 0.5:
                        names.append(draw(person, lambda: f"{city} {dirs[i % len(dirs)]}"))
                    else:
                        names.append(f"{city} {dirs[i % len(dirs)]}")
            for nm in names:
                slots.append(dict(city=city, area=area, weight=weight + rng.random(),
                                  private=False, name=nm))
            rel = list(N.SAINTS + N.PROTESTANT)
            rng.shuffle(rel)
            if city == "Ashbury":
                # the newsroom's fencing story unseats this school by name
                rel.remove("St. Sebastian Prep")
                rel.insert(0, "St. Sebastian Prep")
            preps = list(N.PREPS)
            rng.shuffle(preps)
            for i in range(privates):
                # roughly one prep-tradition school for every two religious ones
                if preps and i % 3 == 2:
                    nm = preps.pop()
                else:
                    base = rel[i % len(rel)]
                    suffix = "" if ("Prep" in base or "Academy" in base) else \
                        rng.choice(["", " Academy", " Prep", ""])
                    nm = f"{base}{suffix}"
                slots.append(dict(city=city, area=area, weight=weight - 1 + rng.random() * 2,
                                  private=True, name=nm))

        # metros and anchors
        add_city("Ashbury", "Ashbury Metro", 12, 5, 10, kind="metro")
        for _ in range(9):   # Ashbury suburbs
            t = self.town_name()
            add_city(t, "Ashbury Metro", rng.randint(1, 3), 0, 7, kind="suburb")
        add_city("Port Meridian", "Harborline", 6, 2, 8, kind="metro")
        add_city("Halbrook", "Halbrook Basin", 5, 2, 8, kind="metro")
        for _ in range(3):
            add_city(self.town_name(), "Halbrook Basin", rng.randint(1, 2), 0, 6, kind="suburb")
        for city, _pop in N.ANCHORS["secondary"]:
            area = rng.choice(["Timber Valley", "Gold Valley", "Juniper Highlands",
                               "Cascade Divide", "South Coast"])
            add_city(city, area, rng.randint(2, 3), rng.random() < 0.4, 5, kind="secondary")

        # Owner-specified cities: population sets the slot weight (and so the
        # classification band); a given school list is used verbatim, otherwise
        # the count follows population and the first school takes the city name.
        for city, pop, area, spec in N.NAMED_CITIES:
            weight = pop / 15_000            # 84k ~ 5.6, 17k ~ 1.2
            if spec is None:
                k = max(1, round(pop / 30_000))
                dirs = [d for d in N.DIRECTIONS]
                rng.shuffle(dirs)
                spec = [city] + [f"{city} {dirs[i]}" for i in range(k - 1)]
            for nm in spec:
                slots.append(dict(city=city, area=area,
                                  weight=weight + rng.random(), private=False, name=nm))

        # the Spanish-derived southern coast around Santa Laura
        for city in N.SPANISH_TOWNS:
            slots.append(dict(city=city, area="South Coast",
                              weight=rng.random() * 3, private=False, name=city))

        # Named private schools + the Christian schools dotted statewide.
        # Cities are already on the map, so their areas come from the slots
        # built above; tier sets the weight band (metro privates run bigger).
        city_area = {s["city"]: s["area"] for s in slots}
        tier_weight = {"metro": lambda: 5.5 + rng.random() * 3,
                       "secondary": lambda: 3.0 + rng.random() * 2,
                       "town": lambda: 0.8 + rng.random() * 2}
        for nm, city, tier in list(N.PRIVATE_NAMED) + list(N.CHRISTIAN_SCHOOLS):
            slots.append(dict(city=city, area=city_area[city],
                              weight=tier_weight[tier](), private=True, name=nm))

        # the rural map: single-school towns until quota. Mostly the town's own
        # name; some consolidated districts (county/union/regional), a few
        # named for the landscape.
        target = sum(CLASS_TARGETS.values())
        counties = list(N.COUNTIES); rng.shuffle(counties)
        area_pool = ["Timber Valley"] * 4 + ["Gold Valley"] * 3 + ["Sage Plains"] * 3 + \
                    ["Juniper Highlands"] * 3 + ["Cascade Divide"] * 2 + \
                    ["South Coast"] * 2 + ["Harborline"] * 2 + ["North Range"] * 4
        while len(slots) < target:
            t = self.town_name()
            area = rng.choice(area_pool)
            roll = rng.random()
            if roll < 0.74:
                nm = t
            elif roll < 0.86 and counties:
                nm = rng.choice(N.REGIONAL_FORMS).format(counties.pop())
            elif roll < 0.94:
                nm = draw(geo, lambda: f"{t} Union")
            else:
                nm = f"{t} Union"
            slots.append(dict(city=t, area=area, weight=rng.random() * 3,
                              private=rng.random() < 0.05, name=nm))
        slots = slots[:target]

        # unique names
        for s in slots:
            base, n = s["name"], 2
            while s["name"].lower() in self.used_schools:
                s["name"] = f"{base} {['Union','Heights','Valley'][n % 3]}"
                n += 1
            self.used_schools.add(s["name"].lower())

        # classification by weight order, quota slices
        slots.sort(key=lambda s: -s["weight"])
        schools, i = [], 0
        for cls in CLASSES:
            for _ in range(CLASS_TARGETS[cls]):
                s = slots[i]; i += 1
                lo, hi = ENROLL[cls]
                schools.append(dict(
                    name=s["name"], city=s["city"], area=s["area"], private=s["private"],
                    classification=cls, enrollment=rng.randint(lo, hi),
                    # Overwritten by generators.jefferson.mascots at the end of
                    # the run. The draw STAYS so the RNG stream is unchanged —
                    # removing it would shift every subsequent result in the
                    # sport and quietly regenerate the season.
                    mascot=rng.choice(N.MASCOTS), quality=rng.gauss(0, 1),
                ))
        return schools

    def build_conferences(self, schools) -> list[dict]:
        """Leagues are geographic — who you can reach on a Tuesday night.

        These used to be built as `members[i::n_conf]` over an area sorted by
        enrollment, so each league took every nth school by size and scattered
        itself across the whole area, then took a name off the random stem list
        with no relation to where it was. Schools now cluster by town before
        they're split, and a league is named for the town it centres on, so
        reading the members tells you where it is.
        """
        rng = self.rng
        confs = []
        flavors = ["League", "Conference", "League", "Athletic Conference"]
        for area, _kind in AREAS:
            members = [s for s in schools if s["area"] == area]
            if not members:
                continue
            n_conf = max(1, round(len(members) / 8))

            by_city: dict[str, list] = {}
            for s in members:
                by_city.setdefault(s["city"], []).append(s)
            ordered = []
            for city in sorted(by_city, key=lambda c: (-len(by_city[c]), c)):
                ordered.extend(sorted(by_city[city], key=lambda s: -s["enrollment"]))

            size = -(-len(ordered) // n_conf)          # ceil, so no empty chunk
            for i in range(n_conf):
                chunk = ordered[i * size:(i + 1) * size]
                if not chunk:
                    continue
                nm = self._conf_name(area)
                slug = slugify(nm)
                for s in chunk:
                    s["conference"] = nm
                confs.append(dict(name=nm, slug=slug, area=area,
                                  members=[s["name"] for s in chunk]))
        return confs

    def _conf_name(self, area) -> str:
        """Next unused name from the area's curated list (names.CONF_NAMES —
        rivers, corridors, historic identities, the odd numeric league), then
        the statewide realignment-leftovers pool. Curated in preference order,
        so an area's flagship league gets its strongest name. A numeric name
        ("Cascade Eight") is allowed to disagree with current membership —
        that's how those names age in real states."""
        for nm in N.CONF_NAMES.get(area, []) + N.CONF_EXTRA:
            if nm.lower() not in self.used_places:
                self.used_places.add(nm.lower())
                return nm
        raise RuntimeError(f"conference name pools exhausted for {area}")

    def build_offerings(self, schools):
        rng = self.rng
        core = ["girls-volleyball", "boys-basketball", "girls-basketball",
                "boys-cross-country", "girls-cross-country", "boys-track", "girls-track"]
        for s in schools:
            lo, hi = OFFER_RANGE[s["classification"]]
            target = rng.randint(lo, hi)
            offered = list(core)
            if not s["private"] or rng.random() < 0.5:
                offered.append("football")
            rest = [sp for sp in CATALOG if sp.key not in offered]
            rng.shuffle(rest)
            for sp in rest:
                if len(offered) >= target:
                    break
                p = {"broad": 0.75, "metro": 0.12, "mountain": 0.08, "aquatic": 0.10}[sp.reach]
                if sp.reach == "metro" and (s["area"].endswith("Metro") or s["area"] == "Harborline" or s["private"]):
                    p = 0.55
                if sp.reach == "mountain" and s["area"] in ("Cascade Divide", "North Range"):
                    p = 0.65
                if sp.reach == "aquatic" and (s["area"].endswith("Metro") or "Coast" in s["area"] or s["area"] == "Harborline"):
                    p = 0.40
                if s["classification"] in ("1A", "2A") and sp.reach != "broad":
                    p *= 0.4
                if rng.random() < p:
                    offered.append(sp.key)
            s["sports"] = sorted(offered[:hi])

    # ------------------------------------------------------------ people
    def pool(self, school):
        """A school's student body: (name, grade, gender).

        Gender is carried on the person, not decided at the point of use, so
        one student is one student — the same Marisol Okafor can appear in
        girls cross country in October and girls track in April, and can never
        turn up in a boys wrestling dual.
        """
        if school not in self.pools:
            rng = self.rng
            n = POOL[self.by_name[school]["classification"]]
            people = []
            for _ in range(n):
                gender = "Boys" if rng.random() < 0.5 else "Girls"
                if rng.random() < 0.10:
                    first = rng.choice(N.UNISEX_FIRST)
                else:
                    first = rng.choice(N.BOYS_FIRST if gender == "Boys"
                                       else N.GIRLS_FIRST)
                people.append((f"{first} {rng.choice(N.LAST_NAMES)}",
                               str(rng.randint(9, 12)), gender))
            self.pools[school] = people
        return self.pools[school]

    def roster(self, school, sport_key, size):
        """The eligible students for one team, stable for the season.

        A Boys sport draws from the boys in the pool and a Girls sport from
        the girls; Coed activities (bowling, debate, winter track, ultimate)
        draw from everyone, which is what "coed" means and is visible on the
        page as a mixed field.
        """
        key = (school, sport_key)
        if key not in self.rosters:
            want = BY_KEY[sport_key].gender if sport_key in BY_KEY else "Coed"
            pool = [p for p in self.pool(school) if want == "Coed" or p[2] == want]
            self.rosters[key] = self.rng.sample(pool, min(size, len(pool)))
        return self.rosters[key]

    def squad(self, school, sport_key, want, size):
        """The boys, or the girls, of a co-ed team.

        `roster` filters on the SPORT's gender, which is all a single-gender
        sport needs. Co-ed badminton has to field four of each and put them on
        specific lines, so it asks for them separately.
        """
        key = (school, sport_key, want)
        if key not in self.rosters:
            pool = [p for p in self.pool(school) if p[2] == want]
            self.rosters[key] = self.rng.sample(pool, min(size, len(pool)))
        return self.rosters[key]

    # --------------------------------------------------------- schedules
    def weeks(self, start: dt.date, n: int, step=7):
        return [start + dt.timedelta(days=step * i) for i in range(n)]

    def strength(self, school, sport_key):
        key = (school, sport_key)
        if key not in self._str:
            self._str[key] = self.by_name[school]["quality"] * 0.6 + self.rng.gauss(0, 0.8)
        return self._str[key]

    def game_score(self, sport_key, ds):
        rng = self.rng
        if sport_key == "football":
            h = max(0, int(24 + 5 * ds + rng.gauss(0, 9)))
            a = max(0, int(24 - 5 * ds + rng.gauss(0, 9)))
            if h == a: h += 3
            return h, a, None
        if "soccer" in sport_key:
            h = max(0, int(rng.gauss(1.6 + ds * 0.8, 1.1)))
            a = max(0, int(rng.gauss(1.6 - ds * 0.8, 1.1)))
            return h, a, None  # ties stand
        if "volleyball" in sport_key:
            hw = 0; aw = 0; periods = []
            while hw < 3 and aw < 3:
                if rng.random() < 0.5 + ds * 0.18:
                    hw += 1; periods.append(Period(f"Set {hw+aw}", 25, rng.randint(12, 23)))
                else:
                    aw += 1; periods.append(Period(f"Set {hw+aw}", rng.randint(12, 23), 25))
            return hw, aw, periods
        if "basketball" in sport_key:
            h = int(54 + 7 * ds + rng.gauss(0, 9)); a = int(54 - 7 * ds + rng.gauss(0, 9))
            if h == a: h += 2
            return max(20, h), max(20, a), None
        if "hockey" in sport_key:
            h = max(0, int(rng.gauss(2.8 + ds, 1.4))); a = max(0, int(rng.gauss(2.8 - ds, 1.4)))
            if h == a and rng.random() < 0.6:
                (h, a) = (h + 1, a) if rng.random() < 0.5 + ds * 0.2 else (h, a + 1)
            return h, a, None
        if "rugby" in sport_key:
            # Sevens: tries are five, conversions two, the odd penalty three.
            def side(edge):
                tries = max(0, int(rng.gauss(4 + edge, 1.8)))
                conv = sum(1 for _ in range(tries) if rng.random() < 0.62)
                pen = 1 if rng.random() < 0.12 else 0
                return tries * 5 + conv * 2 + pen * 3
            h, a = side(ds), side(-ds)
            if h == a:
                h += 5
            return h, a, None
        if "cricket" in sport_key:
            # T10: ten overs a side. The SCORE is runs; wickets and the result
            # sentence are attached by the box-score pass, which is the only
            # place that knows how the innings actually went.
            h = max(28, int(rng.gauss(96 + ds * 9, 22)))
            a = max(28, int(rng.gauss(96 - ds * 9, 22)))
            if h == a and rng.random() < 0.85:
                h += rng.randint(1, 9)
            return h, a, None
        if "water-polo" in sport_key:
            return max(1, int(9 + 3 * ds + rng.gauss(0, 3))), max(1, int(9 - 3 * ds + rng.gauss(0, 3))), None
        # flag football, lacrosse, baseball, softball, boys volleyball
        h = max(0, int(15 + 5 * ds + rng.gauss(0, 7))); a = max(0, int(15 - 5 * ds + rng.gauss(0, 7)))
        if h == a: h += 1
        return h, a, None

    def make_game(self, sport: Sport, home, away, date, played, round_name=None):
        rng = self.rng
        name = f"{away} at {home}" if not round_name else f"{away} at {home} — {round_name}"
        g = Game(name=name, date=date.isoformat(), sport=sport.key, season=SEASON,
                 home=home, away=away, venue=None)
        if played:
            r = rng.random()
            if r < 0.012:
                g.status = "cancelled"
            elif r < 0.022:
                g.status = "postponed"
            else:
                ds = self.strength(home, sport.key) - (
                    self.strength(away, sport.key) if away in self.by_name else rng.gauss(0.3, 0.8)) + 0.25
                h, a, periods = self.game_score(sport.key, ds)
                g.home_score, g.away_score = h, a
                if periods:
                    g.periods = periods
                g.status = "final"
        else:
            g.status = "scheduled"
        self.contests.append(g)
        return g

    #: The lines a dual actually runs, by sport. Everything that was not
    #: tennis or wrestling used to fall through to the fencing card, so girls
    #: badminton was contested at foil, épée and sabre — a whole sport played
    #: with the wrong equipment, in every one of its duals. A dual card is
    #: sport-specific data, not an else branch.
    DUAL_CARDS = {
        "tennis": [("singles", 6), ("doubles", 3)],
        # NFHS runs fourteen weight classes. Eight was a card nobody sponsors.
        "wrestling": [(w, 1) for w in ("106", "113", "120", "126", "132", "138",
                                       "144", "150", "157", "165", "175", "190",
                                       "215", "285")],
        "fencing": [("foil", 3), ("épée", 3), ("sabre", 3)],
        "badminton": [("singles", 3), ("doubles", 2)],
        # Five singles, #1 through #5, in ladder order. An odd card cannot tie.
        "squash": [("singles", 5)],
        # FIVE boards, played in strength order — Board 1 is the team's best.
        # A match is therefore out of 5 and lands on a half as often as not:
        # 5-0, 3-2, 2.5-2.5 are all ordinary results.
        "chess": [("board", 5)],
    }

    def dual_card(self, sport: Sport):
        for fam, card in self.DUAL_CARDS.items():
            if fam in sport.key:
                return card
        return self.DUAL_CARDS["tennis"]

    #: Chess results, as a chess result is written. A DRAW is the ordinary
    #: outcome — roughly a third of decisive-strength games between matched
    #: players — which is why the line has to carry one at all.
    CHESS_DRAW = 0.30

    #: Co-ed badminton, five lines off four boys and four girls. Each entry is
    #: (kind, how many boys, how many girls) and every athlete plays exactly
    #: one line — which is the whole reason the squad is eight and not twelve.
    BADMINTON_LINES = [
        ("boys doubles", 2, 0),
        ("girls doubles", 0, 2),
        ("mixed doubles", 1, 1),
        ("mixed doubles", 1, 1),
        # The co-ed singles court is the one place an athlete plays twice:
        # lines 1-4 use all eight, and the singles is Boy 1 or Girl 1 by the
        # coach's designation. Dealing a fifth boy off a four-boy squad left
        # the court empty, which is what happens when a spec says "everyone
        # plays exactly one line" and then names a fifth line.
        ("singles", 0, 0),
    ]

    def badminton_pairs(self, school, sport_key):
        """Who plays which line: boys 1-2 together, girls 1-2 together, then
        3s and 4s crossed into the two mixed pairs, then a singles court."""
        boys = self.squad(school, sport_key, "Boys", 4)
        girls = self.squad(school, sport_key, "Girls", 4)
        bi = gi = 0
        out = []
        for kind, nb, ng in self.BADMINTON_LINES:
            if kind == "singles":
                # designated seed: the school's best boy or best girl
                pick = boys[:1] if zlib.crc32(school.encode()) % 2 else girls[:1]
                out.append(pick)
                continue
            out.append(boys[bi:bi + nb] + girls[gi:gi + ng])
            bi += nb
            gi += ng
        return out

    def line_score(self, sport: Sport, rng, home_wins: bool):
        """The printed score for one line, and what it is worth.

        Written from the WINNER's side and then flipped if the away side won.
        Generating "6-3, 7-6" and separately deciding the away player won
        published a scoreline that contradicted its own result on every tennis,
        fencing and badminton line in the state — the kind of wrong that is
        invisible in aggregate and obvious on the one page someone reads.
        """
        if "chess" in sport.key:
            # 1-0, 0-1 or 1/2-1/2, and the caller is told which by the winner
            # it gets back rather than by the score string alone.
            return ("1/2-1/2", 0.5) if home_wins is None else \
                   (("1-0", 1.0) if home_wins else ("0-1", 1.0))

        if "wrestling" in sport.key:
            # The bout score is conventionally printed winner-first, so it does
            # not flip; the decision type is what sets the team points.
            kind = rng.choices(["Fall", "Dec", "Maj", "Tech", "Forfeit"],
                               [26, 46, 16, 8, 4])[0]
            score = {
                "Fall": f"Fall {rng.randint(0, 5)}:{rng.randint(10, 59):02d}",
                "Dec": f"Dec {rng.randint(4, 12)}-{rng.randint(0, 3)}",
                "Maj": f"Maj {rng.randint(10, 18)}-{rng.randint(0, 5)}",
                "Tech": f"TF {rng.randint(16, 22)}-{rng.randint(0, 5)}",
                "Forfeit": "Forfeit",
            }[kind]
            return score, {"Fall": 6.0, "Dec": 3.0, "Maj": 4.0,
                           "Tech": 5.0, "Forfeit": 6.0}[kind]

        if "squash" in sport.key:
            # PAR to 11, best of five, and a game can go past 11 on deuce.
            def game():
                return rng.choice([f"11-{rng.randint(2, 9)}", "12-10", "13-11", "11-9"])
            games = [game(), game(), game()]
            if rng.random() < 0.34:            # dropped a game, or two
                games = [game(), _flip_set(game()), game(), game()]
                if rng.random() < 0.4:
                    games = [games[0], games[1], _flip_set(game()), game(), game()]
            score = ", ".join(games)
            return (score if home_wins else _flip_set(score)), 1.0

        if "tennis" in sport.key:
            def set_score():
                return rng.choices([f"6-{rng.randint(0, 4)}", "7-5", "7-6 (5)",
                                    f"7-6 ({rng.randint(2, 8)})"],
                                   [70, 12, 9, 9])[0]
            sets = [set_score(), set_score()]
            if rng.random() < 0.18:            # a third set, and it can be a tiebreak
                sets = [set_score(), _flip_set(set_score()),
                        rng.choice([set_score(), f"10-{rng.randint(4, 8)}"])]
            score = ", ".join(sets)
        elif "badminton" in sport.key:
            games = [f"21-{rng.randint(9, 19)}", f"21-{rng.randint(9, 19)}"]
            if rng.random() < 0.25:
                games = [games[0], _flip_set(games[1]),
                         f"21-{rng.randint(12, 19)}"]
            score = ", ".join(games)
        else:                                   # fencing: bouts to five touches
            score = f"5-{rng.randint(0, 4)}"
        return (score if home_wins else _flip_set(score)), 1.0

    def make_dual(self, sport: Sport, home, away, date, played, round_name=None):
        rng = self.rng
        name = f"{away} at {home}" if not round_name else f"{away} at {home} — {round_name}"
        d = Dual(name=name, date=date.isoformat(), sport=sport.key, season=SEASON,
                 home=home, away=away)
        if played and rng.random() < 0.985:
            # Co-ed badminton assigns SPECIFIC people to specific lines —
            # boys 1-2 to the boys' pair, 3 and 4 into the mixed pairs — so it
            # cannot use the sequential deal the other cards use.
            if "badminton" in sport.key:
                self._badminton_dual(d, sport, home, away, rng)
                self.contests.append(d)
                return d

            slots = self.dual_card(sport)
            hr = self.roster(home, sport.key, 16)
            ar = self.roster(away, sport.key, 16) if away in self.by_name else []
            if not hr:
                self.contests.append(d)
                return d
            hp = ap = 0.0
            hi = ai = 0
            for kind, count in slots:
                # Flights are numbered WITHIN their kind — Singles 1-6 then
                # Doubles 1-3, the way a match card prints them. A running
                # index made the third doubles court "Doubles 9".
                for flight in range(1, count + 1):
                    n_players = 2 if kind == "doubles" else 1
                    hp_players = [Competitor(hr[(hi + k) % len(hr)][0], home, hr[(hi + k) % len(hr)][1]) for k in range(n_players)]
                    hi += n_players
                    if ar:
                        ap_players = [Competitor(ar[(ai + k) % len(ar)][0], away, ar[(ai + k) % len(ar)][1]) for k in range(n_players)]
                        ai += n_players
                    else:
                        ap_players = []
                    home_wins = rng.random() < 0.5 + (self.strength(home, sport.key) -
                                (self.strength(away, sport.key) if away in self.by_name else 0)) * 0.15
                    if "chess" in sport.key and rng.random() < self.CHESS_DRAW:
                        home_wins = None            # the board is drawn
                    score, pt = self.line_score(sport, rng, home_wins)
                    if home_wins is None:
                        hp += pt / 2
                        ap += pt / 2
                        won = "draw"
                    elif home_wins:
                        hp += pt
                        won = "home"
                    else:
                        ap += pt
                        won = "away"
                    d.lines.append(Line(slot=flight, kind=kind, home=hp_players,
                                        away=ap_players, winner=won,
                                        score=score, team_point=pt))
            d.home_points, d.away_points = hp, ap
        self.contests.append(d)
        return d

    def _badminton_dual(self, d, sport, home, away, rng):
        """Five lines off eight players a side; first to three wins the dual."""
        hp_lines = self.badminton_pairs(home, sport.key)
        ap_lines = (self.badminton_pairs(away, sport.key)
                    if away in self.by_name else [[]] * 5)
        hp = ap = 0.0
        flight = {"boys doubles": 0, "girls doubles": 0,
                  "mixed doubles": 0, "singles": 0}
        for i, (kind, _nb, _ng) in enumerate(self.BADMINTON_LINES):
            flight[kind] += 1
            home_wins = rng.random() < 0.5 + (self.strength(home, sport.key) -
                        (self.strength(away, sport.key) if away in self.by_name else 0)) * 0.15
            score, pt = self.line_score(sport, rng, home_wins)
            if home_wins:
                hp += pt
            else:
                ap += pt
            d.lines.append(Line(
                slot=flight[kind], kind=kind,
                home=[Competitor(p[0], home, p[1]) for p in hp_lines[i]],
                away=[Competitor(p[0], away, p[1]) for p in ap_lines[i]],
                winner="home" if home_wins else "away",
                score=score, team_point=pt))
        d.home_points, d.away_points = hp, ap

    def round_robin(self, teams):
        """Circle method; returns rounds of (home, away)."""
        t = list(teams)
        if len(t) % 2:
            t.append(None)
        rounds = []
        for r in range(len(t) - 1):
            pairs = []
            for i in range(len(t) // 2):
                a, b = t[i], t[len(t) - 1 - i]
                if a is not None and b is not None:
                    pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
            rounds.append(pairs)
            t.insert(1, t.pop())
        return rounds

    def team_sport_season(self, sport: Sport, dates: list[dt.date], playoffs_start=None):
        rng = self.rng
        sponsors = [s["name"] for s in self.schools if sport.key in s["sports"]]
        if len(sponsors) < 4:
            return
        by_conf: dict[str, list] = {}
        for nm in sponsors:
            by_conf.setdefault(self.by_name[nm]["conference"], []).append(nm)
        results: dict[str, list] = {}
        for conf, members in sorted(by_conf.items()):
            if len(members) < 2:
                continue
            rounds = self.round_robin(members)[: len(dates) - 1]
            for ri, pairs in enumerate(rounds):
                date = dates[ri + 1]
                for home, away in pairs:
                    played = date <= TODAY
                    if sport.shape.value == "dual":
                        self.make_dual(sport, home, away, date, played)
                    else:
                        self.make_game(sport, home, away, date, played)
        # Non-conference crossovers. Without these every game is a league game,
        # so a team's overall record equals its conference record exactly and
        # the standings carry two identical columns. Schools play whoever is
        # geographically near but in another league — the way non-conference
        # scheduling actually works, since travel is the constraint.
        longest = max((len(self.round_robin(m)[: len(dates) - 1])
                       for m in by_conf.values() if len(m) >= 2), default=0)
        cross = [dates[0]] + dates[longest + 1:][:2]
        for date in cross:
            played = date <= TODAY
            for area in sorted({self.by_name[n]["area"] for n in sponsors}):
                local = sorted(n for n in sponsors if self.by_name[n]["area"] == area)
                rng.shuffle(local)
                # Bucket by league, then repeatedly draw from the two fullest.
                # Walking a shuffled list and skipping same-league neighbours
                # left most of the area unpaired, because an area's schools
                # cluster into the same few leagues in the first place.
                buckets: dict[str, list] = {}
                for n in local:
                    buckets.setdefault(self.by_name[n]["conference"], []).append(n)
                while True:
                    live = sorted((k for k in buckets if buckets[k]),
                                  key=lambda k: (-len(buckets[k]), k))
                    if len(live) < 2:
                        break
                    home, away = buckets[live[0]].pop(), buckets[live[1]].pop()
                    if sport.shape.value == "dual":
                        self.make_dual(sport, home, away, date, played)
                    else:
                        self.make_game(sport, home, away, date, played)

        # interstate openers
        if sport.key in ("football", "boys-basketball", "girls-basketball"):
            metros = [n for n in sponsors if self.by_name[n]["area"] in ("Ashbury Metro", "Halbrook Basin")]
            for nm in metros[:4]:
                self.make_game(sport, nm, rng.choice(OUT_OF_STATE), dates[0], dates[0] <= TODAY)
        # fall postseason brackets
        if playoffs_start and sport.shape.value in ("game", "dual"):
            self.brackets(sport, sponsors, playoffs_start)

    def standings_for(self, sport_key, members):
        w = {m: 0 for m in members}
        for c in self.contests:
            if getattr(c, "sport", None) != sport_key:
                continue
            if isinstance(c, Game) and c.status == "final" and c.winner in w:
                w[c.winner] += 1
            elif isinstance(c, Dual) and c.home_points is not None:
                winner = c.home if c.home_points >= c.away_points else c.away
                if winner in w:
                    w[winner] += 1
        return sorted(members, key=lambda m: (-w[m], m))

    def brackets(self, sport: Sport, sponsors, start: dt.date):
        by_group: dict[str, list] = {}
        for nm in sponsors:
            by_group.setdefault(sport.champ_group(self.by_name[nm]["classification"]), []).append(nm)
        for group, members in sorted(by_group.items()):
            if len(members) < 4:
                continue
            field = self.standings_for(sport.key, members)[: 8 if len(members) >= 10 else 4]
            rounds = [f"JHSAA {group} Quarterfinal", f"JHSAA {group} Semifinal",
                      f"JHSAA {group} Championship"]
            if len(field) == 4:
                rounds = rounds[1:]
            date = start
            while len(field) > 1:
                nxt = []
                rname = rounds[0] if rounds else "Playoff"
                for i in range(len(field) // 2):
                    home, away = field[i], field[len(field) - 1 - i]
                    g = self.make_game(sport, home, away, date, date <= TODAY, rname) \
                        if sport.shape.value == "game" else \
                        self.make_dual(sport, home, away, date, date <= TODAY, rname)
                    if isinstance(g, Game) and g.status == "final":
                        nxt.append(g.winner or home)
                    elif isinstance(g, Dual) and g.home_points is not None:
                        nxt.append(g.home if g.home_points >= g.away_points else g.away)
                    else:
                        nxt.append(home)
                field = nxt
                rounds = rounds[1:]
                date = date + dt.timedelta(days=7)

    # -------------------------------------------------------------- meets
    #
    # A meet's EVENT CARD, by sport family. Each event is
    #
    #     (name, entries per school, low, high, mark kind, relay?)
    #
    # ``entries per school`` of 0 means the SCHOOL is the entrant — a band
    # show, a cheer routine, a choir performance have no individual result.
    # A mark kind of ``None`` takes the sport's own; a card can mix them,
    # which is how one swim meet holds eleven races and a diving competition
    # judged in points, and one track meet holds races, throws and jumps.
    # ``combined`` is a DERIVED event: an all-around, a band total. Its band
    # is ignored and its value is the sum of the entrant's marks in the
    # events above it, so a gymnast's all-around always equals her four
    # apparatus scores added up.
    #
    # Bands are in the mark's own units: seconds, INCHES for a distance or a
    # height, and the printed number for strokes, pinfall, points, ratings.
    #
    # These cards used to be one event each for nine of the twelve families —
    # a bowling "meet" was a single line per school, a gymnastics meet had no
    # apparatus, a swim meet ran six events and no diving. MEET is the shape
    # this whole model exists to carry, so a one-event meet is the flagship
    # case failing quietly.
    MEET_EVENTS = {
        "cross-country": [
            ("5,000 Meter Run", 7, 930, 1380, None, False),
        ],
        "golf": [
            ("18 Holes", 5, 68, 108, None, False),
        ],
        "mountain-biking": [
            ("Varsity Race", 3, 3600, 5400, None, False),
            ("Junior Varsity Race", 3, 3800, 5700, None, False),
            ("Freshman Race", 3, 4000, 6000, None, False),
        ],
        "swimming": [
            ("200 Yard Medley Relay", 1, 105, 135, None, True),
            ("200 Yard Freestyle", 2, 105, 150, None, False),
            ("200 Yard IM", 2, 118, 165, None, False),
            ("50 Yard Freestyle", 2, 22, 32, None, False),
            ("1 Meter Diving", 1, 180, 460, "points", False),
            ("100 Yard Butterfly", 2, 55, 75, None, False),
            ("100 Yard Freestyle", 2, 48, 68, None, False),
            ("500 Yard Freestyle", 2, 290, 400, None, False),
            ("200 Yard Freestyle Relay", 1, 96, 118, None, True),
            ("100 Yard Backstroke", 2, 56, 80, None, False),
            ("100 Yard Breaststroke", 2, 62, 88, None, False),
            ("400 Yard Freestyle Relay", 1, 212, 262, None, True),
        ],
        "alpine-skiing": [
            ("Giant Slalom", 4, 58, 80, None, False),
            ("Slalom", 4, 48, 68, None, False),
        ],
        "nordic-skiing": [
            ("5K Classic", 4, 840, 1200, None, False),
            ("5K Freestyle", 4, 780, 1120, None, False),
        ],
        "bowling": [
            ("Game 1", 5, 120, 235, None, False),
            ("Game 2", 5, 120, 235, None, False),
            ("Game 3", 5, 120, 235, None, False),
        ],
        "gymnastics": [
            ("Vault", 4, 8.0, 9.8, None, False),
            ("Uneven Bars", 4, 7.3, 9.7, None, False),
            ("Balance Beam", 4, 7.4, 9.7, None, False),
            ("Floor Exercise", 4, 8.0, 9.85, None, False),
            ("All-Around", 4, 0, 0, "combined", False),
        ],
        "competitive-spirit": [
            ("Game Day Routine", 0, 62.0, 94.0, None, False),
            ("Traditional Routine", 0, 60.0, 96.0, None, False),
        ],
        "track": [
            ("100 Meter Dash", 2, 10.9, 12.6, None, False),
            ("200 Meter Dash", 2, 22.1, 26.4, None, False),
            ("400 Meter Dash", 2, 49.4, 59.8, None, False),
            ("800 Meter Run", 2, 116.0, 142.0, None, False),
            ("1600 Meter Run", 2, 258.0, 320.0, None, False),
            ("3200 Meter Run", 2, 560.0, 700.0, None, False),
            ("110 Meter Hurdles", 2, 14.6, 18.4, None, False),
            ("300 Meter Hurdles", 2, 39.2, 48.6, None, False),
            ("4x100 Meter Relay", 1, 43.1, 48.9, None, True),
            ("4x400 Meter Relay", 1, 205.0, 232.0, None, True),
            ("4x800 Meter Relay", 1, 490.0, 560.0, None, True),
            ("Shot Put", 2, 420.0, 660.0, "distance", False),
            ("Discus", 2, 1200.0, 2000.0, "distance", False),
            ("Javelin", 2, 1400.0, 2300.0, "distance", False),
            ("High Jump", 2, 60.0, 78.0, "height", False),
            ("Long Jump", 2, 232.0, 290.0, "distance", False),
            ("Triple Jump", 2, 460.0, 580.0, "distance", False),
            ("Pole Vault", 2, 108.0, 174.0, "height", False),
        ],
        "winter-track": [
            ("55 Meter Dash", 2, 6.5, 8.0, None, False),
            ("55 Meter Hurdles", 2, 7.9, 10.2, None, False),
            ("200 Meter Dash", 2, 23.2, 27.5, None, False),
            ("400 Meter Dash", 2, 51.5, 62.0, None, False),
            ("800 Meter Run", 2, 120.0, 148.0, None, False),
            ("1600 Meter Run", 2, 268.0, 330.0, None, False),
            ("3200 Meter Run", 2, 580.0, 720.0, None, False),
            ("4x200 Meter Relay", 1, 95.0, 112.0, None, True),
            ("4x400 Meter Relay", 1, 210.0, 240.0, None, True),
            ("4x800 Meter Relay", 1, 500.0, 580.0, None, True),
            ("Shot Put", 2, 400.0, 620.0, "distance", False),
            ("High Jump", 2, 58.0, 76.0, "height", False),
            ("Long Jump", 2, 225.0, 285.0, "distance", False),
            ("Triple Jump", 2, 450.0, 570.0, "distance", False),
            ("Pole Vault", 2, 105.0, 165.0, "height", False),
        ],
        # Activities: same MEET machinery, marks that match how each is judged.
        # A band show is scored by caption panels; a choir earns a division
        # RATING (I best); debate is pure placement. No invented box scores.
        "marching-band": [
            ("Music Performance", 0, 15.0, 24.0, None, False),
            ("Visual Performance", 0, 14.0, 23.5, None, False),
            ("General Effect", 0, 26.0, 38.0, None, False),
            ("Total Score", 0, 0, 0, "combined", False),
        ],
        "choir": [
            ("Concert Choir", 0, 1.0, 4.0, None, False),
            ("Chamber Ensemble", 0, 1.0, 4.0, None, False),
            ("Sight-Reading", 0, 1.0, 4.0, None, False),
        ],
        "debate": [
            ("Policy Debate", 2, 1.0, 30.0, None, False),
            ("Lincoln-Douglas", 2, 1.0, 30.0, None, False),
            ("Public Forum", 2, 1.0, 30.0, None, False),
            ("Congressional Debate", 2, 1.0, 30.0, None, False),
            ("Extemporaneous Speaking", 2, 1.0, 30.0, None, False),
        ],
    }

    #: The team-scoring rule lives with the CATALOG (`app.sports.MEET_SCORING`),
    #: not here: the renderer needs the same table to label the column, and a
    #: golf team's 326 under a header reading "Points" is the page contradicting
    #: itself. This module computes; that one names.

    #: Place points for a scored meet; a relay is worth double.
    PLACE_POINTS = (10, 8, 6, 5, 4, 3, 2, 1)

    #: Girls' marks are slower and shorter than boys'. One factor per mark kind
    #: beats a second copy of every band, which would drift out of step.
    GIRLS_FACTOR = {"time": 1.12, "distance": 0.78, "height": 0.84}

    def meet_family(self, key):
        fam = meet_family(key)
        return fam, self.MEET_EVENTS[fam]

    def fmt_time(self, secs: float, decimals=1) -> str:
        if secs < 60:
            return f"{secs:.2f}"
        m, s = divmod(secs, 60)
        return f"{int(m)}:{s:04.1f}" if decimals else f"{int(m)}:{int(s):02d}"

    @staticmethod
    def fmt_mark(val: float, kind: str) -> str:
        """A mark as its sport prints it: 12.44, 2:05.44, 45-11.25, 5-04.00."""
        if kind == "time":
            return Gen.fmt_time_static(val)
        if kind in ("distance", "height"):
            feet, inches = int(val // 12), val % 12
            return f"{feet}-{inches:05.2f}" if kind == "height" else f"{feet}-{inches:.2f}"
        if kind in ("strokes", "pinfall"):
            return str(int(round(val)))
        if kind == "rating":
            return ["I", "II", "III", "IV"][min(3, max(0, int(round(val)) - 1))]
        return f"{val:.2f}"

    @staticmethod
    def fmt_time_static(secs: float) -> str:
        if secs < 60:
            return f"{secs:.2f}"
        return f"{int(secs // 60)}:{secs % 60:05.2f}"

    def make_meet(self, sport: Sport, name, host, date, participants, played):
        rng = self.rng
        meet = Meet(name=name, date=date.isoformat(), sport=sport.key, season=SEASON,
                    venue=host, host=host)
        if played:
            fam, card = self.meet_family(sport.key)
            rule = meet_scoring(sport.key)[0]
            incomplete = rng.random() < 0.02
            # One squad per school for the whole meet, so the gymnast on beam
            # is the gymnast on bars and an all-around can be added up. Track
            # and swimming draw per event instead — a sprinter is not the
            # two-miler, and a card where one athlete wins all eighteen events
            # is the tell that nobody modelled the sport.
            squads = {s: self.roster(s, sport.key, 22) for s in participants}
            fixed = fam not in ("track", "winter-track", "swimming", "debate")
            # (school, athlete or None) -> running total, for the combined
            # event. Keyed on None for an ensemble, whose entrant is the school.
            running: dict[tuple, float] = {}
            combined: list[str] = []
            for num, (evname, per_school, lo, hi, kind, relay) in enumerate(card, 1):
                kind = kind or sport.mark_type.value
                mark_type = MarkType(kind) if kind != "combined" else sport.mark_type
                ev = Event(number=num, name=evname, gender=sport.gender,
                           division=None, round="Finals", mark_type=mark_type)
                if kind == "combined":
                    combined.append(evname)
                    self._combined_event(ev, running, rule == "place-points")
                    meet.events.append(ev)
                    continue
                if sport.gender == "Girls" and kind in self.GIRLS_FACTOR:
                    f = self.GIRLS_FACTOR[kind]
                    lo, hi = lo * f, hi * f
                low_good = MarkType(kind) in LOWER_IS_BETTER
                rows = []
                for school in participants:
                    st = self.strength(school, sport.key)
                    squad = squads.get(school) or []
                    n = max(per_school, 1)
                    if per_school and not squad:
                        continue
                    if per_school:
                        who = (squad[:n] if fixed
                               else rng.sample(squad, min(n, len(squad))))
                    else:
                        who = [None] * n
                    for k, person in enumerate(who):
                        base = ((lo + hi) / 2 - st * (hi - lo) * 0.08
                                + rng.gauss(0, (hi - lo) * 0.07))
                        val = min(hi, max(lo, base))
                        if kind == "rating":
                            # An adjudicated rating is four boxes, not a
                            # continuum. Squeezed through the generic draw
                            # every choir in the state earned a II.
                            val = min(4.4, max(0.6, 2.3 - st * 0.6 + rng.gauss(0, 0.85)))
                        elif not low_good:
                            val = lo + hi - val   # reflect: strong teams score high
                        # Snap to the precision the mark PRINTS at, before it
                        # is ranked or added. Ranking the continuous draw made
                        # three golfers on 79 finish first, second and third,
                        # and left a band total a hundredth off the captions
                        # it was the sum of.
                        val = (round(val) if kind in ("strokes", "pinfall", "rating")
                               else round(val, 2))
                        if relay:
                            # Each relay gets its OWN four legs. Slicing from
                            # the top of the squad every time entered the same
                            # four swimmers in the medley, the 200 free and the
                            # 400 free relay.
                            legs = squad[num * 4 % max(len(squad), 1):][:4] or squad[:4]
                            comp = [Competitor(p[0], school, p[1]) for p in legs]
                        elif person is not None:
                            comp = [Competitor(person[0], school, person[1])]
                        else:
                            comp = []
                        who_key = person[0] if person is not None else None
                        running[(school, who_key)] = \
                            running.get((school, who_key), 0.0) + val
                        rows.append((val, school, comp))
                rows.sort(key=lambda r: r[0] if low_good else -r[0])
                places = _competition_ranks([r[0] for r in rows])
                for place, (val, school, comp) in zip(places, rows):
                    raw = (str(place) if kind == "ordinal"
                           else self.fmt_mark(val, kind))
                    mark = parse_mark(raw, mark_type)
                    if incomplete and rng.random() < 0.15:
                        mark = None
                    ev.entries.append(Entry(
                        place=place, school=school, mark=mark, competitors=comp,
                        points=(self.place_points(place, relay)
                                if rule == "place-points" else None)))
                meet.events.append(ev)
            self.score_meet(meet, sport, combined)
        self.contests.append(meet)

    @classmethod
    def place_points(cls, place: int, relay: bool) -> float | None:
        if place > len(cls.PLACE_POINTS):
            return None
        return float(cls.PLACE_POINTS[place - 1] * (2 if relay else 1))

    def _combined_event(self, ev: Event, running: dict, award_points: bool):
        """An all-around or a band total: the entrant's own marks, added.

        Derived rather than drawn, so the number on the all-around line always
        equals the four apparatus above it. A separate draw would put a gymnast
        third on every apparatus and seventh in the all-around.
        """
        rows = sorted(running.items(), key=lambda kv: -kv[1])
        places = _competition_ranks([-v for _, v in rows])
        for place, ((school, who), total) in zip(places, rows):
            comp = [Competitor(who, school, None)] if who else []
            ev.entries.append(Entry(place=place, school=school,
                                    mark=parse_mark(f"{total:.2f}", ev.mark_type),
                                    competitors=comp,
                                    points=(self.place_points(place, False)
                                            if award_points else None)))

    def score_meet(self, meet: Meet, sport: Sport, combined: list[str]):
        """Derive the team result. Never drawn — always read off the entries.

        Scoring is **per event and then summed**, for every rule. Pooling a
        school's places across the whole card let one alpine skier who won both
        the giant slalom and the slalom count twice toward a three-runner team
        score, which put his school on 6 points for a two-race meet.
        """
        rule, count, _label = meet_scoring(sport.key)
        scored = [ev for ev in meet.events
                  if ev.entries and ev.name not in combined]
        totals: dict[str, float] = {}
        complete: dict[str, int] = {}
        low_wins = rule == "places" or (rule == "best-marks"
                                        and sport.mark_type in LOWER_IS_BETTER)

        for ev in scored:
            per: dict[str, list[float]] = {}
            for e in ev.entries:
                if e.mark is None:
                    continue
                if rule == "places" and e.place:
                    per.setdefault(e.school, []).append(float(e.place))
                elif rule == "best-marks" and e.mark.value is not None:
                    per.setdefault(e.school, []).append(e.mark.value)
                elif rule == "place-points" and e.points:
                    totals[e.school] = totals.get(e.school, 0.0) + e.points
            for school, vals in per.items():
                # A team that could not field `count` scorers does not score
                # the event — which is what an incomplete cross-country team is,
                # and why a five-runner sport needs five runners.
                if rule == "places" and len(vals) < count:
                    continue
                vals.sort(reverse=not low_wins)
                totals[school] = totals.get(school, 0.0) + sum(vals[:count])
                complete[school] = complete.get(school, 0) + 1

        if rule != "place-points":
            # Only schools that scored every event get a team result; a golf
            # team that played one round of a three-round card is not leading.
            full = max(complete.values(), default=0)
            totals = {s: v for s, v in totals.items() if complete.get(s) == full}

        ranked = sorted(totals.items(), key=lambda kv: (kv[1] if low_wins else -kv[1],
                                                        kv[0]))
        ranks = _competition_ranks([(v if low_wins else -v) for _, v in ranked])
        for rank, (school, pts) in zip(ranks, ranked):
            meet.team_scores.append(TeamScore(school=school, points=round(pts, 2),
                                              rank=rank, gender=sport.gender,
                                              division=None))

    def meet_sport_season(self, sport: Sport, invite_dates, champ_date=None):
        rng = self.rng
        sponsors = [s["name"] for s in self.schools if sport.key in s["sports"]]
        if len(sponsors) < 4:
            return
        by_area: dict[str, list] = {}
        for nm in sponsors:
            by_area.setdefault(self.by_name[nm]["area"], []).append(nm)
        for area, members in sorted(by_area.items()):
            if len(members) < 3:
                continue
            for i, date in enumerate(invite_dates):
                host = members[i % len(members)]
                field = members[: min(len(members), rng.randint(5, 12))]
                self.make_meet(sport, f"{self.by_name[host]['city']} Invitational",
                               host, date, sorted(field), date <= TODAY)
        if champ_date:
            by_group: dict[str, list] = {}
            for nm in sponsors:
                by_group.setdefault(sport.champ_group(self.by_name[nm]["classification"]), []).append(nm)
            for group, members in sorted(by_group.items()):
                if len(members) < 4:
                    continue
                field = sorted(members, key=lambda m: -self.strength(m, sport.key))[:16]
                self.make_meet(sport, f"JHSAA {group} {sport.name} Championships",
                               "Ashbury", champ_date, sorted(field), champ_date <= TODAY)

    def split_oversize(self):
        """No school is larger than sports.MAX_ENROLLMENT (owner rule 2027-08).

        A district does not let one high school reach 3,000 — it opens another
        and splits the attendance area, which is why the state is full of
        "<Town> East" and "<Town> West". So an oversize school BECOMES two (or
        more), sharing its town, its league and its activities, rather than
        having its enrollment quietly rescaled: the students are real either
        way, and rescaling would have shrunk a city's schools instead of giving
        it the schools a city that size actually has.

        A post-pass, like the mascots and the ladder, so it costs no RNG draw.
        Directions are tried in pairs and the first pair whose names are all
        free wins — many of these schools are already "<Town> East", and
        "<Town> East East" is not a school.
        """
        from app.sports import MAX_ENROLLMENT
        DIRS = ("North", "South", "East", "West", "Northwest", "Southeast")
        FEATURES = ("Bellows Lake", "Kettle Ridge", "Antelope Butte", "Willow Creek",
                    "Sandhill Marsh", "Heron Slough", "Manzanita Ridge", "Buckeye Bend",
                    "Sycamore Flat", "Deer Hollow", "Sulphur Springs", "Indigo Rim",
                    "Vernal Falls", "Lonepine Mesa", "Redbank Bluffs", "Coyote Draw",
                    "Foxtail Meadows", "Cathedral Point", "Gravel Narrows",
                    "Blackbird Canyon", "Cinnabar Divide", "Whiskey Bar")
        FAITHS = ("Catholic", "Christian", "Methodist", "Lutheran", "Episcopal")

        out, made = [], 0
        feats = list(FEATURES)
        for s in self.schools:
            if s["enrollment"] <= MAX_ENROLLMENT:
                out.append(s)
                continue
            n = -(-s["enrollment"] // MAX_ENROLLMENT)          # ceil
            # The school KEEPS ITS NAME and shrinks; the district opens n-1 more
            # beside it. ⚠️ Never stack a second direction on a name that already
            # carries one — "Ashbury East West" is not a school and nothing in
            # the country is named that way (owner, 2027-08). A town whose
            # obvious directional names are used up opens a school named for
            # nearby ground, or a parish/independent school, which is what
            # actually happens.
            last = s["name"].rsplit(" ", 1)[-1]
            directional = last in DIRS
            names = []
            while len(names) < n - 1:
                cand = None
                if not directional:
                    for d in DIRS:
                        if f"{s['name']} {d}".lower() not in self.used_schools:
                            cand = f"{s['name']} {d}"
                            break
                if cand is None:
                    while feats and cand is None:
                        f = feats.pop(0)
                        if f.lower() not in self.used_schools:
                            cand = f
                if cand is None:
                    for faith in FAITHS:
                        for stem in (s["city"], s["area"].split()[0]):
                            t = f"{stem} {faith}"
                            if t.lower() not in self.used_schools:
                                cand = t
                                break
                        if cand:
                            break
                if cand is None:
                    break
                self.used_schools.add(cand.lower())
                names.append(cand)

            # The parts do NOT sum to the parent — enrollment is fictional
            # (owner, 2027-08) and a district splitting a school is not
            # conserving a headcount, it is running two normal schools. Sized
            # off each name's own hash, so figures are stable and spread.
            def sized(nm, base):
                h = zlib.crc32(nm.encode())
                return max(120, min(MAX_ENROLLMENT,
                                    int(base * (0.72 + (h % 1000) / 1000 * 0.5))))
            base = s["enrollment"] / (len(names) + 1)
            s["enrollment"] = sized(s["name"], base)
            out.append(s)
            for nm in names:
                part = dict(s)
                part["name"] = nm
                part["_parent"] = s["name"]
                part["enrollment"] = sized(nm, base)
                part["private"] = any(nm.endswith(" " + f) for f in FAITHS)
                self.by_name[nm] = part
                out.append(part)
                made += 1
                for c in self.confs:
                    if s["name"] in c.get("members", []):
                        c["members"].append(nm)
                        break
        self.schools = out
        print(f"  opened {made} schools beside oversize ones")

    def rename_places(self):
        import json
        """Apply names.TOWN_RENAMES to towns and to the schools named for them.

        A post-pass, like the mascots and the ladder: the town grammar is a
        single RNG stream, so renaming at the draw would re-deal the state.
        """
        for old, new in N.TOWN_RENAMES.items():
            for s in self.schools:
                if s["city"] == old:
                    s["city"] = new
                if s["name"] == old or s["name"].startswith(old + " "):
                    fresh = new + s["name"][len(old):]
                    self.by_name.pop(s["name"], None)
                    for c in self.confs:
                        if s["name"] in c.get("members", []):
                            c["members"].remove(s["name"])
                            c["members"].append(fresh)
                    s["name"] = fresh
                    self.by_name[fresh] = s
            self.used_places.add(new.lower())
        # ⚠️ and in the WRITTEN records: write_orgs runs before every post-pass,
        # so schools.json still carries the pre-rename town and school name.
        path = RECORDS / "orgs" / "schools.json"
        if path.exists():
            doc = json.loads(path.read_text())
            for row in doc["schools"]:
                for old, new in N.TOWN_RENAMES.items():
                    if row["city"] == old:
                        row["city"] = new
                    if row["name"] == old or row["name"].startswith(old + " "):
                        row["name"] = new + row["name"][len(old):]
            path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")

    def write_orgs_final(self, records_dir):
        """Rewrite records/orgs/schools.json from the FINAL roster.

        ⚠️ `records_io.write_orgs` runs BEFORE every post-pass, so the file it
        writes predates the mascots, the oversize splits, the town renames and
        the ladder. `reclassify` then stamped new class labels onto those stale
        rows, which is how the records came to hold a "7A" of 4,070 students —
        a classification from after the cap sitting on an enrollment from
        before it, with the split schools missing entirely. The records are
        written once more, at the end, from what the state actually is.

        Marks are read back off the file, since `mascots.apply` writes there and
        not to `self.schools`; a school opened by a split inherits its parent's.
        """
        import json
        path = records_dir / "orgs" / "schools.json"
        doc = json.loads(path.read_text())
        marks = {r["name"]: (r.get("mascot"), r.get("colors")) for r in doc["schools"]}
        rows = []
        for s in self.schools:
            m, c = marks.get(s["name"]) or marks.get(s.get("_parent"), (None, None))
            rows.append(dict(name=s["name"], city=s["city"], area=s["area"],
                             mascot=m or s["mascot"],
                             colors=c or s.get("colors"),
                             classification=s["classification"],
                             conference=s.get("conference", ""),
                             enrollment=s["enrollment"], private=s["private"],
                             sports=s.get("sports", [])))
        doc["schools"] = sorted(rows, key=lambda r: r["name"])
        path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print(f"  records rewritten from the final roster: {len(rows)} schools")

    #: How many schools each class should hold. A mild pyramid — more small
    #: schools than large — summing to the roster. Enrollment is FICTIONAL, so
    #: the classes are sized first and the numbers made to fit, rather than the
    #: numbers being treated as given and the classes coming out however they
    #: fell. The state had 242 schools in 7A against 84 in 3A purely because the
    #: expansion roster's invented enrollments happened to cluster.
    CLASS_SHAPE = [("9A", 8), ("8A", 9), ("7A", 11), ("6A", 12), ("5A", 12),
                   ("4A", 13), ("3A", 13), ("2A", 12), ("1A", 10)]

    def rebalance_enrollments(self):
        """Spread the roster across the classification bands.

        Order is preserved — the biggest school stays the biggest — so a metro
        flagship is still a big school and a hamlet is still a small one. Only
        the NUMBER moves, into the band its rank deserves, spread inside that
        band by the school's own name hash so figures are stable and varied.
        """
        from app.sports import BANDS, MAX_ENROLLMENT
        band = {c: (max(lo, 55), hi if hi is not None else MAX_ENROLLMENT)
                for c, lo, hi in BANDS}   # nobody fields a 1-student school
        order = sorted(self.schools, key=lambda s: (-s["enrollment"], s["name"]))
        weights = [w for _c, w in self.CLASS_SHAPE]
        total = sum(weights)
        n, i = len(order), 0
        for (cls, w), j in zip(self.CLASS_SHAPE, range(len(weights))):
            take = round(n * w / total) if j < len(weights) - 1 else n - i
            lo, hi = band[cls]
            for s in order[i:i + take]:
                h = zlib.crc32(s["name"].encode())
                s["enrollment"] = lo + h % max(1, hi - lo + 1)
            i += take
        print(f"  enrollments rebalanced across {len(self.CLASS_SHAPE)} classes")

    def reclassify(self, records_dir=None):
        """Put every school on the owner's ladder (2027-08), founding and
        expansion alike, by its own enrollment.

        A POST-PASS, like the mascots, and for the same reason: classification
        used to be dealt by quota slice here and stated in a column there, so
        the two halves of the state ran on different ladders under one set of
        labels — an expansion "1A" (357-649 students) was bigger than a founding
        "3A", and a "3A" of 1,399 outweighed a "5A" of 1,209. Deriving it from
        enrollment is what makes a classification mean one thing. Doing it at
        emit costs no RNG draw and so cannot move a result.
        """
        import json
        from app.sports import classify
        for s in self.schools:
            s["classification"] = classify(s["enrollment"])
        if records_dir is not None:
            path = records_dir / "orgs" / "schools.json"
            if path.exists():
                doc = json.loads(path.read_text())
                by = {s["name"]: s["classification"] for s in self.schools}
                for row in doc["schools"]:
                    row["classification"] = by.get(row["name"], row["classification"])
                path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")

    # ---------------------------------------------------------- gazetteer
    def write_gazetteer(self):
        """Counties and populations, derived from the state that exists.

        Population comes from the schools rather than a fresh random draw: a
        high school's four grades hold roughly 5%% of its town, so town pop ~
        total public enrollment x 15-22, jittered on a stable hash of the name
        (crc32, not the RNG stream — the gazetteer must not perturb the
        season). Anchor and owner-specified cities keep their stated figures.

        COORDINATES are assigned by RANK against the real ground (owner rule
        2027-08). Each Jefferson county names a real county; `data/geo_anchors
        .json` holds that real county's own populated places, largest first,
        and a Jefferson city takes the coordinates of the real place at its own
        population rank. So Ashbury sits where Medford sits, Port Veles where
        Coos Bay sits, and a 4,000-person Antler County mill town lands on a
        real 4,000-person Douglas County mill town. Nothing is scattered or
        jittered — every coordinate in the state is a real place's coordinate,
        which is what keeps coastal towns out of the Pacific and desert towns
        off the ridge lines without a single special case.

        Emitted as records/orgs/cities.json, records/orgs/cities.geojson (drop
        it on any map) and rendered to docs/GAZETTEER-jefferson.md, so no
        document can drift from the records.
        """
        import json
        stated = {N.ANCHORS["inland_metro"][0]: N.ANCHORS["inland_metro"][1],
                  N.ANCHORS["coastal_metro"][0]: N.ANCHORS["coastal_metro"][1],
                  N.ANCHORS["boise_side"][0]: N.ANCHORS["boise_side"][1]}
        stated.update(dict(N.ANCHORS["secondary"]))
        stated.update({c: pop for c, pop, _a, _s in N.NAMED_CITIES})
        # the 7A roster states city populations and counties; data wins
        stated.update({c: pop for c, (pop, _cty) in self.expansion_city_data.items()})
        by_county_name = {c: (c, r) for lst in N.COUNTY_GEO.values() for c, r in lst}
        stated_county = {c: by_county_name[cty]
                         for c, (_pop, cty) in self.expansion_city_data.items()
                         if cty in by_county_name}
        # ⚠️ Cities published before the county map grew are FROZEN to the county
        # they were published under. An unpinned city hashes into its area's
        # county list, so adding a county to an existing area re-deals every
        # unpinned city in it — the gazetteer, the districts named after a
        # dominant county and every archived season referencing them would move
        # at once, for a change that was meant to be purely additive.
        frozen = json.loads((ROOT / "generators/jefferson/data/county_assignments.json")
                            .read_text())["cities"]

        towns = {}
        for s in self.schools:
            e = towns.setdefault((s["city"], s["area"]), dict(enroll=0, publics=0))
            if not s["private"]:
                e["enroll"] += s["enrollment"]
                e["publics"] += 1

        cities = []
        for (city, area), e in sorted(towns.items()):
            h = zlib.crc32(city.encode())
            if city in stated_county:
                county, real = stated_county[city]
            elif city in frozen:
                county, real = by_county_name[frozen[city]]
            elif city in N.COUNTY_PINS:
                county, real = next((c, r) for c, r in sum(N.COUNTY_GEO.values(), [])
                                    if c == N.COUNTY_PINS[city])
            else:
                county, real = N.COUNTY_GEO[area][h % len(N.COUNTY_GEO[area])]
            if city in stated:
                pop = stated[city]
            else:
                pop = e["enroll"] * (15 + h % 8) + h % 997
                pop = int(round(pop, -2 if pop < 20000 else -3))
            cities.append(dict(name=city, county=county, real_county=real,
                               area=area, population=pop))
        cities.sort(key=lambda c: (c["county"], -c["population"], c["name"]))

        # rank-match onto the real ground. `cities` is already ordered by
        # (county, -population), so a county's rank IS its index within its run.
        anchors = json.loads((ROOT / "generators/jefferson/data/geo_anchors.json")
                             .read_text())["counties"]
        rank: dict[str, int] = {}
        for c in cities:
            real = c["real_county"]
            i = rank[real] = rank.get(real, -1) + 1
            pool = anchors.get(real)
            if not pool:
                raise SystemExit(
                    f"no geo anchors for {real}; add it to scripts/"
                    f"build_geo_anchors.py::SEATS and re-run that script")
            if i >= len(pool):
                # Never silently wrap: two towns would share a coordinate and
                # the map would quietly lie. Lake County, OR is the tight one
                # (14 real places), so this is a live possibility, not a hedge.
                raise SystemExit(
                    f"{c['county']} County has {i + 1}+ cities but {real} only "
                    f"supplies {len(pool)} anchors — re-run scripts/"
                    f"build_geo_anchors.py with a larger --per-county")
            _site, c["lat"], c["lon"] = pool[i]

        (RECORDS / "orgs").mkdir(parents=True, exist_ok=True)
        (RECORDS / "orgs/cities.json").write_text(json.dumps(
            {"$type": "org.prepnet.temp.org.cities", "cities": cities},
            indent=1, sort_keys=True) + "\n")
        (RECORDS / "orgs/cities.geojson").write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{"type": "Feature",
                          "geometry": {"type": "Point",
                                       "coordinates": [c["lon"], c["lat"]]},
                          "properties": {k: v for k, v in c.items()
                                         if k not in ("lat", "lon")}}
                         for c in cities]},
            indent=1, sort_keys=True) + "\n")

        lines = ["# Jefferson gazetteer — cities and towns by county",
                 "",
                 "Generated from `records/orgs/cities.json` by the state generator;",
                 "edit the generator, not this file. Counties are fictional; each",
                 "names the real county whose ground it stands on. Owner-stated",
                 "populations are authoritative; only unstated towns derive from",
                 "school enrollment.",
                 "",
                 "Coordinates are real. A Jefferson city stands on the real place",
                 "at its own population rank inside its real county, so the state",
                 "sits on actual valley floors, river bends and harbours. Drop",
                 "`records/orgs/cities.geojson` on any map to see it.",
                 "",
                 "**The ~17.6M state total is a design decision, not an error**",
                 "(owner rule 2027-08: Jefferson is West Coast Texas). Do not",
                 "rescale it.", ""]
        bycounty = {}
        for c in cities:
            bycounty.setdefault((c["county"], c["real_county"]), []).append(c)
        total = 0
        for (county, real), rows in sorted(bycounty.items()):
            csum = sum(r["population"] for r in rows)
            total += csum
            lines.append(f"## {county} County ({real}) — {csum:,}")
            lines.append("")
            lines.append("| City or town | Population | Area | Latitude | Longitude |")
            lines.append("| --- | ---: | --- | ---: | ---: |")
            for r in rows:
                lines.append(f"| {r['name']} | {r['population']:,} | {r['area']} "
                             f"| {r['lat']:.4f} | {r['lon']:.4f} |")
            lines.append("")
        lines.append(f"**State total: {total:,}** across {len(cities)} places, "
                     f"{len(bycounty)} counties.")
        (ROOT / "docs/GAZETTEER-jefferson.md").write_text("\n".join(lines) + "\n")

    # ---------------------------------------------------------- expansion
    def load_expansion(self):
        """The expansion rosters (owner data, 2027-08): the 7A planning file's
        584 schools and 67 conferences, plus the nine new counties' towns and
        schools. New cities carry stated populations and counties. Loaded
        AFTER the founding 256 are built and never through the shared RNG —
        everything a new school needs that the file doesn't state is derived
        from a name hash, so the founding state stays byte-stable."""
        import csv
        # Two rosters: the 7A planning file, and the nine counties added to the
        # map in 2027-08 (scripts/build_county_expansion.py). Both load the same
        # way for the same reason — after the founding RNG stream, never inside it.
        rows = []
        for fn in ("expansion_schools.csv", "expansion_counties.csv"):
            path = ROOT / "generators/jefferson/data" / fn
            if path.exists():
                rows += list(csv.DictReader(open(path)))
        confs_new: dict[str, dict] = {}
        for r in rows:
            name = r["school"]
            h = zlib.crc32(name.encode())
            cls = r["classification"]
            lo, hi = OFFER_RANGE[cls]
            target = lo + h % (hi - lo + 1)
            offered = {"girls-volleyball", "boys-basketball", "girls-basketball",
                       "boys-cross-country", "girls-cross-country",
                       "boys-track", "girls-track"}
            if not (r["private"] == "True") or h % 2:
                offered.add("football")
            for i, sp in enumerate(CATALOG):
                if len(offered) >= target:
                    break
                if sp.key in offered:
                    continue
                p = {"broad": 0.75, "metro": 0.5, "mountain": 0.2,
                     "aquatic": 0.35}[sp.reach]
                if cls in ("1A", "2A") and sp.reach != "broad":
                    p *= 0.4
                if (zlib.crc32(f"{name}|{sp.key}".encode()) % 1000) / 1000 < p:
                    offered.add(sp.key)
            self.used_places.add(r["city"].lower())
            self.used_schools.add(name.lower())
            self.schools.append(dict(
                name=name, city=r["city"], area=r["area"],
                private=r["private"] == "True", classification=cls,
                enrollment=int(r["enrollment"]), mascot=r["mascot"],
                quality=((h >> 4) % 2000) / 1000 - 1.0,
                sports=sorted(offered),
            ))
            self.by_name[name] = self.schools[-1]
            self.schools[-1]["conference"] = r["conference"]
            c = confs_new.setdefault(r["conference"], dict(
                name=r["conference"], slug=slugify(r["conference"]),
                area=r["area"], members=[]))
            c["members"].append(name)
            self.expansion_city_data[r["city"]] = (int(r["city_population"]), r["county"])
        self.confs.extend(confs_new.values())

    # ---------------------------------------------------------------- run
    def run(self):
        self._str = {}
        self.schools = self.build_schools()
        self.by_name = {s["name"]: s for s in self.schools}
        self.confs = self.build_conferences(self.schools)
        self.build_offerings(self.schools)
        self.load_expansion()

        fall_fri = self.weeks(dt.date(2026, 8, 28), 10)
        fall_playoffs = dt.date(2026, 11, 6)
        winter = self.weeks(dt.date(2026, 12, 1), 13)
        spring = self.weeks(dt.date(2027, 3, 19), 10)
        fall_invites = [dt.date(2026, 9, 5) + dt.timedelta(days=14 * i) for i in range(4)]
        winter_invites = [dt.date(2026, 12, 5) + dt.timedelta(days=14 * i) for i in range(6)]
        spring_invites = [dt.date(2027, 3, 27) + dt.timedelta(days=14 * i) for i in range(4)]

        # Athlete pools before the season loop, and a per-sport RNG stream
        # inside it. With one shared stream in catalog order, moving a single
        # sport between seasons redrew every sport after it — the whole state
        # reshuffled to relocate one activity. Now a catalog edit changes that
        # sport and nothing else.
        for s in self.schools:
            self.pool(s["name"])
        base = self.rng

        for sport in CATALOG:
            self.rng = random.Random(SEED ^ zlib.crc32(sport.key.encode()))
            dates = {"fall": fall_fri, "winter": winter, "spring": spring}[sport.season]
            invites = {"fall": fall_invites, "winter": winter_invites,
                       "spring": spring_invites}[sport.season]
            if sport.shape.value in ("game", "dual"):
                self.team_sport_season(
                    sport, dates,
                    playoffs_start=fall_playoffs if sport.season == "fall" else None)
            else:
                self.meet_sport_season(sport, invites,
                                       champ_date=champ_date(sport))
        self.rng = base

        # emit
        shutil.rmtree(RECORDS / "contests", ignore_errors=True)
        shutil.rmtree(RECORDS / "orgs", ignore_errors=True)
        self.contests.sort(key=lambda c: (c.date or "", c.name))
        for i, c in enumerate(self.contests):
            path = RECORDS / "contests" / SEASON / c.sport / f"{i:05d}-{slugify(c.name)[:60]}.json"
            records_io.write_contest(path, c, sequence=i)
        records_io.write_orgs(
            RECORDS,
            [dict(name=s["name"], city=s["city"], area=s["area"], mascot=s["mascot"],
                  classification=s["classification"], conference=s["conference"],
                  enrollment=s["enrollment"], private=s["private"], sports=s["sports"],
                  colors=list(N.SCHOOL_COLORS[zlib.crc32(s["name"].encode())
                                              % len(N.SCHOOL_COLORS)]))
             for s in self.schools],
            self.confs,
        )
        # Mascots are a post-pass: keyed on the school's own name, so they cost
        # no RNG draws and cannot move a result. See that module for why the
        # frequency curve and the regional tail matter.
        from generators.jefferson import mascots as _mascots
        _mascots.apply(RECORDS)
        self.split_oversize()
        self.rename_places()
        self.rebalance_enrollments()
        self.reclassify(RECORDS)
        self.write_orgs_final(RECORDS)
        self.write_gazetteer()
        games = sum(1 for c in self.contests if isinstance(c, Game))
        duals = sum(1 for c in self.contests if isinstance(c, Dual))
        meets = sum(1 for c in self.contests if isinstance(c, Meet))
        played = sum(1 for c in self.contests if (c.date or "") <= TODAY.isoformat())
        print(f"{len(self.schools)} schools · {len(self.confs)} conferences · "
              f"{games} games · {duals} duals · {meets} meets · "
              f"{played:,} on/before {TODAY} · {len(self.contests):,} contests")


if __name__ == "__main__":
    Gen().run()
