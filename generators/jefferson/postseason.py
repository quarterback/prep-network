"""
Derive the JHSAA postseason from the regular season that already exists.

    python3 -m generators.jefferson.postseason [--records DIR] [--today ISO]

The state's 8,000 regular-season contests were generated first; this reads them
back and builds the championship layer on top — qualification, seeds, brackets,
round dates, and the games those rounds produced.

Three things worth knowing before changing it:

**The bracket is derived, the final is not invented.** A handful of championship
finals already exist as GAME records (Mabryville beat Aspen Spur Union for the
1A football title). Those are reused as the last round rather than regenerated,
so a bracket built here agrees with a page that already shipped. Regenerating
them would silently produce a second, contradictory champion.

**Seeds come from results, not from a die.** A team's seed is its regular-season
record in the contests already on disk, tie-broken by name so the output is
stable across runs. A championship field whose seeding has no relationship to
the season underneath it looks fine and reads as nonsense the moment anyone
checks a 1-seed's record.

**The three states are the calendar, not a flag.** At the demo date of
2027-05-13 fall and winter are decided, the earlier spring championships are
mid-bracket, and the late-spring ones have not drawn yet — so complete /
in-progress / upcoming fall out of comparing round dates to ``TODAY`` rather
than being assigned anywhere.

That date is also why every season has results. The clock lives in
``generators.jefferson.gen`` and scoring happens inline with scheduling, so
moving it is not "the same season further along" — it is a different season,
and everything derived from it has to be rebuilt. It is worth doing: parked in
January, two thirds of the calendar had no results at all, and demonstrating a
spring sport meant either fabricating a result or shipping a caveat.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import records_io                                          # noqa: E402
from app.shapes import (                                            # noqa: E402
    Entrant,
    Game,
    Meet,
    Provenance,
    SourceType,
    Tournament,
    TournamentFormat,
    advance,
    build_bracket,
)
from app.sports import BY_KEY, CATALOG, Shape                       # noqa: E402

TODAY = "2027-05-13"
SEASON = "2026-27"

#: Championship weekend by season, with per-sport overrides.
#:
#: Associations do not crown everything on one weekend, and the staggering is
#: what keeps all three bracket states visible at a single demo date: with the
#: clock at 2027-05-13, fall and winter are decided, the earlier spring
#: championships are mid-bracket, and the later ones have not drawn yet. A
#: single spring date would make every spring bracket the same state and the
#: postseason surfaces would only ever demonstrate one of the three.
FINALS = {"fall": "2026-11-20", "winter": "2027-02-27", "spring": "2027-05-22"}

#: Sports whose championship runs late in the spring — still upcoming at the
#: demo date, so "the bracket is drawn but nothing has been played" is a state
#: the pages actually have to render.
LATE_SPRING = {
    "baseball", "softball", "boys-lacrosse", "girls-lacrosse",
    "girls-flag-football", "boys-track", "girls-track",
}
LATE_SPRING_FINAL = "2027-06-12"

#: Days between rounds, counting back from the final.
ROUND_GAP = 7

#: Target field size by how many schools sponsor the sport in that division.
#: Chosen so the six bracket shapes the renderer must support (4/8/12/16/24/32)
#: all actually occur in the state rather than being unit-test-only.
def target_field(eligible: int) -> int:
    # Bands are set against the ACTUAL spread of the state (median ~88 schools
    # per division, range 1-317). Tuned once for a 256-school state, every band
    # but the top one went empty when the 7A expansion tripled it: 59 of 65
    # brackets came out at 32 and the renderer's other five shapes stopped
    # occurring in real data. A qualifying field is a fraction of the division,
    # not a constant.
    for floor, size in ((120, 32), (80, 24), (50, 16), (30, 12), (16, 8)):
        if eligible >= floor:
            return size
    return 4


VENUES = [
    "Jefferson Coliseum, Ashbury", "Copper Lake Fieldhouse",
    "Norview Memorial Stadium", "Port Meridian Civic Arena",
    "Halbrook Events Center", "Sage Summit Pavilion",
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "x"


def contest_key(c) -> str:
    """Stable identity for a contest record, used to link a matchup to a page."""
    return f"{c.sport}:{c.date}:{c.name}"


def _shift(iso: str, days: int) -> str:
    d = _dt.date.fromisoformat(iso) + _dt.timedelta(days=days)
    return d.isoformat()


# ------------------------------------------------------------------ the field


def _records(contests) -> dict[tuple[str, str], list[int]]:
    """Win/loss per (sport, school) from the regular season on disk."""
    table: dict[tuple[str, str], list[int]] = {}

    def bump(sport, school, win):
        row = table.setdefault((sport, school), [0, 0])
        row[0 if win else 1] += 1

    for c in contests:
        if isinstance(c, Meet) or "Championship" in (c.name or ""):
            continue
        if isinstance(c, Game):
            if c.home_score is None or c.home_score == c.away_score:
                continue
            home_won = c.home_score > c.away_score
        else:  # Dual
            if c.home_points is None or c.home_points == c.away_points:
                continue
            home_won = c.home_points > c.away_points
        bump(c.sport, c.home, home_won)
        bump(c.sport, c.away, not home_won)
    return table


def _field(sport_key, group, schools, table, size, anchor=()) -> list[Entrant]:
    """The qualified field, seeded by record.

    ``anchor`` names two schools that a already-published final says met for
    this title. They are seeded 1 and 2 — the only pair of slots in a bracket
    that CANNOT meet before the final — so the derived tree is able to produce
    the result that already shipped. Everyone else is seeded by record.

    Without this the bracket seeds Mabryville first on its regular season, knocks
    it out in the first round, and then staples the published championship score
    onto whichever two teams its own simulation sent to the final. The score is
    real, the teams are real, and together they are a fiction — the failure mode
    that having one authority per fact is supposed to prevent.
    """
    pool = []
    for s in schools:
        w, l = table.get((sport_key, s["name"]), [0, 0])
        if w + l == 0:
            continue
        pct = w / (w + l)
        pool.append((-pct, -w, s["name"], w, l, s.get("conference")))
    pool.sort()

    rows = {r[2]: r for r in pool}
    ordered = [rows[a] for a in anchor if a in rows]
    if len(ordered) != len(anchor):
        ordered = []                       # a finalist that never played: seed normally
    ordered += [r for r in pool if r[2] not in {o[2] for o in ordered}]

    out = []
    for i, (_, _, name, w, l, conf) in enumerate(ordered[:size]):
        out.append(Entrant(
            school=name, seed=i + 1,
            qualifier="Conference champion" if i < 4 else "At-large",
            record=f"{w}-{l}", conference=conf,
        ))
    return out


# --------------------------------------------------------------- the bracket


def _score(sport, rng: random.Random) -> tuple[int, int]:
    """A final score in the sport's own currency, winner first.

    One generic draw (38–72, basketball's band) used to fill every bracket:
    a tennis quarterfinal shipped as 52–48 when a tennis dual is decided in
    team points out of nine, a volleyball playoff carried a 60-point score
    when volleyball is won in sets, and only the finals looked right because
    those were adopted from the state generator, which has always known the
    difference. The published pages' first screenful was fine and every
    interior round was nonsense — which is exactly where a reader clicks next.
    """
    k = sport.key
    if k == "football":
        w, l = rng.randint(17, 49), rng.randint(0, 31)
    elif k == "girls-flag-football":
        w, l = rng.randint(13, 40), rng.randint(0, 26)
    elif "soccer" in k or k == "field-hockey":
        w, l = rng.randint(1, 5), rng.randint(0, 3)
    elif "basketball" in k:
        w, l = rng.randint(48, 82), rng.randint(35, 70)
    elif "volleyball" in k:
        return 3, rng.choice([0, 1, 1, 2])          # sets: 3-0 / 3-1 / 3-2
    elif "tennis" in k or "fencing" in k:
        w = rng.choice([5, 5, 6, 6, 7, 8, 9])       # nine lines, team points
        return w, 9 - w
    elif "badminton" in k:
        w = rng.choice([3, 3, 4, 5])                # five lines
        return w, 5 - w
    elif "wrestling" in k:
        return 3 * rng.randint(11, 18), 3 * rng.randint(3, 9)
    elif "ice-hockey" in k:
        w, l = rng.randint(2, 6), rng.randint(0, 4)
    elif "water-polo" in k:
        w, l = rng.randint(8, 16), rng.randint(4, 12)
    elif "lacrosse" in k:
        w, l = rng.randint(7, 16), rng.randint(3, 12)
    elif k == "ultimate":
        return 15, rng.randint(7, 13)               # game to 15
    elif k in ("baseball", "softball"):
        w, l = rng.randint(2, 10), rng.randint(0, 7)
    else:
        w, l = rng.randint(40, 70), rng.randint(30, 60)
    if l >= w:
        l = w - 1
    return w, max(0, l)


def _play(t: Tournament, today: str, rng: random.Random,
          existing_final, sport) -> list[Game]:
    """Walk the rounds, deciding each matchup whose date has passed.

    Returns the GAME records created for the rounds that were played. The final
    is reused from disk when one already exists, so the bracket cannot crown a
    different champion than the page that already shipped.
    """
    produced: list[Game] = []
    total = len(t.rounds)
    # The two schools a published final says met for this title must survive to
    # meet. They are the 1 and 2 seeds, so protecting them bends no bracket:
    # they cannot be drawn against each other before the last round.
    protected: set[str] = set()
    if existing_final is not None:
        protected = {existing_final.home, existing_final.away}

    for r in t.rounds:
        # Round dates count back from the final so the last round lands on it.
        r_date = _shift(t.final_date, -ROUND_GAP * (total - 1 - r.index))
        for m in r.matchups:
            if m.bye:
                continue
            m.date, m.venue = r_date, (t.final_venue if r.index == total - 1 else None)
            m.time = "7:00 PM" if r.index < total - 1 else "6:30 PM"
        advance(t)

        if r_date > today:
            continue                                   # not played yet

        for m in r.matchups:
            if m.bye or not m.ready or m.decided:
                continue

            if r.index == total - 1 and existing_final is not None:
                # Adopt the result that already exists on disk. The bracket has
                # delivered these two teams here on its own, so this sets the
                # score and the link only — assigning the teams as well would be
                # overwritten by the advance() below and mask a mismatch.
                g = existing_final
                if {m.home, m.away} != {g.home, g.away}:
                    raise AssertionError(
                        f"{t.id}: bracket final {m.home} v {m.away} does not match "
                        f"the published final {g.home} v {g.away}")
                same = m.home == g.home
                m.home_score = g.home_score if same else g.away_score
                m.away_score = g.away_score if same else g.home_score
                # A cancelled final carries its status through: no scores, no
                # champion, and the bracket says so instead of implying one.
                m.status = "cancelled" if g.status == "cancelled" else "final"
                m.contest_key = contest_key(g)
                m.date, m.venue = g.date, g.venue or t.final_venue
                continue

            hi = m.home_seed or 99
            lo = m.away_seed or 99
            if protected & {m.home, m.away}:
                home_wins = m.home in protected
            else:
                # The better seed usually wins; the gap decides how usually.
                edge = 0.5 + min(0.32, abs(hi - lo) * 0.035)
                home_wins = rng.random() < (edge if hi < lo else 1 - edge)
            a, b = _score(sport, rng)
            m.home_score, m.away_score = (a, b) if home_wins else (b, a)
            m.status = "final"

            name = f"{m.away} at {m.home} — JHSAA {t.group} {r.name}"
            if r.index == total - 1:
                name = f"{m.away} at {m.home} — JHSAA {t.group} Championship"
            g = Game(
                name=name, date=m.date, venue=m.venue, sport=t.sport, season=t.season,
                home=m.home, away=m.away,
                home_score=m.home_score, away_score=m.away_score, status="final",
                provenance=Provenance(
                    source_uri=f"generated://jefferson/postseason/{t.id}",
                    adapter="jefferson.postseason", adapter_version="1",
                    extracted_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
                    source_type=SourceType.MANUAL,
                    external_ids={"tournament": t.id, "round": str(r.index),
                                  "slot": str(m.slot)},
                ),
            )
            m.contest_key = contest_key(g)
            produced.append(g)
        advance(t)
    return produced


# ------------------------------------------------------------------- driver


def _drop_undecided_finals(records_dir: pathlib.Path) -> list[str]:
    """Delete published championship games that decide nothing.

    Two kinds, both generated as placeholders and both invisible until a bracket
    is built on top of them:

      * a **draw** — a knockout final cannot end level, somebody lifts the
        trophy;
      * a **scoreless "final"** — status says final, both scores are null.

    Either way the tournament adopts a final with no winner, never resolves, and
    reports itself as still in progress months after it was played. On the
    championships page that reads as "Boys Soccer · Championship — happening
    now" in January.

    A genuinely CANCELLED final is kept: "the title was not decided" is a fact
    about the season, and the bracket says so rather than inventing a champion.
    The rest are removed rather than patched with a made-up winner, so the
    bracket derives the final like any other and there is still exactly one
    record of it.
    """
    dropped = []
    for path in (records_dir / "contests").rglob("*.json"):
        try:
            d = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if "Championship" not in (d.get("name") or ""):
            continue
        if d.get("$type") != records_io.GAME_TYPE:
            continue
        if d.get("status") == "cancelled":
            continue
        home, away = d.get("homeScore"), d.get("awayScore")
        why = None
        if home is None or away is None:
            why = "no score"
        elif home == away:
            why = f"drawn {home}-{away}"
        if why:
            dropped.append(f"{d.get('sport')} {d.get('name')} ({why})")
            path.unlink()
    return dropped


def build(records_dir: pathlib.Path, today: str = TODAY) -> tuple[int, int]:
    schools, _ = records_io.load_orgs(records_dir)
    for note in _drop_undecided_finals(records_dir):
        print(f"  dropped undecided final: {note}")

    # A generator must not read its own output. Left in, last run's quarterfinals
    # count as regular-season wins, which moves the seeds, which moves the
    # bracket, which writes a different postseason — so the state changes every
    # time this is run with nothing else changed, and the run that shipped is
    # not the run you can reproduce. Own the rows by provenance and drop them.
    contests = [
        c for c in records_io.load_contests(records_dir)
        if not (c.provenance and c.provenance.adapter == "jefferson.postseason")
    ]
    table = _records(contests)

    finals_on_disk: dict[tuple[str, str], Game] = {}
    meets_on_disk: dict[tuple[str, str], Meet] = {}
    for c in contests:
        name = c.name or ""
        if "Championship" not in name:
            continue
        # The division follows "JHSAA" in both spellings the state uses:
        # a GAME is "… — JHSAA 1A Championship", a MEET is "JHSAA 1A Boys Cross
        # Country ChampionshipS". Anchoring on the word after JHSAA matches both;
        # requiring "Championship" to come next matches only the games, and
        # every meet-decided title silently loses its link.
        m = re.search(r"JHSAA\s+(\S+)\b", name)
        group = m.group(1) if m else None
        if group is None:
            continue
        if isinstance(c, Game):
            finals_on_disk.setdefault((c.sport, group), c)
        elif isinstance(c, Meet):
            meets_on_disk.setdefault((c.sport, group), c)

    tournaments: list[Tournament] = []
    new_games: list[Game] = []

    for sport in CATALOG:
        by_group: dict[str, list[dict]] = {}
        for s in schools:
            if sport.key not in s.get("sports", []):
                continue
            by_group.setdefault(sport.champ_group(s["classification"]), []).append(s)

        for group, members in by_group.items():
            tid = f"{SEASON}-{sport.key}-{slugify(group)}"
            final_date = (LATE_SPRING_FINAL if sport.key in LATE_SPRING
                          else FINALS[sport.season])
            t = Tournament(
                id=tid,
                name=f"{final_date[:4]} JHSAA {group} {sport.name} State Championship",
                sport=sport.key, season=SEASON, group=group,
                final_date=final_date,
                final_venue=VENUES[hash(tid) % len(VENUES)],
                provenance=Provenance(
                    source_uri=f"generated://jefferson/postseason/{tid}",
                    adapter="jefferson.postseason", adapter_version="1",
                    extracted_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
                    source_type=SourceType.MANUAL,
                ),
            )

            # MEET sports do not bracket. The championship is one meet, and the
            # tournament record points at it rather than restating it.
            if sport.shape is Shape.MEET:
                t.format = TournamentFormat.MEET
                meet = meets_on_disk.get((sport.key, group))
                if meet is not None:
                    # A meet-decided title is COMPLETE when it points at a
                    # meet (`Tournament.status`), so only point at one that
                    # was actually CONTESTED. The state schedules championship
                    # meets ahead of the clock too, and linking those would
                    # crown a champion for an event with no events in it.
                    if meet.events:
                        t.meet_key = contest_key(meet)
                    t.final_date = meet.date or final_date
                    t.final_venue = meet.venue or t.final_venue
                t.entrants = _field(sport.key, group, members, table,
                                    min(len(members), 24))
                t.start_date = t.final_date
                tournaments.append(t)
                continue

            size = min(target_field(len(members)), len(members))
            if size < 4:
                continue
            published = finals_on_disk.get((sport.key, group))
            # The winner takes the 1 seed, the runner-up the 2 — the two slots
            # that can only meet in the final.
            anchor = ()
            if published is not None and published.winner:
                anchor = (published.winner,
                          published.away if published.winner == published.home
                          else published.home)
            entrants = _field(sport.key, group, members, table, size, anchor)
            if len(entrants) < 4:
                continue
            if anchor and not {anchor[0], anchor[1]} <= {e.school for e in entrants}:
                published = None      # a finalist outside the field: keep it derived
            t.entrants = entrants
            t.rounds = build_bracket(entrants)
            t.start_date = _shift(final_date, -ROUND_GAP * (len(t.rounds) - 1))

            rng = random.Random(f"{tid}")
            new_games.extend(_play(t, today, rng, published, sport))
            tournaments.append(t)

    # ---- write. Both outputs are cleared first: this generator is re-run
    #      whenever the seeding or the calendar changes, and a run that only
    #      ADDS leaves the previous run's games on disk beside the new ones.
    #      They are valid records with plausible names, so nothing downstream
    #      rejects them — the state simply acquires a second, contradictory
    #      postseason. Ownership is the provenance adapter, which is why these
    #      games carry one.
    post_dir = records_dir / "postseason" / SEASON
    if post_dir.exists():
        for old in post_dir.glob("*.json"):
            old.unlink()
    for t in tournaments:
        records_io.write_tournament(post_dir / f"{t.id}.json", t)

    for path in (records_dir / "contests").rglob("*.json"):
        try:
            prov = json.loads(path.read_text()).get("provenance") or {}
        except (OSError, ValueError):
            continue
        if prov.get("adapter") == "jefferson.postseason":
            path.unlink()

    base = max((c_seq(p) for p in (records_dir / "contests").rglob("*.json")), default=0)
    for i, g in enumerate(new_games, start=base + 1):
        path = (records_dir / "contests" / SEASON / g.sport /
                f"{i:05d}-{slugify(g.name)[:70]}.json")
        records_io.write_contest(path, g, sequence=i)

    return len(tournaments), len(new_games)


def c_seq(path: pathlib.Path) -> int:
    m = re.match(r"^(\d+)-", path.name)
    return int(m.group(1)) if m else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default=str(ROOT / "records"))
    ap.add_argument("--today", default=TODAY)
    args = ap.parse_args()
    n_t, n_g = build(pathlib.Path(args.records), args.today)
    print(f"{n_t} tournaments · {n_g} postseason games written")

    tours = records_io.load_tournaments(pathlib.Path(args.records))
    by_state: dict[str, int] = {}
    sizes: dict[int, int] = {}
    for t in tours:
        by_state[t.status.value] = by_state.get(t.status.value, 0) + 1
        if t.format is TournamentFormat.BRACKET:
            sizes[t.size] = sizes.get(t.size, 0) + 1
    print("  states:", ", ".join(f"{k} {v}" for k, v in sorted(by_state.items())))
    print("  field sizes:", ", ".join(f"{k}→{v}" for k, v in sorted(sizes.items())))

    # A bracket whose last round is in the past but has no champion is stuck,
    # and a stuck bracket does not look broken — it looks live. Say so loudly
    # rather than shipping a fall championship that reports itself as playing.
    # "No champion" is not the test — a cancelled final has none and is finished.
    # The test is whether anything is still waiting to be played in the past.
    stuck = [t for t in tours
             if t.format is TournamentFormat.BRACKET
             and t.final_date and t.final_date <= args.today
             and t.final is not None and not t.final.resolved]
    if stuck:
        for t in stuck:
            print(f"  \033[33mSTUCK\033[0m {t.id}: final {t.final_date} unresolved")
        return 1
    cancelled = [t for t in tours if t.final is not None
                 and t.final.status == "cancelled"]
    for t in cancelled:
        print(f"  note: {t.id} final was cancelled — no champion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
