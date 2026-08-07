"""
Adapter fidelity against the real format specimen.

These assertions are hand-checked against the printed PDF. They exist to pin the
things that break silently and plausibly: kerning-split names, meets bundled into
one file, and marks that look like numbers but aren't.
"""

from __future__ import annotations

import pathlib

import pytest

from app.shapes import MarkType, Shape, parse_mark, score_meet
from ingest.adapters import hytek_pdf

SPECIMEN = (
    pathlib.Path(__file__).parent.parent
    / "ingest/fixtures/specimens/hytek-meetmanager8-track.pdf"
)


@pytest.fixture(scope="module")
def meets():
    return hytek_pdf.parse(str(SPECIMEN))


# ------------------------------------------------------------- segmentation


def test_specimen_is_a_bundle_of_seven_meets(meets):
    """One published 'results PDF' is not one contest.

    The specimen looks like a single document and is six regionals plus the
    state championships. Parsing it as one meet merges every classification's
    100m into event 1 and produces three athletes tied for first.
    """
    names = [m.name for m in meets]
    assert len(meets) == 7, names
    assert "WHSAA 1A-2A East Regional Meet" in names
    assert "WHSAA State Track & Field Championships" in names


def test_each_meet_carries_its_own_venue_and_dates(meets):
    by_name = {m.name: m for m in meets}
    east = by_name["WHSAA 1A-2A East Regional Meet"]
    assert east.date == "5/15/2026"
    assert east.end_date == "5/16/2026"
    assert east.venue == "Torrington High School"

    state = by_name["WHSAA State Track & Field Championships"]
    assert state.venue is not None and "Kelly Walsh" in state.venue
    assert state.date == "5/21/2026"


# ------------------------------------------------------------------ results


def _event(meets, meet_name, number):
    meet = next(m for m in meets if m.name == meet_name)
    return next(e for e in meet.events if e.number == number)


def test_places_are_unique_and_ordered(meets):
    ev = _event(meets, "WHSAA 1A-2A East Regional Meet", 1)
    places = [e.place for e in ev.entries]
    assert places == sorted(places)
    assert len(places) == len(set(places)), "merged meets produce duplicate places"


def test_first_event_parses_exactly(meets):
    ev = _event(meets, "WHSAA 1A-2A East Regional Meet", 1)
    assert ev.gender == "Girls"
    assert ev.name == "100 Meter Dash"
    assert ev.division == "1A"
    assert ev.mark_type is MarkType.TIME

    winner = ev.entries[0]
    assert winner.place == 1
    assert winner.school == "Kaycee  High School"
    assert winner.mark.raw == "13.08"
    assert winner.mark.value == pytest.approx(13.08)
    assert winner.qualifier == "Q"
    assert winner.heat == 2
    assert winner.competitors[0].name == "Davis, Alaina"
    assert winner.competitors[0].year == "12"


def test_kerning_split_names_are_rejoined_in_emission_order(meets):
    """`Salway, Taelynn` is emitted as `Salwa` + `y, Taelynn` at one anchor.

    Sorting those fragments by x alone yields `y, TaelynnSalwa`, which looks
    plausible enough to ship. This is the single most likely silent corruption
    in the whole pipeline.
    """
    ev = _event(meets, "WHSAA 1A-2A East Regional Meet", 1)
    names = [e.competitors[0].name for e in ev.entries if e.competitors]
    assert "Salway, Taelynn" in names
    assert not any(n.startswith("y,") for n in names)


def test_standing_records_are_captured(meets):
    ev = _event(meets, "WHSAA 1A-2A East Regional Meet", 1)
    assert ev.records, "the record line above an event carries real history"
    rec = ev.records[0]
    assert rec.mark.value == pytest.approx(12.56)
    assert rec.holder == "Maggie Ochsner"


def test_field_events_parse_feet_inches(meets):
    """A distance is `16-11.75`, not a number. Read as a float it becomes 16."""
    meet = next(m for m in meets if m.name == "WHSAA 1A-2A East Regional Meet")
    ev = next(e for e in meet.events if "Long Jump" in e.name)
    assert ev.mark_type is MarkType.DISTANCE
    best = ev.entries[0].mark
    assert "-" in best.raw
    assert best.value == pytest.approx(int(best.raw.split("-")[0]) * 12
                                       + float(best.raw.split("-")[1]))


def test_team_rankings_are_extracted(meets):
    meet = next(m for m in meets if m.name == "WHSAA 1A-2A East Regional Meet")
    assert meet.team_scores
    top = [t for t in meet.team_scores if t.rank == 1]
    assert top and all(t.points > 0 for t in top)


def test_every_meet_has_events_and_schools(meets):
    for m in meets:
        assert m.shape is Shape.MEET
        assert m.events, m.name
        assert m.schools, m.name
        assert m.provenance is not None and m.provenance.adapter == "hytek_pdf"


# -------------------------------------------------------------------- marks


@pytest.mark.parametrize(
    "raw,type,expected",
    [
        ("13.08", MarkType.TIME, 13.08),
        ("2:05.44", MarkType.TIME, 125.44),
        ("16-11.75", MarkType.DISTANCE, 203.75),
        ("5-04.00", MarkType.HEIGHT, 64.0),
        ("45.72m", MarkType.DISTANCE, 45.72 * 39.3701),
    ],
)
def test_mark_parsing(raw, type, expected):
    m = parse_mark(raw, type)
    assert m.value == pytest.approx(expected)
    assert m.raw == raw, "the printed string is never discarded"
    assert m.scored


@pytest.mark.parametrize("raw", ["DNF", "DQ", "NM", "SCR", "--"])
def test_non_marks_are_kept_but_unscored(raw):
    """'She was disqualified' is information, not a missing value."""
    m = parse_mark(raw, MarkType.TIME)
    assert m.value is None
    assert not m.scored
    assert m.raw == raw


def test_team_scores_are_derived_not_trusted(meets):
    """A printed team-score table is a checksum, never an input."""
    meet = next(m for m in meets if m.name == "WHSAA 1A-2A East Regional Meet")
    derived = score_meet(meet)
    assert derived, "scoring must produce results from entries alone"
    assert all(t.rank and t.rank >= 1 for t in derived)


def test_relays_parse_with_their_legs(meets):
    """A relay prints the school in the name column and its athletes below.

    Requiring a school cell — as every other result row has — dropped all 73
    relay events silently. The meet still looked complete because the other
    events were fine.
    """
    state = next(m for m in meets if "State" in m.name)
    relays = [e for e in state.events if "Relay" in e.name and e.entries]
    assert relays, "relay events must not be dropped"

    ev = next(e for e in relays if e.number == 65)
    winner = ev.entries[0]
    assert winner.school == "Southeast High School"
    assert winner.is_relay
    assert len(winner.competitors) == 4
    assert [c.name for c in winner.competitors] == [
        "Mackenzie Booth",
        "Bailey Mehling",
        "Rory Mehling",
        "Kaylee Moats",
    ]
    assert winner.competitors[0].year == "9"


def test_relay_event_keeps_its_classification(meets):
    """A relay header puts record-holders where column labels normally sit.

    Matching the header on the joined row buries the '1A' mid-string and the
    classification is lost, so every relay lands in an unclassified bucket.
    """
    state = next(m for m in meets if "State" in m.name)
    ev = next(e for e in state.events if e.number == 65)
    assert ev.division == "1A"
    assert ev.name == "4x100 Meter Relay"
    assert ev.gender == "Girls"
