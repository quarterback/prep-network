"""
Dual-match card (fixed-width text) -> :class:`app.shapes.Dual`.

Column boundaries are taken from the card's own rule line::

    LINE FLIGHT      HOME PLAYER(S)          VISITOR PLAYER(S)       WON   SCORE
    ---- ----------- ----------------------- ----------------------- ----- ------

Deriving the spans from the run-lengths of that rule is the whole trick, and it
is why this adapter does not carry a table of offsets. A dual card's widths move
with the longest name in the field — a match with "Academy of Arts and
Communication" on it lays out differently from one without — so hard-coded
offsets work on the file they were written against and silently slice names in
half on the next one. The rule line is generated from the same widths as the
rows beneath it, so it is always correct for the file in hand.

Two structural things the card does that a naive line-per-result reader gets
wrong:

* **A doubles line spans two rows.** The partners are on a continuation row with
  an empty LINE cell. Read row-by-row, every doubles team loses a player and the
  continuation row becomes a phantom tenth line.
* **The winner is a column, not a comparison.** ``6-7 (5)`` in the score column
  contains a tiebreak whose digits invite a parser to decide the match itself.
  It doesn't need to: ``WON`` says HOME or AWAY, and third-set match tiebreaks
  (``8-10``) would defeat set-counting anyway.

Team points are recomputed from the lines and checked against the card's printed
``TEAM RESULT``, the same checksum discipline the rest of the pipeline uses.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import re

from app.shapes import (
    Competitor,
    Dual,
    Line,
    Provenance,
    ReviewState,
    SourceType,
)

ADAPTER = "dual_card"
VERSION = "1"

_RULE = re.compile(r"^-{3,}(?:\s+-{3,})+\s*$")
_HEAD = re.compile(r"^([A-Za-z ]+?)\s*:\s*(.+?)\s*$")
_PLAYER = re.compile(r"^(.*?)\s*\((\d{1,2})\)\s*$")
_LINE_ID = re.compile(r"^([SD])(\d+)$")
_TEAM_RESULT = re.compile(r"^(.*?)\s+(\d+),\s*(.*?)\s+(\d+)\s*$")


def _spans(rule: str) -> list[tuple[int, int]]:
    """Column (start, end) pairs from a run of dashes."""
    return [(m.start(), m.end()) for m in re.finditer(r"-+", rule)]


def _cells(line: str, spans: list[tuple[int, int]]) -> list[str]:
    # The last column runs to end-of-line: a score can overflow its rule width.
    out = []
    for i, (a, b) in enumerate(spans):
        out.append((line[a:] if i == len(spans) - 1 else line[a:b]).strip())
    return out


def _competitor(text: str, school: str) -> Competitor | None:
    text = text.strip()
    if not text:
        return None
    m = _PLAYER.match(text)
    name, year = (m.group(1), m.group(2)) if m else (text, None)
    return Competitor(name=name.strip(), school=school, year=year)


def _date(text: str) -> str | None:
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", (text or "").strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def parse(path: str, source_uri: str | None = None) -> list[Dual]:
    data = open(path, "rb").read()
    return parse_text(
        data.decode("utf-8", errors="replace"),
        source_uri=source_uri or path,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def parse_text(text: str, source_uri: str, sha256: str | None = None) -> list[Dual]:
    lines = text.splitlines()

    head: dict[str, str] = {}
    spans: list[tuple[int, int]] = []
    body_start = None
    printed: tuple[str, int, str, int] | None = None
    clinched_label: str | None = None

    for i, line in enumerate(lines):
        if _RULE.match(line):
            spans = _spans(line)
            body_start = i + 1
            continue
        if body_start is None:
            m = _HEAD.match(line)
            if m:
                head[m.group(1).strip().lower()] = m.group(2).strip()
        else:
            m = _HEAD.match(line)
            if m and m.group(1).strip().lower() == "team result":
                r = _TEAM_RESULT.match(m.group(2))
                if r:
                    printed = (r.group(1).strip(), int(r.group(2)),
                               r.group(3).strip(), int(r.group(4)))
            elif m and m.group(1).strip().lower() == "clinched at":
                clinched_label = m.group(2).strip()

    home_school = head.get("home", "")
    away_school = head.get("visitor") or head.get("away", "")
    if not (home_school and away_school and spans):
        return []

    dual = Dual(
        name=f"{away_school} at {home_school}",
        date=_date(head.get("date", "")),
        venue=head.get("site") or None,
        home=home_school,
        away=away_school,
    )

    current: Line | None = None
    for line in lines[body_start:]:
        if not line.strip() or _HEAD.match(line):
            continue
        cells = _cells(line, spans)
        if len(cells) < 5:
            continue
        ident, flight, home_txt, away_txt, won = cells[0], cells[1], cells[2], cells[3], cells[4]
        score = cells[5] if len(cells) > 5 else ""

        m = _LINE_ID.match(ident)
        if m:
            kind = "singles" if m.group(1) == "S" else "doubles"
            current = Line(
                slot=int(m.group(2)),
                kind=kind,
                winner={"HOME": "home", "AWAY": "away"}.get(won.upper()),
                score=score or None,
            )
            dual.lines.append(current)
        elif current is None:
            continue
        # Both the first row of a line and its continuation carry players.
        for txt, school, side in (
            (home_txt, home_school, current.home),
            (away_txt, away_school, current.away),
        ):
            c = _competitor(txt, school)
            if c:
                side.append(c)

    h, a = dual.compute_points()
    dual.home_points, dual.away_points = h, a
    if clinched_label:
        m = _LINE_ID.match(clinched_label.replace("Line", "").strip())
        if m:
            dual.clinched_at = int(m.group(2))

    # --- checksum against the card's own TEAM RESULT
    notes = None
    confidence = 1.0
    if printed:
        want = {printed[0]: printed[1], printed[2]: printed[3]}
        got = {home_school: h, away_school: a}
        if want != got:
            confidence = 0.5
            notes = f"printed {want} vs computed {got}"

    dual.provenance = Provenance(
        source_uri=source_uri,
        adapter=ADAPTER,
        adapter_version=VERSION,
        extracted_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        source_type=SourceType.DUAL_CSV,
        source_sha256=sha256,
        confidence=confidence,
        review_state=ReviewState.PUBLISHED if notes is None else ReviewState.NEEDS_REVIEW,
        external_ids={k: v for k, v in (("matchId", head.get("match id", "")),) if v},
        notes=notes,
    )
    return [dual]
