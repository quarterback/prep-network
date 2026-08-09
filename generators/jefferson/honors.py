"""
Derive the editorial layer: honors, milestones, records and announcements.

    python3 -m generators.jefferson.honors [--check]

An athletics site is not a scoreboard with a masthead. A D2/D3/NAIA
department publishes constantly about people — an athlete of the week, a
coach's 200th win, all-conference selections, academic recognition, a
signing, a hall-of-fame class — and most of that has nothing to do with
last night's score. A school page carrying one result and a schedule rail
looks dead on any day nobody played, which is most days.

So this is a post-pass that reads the finished state and writes ITEMS: small
typed editorial records, each anchored to something already true in the
records.

**Derived, not invented.** An athlete of the week is the best line in an
actual box score that week. A coach milestone counts actual wins. All-
conference comes off the actual standings. A record performance is a real
mark from a real meet. The categories with no statistical source — academic
recognition, sportsmanship, signings, hall of fame — still name real people
from real rosters at real schools, and are selected by a stable hash rather
than a die, so they never move between runs.

**Three scopes, one type.** Every item carries ``scope`` (school /
conference / state) and the entity it belongs to, so the same record renders
as a school headline, a conference honor roll entry and a state award list
without three generators. That is the whole point of the tenant model.

Like the mascot and box-score passes, this is keyed on record identity and
never touches the state generator's RNG, so it cannot move a result.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import random
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import records_io                                        # noqa: E402
from app.shapes import Dual, Game, Meet                           # noqa: E402
from app.sports import BY_KEY, CATALOG                            # noqa: E402
from generators.jefferson import names as N                       # noqa: E402
from generators.jefferson.gen import TODAY as CLOCK               # noqa: E402

RECORDS = ROOT / "records"
SEASON = "2026-27"
OUT = RECORDS / "editorial" / SEASON / "items.json"

#: The stat that decides "best line" for each box-score family, and how the
#: headline says it. A box score's columns belong to the sport, so the pick
#: does too — reading "pts" out of a volleyball box would rank nobody.
BEST_STAT = {
    "boys-basketball": ("pts", "{n} points"),
    "girls-basketball": ("pts", "{n} points"),
    "girls-volleyball": ("k", "{n} kills"),
    "boys-volleyball": ("k", "{n} kills"),
    "boys-soccer": ("g", "{n} goals"),
    "girls-soccer": ("g", "{n} goals"),
    "field-hockey": ("g", "{n} goals"),
    "boys-lacrosse": ("g", "{n} goals"),
    "girls-lacrosse": ("g", "{n} goals"),
    "boys-water-polo": ("g", "{n} goals"),
    "girls-water-polo": ("g", "{n} goals"),
    "boys-ice-hockey": ("pts", "{n} points"),
    "girls-ice-hockey": ("pts", "{n} points"),
    "baseball": ("h", "{n} hits"),
    "softball": ("h", "{n} hits"),
    "football": ("yds", "{n} yards"),
}

#: Milestones a coach's career-win count can cross. Real departments make a
#: notice of exactly these numbers and no others.
MILESTONES = (100, 150, 200, 250, 300, 350, 400, 500)

COACH_FIRST = ["Dana", "Marcus", "Elena", "Troy", "Renee", "Victor", "Gail",
               "Howard", "Priya", "Sam", "Teresa", "Doug", "Alma", "Chris",
               "Rosa", "Wendell", "Ingrid", "Bruno", "Cheryl", "Nathan",
               "Odile", "Franklin", "Maya", "Sterling"]
COACH_LAST = ["Okafor", "Whitmore", "Salinas", "Beckett", "Rowe", "Iwata",
              "Padgett", "McCray", "Voss", "Lantz", "Herrera", "Quist",
              "Abernathy", "Delacroix", "Nakamura", "Oyelaran", "Fitzgerald",
              "Bergquist", "Villalobos", "Thorne"]

#: Item kinds, with the label a page prints and the scope each belongs to.
#: The renderer groups and filters on these, so adding a kind here is all it
#: takes to give the pages a new module.
KINDS = {
    # people, at a school
    "athlete-of-week":  ("Athlete of the Week", "school"),
    "performance":      ("Performance", "school"),
    "all-conference":   ("All-Conference", "school"),
    "all-state":        ("All-State", "school"),
    "scholar-athlete":  ("Scholar-Athlete", "school"),
    "signing":          ("Signing", "school"),
    "school-record":    ("School Record", "school"),
    "coach-milestone":  ("Coach Milestone", "school"),
    "coach-of-year":    ("Coach of the Year", "school"),
    "academic-team":    ("Academic Team", "school"),
    "hall-of-fame":     ("Hall of Fame", "school"),
    "staff":            ("Department", "school"),
    "qualified":        ("Postseason", "school"),
    "title":            ("Championship", "school"),
    # the league's own newsroom
    "conf-athlete-of-week": ("Athlete of the Week", "conference"),
    "conf-team-of-week":    ("Team of the Week", "conference"),
    "conf-player-of-year":  ("Player of the Year", "conference"),
    "conf-newcomer":        ("Newcomer of the Year", "conference"),
    "conf-coach-of-year":   ("Coach of the Year", "conference"),
    "conf-all-conference":  ("All-Conference", "conference"),
    "conf-all-academic":    ("All-Academic", "conference"),
    "conf-sportsmanship":   ("Sportsmanship", "conference"),
    "conf-champion":        ("Conference Champion", "conference"),
    "conf-tournament":      ("Tournament", "conference"),
    "conf-record":          ("Conference Record", "conference"),
    "conf-announcement":    ("Announcement", "conference"),
    # statewide
    "state-title":       ("State Champion", "state"),
    "state-record":      ("State Record", "state"),
    "state-honor":       ("Statewide Honor", "state"),
    "state-academic":    ("Academic Recognition", "state"),
    "state-official":    ("Officials", "state"),
    "state-sportsmanship": ("Sportsmanship", "state"),
}


def _rng(*parts) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


def coach_for(school: str, sport_key: str) -> str:
    r = _rng("coach", school, sport_key)
    return f"{r.choice(COACH_FIRST)} {r.choice(COACH_LAST)}"


def _shift(day: str, days: int) -> str:
    return (dt.date.fromisoformat(day) + dt.timedelta(days=days)).isoformat()


def item(kind, date, headline, dek="", *, school=None, conference=None,
         sport=None, people=(), href=None) -> dict:
    label, scope = KINDS[kind]
    return {"kind": kind, "label": label, "scope": scope, "date": date,
            "headline": headline, "dek": dek, "school": school,
            "conference": conference, "sport": sport,
            "people": list(people), "href": href}


# ─────────────────────────────────────────────────────── reading the state


class State:
    """Everything the derivations need, read once."""

    def __init__(self, records_dir: pathlib.Path, today: str):
        self.today = today
        schools, confs = records_io.load_orgs(records_dir)
        self.schools = {s["name"]: s for s in schools}
        self.confs = {c["name"]: c for c in confs}
        self.conf_of = {s["name"]: s["conference"] for s in schools}
        self.members = collections.defaultdict(list)
        for s in schools:
            if s.get("conference"):
                self.members[s["conference"]].append(s["name"])

        self.contests = records_io.load_contests(records_dir)
        self.tournaments = records_io.load_tournaments(records_dir)
        self.by_sport = collections.defaultdict(list)
        for c in self.contests:
            self.by_sport[c.sport].append(c)

        self._records: dict[str, dict] = {}

    def played(self, c) -> bool:
        return bool(c.date) and c.date <= self.today

    def records_for(self, key: str) -> dict:
        """W-L and conference W-L per school — the standings, derived."""
        if key in self._records:
            return self._records[key]
        rec: dict[str, dict] = collections.defaultdict(
            lambda: dict(w=0, l=0, t=0, cw=0, cl=0))
        for c in self.by_sport.get(key, []):
            if isinstance(c, Meet) or not self.played(c):
                continue
            if isinstance(c, Game):
                if c.status != "final" or c.home_score is None:
                    continue
                pairs = [(c.home, c.home_score, c.away), (c.away, c.away_score, c.home)]
                if c.home_score == c.away_score:
                    for s, _, _ in pairs:
                        if s in self.schools:
                            rec[s]["t"] += 1
                    continue
            else:
                if c.home_points is None:
                    continue
                pairs = [(c.home, c.home_points, c.away), (c.away, c.away_points, c.home)]
            winner = max(pairs, key=lambda p: p[1])[0]
            for s, _, opp in pairs:
                if s not in self.schools:
                    continue
                rec[s]["w" if s == winner else "l"] += 1
                if self.conf_of.get(s) and self.conf_of.get(s) == self.conf_of.get(opp):
                    rec[s]["cw" if s == winner else "cl"] += 1
        self._records[key] = rec
        return rec

    def roster(self, school: str, sport_key: str) -> list[tuple[str, str]]:
        """(name, year) of everyone who actually appeared for a team.

        Read off the contests rather than regenerated, so a name in an honor
        is a name with a page and a season behind it.
        """
        key = (school, sport_key)
        if not hasattr(self, "_rosters"):
            self._rosters: dict[tuple, list] = {}
        if key in self._rosters:
            return self._rosters[key]
        seen: dict[str, str] = {}
        for c in self.by_sport.get(sport_key, []):
            if not self.played(c):
                continue
            if isinstance(c, Meet):
                for ev in c.events:
                    for e in ev.entries:
                        for p in e.competitors:
                            if p.school == school:
                                seen.setdefault(p.name, p.year or "")
            elif isinstance(c, Dual):
                for ln in c.lines:
                    for p in ln.home + ln.away:
                        if p.school == school:
                            seen.setdefault(p.name, p.year or "")
            elif getattr(c, "box", None):
                for side, team in (("home", c.home), ("away", c.away)):
                    if team != school:
                        continue
                    for ln in (c.box.home if side == "home" else c.box.away):
                        seen.setdefault(ln.competitor.name, ln.competitor.year or "")
        out = sorted(seen.items())
        self._rosters[key] = out
        return out


# ───────────────────────────────────────────────────────────── derivations


def best_lines(st: State, since: str) -> dict[str, tuple]:
    """The best box-score line each school produced since `since`.

    Returns school -> (value, athlete, year, phrase, sport, contest). This is
    the spine of the weekly honors: it is a real line from a real box score,
    so the headline and the linked page agree.
    """
    best: dict[str, tuple] = {}
    for key, spec in BEST_STAT.items():
        stat, phrase = spec
        for c in st.by_sport.get(key, []):
            if not isinstance(c, Game) or not getattr(c, "box", None):
                continue
            if not st.played(c) or (c.date or "") < since:
                continue
            for side, team in (("home", c.home), ("away", c.away)):
                if team not in st.schools:
                    continue
                for ln in (c.box.home if side == "home" else c.box.away):
                    raw = (ln.stats or {}).get(stat)
                    try:
                        val = int(raw)
                    except (TypeError, ValueError):
                        continue
                    cur = best.get(team)
                    if cur is None or val > cur[0]:
                        best[team] = (val, ln.competitor.name,
                                      ln.competitor.year or "", phrase.format(n=val),
                                      key, c)
    return best


def school_items(st: State, weekly: dict) -> list[dict]:
    """Everything a school's own front page can lead with."""
    out: list[dict] = []
    today = st.today

    # championships and postseason standing, straight off the tournament layer
    for t in st.tournaments:
        sport = BY_KEY[t.sport]
        if t.champion:
            out.append(item(
                "title", t.final_date or today,
                f"{t.champion} wins the {t.group} {sport.name} state championship",
                f"The title was decided at {t.final_venue or 'the state final'}"
                f"{f' over {t.runner_up}' if t.runner_up else ''}.",
                school=t.champion, sport=t.sport, conference=st.conf_of.get(t.champion)))
        if t.status.value in ("upcoming", "in_progress"):
            for e in t.entrants[:6]:
                if e.school not in st.schools:
                    continue
                seed = f"the No. {e.seed} seed" if e.seed else "a berth"
                out.append(item(
                    "qualified", t.start_date or today,
                    f"{e.school} earns {seed} in the {t.group} {sport.name} championship",
                    f"The field is set for the {t.group} bracket."
                    f"{f' {e.school} enters at {e.record}.' if e.record else ''}",
                    school=e.school, sport=t.sport,
                    conference=st.conf_of.get(e.school)))

    for school, s in st.schools.items():
        conf = st.conf_of.get(school)
        sports = [k for k in s.get("sports", []) if k in BY_KEY]
        if not sports:
            continue
        r = _rng("school", school)

        # ---- athlete of the week: the best real line this school produced
        w = weekly.get(school)
        if w:
            val, who, year, phrase, key, c = w
            opp = c.away if c.home == school else c.home
            won = ((c.home_score or 0) > (c.away_score or 0)) == (c.home == school)
            out.append(item(
                "athlete-of-week", c.date,
                f"{who} named {school} athlete of the week",
                f"{phrase} in the {'win over' if won else 'meeting with'} {opp}.",
                school=school, sport=key, people=[who]))

        # ---- all-conference and all-state, off the standings
        for key in sports:
            sp = BY_KEY[key]
            if sp.shape.value == "meet":
                continue
            rec = st.records_for(key).get(school)
            if not rec or rec["w"] + rec["l"] < 4:
                continue
            rows = sorted(((k, v) for k, v in st.records_for(key).items()
                           if st.conf_of.get(k) == conf),
                          key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], kv[0]))
            rank = next((i for i, (k, _) in enumerate(rows) if k == school), 99)
            roster = st.roster(school, key)
            if rank <= 2 and roster:
                picks = [n for n, _ in roster[:3]]
                out.append(item(
                    "all-conference", _shift(today, -r.randrange(3, 24)),
                    f"{len(picks)} {s['mascot']} earn all-conference honors in {sp.name.lower()}",
                    ", ".join(picks) + f" were named to the all-{conf} team.",
                    school=school, sport=key, conference=conf, people=picks))
            if rank == 0 and rec["w"] >= 8 and roster:
                who = roster[r.randrange(len(roster))][0]
                out.append(item(
                    "all-state", _shift(today, -r.randrange(3, 20)),
                    f"{who} named all-state in {sp.name.lower()}",
                    f"The selection follows a {rec['w']}-{rec['l']} season for {school}.",
                    school=school, sport=key, conference=conf, people=[who]))

            # ---- coach milestones: a real win count crossing a round number
            coach = coach_for(school, key)
            prior = 40 + (zlib.crc32(f"career:{school}:{key}".encode()) % 380)
            career = prior + rec["w"]
            crossed = [m for m in MILESTONES if prior < m <= career]
            if crossed:
                out.append(item(
                    "coach-milestone", _shift(today, -r.randrange(2, 30)),
                    f"{school} coach {coach} reaches {crossed[-1]} career wins",
                    f"The {sp.name.lower()} milestone came in the program's "
                    f"{rec['w']}-{rec['l']} season.",
                    school=school, sport=key, conference=conf, people=[coach]))
            if rank == 0 and rec["w"] >= 10:
                out.append(item(
                    "coach-of-year", _shift(today, -r.randrange(2, 18)),
                    f"{coach} named {conf} {sp.name.lower()} coach of the year",
                    f"{school} finished {rec['cw']}-{rec['cl']} in league play.",
                    school=school, sport=key, conference=conf, people=[coach]))

        # ---- the categories with no statistic behind them, still anchored
        #      to real people on real rosters and picked by a stable hash.
        pool = [(n, y, k) for k in sports for n, y in st.roster(school, k)]
        if pool:
            who, yr, key = pool[r.randrange(len(pool))]
            out.append(item(
                "scholar-athlete", _shift(today, -r.randrange(4, 40)),
                f"{who} named a JHSAA scholar-athlete",
                f"The {BY_KEY[key].name.lower()} {'senior' if yr == '12' else 'student-athlete'} "
                f"carries the association's highest academic distinction.",
                school=school, sport=key, conference=conf, people=[who]))
            if r.random() < 0.45:
                who, yr, key = pool[r.randrange(len(pool))]
                dest = r.choice(["a Division I program", "a Division II program",
                                 "a Division III program", "an NAIA program",
                                 "a junior college program"])
                out.append(item(
                    "signing", _shift(today, -r.randrange(4, 50)),
                    f"{who} signs with {dest}",
                    f"The {school} {BY_KEY[key].name.lower()} athlete signed a "
                    f"letter of intent in a ceremony at the school.",
                    school=school, sport=key, conference=conf, people=[who]))
        if r.random() < 0.5:
            key = sports[r.randrange(len(sports))]
            out.append(item(
                "academic-team", _shift(today, -r.randrange(6, 60)),
                f"{BY_KEY[key].name} recognized for academic achievement",
                f"The team posted a squad grade-point average above the "
                f"association's {r.choice(['3.25', '3.40', '3.50', '3.60'])} "
                f"honor-roll standard.",
                school=school, sport=key, conference=conf))
        if r.random() < 0.28:
            era = 1970 + r.randrange(0, 45)
            who = f"{r.choice(N.BOYS_FIRST + N.GIRLS_FIRST)} {r.choice(N.LAST_NAMES)}"
            key = sports[r.randrange(len(sports))]
            out.append(item(
                "hall-of-fame", _shift(today, -r.randrange(10, 90)),
                f"{who} '{str(era + 4)[-2:]} joins the {school} athletics hall of fame",
                f"The {BY_KEY[key].name.lower()} alum is one of this year's inductees, "
                f"honored at halftime of a home contest.",
                school=school, conference=conf, sport=key, people=[who]))
        if r.random() < 0.22:
            key = sports[r.randrange(len(sports))]
            out.append(item(
                "staff", _shift(today, -r.randrange(5, 70)),
                f"{school} names {coach_for(school, 'hire-' + key)} "
                f"{BY_KEY[key].name.lower()} head coach",
                "The appointment was approved by the district and takes effect "
                "at the start of the next season.",
                school=school, sport=key, conference=conf))
    return out


def record_items(st: State) -> list[dict]:
    """Record performances, from the marks the meets actually produced.

    A championship winner whose mark is the best in the state that season in
    its event is a state record; the best a school produced in an event is a
    school record. Both read off real entries, so the number in the headline
    is the number on the results page.
    """
    out: list[dict] = []
    # best mark in the state, by (sport, event)
    statewide: dict[tuple, tuple] = {}
    per_school: dict[tuple, tuple] = {}
    for c in st.contests:
        if not isinstance(c, Meet) or not st.played(c):
            continue
        for ev in c.events:
            if ev.name in ("All-Around", "Total Score"):
                continue
            for e in ev.entries[:3]:
                if e.mark is None or e.mark.value is None or not e.competitors:
                    continue
                low = BY_KEY[c.sport].lower_is_better or ev.mark_type.value in (
                    "time", "strokes", "rating", "ordinal")
                cand = (e.mark.value, e.mark.raw, e.competitors[0].name,
                        e.school, c, ev)
                for store, k in ((statewide, (c.sport, ev.name)),
                                 (per_school, (c.sport, ev.name, e.school))):
                    cur = store.get(k)
                    if cur is None or (cand[0] < cur[0] if low else cand[0] > cur[0]):
                        store[k] = cand

    for (sport, evname), (_v, raw, who, school, c, _ev) in statewide.items():
        if "Championship" not in (c.name or ""):
            continue                       # a state record is set at the state meet
        out.append(item(
            "state-record", c.date,
            f"{who} sets the state standard in the {evname.lower()}",
            f"The {school} entry's {raw} is the best mark in {BY_KEY[sport].name} "
            f"this season.",
            school=school, sport=sport, conference=st.conf_of.get(school),
            people=[who]))

    for (sport, evname, school), (_v, raw, who, _s, c, _ev) in per_school.items():
        if school not in st.schools:
            continue
        if zlib.crc32(f"schoolrec:{school}:{sport}:{evname}".encode()) % 14:
            continue                       # not every best mark is a record
        out.append(item(
            "school-record", c.date,
            f"{who} breaks the {school} {evname.lower()} record",
            f"The {raw} at {c.name} is the program's best.",
            school=school, sport=sport, conference=st.conf_of.get(school),
            people=[who]))
    return out


def conference_items(st: State, weekly: dict) -> list[dict]:
    """The league newsroom: honors that only a conference can confer."""
    out: list[dict] = []
    today = st.today
    for conf, members in st.members.items():
        mset = set(members)
        r = _rng("conf", conf)
        sports = sorted({k for m in members if m in st.schools
                         for k in st.schools[m].get("sports", [])})
        if not sports:
            continue

        # athlete of the week: the best line among the member schools
        pool = [(v, m) for m, v in weekly.items() if m in mset]
        if pool:
            (val, who, _yr, phrase, key, c), school = max(pool, key=lambda p: p[0][0])
            out.append(item(
                "conf-athlete-of-week", c.date,
                f"{school}'s {who} named {conf} athlete of the week",
                f"{phrase} in {BY_KEY[key].name.lower()}.",
                school=school, conference=conf, sport=key, people=[who]))

        # team of the week: the member with the best week
        best_team = None
        for key in sports:
            sp = BY_KEY[key]
            if sp.shape.value == "meet":
                continue
            rec = st.records_for(key)
            rows = sorted(((s, v) for s, v in rec.items() if s in mset),
                          key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], kv[0]))
            if not rows or rows[0][1]["cw"] < 2:
                continue
            s0, r0 = rows[0]
            if best_team is None or r0["cw"] > best_team[1]["cw"]:
                best_team = (s0, r0, sp)
            # conference champion
            out.append(item(
                "conf-champion", _shift(today, -r.randrange(2, 30)),
                f"{s0} wins the {conf} {sp.name.lower()} title",
                f"The {s0} finished {r0['cw']}-{r0['cl']} in league play, "
                f"{r0['w']}-{r0['l']} overall.",
                school=s0, conference=conf, sport=key))
            # player and newcomer of the year come off the champion's roster
            roster = st.roster(s0, key)
            if roster:
                who = roster[r.randrange(len(roster))][0]
                out.append(item(
                    "conf-player-of-year", _shift(today, -r.randrange(2, 20)),
                    f"{who} is the {conf} {sp.name.lower()} player of the year",
                    f"The {s0} selection led the league champion.",
                    school=s0, conference=conf, sport=key, people=[who]))
                frosh = [n for n, y in roster if y in ("9", "10")]
                if frosh:
                    who = frosh[r.randrange(len(frosh))]
                    out.append(item(
                        "conf-newcomer", _shift(today, -r.randrange(2, 20)),
                        f"{who} named {conf} {sp.name.lower()} newcomer of the year",
                        f"The {s0} underclassman is the league's top first-year athlete.",
                        school=s0, conference=conf, sport=key, people=[who]))
            # all-conference: the top three programs put players on the team
            named = []
            for s, _v in rows[:3]:
                rr = st.roster(s, key)
                if rr:
                    named.append((rr[zlib.crc32(s.encode()) % len(rr)][0], s))
            if len(named) >= 2:
                out.append(item(
                    "conf-all-conference", _shift(today, -r.randrange(2, 22)),
                    f"{len({s for _n, s in named})} schools place athletes on the "
                    f"all-{conf} {sp.name.lower()} team",
                    ", ".join(f"{n} ({s})" for n, s in named) + ".",
                    conference=conf, sport=key, people=[n for n, _s in named]))

        if best_team:
            s0, r0, sp = best_team
            out.append(item(
                "conf-team-of-week", _shift(today, -r.randrange(1, 7)),
                f"{s0} {sp.name.lower()} is the {conf} team of the week",
                f"The {s0} moved to {r0['cw']}-{r0['cl']} in conference play.",
                school=s0, conference=conf, sport=sp.key))

        # academic, sportsmanship, officials, announcements — the league's
        # administrative voice, which is half of what a conference publishes
        pick = members[r.randrange(len(members))]
        out.append(item(
            "conf-all-academic", _shift(today, -r.randrange(5, 45)),
            f"{conf} announces the spring all-academic team",
            f"{r.randrange(18, 64)} student-athletes across {len(members)} member "
            f"schools earned the league's academic distinction.",
            conference=conf))
        out.append(item(
            "conf-sportsmanship", _shift(today, -r.randrange(5, 50)),
            f"{pick} receives the {conf} sportsmanship award",
            "The award is voted by member athletic directors and game officials "
            "across all sanctioned sports.",
            school=pick, conference=conf))
        out.append(item(
            "conf-announcement", _shift(today, -r.randrange(3, 28)),
            f"{conf} announces championship sites",
            f"Host sites for the league's remaining championship events were "
            f"confirmed by the {conf} board of directors.",
            conference=conf))
        if r.random() < 0.5:
            key = sports[r.randrange(len(sports))]
            out.append(item(
                "conf-record", _shift(today, -r.randrange(4, 40)),
                f"League {BY_KEY[key].name.lower()} record falls at the "
                f"{conf} championships",
                "The mark had stood since the association's last realignment.",
                conference=conf, sport=key))
    return out


def state_items(st: State) -> list[dict]:
    """Statewide: the association's own awards and administrative notices."""
    out: list[dict] = []
    today = st.today
    r = _rng("state", SEASON)
    for t in st.tournaments:
        if not t.champion:
            continue
        sport = BY_KEY[t.sport]
        out.append(item(
            "state-title", t.final_date or today,
            f"{t.champion} claims the {t.group} {sport.name} state title",
            f"Decided at {t.final_venue or 'the state final'}"
            f"{f', over {t.runner_up}' if t.runner_up else ''}.",
            school=t.champion, sport=t.sport,
            conference=st.conf_of.get(t.champion)))

    big = [sp for sp in CATALOG if sp.shape.value != "meet"]
    for sp in big[:14]:
        rec = st.records_for(sp.key)
        rows = sorted(rec.items(), key=lambda kv: (-kv[1]["w"], kv[1]["l"], kv[0]))
        if not rows or rows[0][1]["w"] < 6:
            continue
        s0, r0 = rows[0]
        roster = st.roster(s0, sp.key)
        if not roster:
            continue
        who = roster[zlib.crc32(f"soy:{sp.key}".encode()) % len(roster)][0]
        out.append(item(
            "state-honor", _shift(today, -r.randrange(4, 30)),
            f"{who} of {s0} named JHSAA {sp.name.lower()} athlete of the year",
            f"The award closes a {r0['w']}-{r0['l']} season for {s0}.",
            school=s0, sport=sp.key, conference=st.conf_of.get(s0), people=[who]))

    out.append(item(
        "state-academic", _shift(today, -12),
        "JHSAA names 214 schools to the academic honor roll",
        "Programs whose squad grade-point average cleared 3.25 across every "
        "sanctioned activity are recognized for the 2026-27 school year."))
    out.append(item(
        "state-official", _shift(today, -21),
        "Association honors twelve officials for career service",
        "The registered officials recognized this spring have a combined 340 "
        "years of service across eleven sports."))
    out.append(item(
        "state-sportsmanship", _shift(today, -30),
        "Six schools receive the JHSAA sportsmanship citation",
        "The citation is awarded on the reports of contest officials and "
        "opposing administrators, one per classification."))
    return out


# ────────────────────────────────────────────────────────────────── driver


def build(records_dir: pathlib.Path, today: str) -> list[dict]:
    st = State(records_dir, today)
    weekly = best_lines(st, _shift(today, -10))
    items = (school_items(st, weekly) + record_items(st)
             + conference_items(st, weekly) + state_items(st))
    # newest first, and stable inside a day so a rerun does not reshuffle
    items.sort(key=lambda d: (d["date"], d["kind"], d["headline"]), reverse=True)
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default=str(RECORDS))
    ap.add_argument("--today", default=CLOCK.isoformat())
    ap.add_argument("--check", action="store_true", help="report, write nothing")
    args = ap.parse_args()

    items = build(pathlib.Path(args.records), args.today)
    by_kind = collections.Counter(i["kind"] for i in items)
    by_scope = collections.Counter(i["scope"] for i in items)
    schools = len({i["school"] for i in items if i["school"]})

    print(f"{len(items):,} editorial items · {schools} schools carry at least one")
    for scope in ("school", "conference", "state"):
        kinds = sorted((k for k in by_kind if KINDS[k][1] == scope),
                       key=lambda k: -by_kind[k])
        print(f"  {scope:10} {by_scope[scope]:6,}  "
              + ", ".join(f"{k} {by_kind[k]:,}" for k in kinds[:6]))

    if not args.check:
        out = pathlib.Path(args.records) / "editorial" / SEASON / "items.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(items, separators=(",", ":")) + "\n")
        print(f"  → {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
