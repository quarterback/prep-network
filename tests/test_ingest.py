"""
Adapter and resolution tests, against the committed specimens.

These assert STRUCTURE and INVARIANTS rather than golden output: an adapter is
right when relays keep four legs, a scratched swimmer does not inherit a seed
time as a result, and a bad total is refused — not when it reproduces a blob
someone pasted in. Where a value is pinned it is because the value is the point
(a 4x100 relay has four legs; a 6S/3D card has nine lines).
"""

from __future__ import annotations

import pathlib

import pytest

from app import records_io
from app.shapes import Dual, Game, Meet, ReviewState, SourceType
from ingest import resolve as resolve_mod
from ingest.adapters import dual_card, hytek_swim, scorebook_csv
from ingest.resolve import Resolver, normalize
from ingest.run import detect

SPECIMENS = pathlib.Path(__file__).resolve().parent.parent / "ingest" / "fixtures" / "specimens"
RECORDS = pathlib.Path(__file__).resolve().parent.parent / "records"

SWIM = SPECIMENS / "hytek-mm-swimming-results.txt"
BOX = SPECIMENS / "scorebook-basketball-boxscore.csv"
BAD_BOX = SPECIMENS / "scorebook-basketball-badtotals.csv"
CARD = SPECIMENS / "dual-tennis-match-card.txt"


# ------------------------------------------------------------------ swimming


@pytest.fixture(scope="module")
def swim_meet() -> Meet:
    return hytek_swim.parse(str(SWIM))[0]


def test_swim_reads_meet_identity(swim_meet):
    assert "Swimming & Diving" in swim_meet.name
    assert swim_meet.venue == "Ashbury Aquatic Center"
    assert swim_meet.date and swim_meet.end_date          # a two-day championship


def test_swim_splits_both_genders(swim_meet):
    genders = {ev.gender for ev in swim_meet.events}
    assert genders == {"Girls", "Boys"}


def test_swim_relay_keeps_every_leg(swim_meet):
    relays = [ev for ev in swim_meet.events if "Relay" in ev.name]
    assert relays
    for ev in relays:
        for entry in ev.entries:
            if entry.mark and entry.mark.scored:
                # A 200 medley and a 400 free relay both swim four legs. Losing
                # one is the classic silent failure: the entry still looks fine.
                assert len(entry.competitors) in (0, 4), (ev.name, entry.school)


def test_swim_relay_letter_is_kept(swim_meet):
    first = swim_meet.events[0].entries[0]
    assert first.qualifier == "A"


def test_swim_splits_are_preserved(swim_meet):
    noted = [e for ev in swim_meet.events for e in ev.entries if e.note and "(" in e.note]
    assert noted, "no splits captured"
    assert "(28.33)" in noted[0].note


def test_swim_result_is_finals_not_seed(swim_meet):
    """The seed time must never be promoted to the result."""
    free = next(ev for ev in swim_meet.events if ev.number == 3)
    winner = free.entries[0]
    assert winner.mark.raw == "1:51.08"           # finals
    assert "1:52.44" in (winner.note or "")       # seed, kept but not the result


def test_swim_scratch_and_dq_are_unscored(swim_meet):
    marks = {
        e.mark.raw: e.mark.scored
        for ev in swim_meet.events for e in ev.entries if e.mark
    }
    assert marks.get("NS") is False
    assert marks.get("DQ") is False


def test_swim_diving_is_scored_not_timed(swim_meet):
    from app.shapes import MarkType

    diving = [ev for ev in swim_meet.events if "Diving" in ev.name]
    assert diving
    for ev in diving:
        assert ev.mark_type is MarkType.POINTS
        assert ev.entries[0].mark.value > 300     # a score, not a duration


def test_swim_team_rankings_by_gender(swim_meet):
    girls = [t for t in swim_meet.team_scores if t.gender == "Girls"]
    boys = [t for t in swim_meet.team_scores if t.gender == "Boys"]
    assert len(girls) == 10 and len(boys) == 4
    assert girls[0].rank == 1 and girls[0].points == 331


def test_swim_event_records_are_read(swim_meet):
    first = swim_meet.events[0]
    assert len(first.records) == 2
    assert first.records[0].scope == "State"


# ----------------------------------------------------------------- box score


@pytest.fixture(scope="module")
def box_game() -> Game:
    return scorebook_csv.parse(str(BOX))[0]


def test_box_reads_teams_and_score(box_game):
    assert box_game.home == "Ansotegui Siding"
    assert box_game.away == "Copper Lake East"
    assert (box_game.home_score, box_game.away_score) == (53, 65)
    assert box_game.winner == "Copper Lake East"


def test_box_reads_periods_that_add_up(box_game):
    assert [p.label for p in box_game.periods] == ["Q1", "Q2", "Q3", "Q4"]
    assert box_game.periods_agree() is True


def test_box_skips_unplayed_overtime_column(box_game):
    """An empty OT column is not a 0-0 period."""
    assert "OT" not in [p.label for p in box_game.periods]


def test_box_keeps_source_columns_in_source_order(box_game):
    assert box_game.box.columns[:4] == ["min", "fg", "3pt", "ft"]
    assert box_game.box.columns[-1] == "pts"
    # identity columns are not statistics
    assert "name" not in box_game.box.columns
    assert "teamCode" not in box_game.box.columns


def test_box_has_every_player_on_both_sides(box_game):
    assert len(box_game.box.away) == 8
    assert len(box_game.box.home) == 7
    assert sum(1 for s in box_game.box.away if s.starter) == 5


def test_box_players_carry_their_school(box_game):
    assert {s.competitor.school for s in box_game.box.away} == {"Copper Lake East"}


def test_box_totals_agree_with_player_rows(box_game):
    for column in ("pts", "reb", "ast", "to", "pf"):
        assert box_game.box.totals_agree(column) is True, column


def test_box_non_numeric_column_has_no_verdict(box_game):
    """A shooting line like 7-14 is not summable, and says so."""
    assert box_game.box.totals_agree("fg") is None


def test_box_provenance_is_complete(box_game):
    p = box_game.provenance
    assert p.source_type is SourceType.BOXSCORE_CSV
    assert p.adapter == "scorebook_csv" and p.adapter_version
    assert p.external_ids["gameId"] == "JHSAA-BB-2027-05422"
    assert len(p.source_sha256) == 64
    assert p.review_state is ReviewState.PUBLISHED
    assert p.publishable()


def test_bad_totals_land_in_the_review_queue():
    """The corrupt specimen parses cleanly and must still be refused."""
    game = scorebook_csv.parse(str(BAD_BOX))[0]
    assert game.box.totals_agree("pts") is False
    assert game.periods_agree() is False
    p = game.provenance
    assert p.review_state is ReviewState.NEEDS_REVIEW
    assert not p.publishable()
    assert "pts" in p.notes and "linescore" in p.notes


# ---------------------------------------------------------------- dual card


@pytest.fixture(scope="module")
def dual() -> Dual:
    return dual_card.parse(str(CARD))[0]


def test_dual_reads_a_full_6s3d_card(dual):
    assert len(dual.lines) == 9
    assert [l.kind for l in dual.lines].count("singles") == 6
    assert [l.kind for l in dual.lines].count("doubles") == 3


def test_dual_doubles_rows_are_merged_not_duplicated(dual):
    """The continuation row is a partner, not a tenth line."""
    for line in dual.lines:
        want = 2 if line.kind == "doubles" else 1
        assert len(line.home) == want and len(line.away) == want, line.slot


def test_dual_points_match_the_printed_card(dual):
    assert (dual.home_points, dual.away_points) == (5.0, 4.0)
    assert dual.compute_points() == (5.0, 4.0)
    assert dual.provenance.review_state is ReviewState.PUBLISHED


def test_dual_winner_comes_from_the_column_not_the_score(dual):
    """A match tiebreak (8-10) defeats set counting; the card already says."""
    s4 = next(l for l in dual.lines if l.kind == "singles" and l.slot == 4)
    assert s4.score == "3-6, 6-4, 8-10"
    assert s4.winner == "away"


def test_dual_players_carry_the_right_school(dual):
    for line in dual.lines:
        assert all(c.school == dual.home for c in line.home)
        assert all(c.school == dual.away for c in line.away)


def test_dual_grade_is_parsed_off_the_name(dual):
    s1 = dual.lines[0]
    assert s1.home[0].name == "Marchetti, Enzo"
    assert s1.home[0].year == "12"


def test_dual_card_disagreeing_with_itself_is_flagged():
    text = CARD.read_text().replace(
        "TEAM RESULT : Vista Terrace 5,", "TEAM RESULT : Vista Terrace 7,")
    d = dual_card.parse_text(text, source_uri="memory://card")[0]
    assert d.provenance.review_state is ReviewState.NEEDS_REVIEW
    assert not d.provenance.publishable()


# ---------------------------------------------------------------- resolution


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Southeast High School", "southeast"),
        ("Norview  HS", "norview"),
        ("Lingle Ft. Laramie  High Schoo", "lingle ft laramie"),   # truncated
        ("Pine Bluffs  High School", "pine bluffs"),
        ("St. Mary's", "st marys"),
        ("Port Meridian South", "port meridian south"),            # not a suffix
    ],
)
def test_normalize_strips_every_suffix_form(raw, expected):
    assert normalize(raw) == expected


@pytest.fixture(scope="module")
def resolver() -> Resolver:
    return Resolver.from_records(RECORDS)


@pytest.mark.parametrize(
    "raw,school,method",
    [
        ("Vista Terrace", "Vista Terrace", "exact"),
        ("Vista Terrace High School", "Vista Terrace", "normalized"),
        ("Norview  HS", "Norview", "normalized"),
        ("Copper Lake Eas", "Copper Lake East", "prefix"),
    ],
)
def test_resolution_ladder(resolver, raw, school, method):
    r = resolver.resolve(raw)
    assert (r.school, r.method) == (school, method)


def test_ambiguity_is_refused_not_guessed(resolver):
    """Choosing between Copper Lake / East / West would be invisibly wrong.

    Asserted on the SHAPE of the refusal, not on a fixed candidate list — the
    state gains schools, and a test pinned to three names fails for the wrong
    reason the moment a fourth Copper Lake opens.
    """
    r = resolver.resolve("Copper Lak")
    assert r.school is None and r.method == "unresolved"
    assert len(r.candidates) >= 2
    assert all(c.startswith("Copper Lak") for c in r.candidates)


def test_unknown_school_is_reported_not_invented(resolver):
    r = resolver.resolve("Nowhere Consolidated")
    assert r.school is None and r.method == "unresolved"
    assert resolver.school("Nowhere Consolidated") == "Nowhere Consolidated"


def test_resolution_rewrites_competitors_with_their_school():
    """A school renamed without its athletes orphans every one of them."""
    game = scorebook_csv.parse(str(BOX))[0]
    stale = "Ansotegui Siding High School"             # as an unfolded source would
    game.home = stale
    for s in game.box.home:
        s.competitor = type(s.competitor)(
            name=s.competitor.name, school=stale, year=s.competitor.year)
    r = Resolver.from_records(RECORDS)
    resolve_mod.apply_to_contest(game, r)
    assert game.home == "Ansotegui Siding"
    assert {s.competitor.school for s in game.box.home} == {"Ansotegui Siding"}


# ------------------------------------------------------- detection & records


@pytest.mark.parametrize(
    "filename,adapter",
    [
        ("hytek-mm-swimming-results.txt", "hytek_swim"),
        ("scorebook-basketball-boxscore.csv", "scorebook_csv"),
        ("dual-tennis-match-card.txt", "dual_card"),
        ("hytek-meetmanager8-track.pdf", "hytek_pdf"),
    ],
)
def test_adapter_detection(filename, adapter):
    assert detect(SPECIMENS / filename) == adapter


@pytest.mark.parametrize("path", [BOX, CARD, SWIM])
def test_every_import_round_trips_through_the_records_plane(path):
    """Whatever an adapter produces has to survive being written and read."""
    parse = {".csv": scorebook_csv.parse, ".txt": None}[path.suffix]
    if parse is None:
        parse = dual_card.parse if "card" in path.name else hytek_swim.parse
    contest = parse(str(path))[0]
    contest.sport = "boys-basketball"
    contest.season = "2026-27"
    first = records_io.contest_to_dict(contest, sequence=0)
    again = records_io.contest_to_dict(
        records_io.load_contest_dict(first), sequence=0)
    assert again == first


def test_box_score_survives_the_records_plane():
    game = scorebook_csv.parse(str(BOX))[0]
    game.sport, game.season = "boys-basketball", "2026-27"
    back = records_io.load_contest_dict(records_io.contest_to_dict(game))
    assert back.box is not None
    assert back.box.columns == game.box.columns
    assert len(back.box.away) == 8
    assert back.box.totals_agree("pts") is True
    assert back.provenance.external_ids["gameId"] == "JHSAA-BB-2027-05422"
    assert back.provenance.source_sha256 == game.provenance.source_sha256
