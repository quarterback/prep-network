#!/usr/bin/env python3
"""
Put the standard.site records in an AT Protocol repo.

    FH_HANDLE=fieldhouse.example FH_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx \
        python3 scripts/publish_standardsite.py [--dry-run]

Separate from the build on purpose. `site/build.py` is a pure function of the
records in this repo — it writes files and touches no network — and folding a
PDS write into it would mean a deploy could half-succeed: pages published,
records not, or the reverse. This runs when you decide to publish, which is
also when you know the DID that every document's `site` field points at.

The DID is not knowable until login, so the records are built fresh here rather
than read back from `records/atproto/` (where they sit with an empty `site`
until a publication exists). Record keys are the story slugs, so re-running
after an edit updates the document in place instead of adding a second copy.

stdlib only — same as the rest of the project. An app password, not the account
password: https://bsky.app/settings/app-passwords
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import importlib.util as _ilu

_n = _ilu.spec_from_file_location("fh_news", ROOT / "site/news.py")
news = _ilu.module_from_spec(_n); _n.loader.exec_module(news)
_s = _ilu.spec_from_file_location("fh_stdsite", ROOT / "site/standardsite.py")
stdsite = _ilu.module_from_spec(_s); _s.loader.exec_module(stdsite)

PDS = os.environ.get("FH_PDS", "https://bsky.social").rstrip("/")


def _post(path: str, body: dict, token: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{PDS}/xrpc/{path}", data=json.dumps(body).encode(),
        headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{path} failed: {e.code} {e.read().decode()[:400]}")


def main() -> None:
    dry = "--dry-run" in sys.argv
    handle = os.environ.get("FH_HANDLE", "")
    password = os.environ.get("FH_APP_PASSWORD", "")

    if dry:
        did = "did:plc:DRYRUN"
        token = ""
    else:
        if not handle or not password:
            raise SystemExit("set FH_HANDLE and FH_APP_PASSWORD (or pass --dry-run)")
        session = _post("com.atproto.server.createSession",
                        {"identifier": handle, "password": password})
        did, token = session["did"], session["accessJwt"]

    pub_uri = f"at://{did}/{stdsite.PUBLICATION_TYPE}/self"

    records = [(stdsite.PUBLICATION_TYPE, "self", stdsite.publication())]
    for st in news.STORIES:
        doc = stdsite.document(st)
        doc["site"] = pub_uri          # the build cannot know this; login does
        records.append((stdsite.DOCUMENT_TYPE, stdsite.rkey(st), doc))

    for collection, rkey, record in records:
        if dry:
            print(f"would put at://{did}/{collection}/{rkey}")
            continue
        _post("com.atproto.repo.putRecord",
              {"repo": did, "collection": collection, "rkey": rkey,
               "record": record, "validate": False}, token)
        print(f"put at://{did}/{collection}/{rkey}")

    print(f"\n{len(records)} records{' (dry run)' if dry else ''}")
    print(f"Set this so the site emits its <link> tags and .well-known file:\n"
          f"  FH_PUB_URI={pub_uri}")


if __name__ == "__main__":
    main()
