"""
Electronic-scorebook CSV export -> :class:`app.shapes.Game` with a box score.

The shape of the problem, and why the columns are not named here
---------------------------------------------------------------
A scorebook export is a **row-typed** CSV: not one table but several stacked in
one file, each line tagged with what it is (``GAME``, ``TEAM``, ``LINESCORE``,
``PLAYER``, ``TOTALS``). ``csv.DictReader`` is the wrong tool — there is no
single header row — so rows are dispatched on their first field, which is how
the format is actually designed to be read.

The stat columns come from the file's own ``PLAYER`` header row and are carried
through to the record **in source order, unrenamed**. That is deliberate:
basketball prints FG/3PT/FT/REB/AST, volleyball prints K/E/TA/DIG, hockey prints
G/A/PIM, and a mapping table here would be a list of sports in the ingest layer
— the one thing the contest model is built to avoid. The renderer prints the
columns it is given without knowing what they mean.

Totals are read as printed, never summed. A scorebook's TOTALS row is the
operator's own arithmetic and disagreeing with it is a fact worth surfacing:
:meth:`app.shapes.BoxScore.totals_agree` is what a review queue reads, and this
adapter drops ``confidence`` when the file fails its own checksum rather than
quietly correcting it.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import re

from app.shapes import (
    BoxScore,
    Competitor,
    Game,
    Period,
    Provenance,
    ReviewState,
    SourceType,
    StatLine,
)

ADAPTER = "scorebook_csv"
VERSION = "1"

#: Columns that identify the row rather than describe performance. They are
#: stripped from the stat set so the box score's columns are only statistics.
_NON_STAT = {"teamCode", "team", "no", "name", "yr", "gs"}


def _date(text: str) -> str | None:
    text = (text or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def _int(text: str) -> int | None:
    try:
        return int((text or "").strip())
    except ValueError:
        return None


def parse(path: str, source_uri: str | None = None) -> list[Game]:
    data = open(path, "rb").read()
    return parse_text(
        data.decode("utf-8", errors="replace"),
        source_uri=source_uri or path,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def parse_text(text: str, source_uri: str, sha256: str | None = None) -> list[Game]:
    rows = list(csv.reader(io.StringIO(text)))

    meta: dict[str, str] = {}
    teams: dict[str, dict] = {}          # role -> {school, code, conference, final}
    code_to_role: dict[str, str] = {}
    linescore: dict[str, list[str]] = {}
    columns: list[str] = []
    sections: dict[str, list[str]] = {}
    section = ""
    players: dict[str, list[StatLine]] = {"home": [], "away": []}
    totals: dict[str, dict[str, str]] = {"home": {}, "away": {}}
    game_header: list[str] = []
    player_header: list[str] = []
    line_header: list[str] = []

    for row in rows:
        if not row or not row[0].strip() or row[0].lstrip().startswith("#"):
            continue
        tag = row[0].strip()
        cells = [c.strip() for c in row]

        if tag == "GAME":
            # The tag's first appearance is its header; the second is its data.
            if not game_header:
                game_header = cells
            else:
                meta = dict(zip(game_header[1:], cells[1:]))
        elif tag == "TEAM":
            if cells[1] in ("role",):
                continue
            role = cells[1]
            teams[role] = {
                "school": cells[2], "code": cells[3],
                "conference": cells[4] if len(cells) > 4 else None,
                "final": cells[5] if len(cells) > 5 else None,
            }
            code_to_role[cells[3]] = role
        elif tag == "LINESCORE":
            if cells[1] in ("teamCode", "team"):
                line_header = cells
            else:
                linescore[cells[1]] = cells[2:]
        elif tag == "SECTION":
            # A sport with more than one table restates the PLAYER header per
            # section, because the columns differ: football prints PASSING then
            # RUSHING then RECEIVING, baseball prints BATTING then PITCHING.
            # One column set per game cannot hold either.
            section = cells[1]
            player_header = []
            continue
        elif tag == "PLAYER":
            if not player_header:
                player_header = cells
                cols = [c for c in cells[1:] if c not in _NON_STAT]
                if section:
                    sections[section] = cols
                else:
                    columns = cols
                continue
            fields = dict(zip(player_header[1:], cells[1:]))
            role = code_to_role.get(cells[1])
            if role is None:
                continue
            cols = sections.get(section) or columns
            players[role].append(
                StatLine(
                    competitor=Competitor(
                        name=fields.get("name", ""),
                        school=teams[role]["school"],
                        year=fields.get("yr") or None,
                    ),
                    stats={k: v for k, v in fields.items() if k in cols and v != ""},
                    starter=fields.get("gs") == "1",
                    section=section,
                )
            )
        elif tag == "TOTALS":
            role = code_to_role.get(cells[1])
            if role is None or not player_header:
                continue
            # The TOTALS row is positional against the PLAYER header and leaves
            # the identity columns empty; zip against the same header so a
            # column lands in the same place it does for a player.
            fields = dict(zip(player_header[1:], cells[1:]))
            cols = sections.get(section) or columns
            if section:
                # Per-section totals would need a per-section slot; the sports
                # that use sections print a total only for the whole side, so
                # this keeps the last one rather than inventing structure.
                totals[role] = {**totals.get(role, {}),
                                **{k: v for k, v in fields.items() if k in cols and v != ""}}
            else:
                totals[role] = {k: v for k, v in fields.items() if k in cols and v != ""}

    if "home" not in teams or "away" not in teams:
        return []

    box = BoxScore(
        columns=columns or (next(iter(sections.values())) if sections else []),
        home=players["home"], away=players["away"],
        home_totals=totals["home"], away_totals=totals["away"],
        sections=sections,
    )

    periods: list[Period] = []
    if linescore and line_header:
        labels = [c for c in line_header[2:] if c.upper() != "FINAL"]
        hs = linescore.get(teams["home"]["code"], [])
        as_ = linescore.get(teams["away"]["code"], [])
        for i, label in enumerate(labels):
            h, a = _int(hs[i] if i < len(hs) else ""), _int(as_[i] if i < len(as_) else "")
            if h is None and a is None:
                continue            # an unplayed overtime column, not a 0-0 period
            periods.append(Period(label=label, home=h or 0, away=a or 0))

    game = Game(
        name=f"{teams['away']['school']} at {teams['home']['school']}",
        date=_date(meta.get("date", "")),
        venue=meta.get("venue") or None,
        status=(meta.get("status") or "final").lower(),
        home=teams["home"]["school"],
        away=teams["away"]["school"],
        home_score=_int(teams["home"]["final"] or ""),
        away_score=_int(teams["away"]["final"] or ""),
        periods=periods,
        box=box,
    )

    # --- the file's own checksums decide whether this is publishable
    failures = [] if box.sections else [
        c for c in columns if box.totals_agree(c) is False]
    if game.periods_agree() is False:
        failures.append("linescore")
    confidence = 1.0 if not failures else 0.5
    game.provenance = Provenance(
        source_uri=source_uri,
        adapter=ADAPTER,
        adapter_version=VERSION,
        extracted_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        source_type=SourceType.BOXSCORE_CSV,
        source_sha256=sha256,
        confidence=confidence,
        review_state=ReviewState.PUBLISHED if not failures else ReviewState.NEEDS_REVIEW,
        external_ids={k: v for k, v in (("gameId", meta.get("gameId", "")),) if v},
        notes=None if not failures else "totals disagree: " + ", ".join(failures),
    )
    return [game]
