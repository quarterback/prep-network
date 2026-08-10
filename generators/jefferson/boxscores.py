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

Like the mascot pass, this is keyed on the record's own identity and never
touches the state generator's RNG, so it cannot move a result.

**Meets are not this module's business.** They were, briefly: track meets came
out of the state generator with one event, so this pass rewrote the card. That
left the team scores behind — they had been derived from the single event this
pass then deleted, so every track meet in the state published eighteen events
and a team score computed from a race that no longer appeared on the page. A
meet's events and its team score are one derivation and belong to one owner,
which is ``gen.make_meet``.
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

from app.sports import BY_KEY                   # noqa: E402
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
    "boys-rugby": ("H", 2), "girls-rugby": ("H", 2),
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
    "rugby": {
        "SCORING": "t c p dg pts".split(),
        "PLAY": "min car m tkl mt to".split(),
    },
    # Cricket prints FOUR tables, not one: each innings has a batting card and
    # a bowling card, and the bowling card belongs to the OTHER side. This is
    # the case the section mechanism was built for — the renderer draws one
    # table per named section without knowing what an over is.
    "cricket": {
        "1ST INNINGS — BATTING": "r b 4s 6s sr out".split(),
        "1ST INNINGS — BOWLING": "o m r w wd nb econ".split(),
        "2ND INNINGS — BATTING": "r b 4s 6s sr out".split(),
        "2ND INNINGS — BOWLING": "o m r w wd nb econ".split(),
    },
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
    "boys-rugby": "rugby", "girls-rugby": "rugby",
    "cricket": "cricket",
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

    Given names follow the sport's gender, the same rule the state generator's
    pools follow. A shared name list put Vera and Imogen on a football roster
    and Rafael on a softball one, which is the first thing a reader notices and
    the last thing they forgive.
    """
    gender = BY_KEY[sport].gender if sport in BY_KEY else "Coed"
    firsts = {"Boys": N.BOYS_FIRST + N.UNISEX_FIRST,
              "Girls": N.GIRLS_FIRST + N.UNISEX_FIRST}.get(gender, N.FIRST_NAMES)
    rng = random.Random(zlib.crc32(f"roster:{school}:{sport}".encode()))
    out, used, numbers = [], set(), set()
    while len(out) < size:
        who = f"{rng.choice(firsts)} {rng.choice(N.LAST_NAMES)}"
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
    elif family == "rugby":
        # Sevens: seven on the field, a couple off the bench. Points are the
        # tries and conversions added, so the column agrees with the scoreline.
        # Solve the scoreline back into tries, conversions and a penalty, so
        # the SCORING column sums to the score on the page. A box score whose
        # points do not add to the final is the one mistake this pass exists
        # to avoid making at scale.
        nt = nc = npen = 0
        for pen in (0, 1):
            rem0 = points - 3 * pen
            for tr in range(rem0 // 5, -1, -1):
                rem = rem0 - 5 * tr
                if rem >= 0 and rem % 2 == 0 and rem // 2 <= tr:
                    nt, nc, npen = tr, rem // 2, pen
                    break
            if nt or points == 3 * pen:
                break
        tries = split(rng, nt, n)
        convs = split(rng, nc, 1) and [nc] + [0] * (n - 1)   # one kicker
        pens = [npen] + [0] * (n - 1)
        for i, (who, yr, no) in enumerate(people):
            c, pn = convs[i], pens[i]
            rows.append((who, yr, {
                "t": str(tries[i]), "c": str(c), "p": str(pn), "dg": "0",
                "pts": str(tries[i] * 5 + c * 2 + pn * 3),
            }, "SCORING", i < 7))
        for i, (who, yr, no) in enumerate(people):
            car = rng.randint(2, 14)
            rows.append((who, yr, {
                "min": str(rng.randint(7, 14)), "car": str(car),
                "m": str(int(car * rng.uniform(1.5, 8.0))),
                "tkl": str(rng.randint(0, 9)), "mt": str(rng.randint(0, 3)),
                "to": str(rng.randint(0, 2)),
            }, "PLAY", i < 7))
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


#: How a batter got out, and how often. "not out" is not a dismissal.
DISMISSALS = ["b", "c", "lbw", "run out", "st", "c & b", "not out"]
DISMISS_W = [22, 34, 14, 9, 6, 5, 10]


def _innings(rng, batting: str, bowling: str, runs: int, label: str):
    """One innings: a batting card that adds up, and the bowling that caused it.

    The two cards are the same ten overs seen from opposite ends, so they have
    to agree — the bowlers' runs conceded sum to the innings total and their
    wickets sum to the wickets that fell. A box score whose two halves
    contradict each other is the exact thing this project's review queue
    exists to catch, and it would be inexcusable to generate one.
    """
    wickets = min(9, max(0, int(rng.gauss(5.4, 2.1))))
    bat = roster(batting, "cricket", 11)
    bowl = roster(bowling, "cricket", 11)[5:10]        # five bowlers, ten overs

    # runs across the order, weighted to the top; extras take a few
    extras = rng.randint(2, 11)
    made = split(rng, max(runs - extras, 0), 8)
    made.sort(reverse=True)
    rng.shuffle(made[3:])
    rows, out_count = [], 0
    for i, (who, yr, _no) in enumerate(bat[:8]):
        r = made[i]
        balls = max(1, int(r / rng.uniform(0.9, 2.1)) + rng.randint(0, 5))
        fours = min(r // 4, rng.randint(0, 6))
        sixes = min((r - fours * 4) // 6, rng.randint(0, 3))
        if out_count < wickets and (i < wickets or rng.random() < 0.5):
            how = rng.choices(DISMISSALS[:-1], DISMISS_W[:-1])[0]
            out_count += 1
        else:
            how = "not out"
        rows.append((who, yr, {
            "r": str(r), "b": str(balls), "4s": str(fours), "6s": str(sixes),
            "sr": f"{r / balls * 100:.1f}", "out": how,
        }, f"{label} — BATTING", i < 3))

    # the bowling card has to reconcile: conceded == runs, wickets == out_count
    conceded = split(rng, runs, len(bowl))
    got = split(rng, out_count, len(bowl))
    overs = [2] * len(bowl)
    for i, (who, yr, _no) in enumerate(bowl):
        rows.append((who, yr, {
            "o": f"{overs[i]}.0", "m": str(1 if rng.random() < 0.12 else 0),
            "r": str(conceded[i]), "w": str(got[i]),
            "wd": str(rng.randint(0, 3)), "nb": str(rng.randint(0, 1)),
            "econ": f"{conceded[i] / overs[i]:.2f}",
        }, f"{label} — BOWLING", True))
    return rows, wickets, out_count


def cricket_result(home: str, away: str, hs: int, as_: int, hw: int, aw: int,
                   first: str, rng) -> str:
    """The result in cricket's own words.

    "104 to 92" is not a cricket result. The side batting first DEFENDS a
    total and wins BY RUNS; the side chasing wins BY WICKETS, with the balls
    it had left. Same two numbers, two different sentences, and the reader who
    gets only the numbers has not been told what happened.
    """
    if hs == as_:
        return f"Match tied. {rng.choice([home, away])} won the Super Over."
    winner = home if hs > as_ else away
    if winner == first:
        # defended a total: the margin is in RUNS
        return f"{winner} won by {abs(hs - as_)} runs"
    # chased it down: the margin is in WICKETS IN HAND, plus what was left
    wk = hw if winner == home else aw
    left = max(1, 10 - wk)
    balls = rng.randint(1, 17)
    return (f"{winner} won by {left} wicket{'s' if left != 1 else ''} "
            f"with {balls} ball{'s' if balls != 1 else ''} remaining")


def box_for(sport: str, home: str, away: str, hs: int, as_: int, rng) -> dict | None:
    family = FAMILY.get(sport)
    if not family:
        return None
    sections = COLUMNS[family]
    multi = list(sections) != [""]
    n = {"basketball": 8, "volleyball": 8, "soccer": 12, "hockey": 12,
         "baseball": 11, "football": 13, "rugby": 9, "cricket": 11}[family]

    def side(school, points):
        return _lines(rng, school, sport, family, points, n)

    def pack(rows, school):
        return [{"competitor": {"name": w, "school": school, "year": y},
                 "stats": st,
                 **({"starter": True} if starter else {}),
                 **({"section": sec} if sec else {})}
                for w, y, st, sec, starter in rows]

    if family == "cricket":
        # Cricket does not have two symmetrical sides. It has two INNINGS, and
        # in each one a side bats while the other bowls — so the rows are
        # built per innings, not per team, and the batting card of the first
        # innings sits opposite the bowling card of the same ten overs.
        first, second = (home, away) if rng.random() < 0.55 else (away, home)
        fr, sr = (hs, as_) if first == home else (as_, hs)
        rows1, w1, _o1 = _innings(rng, first, second, fr, "1ST INNINGS")
        rows2, w2, _o2 = _innings(rng, second, first, sr, "2ND INNINGS")
        by_team = {home: [], away: []}
        for rows, batting, bowling in ((rows1, first, second), (rows2, second, first)):
            for r in rows:
                by_team["BOWLING" in r[3] and bowling or batting].append(r)
        doc = {
            "columns": sections["1ST INNINGS — BATTING"],
            "home": pack(by_team[home], home), "away": pack(by_team[away], away),
            "homeTotals": {}, "awayTotals": {},
            "sections": {k: v for k, v in sections.items()},
        }
        hw, aw = (w1, w2) if first == home else (w2, w1)
        doc["_result"] = cricket_result(home, away, hs, as_, hw, aw, first, rng)
        doc["_wickets"] = {"home": hw, "away": aw}
        return doc

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


# ──────────────────────────────────────────────────────────────────── driver


def run(records_dir: pathlib.Path, write: bool = True) -> dict:
    stats = {"games": 0, "periods": 0, "boxes": 0}
    for path in sorted((records_dir / "contests").rglob("*.json")):
        try:
            d = json.loads(path.read_text())
        except (OSError, ValueError):
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
            if b:
                # `_result` and `_wickets` are the box telling the RECORD
                # something about itself; they are not columns and must not
                # reach the stored box score.
                res = b.pop("_result", None)
                wk = b.pop("_wickets", None)
                if res and d.get("result") != res:
                    d["result"] = res
                    changed = True
                if wk:
                    d["homeWickets"], d["awayWickets"] = wk["home"], wk["away"]
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
