"""
Write scorebook-CSV specimens for several sports, against real state games.

    python3 -m ingest.fixtures.make_boxscores

The point of these is not the numbers — it is that **five sports produce five
completely different column sets and the renderer is told none of them**.
Basketball prints FG/3PT/FT/REB/AST, volleyball prints K/E/TA/PCT/DIG, hockey
prints G/A/PIM/SOG and a separate goalie line, football prints three tables,
baseball prints two. Every one of those arrives as the source's own header row
and is drawn without the site knowing what any of it means.

Numbers are internally consistent — a scorebook's totals row is a checksum the
ingest layer verifies, so a fixture whose rows do not add up would land in the
review queue and prove the wrong thing. (One deliberately corrupt fixture,
``scorebook-basketball-badtotals.csv``, exists for that.)

The games are chosen from records already in the state so the import UPDATES a
real fixture rather than inventing a contest nobody scheduled.
"""

from __future__ import annotations

import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "ingest" / "fixtures" / "specimens"
RECORDS = ROOT / "records"

FIRST = ["Devin", "Rohan", "Mateo", "Fintan", "Luca", "Erik", "Karim", "Dmitri",
         "Cade", "Tobias", "Obi", "Kyle", "Felipe", "Bryce", "Long", "Anders",
         "Nnamdi", "Sven", "Julien", "Otgon", "Marek", "Ousmane", "Nils", "Santiago",
         "Elle", "Marisol", "Danae", "Priya", "Nadia", "Sunita", "Ava", "Rin",
         "Talia", "Joana", "Mira", "Zainab", "Anya", "Simone", "Tui", "Rosa"]
LAST = ["Ashworth", "Bhatt", "Castellanos", "Doyle", "Ferraro", "Gundersen",
        "Haddad", "Ivanov", "Whitlock", "Ramos", "Nkemelu", "Sandberg", "Duarte",
        "Harlow", "Pham", "Lindgren", "Achebe", "Lindqvist", "Moreau", "Batbayar",
        "Kowalski", "Diallo", "Halvorsen", "Reyes", "Okonkwo", "Vasquez",
        "Bergstrom", "Mwangi", "Escobar", "Ferreira", "Abioye", "Petrov"]


def roster(rng, n):
    names, used = [], set()
    while len(names) < n:
        who = f"{rng.choice(LAST)}, {rng.choice(FIRST)}"
        if who not in used:
            used.add(who)
            names.append(who)
    return names


def header(rows, meta, home, away, hs, aws, labels, hl, al):
    rows += [
        "# JHSAA Electronic Scorebook — Game Export v2.4",
        f"# {meta['note']}",
        "GAME,gameId,date,sport,level,venue,attendance,status",
        f"GAME,{meta['id']},{meta['date']},{meta['sport']},Varsity,"
        f"{meta['venue']},{meta['att']},Final",
        "TEAM,role,school,schoolCode,conference,final",
        f"TEAM,home,{home[0]},{home[1]},{home[2]},{hs}",
        f"TEAM,away,{away[0]},{away[1]},{away[2]},{aws}",
        "LINESCORE,teamCode," + ",".join(labels) + ",FINAL",
        f"LINESCORE,{home[1]}," + ",".join(str(x) for x in hl) + f",{hs}",
        f"LINESCORE,{away[1]}," + ",".join(str(x) for x in al) + f",{aws}",
    ]


def split(rng, total, n, lo=0):
    """n non-negative ints summing to total — so the totals row is honest."""
    if n <= 0:
        return []
    out = [lo] * n
    left = total - lo * n
    while left > 0:
        i = rng.randrange(n)
        out[i] += 1
        left -= 1
    while left < 0:
        i = rng.randrange(n)
        if out[i] > 0:
            out[i] -= 1
            left += 1
    return out


# ───────────────────────────────────────────────────────────── volleyball


def volleyball(rng, meta, home, away, sets_h, sets_a, set_scores):
    n = 8
    rows: list[str] = []
    header(rows, meta, home, away, sets_h, sets_a,
           [f"S{i+1}" for i in range(len(set_scores))],
           [s[0] for s in set_scores], [s[1] for s in set_scores])
    cols = "no,name,yr,gs,sp,k,e,ta,pct,ast,dig,bs,ba,sa,se"
    rows.append(f"PLAYER,teamCode,{cols}")
    for code, school, kills in ((home[1], home[0], 48), (away[1], away[0], 39)):
        players = roster(rng, n)
        K = split(rng, kills, n)
        E = split(rng, rng.randint(10, 18), n)
        AST = split(rng, rng.randint(38, 46), n)
        DIG = split(rng, rng.randint(45, 60), n)
        BS = split(rng, rng.randint(2, 6), n)
        BA = split(rng, rng.randint(4, 10), n)
        SA = split(rng, rng.randint(4, 9), n)
        SE = split(rng, rng.randint(5, 11), n)
        TA, tot_ta = [], 0
        for i in range(n):
            ta = K[i] + E[i] + rng.randint(2, 14)
            TA.append(ta)
            tot_ta += ta
        for i, who in enumerate(players):
            pct = (K[i] - E[i]) / TA[i] if TA[i] else 0
            rows.append(
                f"PLAYER,{code},{rng.randint(1,25)},\"{who}\",{rng.choice('9 10 11 12'.split())},"
                f"{1 if i < 6 else 0},{len(set_scores)},{K[i]},{E[i]},{TA[i]},"
                f"{pct:+.3f},{AST[i]},{DIG[i]},{BS[i]},{BA[i]},{SA[i]},{SE[i]}")
        tk, te = sum(K), sum(E)
        rows.append(
            f"TOTALS,{code},,,,,{len(set_scores)},{tk},{te},{tot_ta},"
            f"{(tk-te)/tot_ta:+.3f},{sum(AST)},{sum(DIG)},{sum(BS)},{sum(BA)},"
            f"{sum(SA)},{sum(SE)}")
    return rows


# ─────────────────────────────────────────────────────────────── hockey


def hockey(rng, meta, home, away, hs, aws, periods):
    rows: list[str] = []
    header(rows, meta, home, away, hs, aws,
           ["P1", "P2", "P3", "OT"],
           [p[0] for p in periods] + [""], [p[1] for p in periods] + [""])
    rows.append("SECTION,SKATERS")
    rows.append("PLAYER,teamCode,no,name,yr,gs,g,a,pts,pm,pim,sog,fow")
    for code, school, goals in ((home[1], home[0], hs), (away[1], away[0], aws)):
        n = 11
        players = roster(rng, n)
        G = split(rng, goals, n)
        A = split(rng, min(goals * 2, 14), n)
        PIM = split(rng, rng.randint(4, 14), n)
        SOG = split(rng, rng.randint(22, 34), n)
        FOW = split(rng, rng.randint(18, 30), n)
        for i, who in enumerate(players):
            pm = rng.randint(-2, 3)
            rows.append(
                f"PLAYER,{code},{rng.randint(2,29)},\"{who}\","
                f"{rng.choice('9 10 11 12'.split())},{1 if i < 6 else 0},"
                f"{G[i]},{A[i]},{G[i]+A[i]},{pm:+d},{PIM[i]},{SOG[i]},{FOW[i]}")
        rows.append(
            f"TOTALS,{code},,,,,{sum(G)},{sum(A)},{sum(G)+sum(A)},,{sum(PIM)},"
            f"{sum(SOG)},{sum(FOW)}")
    # A goalie's columns are not a skater's — the second table earns itself.
    rows.append("SECTION,GOALTENDING")
    rows.append("PLAYER,teamCode,no,name,yr,gs,min,sa,sv,ga,svpct")
    for code, against in ((home[1], aws), (away[1], hs)):
        sa = rng.randint(24, 36) + against
        rows.append(
            f"PLAYER,{code},{rng.randint(30,35)},\"{roster(rng,1)[0]}\","
            f"{rng.choice('10 11 12'.split())},1,51:00,{sa},{sa-against},{against},"
            f"{(sa-against)/sa:.3f}")
    return rows


# ───────────────────────────────────────────────────────────── football


def football(rng, meta, home, away, hs, aws, quarters):
    rows: list[str] = []
    header(rows, meta, home, away, hs, aws, ["Q1", "Q2", "Q3", "Q4", "OT"],
           [q[0] for q in quarters] + [""], [q[1] for q in quarters] + [""])
    for section, cols in (
        ("PASSING", "cp,att,yds,td,int,lg"),
        ("RUSHING", "car,yds,avg,td,lg"),
        ("RECEIVING", "rec,yds,avg,td,lg"),
        ("DEFENSE", "tkl,ast,tfl,sack,int,pd"),
    ):
        rows.append(f"SECTION,{section}")
        rows.append(f"PLAYER,teamCode,no,name,yr,{cols}")
        for code in (home[1], away[1]):
            n = {"PASSING": 1, "RUSHING": 3, "RECEIVING": 4, "DEFENSE": 5}[section]
            for who in roster(rng, n):
                yr = rng.choice("9 10 11 12".split())
                no = rng.randint(1, 88)
                if section == "PASSING":
                    att = rng.randint(14, 30)
                    cp = rng.randint(7, att)
                    rows.append(f"PLAYER,{code},{no},\"{who}\",{yr},{cp},{att},"
                                f"{rng.randint(90,290)},{rng.randint(0,3)},"
                                f"{rng.randint(0,2)},{rng.randint(18,58)}")
                elif section in ("RUSHING", "RECEIVING"):
                    tries = rng.randint(3, 22)
                    yds = rng.randint(8, 150)
                    rows.append(f"PLAYER,{code},{no},\"{who}\",{yr},{tries},{yds},"
                                f"{yds/tries:.1f},{rng.randint(0,2)},{rng.randint(6,44)}")
                else:
                    rows.append(f"PLAYER,{code},{no},\"{who}\",{yr},"
                                f"{rng.randint(2,11)},{rng.randint(0,6)},"
                                f"{rng.randint(0,3)},{rng.randint(0,2)},"
                                f"{rng.randint(0,1)},{rng.randint(0,3)}")
    return rows


# ───────────────────────────────────────────────────────────── baseball


def baseball(rng, meta, home, away, hs, aws, innings):
    rows: list[str] = []
    header(rows, meta, home, away, hs, aws,
           [str(i + 1) for i in range(len(innings))],
           [i[0] for i in innings], [i[1] for i in innings])
    rows.append("SECTION,BATTING")
    rows.append("PLAYER,teamCode,no,name,yr,gs,ab,r,h,rbi,bb,so,lob,avg")
    for code, runs in ((home[1], hs), (away[1], aws)):
        n = 9
        players = roster(rng, n)
        R = split(rng, runs, n)
        H = split(rng, runs + rng.randint(1, 4), n)
        RBI = split(rng, runs, n)
        BB = split(rng, rng.randint(1, 5), n)
        SO = split(rng, rng.randint(4, 10), n)
        AB, tot_ab = [], 0
        for i in range(n):
            ab = max(H[i], rng.randint(2, 4))
            AB.append(ab)
            tot_ab += ab
        for i, who in enumerate(players):
            rows.append(
                f"PLAYER,{code},{rng.randint(1,45)},\"{who}\","
                f"{rng.choice('9 10 11 12'.split())},1,{AB[i]},{R[i]},{H[i]},"
                f"{RBI[i]},{BB[i]},{SO[i]},{rng.randint(0,4)},"
                f"{H[i]/AB[i]:.3f}".replace("0.", "."))
        rows.append(
            f"TOTALS,{code},,,,,{tot_ab},{sum(R)},{sum(H)},{sum(RBI)},{sum(BB)},"
            f"{sum(SO)},,{sum(H)/tot_ab:.3f}".replace("0.", "."))
    rows.append("SECTION,PITCHING")
    rows.append("PLAYER,teamCode,no,name,yr,gs,ip,h,r,er,bb,so,hr,era")
    for code, allowed in ((home[1], aws), (away[1], hs)):
        for i, who in enumerate(roster(rng, 2)):
            ip = "4.2" if i else "2.1"
            er = split(rng, allowed, 2)[i]
            rows.append(
                f"PLAYER,{code},{rng.randint(1,45)},\"{who}\","
                f"{rng.choice('10 11 12'.split())},{1 if i == 0 else 0},{ip},"
                f"{rng.randint(2,7)},{er},{er},{rng.randint(0,4)},"
                f"{rng.randint(1,8)},{rng.randint(0,2)},{rng.uniform(1.2,4.8):.2f}")
    return rows


# ──────────────────────────────────────────────────────────────── driver

SPECS = [
    ("girls-volleyball", "scorebook-volleyball-boxscore.csv", volleyball,
     dict(sets=[(25, 19), (25, 22), (25, 20)])),
    ("boys-ice-hockey", "scorebook-hockey-boxscore.csv", hockey,
     dict(periods=[(2, 0), (1, 0), (2, 0)])),
    ("football", "scorebook-football-boxscore.csv", football,
     dict(quarters=[(7, 3), (6, 7), (0, 3), (7, 3)])),
    ("baseball", "scorebook-baseball-boxscore.csv", baseball,
     dict(innings=[(0, 1), (2, 0), (0, 0), (1, 2), (0, 0), (3, 0), (0, 1)])),
]

VENUES = {"girls-volleyball": "Main Gymnasium", "boys-ice-hockey": "Community Ice Arena",
          "football": "Memorial Field", "baseball": "Legion Park"}


def pick_game(sport):
    """A real game in this sport, so an import UPDATES rather than invents.

    Returns ``(record, played)``. Spring sports have no played game at the demo
    date of 2027-01-16 — baseball's season has not started — so those fixtures
    are written as **parse-only specimens**: the format and its columns are
    demonstrated by ``ingest.run --demo`` without stamping a April result onto
    a January state. Inventing the game would be the easy option and would put
    a played contest in the site's future.
    """
    fallback = None
    for path in sorted((RECORDS / "contests").rglob(f"*/{sport}/*.json")):
        d = json.loads(path.read_text())
        if d.get("box"):
            continue
        if d.get("homeScore") is not None:
            return d, True
        fallback = fallback or d
    return fallback, False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for sport, filename, fn, kw in SPECS:
        g, played = pick_game(sport)
        if g is None:
            print(f"{sport}: no game to attach to")
            continue
        rng = random.Random(f"{sport}:{g['date']}:{g['home']}")
        splits = next(iter(kw.values()))
        hs = sum(s[0] for s in splits)
        aws = sum(s[1] for s in splits)
        if sport == "girls-volleyball":
            hs, aws = sum(1 for a, b in splits if a > b), sum(1 for a, b in splits if b > a)
        meta = {
            "id": f"JHSAA-{sport[:3].upper()}-{g['date'].replace('-','')}",
            "date": g["date"], "sport": sport.replace("-", " ").title(),
            "venue": f"{g['home']} {VENUES[sport]}",
            "att": rng.randint(180, 2400),
            "note": (f"Generated for {g['away']} at {g['home']}"
                     + ("" if played else
                        "  — PARSE-ONLY: this sport's season has not started at the "
                        "demo date, so the record is not imported")),
        }
        code = lambda s: "".join(w[0] for w in s.split()[:3]).upper()  # noqa: E731
        rows = fn(rng, meta,
                  (g["home"], code(g["home"]), "—"),
                  (g["away"], code(g["away"]), "—"),
                  hs, aws, splits)
        (OUT / filename).write_text("\n".join(rows) + "\n")
        tag = "" if played else "   [parse-only: season not started]"
        print(f"{filename:42} {g['away']} {aws} at {g['home']} {hs}  ({g['date']}){tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
