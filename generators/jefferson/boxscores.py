"""
Give the generated games period scoring and box scores.

    python3 -m generators.jefferson.boxscores [--check]

The ingestion work proved a box score could be parsed and rendered, on five
imported files. That left the other 23,144 played games in the state as a bare
final score — including every championship — which is the exact complaint the
whole task started from. A capability demonstrated on five records is a
capability nobody browsing the site will ever meet.

So this is a post-pass over the finished contest records:

* **Period scoring on everything that has periods.** Cheap and the biggest
  visible win: quarters for basketball and football, halves for soccer, three
  periods for hockey, innings for baseball. Only volleyball had them before,
  because the state generator returns sets for volleyball and ``None`` for
  everything else.
* **Box scores on a slice, not on everything.** These are fictional games; the
  point is that the page type is demonstrable, not that all 23,000 have player
  stats. Every postseason game gets one — those are the pages a reader is sent
  to from a bracket — plus a deterministic share of the regular season so
  ordinary browsing lands on them regularly. Boxing all of them would add
  ~60MB of invented statistics to the repository for no extra proof.

**Rosters are per (school, sport) and stable across games**, which is the part
that matters beyond one page: a player who scores 18 in December is the same
player on the same roster in February, so athlete pages accumulate a season
instead of showing one disconnected line.

* **Event cards for track meets.** The state's track meets carried exactly one
  event each. A real one runs eighteen — six flat races, two hurdles, three
  relays, and seven field events — and MEET is the shape this whole model was
  designed around, so a one-event track meet is the flagship case failing
  quietly. Cross country, golf and bowling legitimately have one event and are
  left alone.

Like the mascot pass, this is keyed on the record's own identity and never
touches the state generator's RNG, so it cannot move a result.
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

from generators.jefferson import names as N     # noqa: E402

RECORDS = ROOT / "records"

#: How the clock is divided, by sport. ``None`` means the sport has no period
#: split worth showing (golf, and the meet sports, which are not GAMEs anyway).
PERIODS: dict[str, tuple[str, int]] = {
    "football": ("Q", 4),
    "boys-basketball": ("Q", 4),
    "girls-basketball": ("Q", 4),
    "boys-soccer": ("H", 2),
    "girls-soccer": ("H", 2),
    "field-hockey": ("Q", 4),
    "boys-ice-hockey": ("P", 3),
    "girls-ice-hockey": ("P", 3),
    "boys-water-polo": ("Q", 4),
    "girls-water-polo": ("Q", 4),
    "boys-lacrosse": ("Q", 4),
    "girls-lacrosse": ("Q", 4),
    "girls-flag-football": ("H", 2),
    "ultimate": ("H", 2),
    "baseball": ("Inn", 7),
    "softball": ("Inn", 7),
}

#: Box-score columns, in the order a scorebook for that sport prints them.
#: Sports with more than one table name their sections; the renderer draws one
#: table per section without knowing what any column means.
COLUMNS: dict[str, dict[str, list[str]]] = {
    "basketball": {"": "min fg 3pt ft oreb dreb reb ast stl blk to pf pts".split()},
    "football": {
        "PASSING": "cp att yds td int lg".split(),
        "RUSHING": "car yds avg td lg".split(),
        "RECEIVING": "rec yds avg td lg".split(),
        "DEFENSE": "tkl ast tfl sack int pd".split(),
    },
    "hockey": {
        "SKATERS": "g a pts pm pim sog fow".split(),
        "GOALTENDING": "min sa sv ga svpct".split(),
    },
    "volleyball": {"": "sp k e ta pct ast dig bs ba sa se".split()},
    "baseball": {
        "BATTING": "ab r h rbi bb so lob avg".split(),
        "PITCHING": "ip h r er bb so hr era".split(),
    },
    "soccer": {"": "min g a sh sog fc off sv".split()},
}

#: Which column set a sport uses.
FAMILY: dict[str, str] = {
    "boys-basketball": "basketball", "girls-basketball": "basketball",
    "football": "football",
    "boys-ice-hockey": "hockey", "girls-ice-hockey": "hockey",
    "girls-volleyball": "volleyball", "boys-volleyball": "volleyball",
    "baseball": "baseball", "softball": "baseball",
    "boys-soccer": "soccer", "girls-soccer": "soccer",
    "boys-lacrosse": "soccer", "girls-lacrosse": "soccer",
    "field-hockey": "soccer",
    "boys-water-polo": "soccer", "girls-water-polo": "soccer",
}

#: Share of regular-season games that get a box score. Postseason is always 1.0
#: — those are the pages a bracket sends you to.
REGULAR_SHARE = 0.22

YEARS = ["9", "10", "11", "12"]

#: Adapters that mean "this record came from a real source file". Those box
#: scores are the import's, not this generator's, and are never touched.
IMPORTED = {"scorebook_csv", "dual_card", "hytek_swim", "hytek_pdf"}


def roster(school: str, sport: str, size: int = 14) -> list[tuple[str, str, int]]:
    """A stable (name, year, jersey) roster for a school in a sport.

    Keyed on the pair, so the same players appear in every one of that team's
    games and an athlete page accumulates a season rather than a single line.
    """
    rng = random.Random(zlib.crc32(f"roster:{school}:{sport}".encode()))
    out, used, numbers = [], set(), set()
    while len(out) < size:
        who = f"{rng.choice(N.LAST_NAMES)}, {rng.choice(N.FIRST_NAMES)}"
        if who in used:
            continue
        used.add(who)
        while True:
            no = rng.randint(1, 45)
            if no not in numbers:
                numbers.add(no)
                break
        out.append((who, rng.choice(YEARS), no))
    return out


def split(rng, total: int, n: int) -> list[int]:
    """`n` non-negative ints summing exactly to `total`, so a totals row that
    claims to be a sum actually is one."""
    out = [0] * n
    for _ in range(max(total, 0)):
        out[rng.randrange(n)] += 1
    return out


# ────────────────────────────────────────────────────────────────── periods


def periods_for(sport: str, home: int, away: int, rng) -> list[dict]:
    spec = PERIODS.get(sport)
    if not spec:
        return []
    label, count = spec
    hs, as_ = split(rng, home, count), split(rng, away, count)
    out = []
    for i in range(count):
        name = f"{label}{i + 1}" if label != "Inn" else str(i + 1)
        out.append({"label": name, "home": hs[i], "away": as_[i]})
    return out


# ──────────────────────────────────────────────────────────────── box scores


def _lines(rng, school, sport, family, points, n):
    """Player rows for one side, with the stat shapes that sport prints."""
    people = roster(school, sport)[:n]
    rows = []
    if family == "basketball":
        pts = split(rng, points, n)
        for i, (who, yr, no) in enumerate(people):
            three = rng.randint(0, min(3, pts[i] // 3))
            ft = rng.randint(0, min(4, max(0, pts[i] - 3 * three)))
            fg = max(0, (pts[i] - ft - 3 * three) // 2 + three)
            oreb, dreb = rng.randint(0, 3), rng.randint(0, 7)
            rows.append((who, yr, {
                "min": str(rng.randint(6, 32)),
                "fg": f"{fg}-{fg + rng.randint(1, 8)}",
                "3pt": f"{three}-{three + rng.randint(0, 4)}",
                "ft": f"{ft}-{ft + rng.randint(0, 3)}",
                # Total rebounds are the two halves added, not a third draw:
                # a box score where OREB + DREB does not equal REB is wrong in
                # a way any reader who checks will spot immediately.
                "oreb": str(oreb), "dreb": str(dreb),
                "reb": str(oreb + dreb), "ast": str(rng.randint(0, 7)),
                "stl": str(rng.randint(0, 3)), "blk": str(rng.randint(0, 2)),
                "to": str(rng.randint(0, 4)), "pf": str(rng.randint(0, 4)),
                "pts": str(pts[i]),
            }, "", i < 5))
    elif family == "volleyball":
        for i, (who, yr, no) in enumerate(people):
            k, e = rng.randint(0, 14), rng.randint(0, 5)
            ta = k + e + rng.randint(2, 14)
            rows.append((who, yr, {
                "sp": "3", "k": str(k), "e": str(e), "ta": str(ta),
                "pct": f"{(k - e) / ta:+.3f}", "ast": str(rng.randint(0, 12)),
                "dig": str(rng.randint(0, 14)), "bs": str(rng.randint(0, 2)),
                "ba": str(rng.randint(0, 3)), "sa": str(rng.randint(0, 3)),
                "se": str(rng.randint(0, 3)),
            }, "", i < 6))
    elif family == "soccer":
        goals = split(rng, points, n)
        for i, (who, yr, no) in enumerate(people):
            rows.append((who, yr, {
                "min": str(rng.randint(20, 80)), "g": str(goals[i]),
                "a": str(rng.randint(0, 2)), "sh": str(rng.randint(0, 6)),
                "sog": str(rng.randint(0, 4)), "fc": str(rng.randint(0, 3)),
                "off": str(rng.randint(0, 2)),
                "sv": str(rng.randint(2, 9)) if i == 0 else "",
            }, "", i < 11))
    elif family == "hockey":
        goals = split(rng, points, n)
        for i, (who, yr, no) in enumerate(people[:11]):
            a = rng.randint(0, 2)
            rows.append((who, yr, {
                "g": str(goals[i]), "a": str(a), "pts": str(goals[i] + a),
                "pm": f"{rng.randint(-2, 3):+d}", "pim": str(rng.randint(0, 4)),
                "sog": str(rng.randint(0, 5)), "fow": str(rng.randint(0, 6)),
            }, "SKATERS", i < 6))
        who, yr, no = people[11]
        sa = rng.randint(22, 38)
        rows.append((who, yr, {
            "min": "51:00", "sa": str(sa), "sv": str(sa - points),
            "ga": str(points), "svpct": f"{(sa - points) / sa:.3f}",
        }, "GOALTENDING", True))
    elif family == "baseball":
        runs = split(rng, points, 9)
        for i, (who, yr, no) in enumerate(people[:9]):
            h = rng.randint(0, 3)
            ab = max(h, rng.randint(2, 4))
            rows.append((who, yr, {
                "ab": str(ab), "r": str(runs[i]), "h": str(h),
                "rbi": str(rng.randint(0, 3)), "bb": str(rng.randint(0, 2)),
                "so": str(rng.randint(0, 2)), "lob": str(rng.randint(0, 4)),
                "avg": f"{h / ab:.3f}".replace("0.", "."),
            }, "BATTING", True))
        for i, (who, yr, no) in enumerate(people[9:11]):
            er = rng.randint(0, max(points, 1))
            rows.append((who, yr, {
                "ip": "4.2" if i == 0 else "2.1", "h": str(rng.randint(2, 7)),
                "r": str(er), "er": str(er), "bb": str(rng.randint(0, 4)),
                "so": str(rng.randint(1, 8)), "hr": str(rng.randint(0, 2)),
                "era": f"{rng.uniform(1.2, 4.8):.2f}",
            }, "PITCHING", i == 0))
    elif family == "football":
        for section, count in (("PASSING", 1), ("RUSHING", 3),
                               ("RECEIVING", 4), ("DEFENSE", 5)):
            for who, yr, no in roster(school, sport, 20)[:count]:
                if section == "PASSING":
                    att = rng.randint(14, 30)
                    st = {"cp": str(rng.randint(7, att)), "att": str(att),
                          "yds": str(rng.randint(90, 290)),
                          "td": str(rng.randint(0, 3)), "int": str(rng.randint(0, 2)),
                          "lg": str(rng.randint(18, 58))}
                elif section in ("RUSHING", "RECEIVING"):
                    tries = rng.randint(3, 18)
                    # Yards scale with attempts so the average is not absurd —
                    # 22 carries for 11 yards adds up and still reads as broken.
                    yds = int(tries * rng.uniform(1.8, 9.0))
                    key = "car" if section == "RUSHING" else "rec"
                    st = {key: str(tries), "yds": str(yds),
                          "avg": f"{yds / tries:.1f}", "td": str(rng.randint(0, 2)),
                          "lg": str(rng.randint(6, 44))}
                else:
                    st = {"tkl": str(rng.randint(2, 11)), "ast": str(rng.randint(0, 6)),
                          "tfl": str(rng.randint(0, 3)), "sack": str(rng.randint(0, 2)),
                          "int": str(rng.randint(0, 1)), "pd": str(rng.randint(0, 3))}
                rows.append((who, yr, st, section, True))
    return rows


def box_for(sport: str, home: str, away: str, hs: int, as_: int, rng) -> dict | None:
    family = FAMILY.get(sport)
    if not family:
        return None
    sections = COLUMNS[family]
    multi = list(sections) != [""]
    n = {"basketball": 8, "volleyball": 8, "soccer": 12,
         "hockey": 12, "baseball": 11, "football": 13}[family]

    def side(school, points):
        return _lines(rng, school, sport, family, points, n)

    def pack(rows, school):
        return [{"competitor": {"name": w, "school": school, "year": y},
                 "stats": st,
                 **({"starter": True} if starter else {}),
                 **({"section": sec} if sec else {})}
                for w, y, st, sec, starter in rows]

    hrows, arows = side(home, hs), side(away, as_)
    doc = {
        "columns": sections.get("", next(iter(sections.values()))),
        "home": pack(hrows, home), "away": pack(arows, away),
        "homeTotals": {}, "awayTotals": {},
    }
    if multi:
        doc["sections"] = {k: v for k, v in sections.items()}
    else:
        cols = sections[""]
        for key, rows in (("homeTotals", hrows), ("awayTotals", arows)):
            tot = {}
            for c in cols:
                vals = [r[2].get(c, "") for r in rows]
                try:
                    tot[c] = str(sum(int(v) for v in vals if v != ""))
                except ValueError:
                    continue          # a shooting line or a rate: not a sum
            doc[key] = tot
    return doc


# ─────────────────────────────────────────────────────────── track meets

#: The card a high-school track meet actually runs. (name, mark, low, high,
#: relay) where the band is seconds for a race and INCHES for a field event.
TRACK_EVENTS = [
    ("100 Meter Dash", "time", 10.9, 12.6, False),
    ("200 Meter Dash", "time", 22.1, 26.4, False),
    ("400 Meter Dash", "time", 49.4, 59.8, False),
    ("800 Meter Run", "time", 116.0, 142.0, False),
    ("1600 Meter Run", "time", 258.0, 320.0, False),
    ("3200 Meter Run", "time", 560.0, 700.0, False),
    ("110 Meter Hurdles", "time", 14.6, 18.4, False),
    ("300 Meter Hurdles", "time", 39.2, 48.6, False),
    ("4x100 Meter Relay", "time", 43.1, 48.9, True),
    ("4x400 Meter Relay", "time", 205.0, 232.0, True),
    ("4x800 Meter Relay", "time", 490.0, 560.0, True),
    ("Shot Put", "distance", 420.0, 660.0, False),
    ("Discus", "distance", 1200.0, 2000.0, False),
    ("Javelin", "distance", 1400.0, 2300.0, False),
    ("High Jump", "height", 60.0, 78.0, False),
    ("Long Jump", "distance", 232.0, 290.0, False),
    ("Triple Jump", "distance", 460.0, 580.0, False),
    ("Pole Vault", "height", 108.0, 174.0, False),
]

#: Girls' marks are slower and shorter; one factor per mark type beats keeping
#: a second table that will drift out of step with the first.
GIRLS_FACTOR = {"time": 1.12, "distance": 0.78, "height": 0.84}

PLACE_POINTS = [10, 8, 6, 5, 4, 3, 2, 1]


def _fmt(value: float, kind: str) -> str:
    """A mark as the sport prints it: 12.44, 2:05.44, 16-11.75, 5-04.00."""
    if kind == "time":
        if value < 60:
            return f"{value:.2f}"
        return f"{int(value // 60)}:{value % 60:05.2f}"
    feet, inches = int(value // 12), value % 12
    return f"{feet}-{inches:05.2f}" if kind == "height" else f"{feet}-{inches:.2f}"


def track_events(sport: str, schools: list[str], rng) -> list[dict]:
    """A full event card, with entries drawn from each school's own roster."""
    girls = sport.startswith("girls")
    out = []
    for number, (name, kind, lo, hi, relay) in enumerate(TRACK_EVENTS, start=1):
        if girls:
            f = GIRLS_FACTOR[kind]
            lo, hi = lo * f, hi * f
        field = []
        for school in schools:
            people = roster(school, sport, 18)
            take = 1 if relay else 2
            for who, yr, _no in rng.sample(people, min(take, len(people))):
                field.append((rng.uniform(lo, hi), school, who, yr))
        if not field:
            continue
        # A race is won by the LOW mark, a field event by the high one.
        field.sort(key=lambda t: t[0], reverse=(kind != "time"))
        entries = []
        for place, (v, school, who, yr) in enumerate(field[:12], start=1):
            if relay:
                comps = [{"name": w, "school": school, "year": y}
                         for w, y, _ in roster(school, sport, 18)[:4]]
            else:
                comps = [{"name": who, "school": school, "year": yr}]
            entries.append({
                "place": place, "school": school,
                "mark": {"raw": _fmt(v, kind), "type": kind,
                         "value": round(v, 2), "scored": True},
                "competitors": comps,
                "points": float(PLACE_POINTS[place - 1]) if place <= 8 else None,
                "heat": None, "qualifier": None, "note": None,
            })
        out.append({
            "number": number, "name": name,
            "gender": "Girls" if girls else "Boys",
            "division": None, "round": "Finals", "markType": kind,
            "entries": entries, "records": [],
        })
    return out


# ──────────────────────────────────────────────────────────────────── driver


#: Meets whose one event is correct — a cross-country race, a golf round, a
#: bowling series. Only track is expanded.
def _expand_meet(d: dict) -> bool:
    sport = d.get("sport", "")
    if "track" not in sport or len(d.get("events") or []) > 1:
        return False
    if (d.get("provenance") or {}).get("adapter") in IMPORTED:
        return False
    schools = sorted({e["school"] for ev in (d.get("events") or [])
                      for e in ev.get("entries", [])})
    if len(schools) < 2:
        schools = sorted({t["school"] for t in d.get("teamScores", [])})
    if len(schools) < 2:
        return False
    rng = random.Random(zlib.crc32(f"meet:{sport}:{d.get('date')}:{d.get('name')}".encode()))
    evs = track_events(sport, schools, rng)
    if not evs:
        return False
    d["events"] = evs
    return True


def run(records_dir: pathlib.Path, write: bool = True) -> dict:
    stats = {"games": 0, "periods": 0, "boxes": 0, "meets": 0}
    for path in sorted((records_dir / "contests").rglob("*.json")):
        try:
            d = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if d.get("$type", "").endswith(".meet"):
            if write and _expand_meet(d):
                path.write_text(json.dumps(d, separators=(",", ":")) + "\n")
                stats["meets"] += 1
            continue
        if not d.get("$type", "").endswith(".game"):
            continue
        hs, as_ = d.get("homeScore"), d.get("awayScore")
        if hs is None or as_ is None or d.get("status") != "final":
            continue
        sport = d.get("sport", "")
        stats["games"] += 1
        if (d.get("provenance") or {}).get("adapter") in IMPORTED:
            # An imported record's box score belongs to its source file.
            stats["periods"] += bool(d.get("periods"))
            stats["boxes"] += bool(d.get("box"))
            continue

        ident = f"{sport}:{d.get('date')}:{d.get('home')}:{d.get('away')}"
        # THREE independent streams, not one shared one. Sharing it made the
        # box-score decision depend on whether periods happened to be generated
        # this run, so a second run over the same records selected a different
        # set of games and the count grew every time. Same idempotency bug the
        # postseason generator had; same fix.
        rng = random.Random(zlib.crc32(f"periods:{ident}".encode()))
        pick = random.Random(zlib.crc32(f"pick:{ident}".encode()))
        brng = random.Random(zlib.crc32(f"boxof:{ident}".encode()))

        changed = False
        if not d.get("periods"):
            p = periods_for(sport, hs, as_, rng)
            if p:
                d["periods"] = p
                changed = True
        if d.get("periods"):
            stats["periods"] += 1

        postseason = "Championship" in (d.get("name") or "") or \
            (d.get("provenance") or {}).get("adapter") == "jefferson.postseason"
        wanted = postseason or pick.random() < REGULAR_SHARE
        if wanted and sport in FAMILY:
            # Rewritten, not skipped-if-present: this pass owns these boxes, and
            # skipping means a fix to the stat logic never reaches the records
            # already carrying the old version.
            b = box_for(sport, d["home"], d["away"], hs, as_, brng)
            if b and b != d.get("box"):
                d["box"] = b
                changed = True
        elif d.get("box"):
            del d["box"]                      # no longer selected: do not strand it
            changed = True
        if d.get("box"):
            stats["boxes"] += 1

        if changed and write:
            path.write_text(json.dumps(d, separators=(",", ":")) + "\n")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default=str(RECORDS))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    s = run(pathlib.Path(args.records), write=not args.check)
    g = max(s["games"], 1)
    print(f"{s['games']:,} played games")
    print(f"  period scoring: {s['periods']:,} ({s['periods']/g:.0%})")
    print(f"  box scores    : {s['boxes']:,} ({s['boxes']/g:.0%})")
    print(f"  track meets expanded: {s['meets']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
