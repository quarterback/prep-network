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

**The three states are the calendar, not a flag.** Fall championships finished
in November, winter runs through the demo date, spring has not started — so
complete / in-progress / upcoming fall out of comparing round dates to ``TODAY``
rather than being assigned. That is also why the winter window sits in January
here: the demo date is 2027-01-16 and a bracket nobody can see mid-flight is
the one state hardest to get right and most worth showing.
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

TODAY = "2027-01-16"
SEASON = "2026-27"

#: Championship weekend by season. Winter straddles the demo date on purpose.
FINALS = {"fall": "2026-11-20", "winter": "2027-01-24", "spring": "2027-05-22"}

#: Days between rounds, counting back from the final.
ROUND_GAP = 7

#: Target field size by how many schools sponsor the sport in that division.
#: Chosen so the six bracket shapes the renderer must support (4/8/12/16/24/32)
#: all actually occur in the state rather than being unit-test-only.
def target_field(eligible: int) -> int:
    for floor, size in ((44, 32), (30, 24), (20, 16), (14, 12), (8, 8)):
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
                m.status, m.contest_key = "final", contest_key(g)
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
            a, b = sorted([rng.randint(38, 72), rng.randint(30, 64)], reverse=True)
            if sport.key in ("football",):
                a, b = sorted([rng.randint(14, 49), rng.randint(0, 35)], reverse=True)
            elif sport.key in ("boys-soccer", "girls-soccer", "field-hockey"):
                a, b = sorted([rng.randint(1, 5), rng.randint(0, 3)], reverse=True)
            if a == b:
                a += 1
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


def build(records_dir: pathlib.Path, today: str = TODAY) -> tuple[int, int]:
    schools, _ = records_io.load_orgs(records_dir)

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
            final_date = FINALS[sport.season]
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
