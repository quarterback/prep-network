"""
The records plane must be lossless: parse -> JSON -> shapes -> JSON identical.

If this fails, the managed layer silently drifts from what the adapter saw,
and every downstream page renders from corrupted records while looking fine.
"""

from __future__ import annotations

import pathlib

import pytest

from app import records_io
from ingest.adapters import hytek_pdf

SPECIMEN = (
    pathlib.Path(__file__).parent.parent
    / "ingest/fixtures/specimens/hytek-meetmanager8-track.pdf"
)


@pytest.fixture(scope="module")
def meets():
    return hytek_pdf.parse(str(SPECIMEN))


def test_round_trip_is_lossless(meets, tmp_path_factory):
    """Write every meet to JSON, read it back, compare canonical dicts.

    Covers the hard cases in one pass because the specimen contains them all:
    relays with legs, standing records, Q/q qualifiers, prelims/finals splits,
    unscored non-marks, and the blank-mark finals winner.
    """
    tmp = tmp_path_factory.mktemp("records")
    for i, m in enumerate(meets):
        records_io.write_meet(
            tmp / "contests" / "2026" / f"m{i}.json", m, sequence=i
        )
    loaded = records_io.load_contests(tmp)
    assert len(loaded) == len(meets)
    for a, b in zip(meets, loaded):
        assert records_io.meet_to_dict(a) == records_io.meet_to_dict(b), a.name


def test_sequence_preserves_meet_order(meets, tmp_path_factory):
    """Meet order is meaning (regionals then state); globbing is alphabetical,
    so order must ride on the stored sequence, not the filename."""
    tmp = tmp_path_factory.mktemp("records")
    for i, m in enumerate(meets):
        # filenames alphabetize in REVERSE of sequence on purpose
        records_io.write_meet(tmp / "contests" / "2026" / f"{9 - i}.json", m, sequence=i)
    loaded = records_io.load_contests(tmp)
    assert [m.name for m in loaded] == [m.name for m in meets]
