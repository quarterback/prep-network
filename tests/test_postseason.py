"""
Bracket construction, advancement, geometry, and the generated state's
postseason.

The invariants here are the ones that make a bracket a bracket: the top two
seeds can only meet in the final, byes go to the teams the seeding says, a
winner appears in exactly one slot of the next round, and the drawn tree and
the drawn connector lines agree about where everything is.
"""

from __future__ import annotations

import pathlib

import pytest

from app import records_io
from app.postseason import CARD_H, layout
from app.shapes import (
    Entrant,
    Matchup,
    Tournament,
    TournamentFormat,
    TournamentStatus,
    advance,
    build_bracket,
    seed_order,
)

RECORDS = pathlib.Path(__file__).resolve().parent.parent / "records"

SIZES = [4, 8, 12, 16, 24, 32]


def field(n: int) -> list[Entrant]:
    return [Entrant(school=f"School {i}", seed=i, record=f"{n - i}-{i}")
            for i in range(1, n + 1)]


def tourney(n: int) -> Tournament:
    ents = field(n)
    t = Tournament(id=f"t{n}", name=f"{n}-team", sport="football",
                   season="2026-27", group="1A", entrants=ents,
                   rounds=build_bracket(ents))
    advance(t)
    return t


def play(t: Tournament, upset: set[int] = frozenset()) -> None:
    """Play the whole bracket; the better seed wins unless its round is in
    ``upset``, in which case the lower seed does."""
    for r in t.rounds:
        for m in r.matchups:
            if m.bye or not m.ready or m.decided:
                continue
            better_home = (m.home_seed or 99) < (m.away_seed or 99)
            home_wins = better_home if r.index not in upset else not better_home
            m.home_score, m.away_score = (30, 10) if home_wins else (10, 30)
            m.status = "final"
        advance(t)


# ------------------------------------------------------------------ seeding


@pytest.mark.parametrize("size", [2, 4, 8, 16, 32])
def test_seed_order_is_a_permutation(size):
    order = seed_order(size)
    assert sorted(order) == list(range(1, size + 1))


@pytest.mark.parametrize("size", [4, 8, 16, 32])
def test_every_first_round_pairing_sums_to_one_more_than_the_field(size):
    order = seed_order(size)
    for i in range(0, size, 2):
        assert order[i] + order[i + 1] == size + 1


# ----------------------------------------------------------------- brackets


@pytest.mark.parametrize("n", SIZES)
def test_bracket_has_the_right_shape(n):
    t = tourney(n)
    assert t.bracket_size >= n
    assert len(t.rounds) == t.bracket_size.bit_length() - 1
    assert len(t.rounds[-1].matchups) == 1


@pytest.mark.parametrize("n", SIZES)
def test_byes_go_to_the_top_seeds(n):
    t = tourney(n)
    byes = sorted(m.home_seed for m in t.rounds[0].matchups if m.bye)
    assert byes == list(range(1, t.byes + 1))


@pytest.mark.parametrize("n", SIZES)
def test_a_bye_has_no_opponent_and_no_contest(n):
    """Structural, not a fake team: a phantom opponent would enter the schools
    index and every page that counts opponents."""
    for m in tourney(n).rounds[0].matchups:
        if m.bye:
            assert m.away is None and m.away_seed is None
            assert m.contest_key is None
            assert m.winner == m.home


@pytest.mark.parametrize("n", SIZES)
def test_first_round_game_count(n):
    t = tourney(n)
    games = sum(1 for m in t.rounds[0].matchups if not m.bye)
    assert games == n - t.bracket_size // 2


@pytest.mark.parametrize("n", SIZES)
def test_top_two_seeds_meet_only_in_the_final(n):
    t = tourney(n)
    play(t)
    assert t.champion == "School 1"
    assert t.runner_up == "School 2"
    assert t.final.round == len(t.rounds) - 1


@pytest.mark.parametrize("n", SIZES)
def test_a_winner_advances_to_exactly_one_slot(n):
    t = tourney(n)
    play(t)
    for i in range(len(t.rounds) - 1):
        winners = {m.winner for m in t.rounds[i].matchups if m.winner}
        standing = {s for m in t.rounds[i + 1].matchups for s in (m.home, m.away) if s}
        assert standing <= winners
        assert len(standing) == len(winners)


@pytest.mark.parametrize("n", SIZES)
def test_advance_is_idempotent(n):
    t = tourney(n)
    play(t)
    before = [(m.home, m.away) for r in t.rounds for m in r.matchups]
    advance(t)
    advance(t)
    assert [(m.home, m.away) for r in t.rounds for m in r.matchups] == before


def test_upsets_propagate():
    """Invert the first round and seeds 9-16 advance; normal play from there
    leaves the best of them standing."""
    t = tourney(16)
    play(t, upset={0})
    assert {m.winner for m in t.rounds[0].matchups} == {f"School {i}" for i in range(9, 17)}
    assert t.champion == "School 9"


# ------------------------------------------------------------------- status


def test_a_fresh_bracket_with_byes_is_not_in_progress():
    """A bye is decided when the field is drawn; that is not play."""
    assert tourney(12).status is TournamentStatus.UPCOMING


def test_status_moves_with_the_first_real_result():
    t = tourney(12)
    m = next(m for m in t.rounds[0].matchups if not m.bye)
    m.home_score, m.away_score, m.status = 40, 20, "final"
    advance(t)
    assert t.status is TournamentStatus.IN_PROGRESS


def test_status_completes_with_the_final():
    t = tourney(8)
    play(t)
    assert t.status is TournamentStatus.COMPLETE


def test_meet_format_completes_on_its_meet_not_its_rounds():
    t = Tournament(id="x", format=TournamentFormat.MEET)
    assert t.status is TournamentStatus.UPCOMING
    t.meet_key = "boys-cross-country:2026-10-31:JHSAA 1A"
    assert t.status is TournamentStatus.COMPLETE


# ----------------------------------------------------------------- geometry


@pytest.mark.parametrize("n", SIZES)
def test_layout_places_every_matchup_once(n):
    cv = layout(tourney(n))
    assert len(cv.cards) == sum(len(r.matchups) for r in tourney(n).rounds)


@pytest.mark.parametrize("n", SIZES)
def test_the_final_is_vertically_centred(n):
    """The whole point of averaging feeders: the tree converges on the middle."""
    cv = layout(tourney(n))
    final = next(c for c in cv.cards if c.round_name == "Championship")
    assert abs((final.y + CARD_H / 2) - cv.height / 2) < 1.0


@pytest.mark.parametrize("n", SIZES)
def test_a_card_sits_between_the_two_that_feed_it(n):
    t = tourney(n)
    cv = layout(t)
    by_pos = {(c.col, c.slot): c for c in cv.cards}
    for (col, slot), card in by_pos.items():
        if col == 0:
            continue
        feeders = [by_pos.get((col - 1, 2 * slot)), by_pos.get((col - 1, 2 * slot + 1))]
        feeders = [f for f in feeders if f]
        if len(feeders) == 2:
            lo, hi = sorted(f.y for f in feeders)
            assert lo <= card.y <= hi


@pytest.mark.parametrize("n", SIZES)
def test_columns_do_not_overlap_and_advance_left_to_right(n):
    cv = layout(tourney(n))
    xs = [c.x for c in cv.columns]
    assert xs == sorted(xs)
    assert len(set(xs)) == len(xs)


@pytest.mark.parametrize("n", SIZES)
def test_every_link_starts_and_ends_on_a_column_edge(n):
    """Cards and elbows share one coordinate system or the bracket drifts."""
    cv = layout(tourney(n))
    edges = {c.x for c in cv.columns}
    rights = {c.x + cv.card_w for c in cv.columns}
    for link in cv.links:
        parts = link.d.split()
        assert float(parts[1]) in rights
        assert float(parts[-1]) in edges


def test_links_go_live_only_when_a_winner_actually_advances():
    t = tourney(8)
    assert not any(l.live for l in layout(t).links)
    play(t)
    live = [l for l in layout(t).links if l.live]
    # Every non-final round contributes one live edge per advancing team.
    assert len(live) == sum(len(r.matchups) for r in t.rounds[:-1])


def test_layout_of_an_empty_tournament_is_none():
    assert layout(Tournament(id="x")) is None


# --------------------------------------------------- the generated state


@pytest.fixture(scope="module")
def tournaments():
    return records_io.load_tournaments(RECORDS)


def test_the_state_has_a_postseason(tournaments):
    assert len(tournaments) > 80


def test_all_three_states_are_represented(tournaments):
    states = {t.status for t in tournaments}
    assert states == {
        TournamentStatus.UPCOMING,
        TournamentStatus.IN_PROGRESS,
        TournamentStatus.COMPLETE,
    }


def test_every_required_bracket_size_occurs(tournaments):
    sizes = {t.size for t in tournaments if t.format is TournamentFormat.BRACKET}
    assert {4, 8, 12, 16, 24, 32} <= sizes


def test_tournament_ids_are_unique(tournaments):
    ids = [t.id for t in tournaments]
    assert len(ids) == len(set(ids))


def test_seeds_are_dense_and_unique(tournaments):
    for t in tournaments:
        seeds = sorted(e.seed for e in t.entrants)
        assert seeds == list(range(1, len(t.entrants) + 1)), t.id


def test_a_school_appears_at_most_once_in_a_field(tournaments):
    for t in tournaments:
        names = [e.school for e in t.entrants]
        assert len(names) == len(set(names)), t.id


def test_completed_brackets_have_a_champion(tournaments):
    done = [t for t in tournaments
            if t.status is TournamentStatus.COMPLETE
            and t.format is TournamentFormat.BRACKET]
    assert done
    for t in done:
        assert t.champion and t.champion in t.schools()


def test_in_progress_brackets_have_both_played_and_unplayed_rounds(tournaments):
    live = [t for t in tournaments if t.status is TournamentStatus.IN_PROGRESS]
    assert live
    for t in live:
        assert any(r.complete for r in t.rounds), t.id
        assert any(not r.complete for r in t.rounds), t.id


def test_the_1a_football_bracket_matches_the_published_final(tournaments):
    """The demo path: the bracket must deliver the champion already on disk."""
    t = next(x for x in tournaments if x.id == "2026-27-football-1a")
    assert t.status is TournamentStatus.COMPLETE
    assert t.champion == "Mabryville"
    assert t.runner_up == "Aspen Spur Union"
    assert (t.final.home_score, t.final.away_score) == (26, 17)
    assert t.final.contest_key


def test_played_matchups_link_to_a_contest(tournaments):
    for t in tournaments:
        if t.format is not TournamentFormat.BRACKET:
            continue
        for r in t.rounds:
            for m in r.matchups:
                if m.decided and not m.bye:
                    assert m.contest_key, (t.id, r.name, m.slot)


def test_meet_championships_point_at_a_meet_not_a_game(tournaments):
    linked = [t for t in tournaments
              if t.format is TournamentFormat.MEET and t.meet_key]
    assert linked
    for t in linked:
        assert not t.rounds
        assert t.meet_key.startswith(t.sport + ":")


def test_tournaments_round_trip(tournaments):
    for t in tournaments[:25]:
        d = records_io.tournament_to_dict(t)
        assert records_io.tournament_to_dict(records_io._tournament_from(d)) == d
