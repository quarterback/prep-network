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
    BoxScore,
    Competitor,
    Entrant,
    Entry,
    Event,
    Mark,
    MarkType,
    Matchup,
    Meet,
    Provenance,
    ReviewState,
    Round,
    SourceType,
    StandingRecord,
    StatLine,
    TeamScore,
    Tournament,
    TournamentFormat,
)

MEET_TYPE = "org.prepnet.temp.contest.meet"


# --------------------------------------------------------------- provenance

# One serializer for all three shapes. This was copied per-shape; adding the
# audit fields to a copy and not its siblings is exactly how a record ends up
# unauditable, so there is now one of it.


def _prov(p: Provenance | None) -> dict | None:
    if p is None:
        return None
    d = {
        "sourceType": p.source_type.value,
        "sourceUri": p.source_uri,
        "adapter": p.adapter,
        "adapterVersion": p.adapter_version,
        "extractedAt": p.extracted_at,
        "confidence": p.confidence,
        "reviewState": p.review_state.value,
    }
    # Optional fields stay absent rather than null: 8,000 records carry this
    # block, and a null per absent field is real bytes for no information.
    if p.source_sha256:
        d["sourceSha256"] = p.source_sha256
    if p.source_page is not None:
        d["sourcePage"] = p.source_page
    if p.external_ids:
        d["externalIds"] = dict(p.external_ids)
    if p.notes:
        d["notes"] = p.notes
    return d


def _prov_from(p: dict | None) -> Provenance | None:
    if not p:
        return None
    return Provenance(
        source_uri=p["sourceUri"],
        adapter=p["adapter"],
        extracted_at=p["extractedAt"],
        confidence=p.get("confidence", 1.0),
        review_state=ReviewState(p.get("reviewState", "published")),
        source_type=SourceType(p.get("sourceType", "unknown")),
        source_sha256=p.get("sourceSha256"),
        source_page=p.get("sourcePage"),
        adapter_version=p.get("adapterVersion", "0"),
        external_ids=p.get("externalIds", {}) or {},
        notes=p.get("notes"),
    )


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
        "provenance": _prov(m.provenance),
        "events": [_event(ev) for ev in m.events],
        "teamScores": [_team_score(t) for t in m.team_scores],
    }


# -------------------------------------------------------------- from JSON


def _mark_from(d: dict | None) -> Mark | None:
    if d is None:
        return None
    return Mark(raw=d["raw"], type=MarkType(d["type"]), value=d["value"], scored=d["scored"])


def _meet_from(d: dict) -> Meet:
    prov = _prov_from(d.get("provenance"))
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
        elif d["$type"] == GAME_TYPE:
            out.append(_game_from(d))
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
        "provenance": _prov(d.provenance),
    }


def _dual_from(dd: dict):
    from app.shapes import Dual, Line

    dual = Dual(
        name=dd["name"], date=dd.get("date"), venue=dd.get("venue"),
        sport=dd.get("sport"), season=dd.get("season"),
        home=dd["home"], away=dd["away"],
        home_points=dd.get("homePoints"), away_points=dd.get("awayPoints"),
        clinched_at=dd.get("clinchedAt"),
        provenance=_prov_from(dd.get("provenance")),
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


# ------------------------------------------------------------------- games

GAME_TYPE = "org.prepnet.temp.contest.game"


def game_to_dict(g, sequence: int = 0) -> dict:
    from app.shapes import Game

    assert isinstance(g, Game)
    return {
        "$type": GAME_TYPE,
        "sequence": sequence,
        "name": g.name,
        "date": g.date,
        "venue": g.venue,
        "sport": g.sport,
        "season": g.season,
        "home": g.home,
        "away": g.away,
        "homeScore": g.home_score,
        "awayScore": g.away_score,
        "status": g.status,
        "periods": [{"label": p.label, "home": p.home, "away": p.away} for p in g.periods],
        **({"box": _box(g.box)} if g.box else {}),
        "provenance": _prov(g.provenance),
    }


def _stat_line(s: StatLine) -> dict:
    d = {"competitor": _competitor(s.competitor), "stats": dict(s.stats)}
    if s.starter:
        d["starter"] = True
    if s.section:
        d["section"] = s.section
    return d


def _box(b: BoxScore) -> dict:
    return {
        "columns": list(b.columns),
        "home": [_stat_line(s) for s in b.home],
        "away": [_stat_line(s) for s in b.away],
        "homeTotals": dict(b.home_totals),
        "awayTotals": dict(b.away_totals),
        **({"sections": {k: list(v) for k, v in b.sections.items()}} if b.sections else {}),
    }


def _box_from(d: dict | None) -> BoxScore | None:
    if not d:
        return None

    def lines(key):
        return [
            StatLine(
                competitor=Competitor(
                    name=s["competitor"]["name"],
                    school=s["competitor"]["school"],
                    year=s["competitor"].get("year"),
                ),
                stats=s.get("stats", {}),
                starter=s.get("starter", False),
                section=s.get("section", ""),
            )
            for s in d.get(key, [])
        ]

    return BoxScore(
        columns=d.get("columns", []),
        home=lines("home"),
        away=lines("away"),
        home_totals=d.get("homeTotals", {}),
        away_totals=d.get("awayTotals", {}),
        sections=d.get("sections", {}),
    )


def _game_from(d: dict):
    from app.shapes import Game, Period

    g = Game(
        name=d["name"], date=d.get("date"), venue=d.get("venue"),
        sport=d.get("sport"), season=d.get("season"),
        home=d["home"], away=d["away"],
        home_score=d.get("homeScore"), away_score=d.get("awayScore"),
        status=d.get("status", "final"),
        box=_box_from(d.get("box")),
        provenance=_prov_from(d.get("provenance")),
    )
    for pd in d.get("periods", []):
        g.periods.append(Period(label=pd["label"], home=pd["home"], away=pd["away"]))
    return g


def contest_to_dict(c, sequence: int = 0) -> dict:
    from app.shapes import Dual, Game, Meet

    if isinstance(c, Meet):
        return meet_to_dict(c, sequence)
    if isinstance(c, Dual):
        return dual_to_dict(c, sequence)
    if isinstance(c, Game):
        return game_to_dict(c, sequence)
    raise TypeError(type(c))


def load_contest_dict(d: dict):
    """One canonical JSON document -> its dataclass. The inverse of
    :func:`contest_to_dict`, and what makes a round-trip test possible."""
    kind = d["$type"]
    if kind == MEET_TYPE:
        return _meet_from(d)
    if kind == DUAL_TYPE:
        return _dual_from(d)
    if kind == GAME_TYPE:
        return _game_from(d)
    raise ValueError(f"unknown record type {kind!r}")


def write_contest(path: pathlib.Path, contest, sequence: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contest_to_dict(contest, sequence), separators=(",", ":")) + "\n")


# ------------------------------------------------------------- tournaments

TOURNAMENT_TYPE = "org.prepnet.temp.postseason.tournament"


def tournament_to_dict(t: Tournament) -> dict:
    """A tournament stores STRUCTURE and pointers, never a copy of a result.

    Matchup scores are the exception and are stored: the bracket has to draw a
    score without opening 31 contest records, and the game record stays the
    authority (:func:`reconcile` re-reads it). Anything else the bracket needs —
    who is playing, who advanced — is derived.
    """
    return {
        "$type": TOURNAMENT_TYPE,
        "id": t.id,
        "name": t.name,
        "sport": t.sport,
        "season": t.season,
        "group": t.group,
        "format": t.format.value,
        "startDate": t.start_date,
        "finalDate": t.final_date,
        "finalVenue": t.final_venue,
        "meetKey": t.meet_key,
        "entrants": [
            {
                "seed": e.seed,
                "school": e.school,
                "qualifier": e.qualifier,
                "record": e.record,
                "conference": e.conference,
            }
            for e in t.entrants
        ],
        "rounds": [
            {
                "index": r.index,
                "name": r.name,
                "matchups": [
                    {
                        "round": m.round,
                        "slot": m.slot,
                        "home": m.home,
                        "away": m.away,
                        "homeSeed": m.home_seed,
                        "awaySeed": m.away_seed,
                        "homeScore": m.home_score,
                        "awayScore": m.away_score,
                        "contestKey": m.contest_key,
                        "date": m.date,
                        "time": m.time,
                        "venue": m.venue,
                        "status": m.status,
                        "bye": m.bye,
                    }
                    for m in r.matchups
                ],
            }
            for r in t.rounds
        ],
        "provenance": _prov(t.provenance),
    }


def _tournament_from(d: dict) -> Tournament:
    t = Tournament(
        id=d["id"],
        name=d["name"],
        sport=d["sport"],
        season=d.get("season", ""),
        group=d.get("group", ""),
        format=TournamentFormat(d.get("format", "bracket")),
        start_date=d.get("startDate"),
        final_date=d.get("finalDate"),
        final_venue=d.get("finalVenue"),
        meet_key=d.get("meetKey"),
        provenance=_prov_from(d.get("provenance")),
    )
    t.entrants = [
        Entrant(
            school=e["school"],
            seed=e.get("seed"),
            qualifier=e.get("qualifier"),
            record=e.get("record"),
            conference=e.get("conference"),
        )
        for e in d.get("entrants", [])
    ]
    for rd in d.get("rounds", []):
        t.rounds.append(
            Round(
                index=rd["index"],
                name=rd["name"],
                matchups=[
                    Matchup(
                        round=m["round"],
                        slot=m["slot"],
                        home=m.get("home"),
                        away=m.get("away"),
                        home_seed=m.get("homeSeed"),
                        away_seed=m.get("awaySeed"),
                        home_score=m.get("homeScore"),
                        away_score=m.get("awayScore"),
                        contest_key=m.get("contestKey"),
                        date=m.get("date"),
                        time=m.get("time"),
                        venue=m.get("venue"),
                        status=m.get("status", "scheduled"),
                        bye=m.get("bye", False),
                    )
                    for m in rd.get("matchups", [])
                ],
            )
        )
    return t


def write_tournament(path: pathlib.Path, t: Tournament) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tournament_to_dict(t), separators=(",", ":")) + "\n")


def load_tournaments(records_dir: pathlib.Path) -> list[Tournament]:
    out = []
    for p in sorted(records_dir.glob("postseason/**/*.json")):
        d = json.loads(p.read_text())
        if d.get("$type") == TOURNAMENT_TYPE:
            out.append(_tournament_from(d))
    return out


# -------------------------------------------------------------------- orgs


def write_orgs(records_dir: pathlib.Path, schools: list[dict], conferences: list[dict]) -> None:
    d = records_dir / "orgs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "schools.json").write_text(json.dumps(
        {"$type": "org.prepnet.temp.org.schools", "schools": schools}, indent=1) + "\n")
    (d / "conferences.json").write_text(json.dumps(
        {"$type": "org.prepnet.temp.org.conferences", "conferences": conferences}, indent=1) + "\n")


def load_orgs(records_dir: pathlib.Path) -> tuple[list[dict], list[dict]]:
    d = records_dir / "orgs"
    schools: list[dict] = []
    conferences: list[dict] = []
    if (d / "schools.json").exists():
        schools = json.loads((d / "schools.json").read_text())["schools"]
    if (d / "conferences.json").exists():
        conferences = json.loads((d / "conferences.json").read_text())["conferences"]
    return schools, conferences
