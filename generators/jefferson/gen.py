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
    Competitor, Dual, Entry, Event, Game, Line, Meet, Period, TeamScore, parse_mark,
)
from app.sports import BY_KEY, CATALOG, CLASSES, Sport  # noqa: E402
from generators.jefferson import names as N  # noqa: E402

SEED = 5
SEASON = "2026-27"
TODAY = dt.date(2027, 1, 16)
RECORDS = ROOT / "records"

CLASS_TARGETS = {"6A": 38, "5A": 42, "4A": 44, "3A": 38, "2A": 36, "1A": 58}
ENROLL = {"6A": (1800, 3200), "5A": (1200, 1799), "4A": (700, 1199),
          "3A": (400, 699), "2A": (220, 399), "1A": (60, 219)}
OFFER_RANGE = {"6A": (20, 28), "5A": (17, 24), "4A": (14, 20),
               "3A": (11, 15), "2A": (8, 12), "1A": (6, 10)}
POOL = {"6A": 72, "5A": 60, "4A": 48, "3A": 38, "2A": 30, "1A": 22}

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


class Gen:
    def __init__(self):
        self.rng = random.Random(SEED)
        self.used_places: set[str] = set(N.BLOCKLIST)
        self.used_schools: set[str] = set()
        self.contests: list = []
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
                   "Port Meridian": ["Port Meridian Polytechnic",
                                     "Port Meridian Maritime"],
                   "Halbrook": ["Halbrook Technical"]}

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
        if school not in self.pools:
            rng = self.rng
            n = POOL[self.by_name[school]["classification"]]
            self.pools[school] = [
                (f"{rng.choice(N.FIRST_NAMES)} {rng.choice(N.LAST_NAMES)}",
                 str(rng.randint(9, 12)))
                for _ in range(n)
            ]
        return self.pools[school]

    def roster(self, school, sport_key, size):
        key = (school, sport_key)
        if key not in self.rosters:
            pool = self.pool(school)
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

    def make_dual(self, sport: Sport, home, away, date, played, round_name=None):
        rng = self.rng
        name = f"{away} at {home}" if not round_name else f"{away} at {home} — {round_name}"
        d = Dual(name=name, date=date.isoformat(), sport=sport.key, season=SEASON,
                 home=home, away=away)
        if played and rng.random() < 0.985:
            if "tennis" in sport.key:
                slots = [("singles", 4), ("doubles", 3)]
            elif "wrestling" in sport.key:
                slots = [("106", 1), ("120", 1), ("132", 1), ("145", 1),
                         ("160", 1), ("182", 1), ("220", 1), ("285", 1)]
            else:  # fencing
                slots = [("foil", 3), ("épée", 3), ("sabre", 3)]
            hr = self.roster(home, sport.key, 12)
            ar = self.roster(away, sport.key, 12) if away in self.by_name else []
            hp = ap = 0.0
            slot_i = 0
            hi = ai = 0
            for kind, count in slots:
                for _ in range(count):
                    slot_i += 1
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
                    if "tennis" in sport.key:
                        score = f"6-{rng.randint(0,4)}, {rng.choice(['6-'+str(rng.randint(0,4)), '7-5', '7-6'])}"
                        pt = 1.0
                    elif "wrestling" in sport.key:
                        kindres = rng.choice(["Fall", "Dec", "Maj"])
                        score = {"Fall": f"Fall {rng.randint(0,5)}:{rng.randint(10,59)}",
                                 "Dec": f"Dec {rng.randint(4,12)}-{rng.randint(0,3)}",
                                 "Maj": f"Maj {rng.randint(10,18)}-{rng.randint(0,5)}"}[kindres]
                        pt = {"Fall": 6.0, "Dec": 3.0, "Maj": 4.0}[kindres]
                    else:
                        score = f"5-{rng.randint(0,4)}"
                        pt = 1.0
                    if home_wins:
                        hp += pt
                    else:
                        ap += pt
                    d.lines.append(Line(slot=slot_i, kind=kind, home=hp_players,
                                        away=ap_players, winner="home" if home_wins else "away",
                                        score=score, team_point=pt))
            d.home_points, d.away_points = hp, ap
        self.contests.append(d)
        return d

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
    MEET_EVENTS = {
        "cross-country": [("5,000 Meter Run", 5, (930, 1380))],
        "boys-golf": [("18 Holes", 4, (68, 108))],
        "girls-golf": [("18 Holes", 4, (68, 108))],
        "mountain-biking": [("Varsity Race", 4, (3600, 5400))],
        "swimming": [("200 Medley Relay", 0, (105, 135)), ("200 Freestyle", 2, (105, 150)),
                     ("50 Freestyle", 2, (22, 32)), ("100 Butterfly", 2, (55, 75)),
                     ("100 Freestyle", 2, (48, 68)), ("500 Freestyle", 2, (290, 400))],
        "alpine-skiing": [("Giant Slalom", 4, (58, 80))],
        "nordic-skiing": [("5K Classic", 4, (840, 1200))],
        "bowling": [("3-Game Series", 5, (420, 720))],
        "gymnastics": [("All-Around", 4, (30.0, 38.5))],
        "competitive-spirit": [("Game Day Routine", 0, (62.0, 94.0))],
        "winter-track": [("60 Meter Dash", 3, (7.0, 8.6)), ("400 Meter Dash", 3, (50, 68)),
                         ("1600 Meter Run", 3, (260, 340))],
        # Activities: same MEET machinery, marks that match how each is judged.
        # A band show is scored by a judging panel; a choir earns a division
        # RATING (I best); debate is pure placement. No invented box scores.
        "marching-band": [("Field Show", 0, (58.0, 96.0))],
        "choir": [("Concert Choir", 0, (1.0, 4.0)), ("Chamber Ensemble", 0, (1.0, 4.0))],
        "debate": [("Policy Debate", 2, (1.0, 30.0)), ("Lincoln-Douglas", 2, (1.0, 30.0)),
                   ("Public Forum", 2, (1.0, 30.0))],
    }

    def meet_family(self, key):
        for fam in self.MEET_EVENTS:
            if fam in key:
                return self.MEET_EVENTS[fam]
        return self.MEET_EVENTS["cross-country"]

    def fmt_time(self, secs: float, decimals=1) -> str:
        if secs < 60:
            return f"{secs:.2f}"
        m, s = divmod(secs, 60)
        return f"{int(m)}:{s:04.1f}" if decimals else f"{int(m)}:{int(s):02d}"

    def make_meet(self, sport: Sport, name, host, date, participants, played):
        rng = self.rng
        meet = Meet(name=name, date=date.isoformat(), sport=sport.key, season=SEASON,
                    venue=host, host=host)
        if played:
            incomplete = rng.random() < 0.02
            for num, (evname, per_school, rng_range) in enumerate(self.meet_family(sport.key), 1):
                ev = Event(number=num, name=evname, gender=sport.gender,
                           division=None, round="Finals", mark_type=sport.mark_type)
                lo, hi = rng_range
                rows = []
                for school in participants:
                    st = self.strength(school, sport.key)
                    n = per_school or 1
                    roster = self.roster(school, sport.key, 10) if per_school else []
                    for k in range(n):
                        base = (lo + hi) / 2 - st * (hi - lo) * 0.08 + rng.gauss(0, (hi - lo) * 0.07)
                        val = min(hi, max(lo, base))
                        if sport.lower_is_better is False and sport.mark_type.value in ("points", "pinfall"):
                            val = lo + hi - val  # reflect: strong teams score high
                        comp = []
                        if roster:
                            p = roster[k % len(roster)]
                            comp = [Competitor(p[0], school, p[1])]
                        if sport.mark_type.value == "time":
                            raw = self.fmt_time(val)
                        elif sport.mark_type.value in ("strokes", "pinfall"):
                            raw = str(int(val))
                        elif sport.mark_type.value == "rating":
                            raw = ["I", "II", "III", "IV"][min(3, int(val) - 1)]
                        else:
                            raw = f"{val:.2f}"
                        rows.append((val, school, comp, raw))
                better_low = sport.lower_is_better or sport.mark_type.value in ("time", "strokes")
                rows.sort(key=lambda r: r[0] if better_low else -r[0])
                for place, (val, school, comp, raw) in enumerate(rows, 1):
                    if sport.mark_type.value == "ordinal":
                        raw = str(place)     # debate's mark IS the placement
                    mark = parse_mark(raw, sport.mark_type)
                    if incomplete and rng.random() < 0.15:
                        mark = None
                    ev.entries.append(Entry(place=place, school=school, mark=mark,
                                            competitors=comp))
                meet.events.append(ev)
            # derived team scores: sum of places of a school's best entries (low good)
            totals: dict[str, float] = {}
            for ev in meet.events:
                for e in ev.entries:
                    totals[e.school] = totals.get(e.school, 0) + (e.place or 0)
            ranked = sorted(totals.items(), key=lambda kv: kv[1])
            for rank, (school, pts) in enumerate(ranked, 1):
                meet.team_scores.append(TeamScore(school=school, points=pts, rank=rank,
                                                  gender=sport.gender, division=None))
        self.contests.append(meet)

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

    # ---------------------------------------------------------- gazetteer
    def write_gazetteer(self):
        """Counties and populations, derived from the state that exists.

        Population comes from the schools rather than a fresh random draw: a
        high school's four grades hold roughly 5%% of its town, so town pop ~
        total public enrollment x 15-22, jittered on a stable hash of the name
        (crc32, not the RNG stream — the gazetteer must not perturb the
        season). Anchor and owner-specified cities keep their stated figures.
        Emitted as records/orgs/cities.json and rendered to
        docs/GAZETTEER-jefferson.md so the document can never drift from the
        records.
        """
        import json
        stated = {N.ANCHORS["inland_metro"][0]: N.ANCHORS["inland_metro"][1],
                  N.ANCHORS["coastal_metro"][0]: N.ANCHORS["coastal_metro"][1],
                  N.ANCHORS["boise_side"][0]: N.ANCHORS["boise_side"][1]}
        stated.update(dict(N.ANCHORS["secondary"]))
        stated.update({c: pop for c, pop, _a, _s in N.NAMED_CITIES})

        towns = {}
        for s in self.schools:
            e = towns.setdefault((s["city"], s["area"]), dict(enroll=0, publics=0))
            if not s["private"]:
                e["enroll"] += s["enrollment"]
                e["publics"] += 1

        cities = []
        for (city, area), e in sorted(towns.items()):
            h = zlib.crc32(city.encode())
            county, real = (N.COUNTY_GEO[area][h % len(N.COUNTY_GEO[area])]
                            if city not in N.COUNTY_PINS else
                            next((c, r) for c, r in sum(N.COUNTY_GEO.values(), [])
                                 if c == N.COUNTY_PINS[city]))
            if city in stated:
                pop = stated[city]
            else:
                pop = e["enroll"] * (15 + h % 8) + h % 997
                pop = int(round(pop, -2 if pop < 20000 else -3))
            cities.append(dict(name=city, county=county, real_county=real,
                               area=area, population=pop))
        cities.sort(key=lambda c: (c["county"], -c["population"], c["name"]))

        (RECORDS / "orgs").mkdir(parents=True, exist_ok=True)
        (RECORDS / "orgs/cities.json").write_text(json.dumps(
            {"$type": "org.prepnet.temp.org.cities", "cities": cities},
            indent=1, sort_keys=True) + "\n")

        lines = ["# Jefferson gazetteer — cities and towns by county",
                 "",
                 "Generated from `records/orgs/cities.json` by the state generator;",
                 "edit the generator, not this file. Counties are fictional; each",
                 "names the real county whose ground it stands on. Populations are",
                 "derived from school enrollment (a town holds roughly 15-22 people",
                 "per public-high-school seat); anchor and owner-specified cities",
                 "keep their stated figures.", ""]
        bycounty = {}
        for c in cities:
            bycounty.setdefault((c["county"], c["real_county"]), []).append(c)
        total = 0
        for (county, real), rows in sorted(bycounty.items()):
            csum = sum(r["population"] for r in rows)
            total += csum
            lines.append(f"## {county} County ({real}) — {csum:,}")
            lines.append("")
            lines.append("| City or town | Population | Area |")
            lines.append("| --- | ---: | --- |")
            for r in rows:
                lines.append(f"| {r['name']} | {r['population']:,} | {r['area']} |")
            lines.append("")
        lines.append(f"**State total: {total:,}** across {len(cities)} places, "
                     f"{len(bycounty)} counties.")
        (ROOT / "docs/GAZETTEER-jefferson.md").write_text("\n".join(lines) + "\n")

    # ---------------------------------------------------------------- run
    def run(self):
        self._str = {}
        self.schools = self.build_schools()
        self.by_name = {s["name"]: s for s in self.schools}
        self.confs = self.build_conferences(self.schools)
        self.build_offerings(self.schools)

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
                self.meet_sport_season(
                    sport, invites,
                    champ_date=dt.date(2026, 10, 31) if sport.season == "fall" else None)
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
                  enrollment=s["enrollment"], private=s["private"], sports=s["sports"])
             for s in self.schools],
            self.confs,
        )
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
