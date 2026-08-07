"""
Records plane: `app.shapes` dataclasses ↔ canonical JSON.

One file per contest under `records/contests/<season>/`. These JSON shapes are
the managed layer — what entry forms, uploads and hand edits produce — and they
double as the draft `org.prepnet.*` lexicons, which is why serialization is
explicit rather than `dataclasses.asdict` magic: the on-disk shape is a schema
commitment, not an implementation detail.

`$type` carries a `.temp.` NSID per the AT Protocol style guide for schemas
still in motion; stabilizing it is a Phase-B decision, not a rename hazard now.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from app.shapes import (
    Competitor,
    Entry,
    Event,
    Mark,
    MarkType,
    Meet,
    Provenance,
    ReviewState,
    StandingRecord,
    TeamScore,
)

MEET_TYPE = "org.prepnet.temp.contest.meet"


# ---------------------------------------------------------------- to JSON


def _mark(m: Mark | None) -> dict | None:
    if m is None:
        return None
    return {"raw": m.raw, "type": m.type.value, "value": m.value, "scored": m.scored}


def _competitor(c: Competitor) -> dict:
    return {"name": c.name, "school": c.school, "year": c.year}


def _entry(e: Entry) -> dict:
    return {
        "place": e.place,
        "school": e.school,
        "mark": _mark(e.mark),
        "competitors": [_competitor(c) for c in e.competitors],
        "points": e.points,
        "heat": e.heat,
        "qualifier": e.qualifier,
        "note": e.note,
    }


def _record(r: StandingRecord) -> dict:
    return {
        "scope": r.scope,
        "mark": _mark(r.mark),
        "holder": r.holder,
        "school": r.school,
        "date": r.date,
    }


def _event(ev: Event) -> dict:
    return {
        "number": ev.number,
        "name": ev.name,
        "gender": ev.gender,
        "division": ev.division,
        "round": ev.round,
        "markType": ev.mark_type.value,
        "entries": [_entry(e) for e in ev.entries],
        "records": [_record(r) for r in ev.records],
    }


def _team_score(t: TeamScore) -> dict:
    return {
        "school": t.school,
        "points": t.points,
        "rank": t.rank,
        "gender": t.gender,
        "division": t.division,
    }


def meet_to_dict(m: Meet, sequence: int = 0) -> dict:
    return {
        "$type": MEET_TYPE,
        "sequence": sequence,
        "name": m.name,
        "date": m.date,
        "endDate": m.end_date,
        "venue": m.venue,
        "sport": m.sport,
        "season": m.season,
        "host": m.host,
        "provenance": (
            {
                "sourceUri": m.provenance.source_uri,
                "adapter": m.provenance.adapter,
                "extractedAt": m.provenance.extracted_at,
                "confidence": m.provenance.confidence,
                "reviewState": m.provenance.review_state.value,
            }
            if m.provenance
            else None
        ),
        "events": [_event(ev) for ev in m.events],
        "teamScores": [_team_score(t) for t in m.team_scores],
    }


# -------------------------------------------------------------- from JSON


def _mark_from(d: dict | None) -> Mark | None:
    if d is None:
        return None
    return Mark(raw=d["raw"], type=MarkType(d["type"]), value=d["value"], scored=d["scored"])


def _meet_from(d: dict) -> Meet:
    prov = None
    if d.get("provenance"):
        p = d["provenance"]
        prov = Provenance(
            source_uri=p["sourceUri"],
            adapter=p["adapter"],
            extracted_at=p["extractedAt"],
            confidence=p["confidence"],
            review_state=ReviewState(p["reviewState"]),
        )
    meet = Meet(
        name=d["name"],
        date=d.get("date"),
        end_date=d.get("endDate"),
        venue=d.get("venue"),
        sport=d.get("sport"),
        season=d.get("season"),
        host=d.get("host"),
        provenance=prov,
    )
    for evd in d["events"]:
        ev = Event(
            number=evd["number"],
            name=evd["name"],
            gender=evd.get("gender"),
            division=evd.get("division"),
            round=evd.get("round"),
            mark_type=MarkType(evd["markType"]),
        )
        for ed in evd["entries"]:
            ev.entries.append(
                Entry(
                    place=ed["place"],
                    school=ed["school"],
                    mark=_mark_from(ed.get("mark")),
                    competitors=[
                        Competitor(name=c["name"], school=c["school"], year=c.get("year"))
                        for c in ed["competitors"]
                    ],
                    points=ed.get("points"),
                    heat=ed.get("heat"),
                    qualifier=ed.get("qualifier"),
                    note=ed.get("note"),
                )
            )
        for rd in evd["records"]:
            ev.records.append(
                StandingRecord(
                    scope=rd["scope"],
                    mark=_mark_from(rd["mark"]),
                    holder=rd.get("holder"),
                    school=rd.get("school"),
                    date=rd.get("date"),
                )
            )
        meet.events.append(ev)
    for td in d["teamScores"]:
        meet.team_scores.append(
            TeamScore(
                school=td["school"],
                points=td["points"],
                rank=td.get("rank"),
                gender=td.get("gender"),
                division=td.get("division"),
            )
        )
    return meet


# ------------------------------------------------------------------- files


def write_meet(path: pathlib.Path, meet: Meet, sequence: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meet_to_dict(meet, sequence), indent=1) + "\n")


def load_contests(records_dir: pathlib.Path) -> list[Meet]:
    """Every contest record, in stored sequence order."""
    docs: list[tuple[int, Any]] = []
    for p in sorted(records_dir.glob("contests/**/*.json")):
        d = json.loads(p.read_text())
        docs.append((d.get("sequence", 0), d))
    docs.sort(key=lambda t: t[0])
    out = []
    for _, d in docs:
        if d["$type"] == MEET_TYPE:
            out.append(_meet_from(d))
        elif d["$type"] == DUAL_TYPE:
            out.append(_dual_from(d))
        else:
            raise ValueError(f"unknown record type {d['$type']!r}")
    return out


# ------------------------------------------------------------------- duals

DUAL_TYPE = "org.prepnet.temp.contest.dual"


def dual_to_dict(d, sequence: int = 0) -> dict:
    from app.shapes import Dual

    assert isinstance(d, Dual)
    return {
        "$type": DUAL_TYPE,
        "sequence": sequence,
        "name": d.name,
        "date": d.date,
        "venue": d.venue,
        "sport": d.sport,
        "season": d.season,
        "home": d.home,
        "away": d.away,
        "homePoints": d.home_points,
        "awayPoints": d.away_points,
        "clinchedAt": d.clinched_at,
        "lines": [
            {
                "slot": l.slot,
                "kind": l.kind,
                "home": [_competitor(c) for c in l.home],
                "away": [_competitor(c) for c in l.away],
                "winner": l.winner,
                "score": l.score,
                "teamPoint": l.team_point,
            }
            for l in d.lines
        ],
        "provenance": (
            {
                "sourceUri": d.provenance.source_uri,
                "adapter": d.provenance.adapter,
                "extractedAt": d.provenance.extracted_at,
                "confidence": d.provenance.confidence,
                "reviewState": d.provenance.review_state.value,
            }
            if d.provenance
            else None
        ),
    }


def _dual_from(dd: dict):
    from app.shapes import Dual, Line

    dual = Dual(
        name=dd["name"], date=dd.get("date"), venue=dd.get("venue"),
        sport=dd.get("sport"), season=dd.get("season"),
        home=dd["home"], away=dd["away"],
        home_points=dd.get("homePoints"), away_points=dd.get("awayPoints"),
        clinched_at=dd.get("clinchedAt"),
    )
    for ld in dd["lines"]:
        dual.lines.append(
            Line(
                slot=ld["slot"], kind=ld["kind"],
                home=[Competitor(name=c["name"], school=c["school"], year=c.get("year")) for c in ld["home"]],
                away=[Competitor(name=c["name"], school=c["school"], year=c.get("year")) for c in ld["away"]],
                winner=ld.get("winner"), score=ld.get("score"),
                team_point=ld.get("teamPoint", 1.0),
            )
        )
    return dual
