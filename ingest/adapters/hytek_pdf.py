"""
Hy-Tek MEET MANAGER printout -> :class:`app.shapes.Meet`.

This is the adapter that justifies the project. A state association runs a meet
in Hy-Tek, which holds every place, mark, grade, school, heat assignment and
qualifying flag as structured data — and then prints a PDF and discards it. The
PDF is what gets published. This reads it back.

The format specimen is ``ingest/fixtures/specimens/hytek-meetmanager8-track.pdf``:
a 237-page 2026 state-qualifying printout. It is kept as a FORMAT specimen, not
as a corpus — this project is day-one-forward and does not backfill history. The
file exists so the parser is written against real structure instead of an
invented one.

Layout, as observed
-------------------
Column anchors are stable within a page and drift a few points between pages,
so fields are resolved by x-band rather than by fixed offset::

    [18]  Event 105  Girls Long Jump 1A   Name  Yr  School  Finals  H#  Points
    [47]  1A2A East:  18-05  @  5/12/2022  Jordan Stoddard, Southeast
    [18]  Finals
    [35]1  [48]Moats, Kaylee  [204]10  [221]Southeast High School  [398]16-11.75  [498]2  [535]10
    [54]1) Dewey, Lathan 12  [180]2) Haskell, Alex 10  [306]3) Gerry, Kendyll 9
    [34]1) [48]Southeast High School [247]183.5   [304]2) [318]Lingle Ft. Laramie [528]144
    [187] Women - 1A - Team Rankings - 18 Events Scored

Events continue across pages with a ``... (Event 83 Girls 4x800 Meter Relay 3A)``
marker, which is how a relay's member lines stay attached to their entry.
"""

from __future__ import annotations

import datetime as _dt
import re

from app.shapes import (
    Competitor,
    Entry,
    Event,
    Mark,
    MarkType,
    Meet,
    Provenance,
    StandingRecord,
    TeamScore,
    parse_mark,
)
from ingest import pdftext

ADAPTER = "hytek_pdf"

# ------------------------------------------------------------------ patterns

_EVENT = re.compile(
    r"^Event\s+(\d+)\s+(Girls|Boys|Women|Men|Mixed)?\s*(.+?)"
    r"(?:\s+(Name\s+Yr\s+School.*))?$"
)
_ROUND = re.compile(r"^(Finals|Preliminaries|Semi-Finals|Quarterfinals)\b")
_CONTINUED = re.compile(r"^\.\.\.\s*\(Event\s+(\d+)")
_RECORD = re.compile(r"^(.+?):\s*(\S+)\s*[@#*]\s*(\S+)\s*(.*)$")
_RANKING_HEAD = re.compile(
    r"^(Women|Men|Girls|Boys)\s*-\s*(\S+)\s*-\s*Team Rankings\s*-\s*(\d+)\s+Events"
)
_TEAM_RANK = re.compile(r"^(\d+)\)$")
_RELAY_LEG = re.compile(r"(\d)\)\s*([^)]+?)(?=\s+\d\)|$)")
_MEET_TITLE = re.compile(r"^(\d{4})?\s*(.+?)\s*-\s*(\d+/\d+/\d{4})(?:\s*to\s*(\d+/\d+/\d{4}))?$")
_CLASS = re.compile(r"\b(\d+A(?:-\d+A)?|D[1-4]|Open|JV|Varsity)\s*$")

#: Event-name fragments that decide how a mark is read.
_FIELD_DISTANCE = ("Long Jump", "Triple Jump", "Shot Put", "Discus", "Javelin", "Hammer")
_FIELD_HEIGHT = ("High Jump", "Pole Vault")

# Column x-bands, from the observed layout. Bands rather than points because
# anchors drift a few units page to page (place sits at 29.8-35.0, marks at
# 397-411 depending on string width).
_BANDS = {
    "place": (25.0, 40.0),
    "name": (44.0, 60.0),
    "year": (195.0, 215.0),
    "school": (216.0, 320.0),
    "mark": (330.0, 425.0),
    "flag": (430.0, 450.0),
    "heat": (490.0, 505.0),
    "points": (525.0, 560.0),
}


def _band(x: float) -> str | None:
    for name, (lo, hi) in _BANDS.items():
        if lo <= x < hi:
            return name
    return None


def mark_type_for(event_name: str) -> MarkType:
    """Which kind of mark an event's results carry."""
    if any(k in event_name for k in _FIELD_DISTANCE):
        return MarkType.DISTANCE
    if any(k in event_name for k in _FIELD_HEIGHT):
        return MarkType.HEIGHT
    return MarkType.TIME


def _int(text: str | None) -> int | None:
    if not text:
        return None
    m = re.match(r"^(\d+)", text.strip())
    return int(m.group(1)) if m else None


def _float(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return float(text.strip())
    except ValueError:
        return None


def _split_class(name: str) -> tuple[str, str | None]:
    """Peel the classification off an event name: 'Girls Long Jump 1A' -> 1A."""
    m = _CLASS.search(name.strip())
    if not m:
        return name.strip(), None
    return name[: m.start()].strip(), m.group(1)


# -------------------------------------------------------------------- parsing


def _parse_result_row(row, mark_type: MarkType, relay: bool = False) -> Entry | None:
    """A placed result line. Returns None if the row isn't one.

    A relay prints the SCHOOL in the name column and emits no school cell at
    all — its athletes are listed on the following line instead. Requiring both
    columns silently drops every relay in the meet.
    """
    fields: dict[str, str] = {}
    for cell in row.cells:
        band = _band(cell.x)
        if band and band not in fields:
            fields[band] = cell.text

    place_raw = fields.get("place", "")
    if not re.match(r"^\d+$", place_raw.strip()):
        return None
    if "name" not in fields:
        return None
    if "school" not in fields and not relay:
        return None

    name = fields["name"].strip()
    school = fields.get("school", name).strip()
    year = (fields.get("year") or "").strip() or None
    if year in ("--", ""):
        year = None

    raw_mark = fields.get("mark")
    mark: Mark | None = parse_mark(raw_mark, mark_type) if raw_mark else None

    # A relay entry names the school in the name column, not a person.
    competitors: list[Competitor] = []
    if not relay and ("," in name or " " in name):
        competitors = [Competitor(name=name, school=school, year=year)]

    return Entry(
        place=int(place_raw),
        school=school,
        mark=mark,
        competitors=competitors,
        points=_float(fields.get("points")),
        heat=_int(fields.get("heat")),
        qualifier=(fields.get("flag") or "").strip() or None,
    )


def _parse_relay_legs(row, entry: Entry | None) -> None:
    """Attach '1) Dewey, Lathan 12  2) Haskell, Alex 10' to the entry above."""
    if entry is None:
        return
    text = row.text()
    legs = _RELAY_LEG.findall(text)
    if len(legs) < 2:
        return
    for _, leg in legs:
        leg = leg.strip()
        m = re.match(r"^(.+?)\s+(\d{1,2}|--)$", leg)
        if m:
            who, yr = m.group(1).strip(), m.group(2)
        else:
            who, yr = leg, None
        if who:
            entry.competitors.append(
                Competitor(name=who, school=entry.school, year=None if yr == "--" else yr)
            )


def _parse_team_ranks(row, gender: str | None, division: str | None) -> list[TeamScore]:
    """The two-up team-ranking table: '1) School 183.5   2) School 144'."""
    out: list[TeamScore] = []
    cells = list(row.cells)
    i = 0
    while i < len(cells):
        m = _TEAM_RANK.match(cells[i].text.strip())
        if m and i + 2 < len(cells):
            school = cells[i + 1].text.strip()
            pts = _float(cells[i + 2].text)
            if pts is not None and school:
                out.append(
                    TeamScore(
                        school=school,
                        points=pts,
                        rank=int(m.group(1)),
                        gender=gender,
                        division=division,
                    )
                )
            i += 3
            continue
        i += 1
    return out


def parse(path: str, source_uri: str | None = None) -> list[Meet]:
    """Read a Hy-Tek printout into every :class:`Meet` it contains."""
    pages = pdftext.load(path)
    return parse_pages(pages, source_uri=source_uri or path)


def parse_pages(pages: list[list], source_uri: str) -> list[Meet]:
    """Segment a printout into meets, then parse each.

    A published association "results PDF" is routinely a BUNDLE, not a contest.
    The format specimen looks like one document and is in fact six meets
    concatenated — 1A-2A East and West, 3A East and West, 4A East and West —
    each with its own venue, dates, and event numbering that restarts from 1.
    An adapter that parses the file as a single meet silently merges them: event
    1 collects every classification's 100m, several athletes tie for first, and
    the team scores are nonsense. Segmentation is not a refinement here, it is
    the difference between right and wrong.

    Meets are delimited by the running header, which repeats on every page and
    changes at the boundary.
    """
    meets: list[Meet] = []
    meet: Meet | None = None
    current: Event | None = None
    last_entry: Entry | None = None
    by_number: dict[tuple[int, str | None], Event] = {}
    rank_gender: str | None = None
    rank_division: str | None = None
    title: str | None = None
    # The venue is printed ABOVE the title line, so it is read before the meet
    # it belongs to exists. Hold the last lone centred row and claim it when the
    # title creates the meet.
    prev_lone: str | None = None

    def _provenance() -> Provenance:
        return Provenance(
            source_uri=source_uri,
            adapter=ADAPTER,
            extracted_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        )

    for page in pages:
        for row in page:
            text = row.text()
            if not text:
                continue
            first = row.cells[0]

            # --- the running header delimits meets
            m = _MEET_TITLE.match(text)
            if m and ("Meet" in text or "Regional" in text or "Championship" in text):
                name = m.group(2).strip()
                if name != title:
                    title = name
                    meet = Meet(name=name, provenance=_provenance())
                    meet.date, meet.end_date = m.group(3), m.group(4)
                    if prev_lone and ("School" in prev_lone or "," in prev_lone):
                        meet.venue = prev_lone
                    meets.append(meet)
                    current = last_entry = None
                    by_number = {}
                    rank_gender = rank_division = None
                elif meet is not None:
                    if meet.date is None:
                        meet.date, meet.end_date = m.group(3), m.group(4)
                    if meet.venue is None and prev_lone and "School" in prev_lone:
                        meet.venue = prev_lone
                continue

            # A lone centred row is a candidate venue for the title beneath it.
            if len(row.cells) == 1 and first.x > 150 and len(text) < 60:
                prev_lone = text

            if meet is None:
                continue

            # --- team rankings
            m = _RANKING_HEAD.match(text)
            if m:
                rank_gender = {"Women": "Girls", "Men": "Boys"}.get(m.group(1), m.group(1))
                rank_division = m.group(2)
                continue
            if rank_gender and _TEAM_RANK.match(first.text.strip()):
                found = _parse_team_ranks(row, rank_gender, rank_division)
                if found:
                    meet.team_scores.extend(found)
                    continue

            # --- event header
            if first.x < 20:
                m = _CONTINUED.match(text)
                if m:
                    n = int(m.group(1))
                    # A continuation names only the event number, so re-attach
                    # to the round already open rather than guessing.
                    if current is None or current.number != n:
                        for (num, _rnd), ev in by_number.items():
                            if num == n:
                                current = ev
                                break
                    continue
                # Match the header on its FIRST cell only. The cells after it
                # are column labels for a normal event but record-holder names
                # for a relay ("Event 65 Girls 4x100 Meter Relay 1A" followed by
                # "M Booth, B Mehling, …"), and joining them buries the
                # classification mid-string where it cannot be peeled off.
                head = row.cells[0].text
                labels = " ".join(c.text for c in row.cells[1:])
                m = _EVENT.match(head)
                if m:
                    number = int(m.group(1))
                    gender = m.group(2)
                    name, division = _split_class(m.group(3))

                    # An event number is reused across rounds: the SAME number
                    # is printed for the prelims and again for the final. The
                    # round is carried in the column labels — "… Prelims H#"
                    # versus "… Finals Points" — so key on (number, round).
                    # Keying on number alone stacks both rounds into one event
                    # and every place appears twice.
                    if "Prelims" in labels:
                        rnd = "Preliminaries"
                    elif "Finals" in labels:
                        rnd = "Finals"
                    else:
                        rnd = None

                    key = (number, rnd)
                    if key in by_number:
                        current = by_number[key]
                    else:
                        current = Event(
                            number=number,
                            name=name,
                            gender=gender,
                            division=division,
                            round=rnd,
                            mark_type=mark_type_for(name),
                        )
                        by_number[key] = current
                        meet.events.append(current)
                    last_entry = None
                    continue
                m = _ROUND.match(text)
                if m and current is not None:
                    if current.round is None:
                        current.round = m.group(1)
                    continue

            if current is None:
                continue

            # --- standing record line, e.g. "1A2A East: 18-05 @ 5/12/2022 Jordan…"
            if 40 < first.x < 120 and ":" in text:
                m = _RECORD.match(text)
                if m:
                    scope, raw, date, who = m.groups()
                    holder, _, school = (who or "").partition(",")
                    current.records.append(
                        StandingRecord(
                            scope=scope.strip(),
                            mark=parse_mark(raw, current.mark_type),
                            holder=holder.strip() or None,
                            school=school.strip() or None,
                            date=date,
                        )
                    )
                    continue

            # --- relay legs continue the entry above
            if first.x > 45 and _RELAY_LEG.search(text) and "High School" not in first.text:
                _parse_relay_legs(row, last_entry)
                continue

            # --- a placed result
            entry = _parse_result_row(
                row, current.mark_type, relay="Relay" in current.name
            )
            if entry is not None:
                current.entries.append(entry)
                last_entry = entry

    for mt in meets:
        mt.events = [e for e in mt.events if e.entries]
    return [mt for mt in meets if mt.events]
