"""
Hy-Tek MEET MANAGER **text** results report (swimming & diving) -> :class:`Meet`.

Why this is a second adapter and not a flag on ``hytek_pdf``
-----------------------------------------------------------
Same vendor, same report engine, materially different document — enough so that
sharing a parser would mean a conditional on every branch:

* **It is text, not positioned PDF.** ``hytek_pdf`` resolves fields by x-band
  because a PDF has no columns, only glyphs at coordinates. A text report has
  real whitespace, so fields come from run-of-spaces splitting instead. None of
  the band logic transfers.
* **Two result rows per event, not one.** Swimming prints a *seed* time next to
  the *finals* time. A parser that takes "the last time on the line" as the
  result records the seed for every swimmer who was scratched, because the
  finals column is then blank.
* **Splits.** ``25.11  53.44 (28.33)  1:21.02 (27.58)`` continues the row above
  and is the richest data in the document. It looks exactly like a result row
  that lost its place number.
* **Relays print a leg letter** (``A``/``B``) where an individual prints a grade,
  and a school's B relay routinely scores.
* **Diving is scored, not timed** — ``Seed Score``/``Finals Score`` in the same
  report, so the mark type is a property of the event's COLUMN HEADER, not of
  the meet.

Provenance note
---------------
Unlike ``hytek_pdf``, whose specimen is a real 237-page published printout, this
adapter's fixture is a *reconstruction* of the MM text layout — the column
semantics are taken from the captured PDF specimen, but the file itself was
written for this repository. That is a weaker footing than the project's "no
format is coded from memory" rule wants, and it is recorded here rather than
left for someone to discover: the individual/relay/splits/diving row shapes are
right, but real-world MM text reports will carry variants this has never seen.
"""

from __future__ import annotations

import datetime as _dt
import re

from app.shapes import (
    Competitor,
    Entry,
    Event,
    MarkType,
    Meet,
    Provenance,
    SourceType,
    StandingRecord,
    TeamScore,
    parse_mark,
)

ADAPTER = "hytek_swim"
VERSION = "1"

_EVENT = re.compile(r"^Event\s+(\d+)\s+(Girls|Boys|Women|Men|Mixed)\s+(.+?)\s*$")
_HEADER = re.compile(r"^\s+(Name|Team)\b.*(Finals\s+(?:Time|Score))", re.I)
_RULE = re.compile(r"^=+\s*$")
_RECORD = re.compile(r"^\s{2,}(.+?):\s*[!%#*@]?\s*(\S+)\s+(\d+/\d+/\d{4})\s*(.*)$")
_RANKING = re.compile(
    r"^(Girls|Boys|Women|Men)\s*-\s*(\S+)\s*-\s*Team Rankings", re.I
)
_RANK_ROW = re.compile(r"(\d+)\)\s+(.+?)\s{2,}(\d+(?:\.\d+)?)")
_LEG = re.compile(r"\d\)\s*([^)]+?)(?=\s{2,}\d\)|\s*$)")
_SPLIT = re.compile(r"^\s{4,}\d{1,2}?:?\d{1,2}\.\d{2}\b")
_YEAR = r"(?:1[0-2]|[7-9]|--)"

#: An individual row: place, "Last, First", grade, school, seed, finals, points.
_INDIV = re.compile(
    r"^\s*(\d+|--)\s+"
    r"(\S[^\d]*?,\s*\S[^\d]*?)\s{2,}"
    rf"({_YEAR})\s+"
    r"(\S.*?)\s{2,}"
    r"(\S+)"
    r"(?:\s+(\S+))?"
    r"(?:\s+(\d+))?\s*$"
)

#: A relay row: place, school, relay letter, seed, finals, points.
_RELAY = re.compile(
    r"^\s*(\d+|--)\s+"
    r"(\S.*?)\s{2,}"
    r"([A-D])\s{2,}"
    r"(\S+)"
    r"(?:\s+(\S+))?"
    r"(?:\s+(\d+))?\s*$"
)


def _iso(text: str | None) -> str | None:
    """Hy-Tek prints US dates; every record in this project stores ISO.

    Left as printed, a meet sorts as a string against ISO neighbours and lands
    in the wrong place on every schedule it appears on — while still looking
    like a date on its own page.
    """
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", (text or "").strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else (text or None)


def _grade(text: str | None) -> str | None:
    t = (text or "").strip()
    return None if t in ("", "--") else t


def _points(text: str | None) -> float | None:
    try:
        return float(text) if text else None
    except ValueError:
        return None


def parse(path: str, source_uri: str | None = None) -> list[Meet]:
    text = open(path, encoding="utf-8", errors="replace").read()
    return parse_text(text, source_uri=source_uri or path)


def parse_text(text: str, source_uri: str) -> list[Meet]:
    """Read one MM text results report into a single :class:`Meet`.

    A text report is one meet, unlike the PDF bundle — the report is generated
    per meet. Segmentation is therefore not this adapter's problem.
    """
    prov = Provenance(
        source_uri=source_uri,
        adapter=ADAPTER,
        adapter_version=VERSION,
        extracted_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        source_type=SourceType.HYTEK_PDF,
    )
    meet = Meet(name="", provenance=prov, sport=None)

    current: Event | None = None
    last: Entry | None = None
    is_relay = False
    rank_gender: str | None = None
    rank_division: str | None = None
    in_results = False

    lines = text.splitlines()
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        if not line.strip():
            continue

        # --- meet identity: the two centred lines under the licence banner
        if not meet.name and "HY-TEK" in line.upper():
            for nxt in lines[i + 1 : i + 5]:
                nxt = nxt.strip()
                if not nxt:
                    continue
                if not meet.name:
                    meet.name = nxt
                    continue
                m = re.match(r"^(.*?)\s+-\s+(\d+/\d+/\d{4})(?:\s+to\s+(\d+/\d+/\d{4}))?$", nxt)
                if m:
                    meet.venue = m.group(1).strip()
                    meet.date, meet.end_date = _iso(m.group(2)), _iso(m.group(3))
                break
            continue

        # --- team rankings close out the report
        m = _RANKING.match(line.strip())
        if m:
            rank_gender = {"Women": "Girls", "Men": "Boys"}.get(m.group(1), m.group(1))
            rank_division = m.group(2)
            current, in_results = None, False
            continue
        if rank_gender and _RANK_ROW.search(line):
            for rank, school, pts in _RANK_ROW.findall(line):
                meet.team_scores.append(
                    TeamScore(school=school.strip(), points=float(pts), rank=int(rank),
                              gender=rank_gender, division=rank_division))
            continue

        # --- event header
        m = _EVENT.match(line.strip())
        if m:
            number, gender, name = int(m.group(1)), m.group(2), m.group(3).strip()
            gender = {"Women": "Girls", "Men": "Boys"}.get(gender, gender)
            is_relay = "Relay" in name
            current = Event(number=number, name=name, gender=gender,
                            round="Finals", mark_type=MarkType.TIME)
            meet.events.append(current)
            last, in_results = None, False
            continue

        if current is None:
            continue

        # --- the column header decides how the mark is read. Diving prints
        #     "Finals Score" in the same report as "Finals Time"; the event NAME
        #     is not reliable ("1 mtr Diving" is, "Platform" would not be).
        m = _HEADER.match(line)
        if m:
            if "score" in m.group(2).lower():
                current.mark_type = MarkType.POINTS
            continue
        if _RULE.match(line):
            in_results = True
            continue

        # --- a standing record printed above the event
        if not in_results:
            m = _RECORD.match(line)
            if m and current is not None:
                scope, raw_mark, date, who = m.groups()
                holder, _, school = (who or "").partition(",")
                current.records.append(StandingRecord(
                    scope=scope.strip(), mark=parse_mark(raw_mark, current.mark_type),
                    holder=holder.strip() or None, school=school.strip() or None,
                    date=date))
            continue

        # --- splits continue the entry above. Tested BEFORE relay legs, and
        #     legs are anchored to the START of the line, because a cumulative
        #     split carries its interval in parentheses — "1:21.02 (27.58)" —
        #     and the "8)" inside one matches an unanchored leg marker. Ordered
        #     the other way the splits row is swallowed by the leg branch and
        #     every split in the meet is dropped without an error.
        if last is not None and _SPLIT.match(line) and "(" in line:
            splits = " ".join(line.split())
            # An individual row already parked its seed time here; keep both
            # rather than letting whichever is parsed last win.
            last.note = f"{last.note} · {splits}" if last.note else splits
            continue

        # --- relay legs continue the entry above
        if last is not None and re.match(r"^\s*\d\)\s*\S", line):
            for who in _LEG.findall(line):
                who = who.strip()
                mm = re.match(rf"^(.+?)\s+({_YEAR})$", who)
                name, yr = (mm.group(1), mm.group(2)) if mm else (who, None)
                if name:
                    last.competitors.append(
                        Competitor(name=name.strip(), school=last.school, year=_grade(yr)))
            continue

        entry = _relay_row(line, current) if is_relay else _indiv_row(line, current)
        if entry is not None:
            current.entries.append(entry)
            last = entry

    meet.events = [e for e in meet.events if e.entries]
    return [meet] if meet.events else []


def _finals(seed: str | None, finals: str | None) -> str:
    """The RESULT column, which is the second time when there is one.

    A scratched swimmer prints a seed time and nothing after it. Taking the last
    token on the line would silently promote every seed time to a result.
    """
    return (finals if finals else seed) or ""


def _indiv_row(line: str, ev: Event) -> Entry | None:
    m = _INDIV.match(line)
    if not m:
        return None
    place, name, yr, school, seed, finals, pts = m.groups()
    school = school.strip()
    if not school:
        return None
    result = _finals(seed, finals)
    return Entry(
        place=None if place == "--" else int(place),
        school=school,
        mark=parse_mark(result, ev.mark_type),
        competitors=[Competitor(name=name.strip(), school=school, year=_grade(yr))],
        points=_points(pts),
        note=f"seed {seed}" if finals else None,
    )


def _relay_row(line: str, ev: Event) -> Entry | None:
    m = _RELAY.match(line)
    if not m:
        return None
    place, school, letter, seed, finals, pts = m.groups()
    result = _finals(seed, finals)
    return Entry(
        place=None if place == "--" else int(place),
        school=school.strip(),
        mark=parse_mark(result, ev.mark_type),
        points=_points(pts),
        # The relay letter matters: a school's B relay is a different entry and
        # in many associations scores separately.
        qualifier=letter,
    )
