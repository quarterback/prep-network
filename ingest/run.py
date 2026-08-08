"""
Ingest: source file -> canonical contest records under ``records/``.

    python3 -m ingest.run <file> [--adapter NAME] [--sport KEY] [--dry-run]

One command, and it prints what it produced rather than only what it read: the
contests, the records written, the names it could not resolve, and anything the
source's own checksums flagged. An import you cannot inspect is an import you
have to trust.

    python3 -m ingest.run --demo        # every committed specimen, dry run

This is the write path the upload surface calls; run by hand it is the same
pipeline. It never touches the site — publishing is a rebuild after the records
land (and, in the managed flow, after the PR carrying them is reviewed).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import records_io                                    # noqa: E402
from app.shapes import Dual, Game, Meet, ReviewState           # noqa: E402
from ingest import resolve as resolve_mod                      # noqa: E402
from ingest.adapters import (                                  # noqa: E402
    dual_card,
    hytek_pdf,
    hytek_swim,
    scorebook_csv,
)

ADAPTERS = {
    "hytek_pdf": hytek_pdf.parse,
    "hytek_swim": hytek_swim.parse,
    "scorebook_csv": scorebook_csv.parse,
    "dual_card": dual_card.parse,
}

#: Auto-detection, by extension and then by a cheap look at the head of the
#: file. Explicit ``--adapter`` always wins; this only saves typing.
def detect(path: pathlib.Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "hytek_pdf"
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return None
    if "HY-TEK" in head.upper():
        return "hytek_swim"
    if re.search(r"^GAME,", head, re.M) or "LINESCORE" in head:
        return "scorebook_csv"
    if "DUAL MATCH CARD" in head.upper() or re.search(r"^S1\s", head, re.M):
        return "dual_card"
    return None


SPECIMENS = ROOT / "ingest" / "fixtures" / "specimens"

#: The committed specimens, with the sport each should be filed under. The
#: track PDF is a FORMAT specimen from another association's meet, so it is
#: expected to resolve to no Jefferson school — that is the honest result, not
#: a failure, and --demo says so rather than hiding it.
DEMO = [
    ("hytek-mm-swimming-results.txt", "girls-swimming"),
    ("scorebook-volleyball-boxscore.csv", "girls-volleyball"),
    ("scorebook-hockey-boxscore.csv", "boys-ice-hockey"),
    ("scorebook-football-boxscore.csv", "football"),
    ("scorebook-baseball-boxscore.csv", "baseball"),
    ("scorebook-basketball-boxscore.csv", "boys-basketball"),
    ("scorebook-basketball-badtotals.csv", "boys-basketball"),
    ("dual-tennis-match-card.txt", "boys-tennis"),
    ("hytek-meetmanager8-track.pdf", "girls-track"),
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "x"


def _kind(contest) -> str:
    return "meet" if isinstance(contest, Meet) else "dual" if isinstance(contest, Dual) else "game"


def _describe(contest) -> str:
    if isinstance(contest, Meet):
        results = sum(len(e.entries) for e in contest.events)
        return f"{len(contest.events)} events · {results:,} results · {len(contest.schools)} schools"
    if isinstance(contest, Dual):
        return f"{len(contest.lines)} lines · {contest.home_points}–{contest.away_points}"
    bits = [f"{contest.away_score}–{contest.home_score}"]
    if contest.periods:
        bits.append(f"{len(contest.periods)} periods")
    if contest.box:
        bits.append(f"box {len(contest.box.home) + len(contest.box.away)} players"
                    f" · {len(contest.box.columns)} columns")
    return " · ".join(bits)


def _existing_path(records_dir: pathlib.Path, contest) -> pathlib.Path | None:
    """The record this import UPDATES, if the state already has one.

    A re-import has to land on the same file or the state acquires two records
    for one contest — both valid, both linked from the school pages, differing
    only in that one of them came from the source. Identity is the contest
    itself (sport, date, and the two teams), which is what a second export of
    the same game agrees with even when the file name and the internal ids do
    not.
    """
    home = getattr(contest, "home", None)
    if not home or not contest.date:
        return None
    for path in (records_dir / "contests").rglob("*.json"):
        try:
            d = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if (d.get("sport") == contest.sport and d.get("date") == contest.date
                and d.get("home") == home and d.get("away") == contest.away):
            return path
    return None


#: Sports the association runs as separate gendered championships, keyed by the
#: pair of sport keys a combined meet has to be split into.
GENDERED = {
    "swimming": ("boys-swimming", "girls-swimming"),
    "track": ("boys-track", "girls-track"),
    "cross-country": ("boys-cross-country", "girls-cross-country"),
}


def split_by_gender(meet, sport: str | None):
    """One combined meet -> one contest per gendered sport key.

    Hy-Tek runs boys and girls in a single meet and prints one results report
    for both; the association sanctions them as two championships with two sets
    of team scores. Filing the combined meet under either key is wrong in a way
    that looks fine — the girls' swimming page would carry the boys' 200 free —
    so the split happens here, at the boundary between the source's shape and
    the association's.
    """
    import copy

    family = next((f for f in GENDERED if sport and f in sport), None)
    if family is None:
        return [(meet, sport)]
    genders = {ev.gender for ev in meet.events if ev.gender}
    if len(genders) < 2:
        return [(meet, sport)]

    boys_key, girls_key = GENDERED[family]
    out = []
    for gender, key in (("Boys", boys_key), ("Girls", girls_key)):
        part = copy.copy(meet)
        part.events = [ev for ev in meet.events if ev.gender == gender]
        part.team_scores = [t for t in meet.team_scores if t.gender == gender]
        if not part.events:
            continue
        part.name = f"{meet.name} — {gender}"
        out.append((part, key))
    return out or [(meet, sport)]


def run_one(source: pathlib.Path, adapter: str, sport: str | None,
            records_dir: pathlib.Path, season: str, dry_run: bool) -> int:
    print(f"\n\033[1m{source.name}\033[0m  →  adapter {adapter}")
    parsed = ADAPTERS[adapter](str(source))
    if not parsed:
        print("  nothing parsed")
        return 0
    contests = []
    for c in parsed:
        if isinstance(c, Meet):
            contests.extend(split_by_gender(c, sport))
        else:
            contests.append((c, sport))

    resolver = resolve_mod.Resolver.from_records(records_dir)
    written = 0
    for i, (contest, target_sport) in enumerate(contests):
        resolve_mod.apply_to_contest(contest, resolver)
        contest.season = contest.season or season
        contest.sport = contest.sport or target_sport

        name = contest.name or f"{adapter}-{i}"
        existing = _existing_path(records_dir, contest)
        path = existing or (records_dir / "contests" / season /
                            (contest.sport or "unfiled") / f"{slugify(name)[:70]}.json")
        if existing is not None:
            # Keep the record's place in the stored sequence; the site orders by
            # it and a re-import should not jump a January game to the end.
            try:
                i = json.loads(existing.read_text()).get("sequence", i)
            except (OSError, ValueError):
                pass
        flag = ""
        prov = contest.provenance
        if prov and prov.review_state is ReviewState.NEEDS_REVIEW:
            flag = f"  \033[33m[needs review: {prov.notes}]\033[0m"
        print(f"  {_kind(contest):5} {name[:58]:58} {_describe(contest)}{flag}")
        if not dry_run:
            records_io.write_contest(path, contest, sequence=i)
            written += 1
            print(f"        → {path.relative_to(ROOT)}")

    rep = resolver.report
    print(f"  resolution: {rep.summary()}")
    for r in rep.inexact[:8]:
        print(f"        ~ {r.raw!r} → {r.school!r} ({r.method} {r.confidence})")
    unresolved = rep.unresolved
    if unresolved:
        shown = ", ".join(repr(r.raw) for r in unresolved[:6])
        more = f" (+{len(unresolved) - 6} more)" if len(unresolved) > 6 else ""
        print(f"  \033[33munresolved {len(unresolved)}:\033[0m {shown}{more}")
        for r in unresolved:
            if r.candidates:
                print(f"        ? {r.raw!r} ambiguous between {list(r.candidates)}")
                break
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ingest.run")
    ap.add_argument("source", nargs="?")
    ap.add_argument("--adapter", choices=sorted(ADAPTERS))
    ap.add_argument("--sport", help="sport key to file the contest under")
    ap.add_argument("--season", default="2026-27")
    ap.add_argument("--records", default=str(ROOT / "records"))
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report, write nothing")
    ap.add_argument("--demo", action="store_true",
                    help="run every committed specimen as a dry run")
    args = ap.parse_args(argv)

    records_dir = pathlib.Path(args.records)

    if args.demo:
        print("Every committed specimen, parsed and resolved. Nothing is written.")
        for filename, sport in DEMO:
            path = SPECIMENS / filename
            if not path.exists():
                print(f"\n{filename}: missing")
                continue
            adapter = detect(path)
            if adapter is None:
                print(f"\n{filename}: no adapter detected")
                continue
            run_one(path, adapter, sport, records_dir, args.season, dry_run=True)
        print("\nThe track PDF is a format specimen from another association's meet;")
        print("its schools are not Jefferson schools, so they do not resolve. That is")
        print("the correct result — the parse is sound, the field is foreign.")
        return 0

    if not args.source:
        ap.error("a source file is required (or --demo)")
    source = pathlib.Path(args.source)
    if not source.exists():
        ap.error(f"no such file: {source}")

    adapter = args.adapter or detect(source)
    if adapter is None:
        ap.error("could not detect an adapter; pass --adapter")

    written = run_one(source, adapter, args.sport, records_dir, args.season, args.dry_run)
    print(f"\n{written} record(s) written" if not args.dry_run else "\ndry run — nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
