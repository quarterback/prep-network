"""
Ingest: source file -> canonical contest records under records/.

    python3 ingest/run.py <file> [--adapter hytek_pdf] [--season 2026]

This is the write path the upload surface calls; run by hand it is the same
pipeline. It never touches the site — publishing is a rebuild after the records
land (and, in the managed flow, after the PR carrying them is reviewed).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import records_io  # noqa: E402
from ingest.adapters import hytek_pdf  # noqa: E402

ADAPTERS = {"hytek_pdf": hytek_pdf.parse}


def slugify(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--adapter", default="hytek_pdf", choices=sorted(ADAPTERS))
    ap.add_argument("--season", default="2026")
    ap.add_argument("--records", default=str(ROOT / "records"))
    args = ap.parse_args()

    meets = ADAPTERS[args.adapter](args.source)
    records_dir = pathlib.Path(args.records)
    for i, meet in enumerate(meets):
        meet.season = meet.season or args.season
        path = records_dir / "contests" / args.season / f"{slugify(meet.name)}.json"
        records_io.write_meet(path, meet, sequence=i)
        n = sum(len(e.entries) for e in meet.events)
        print(f"  {path.relative_to(ROOT)}  ·  {len(meet.events)} events · {n:,} results")
    print(f"{len(meets)} contest record(s) written")


if __name__ == "__main__":
    main()
