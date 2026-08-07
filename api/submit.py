"""
Entry-form writer: contest record in -> records PR out.

Vercel Python function. Validates the payload as a known record type, writes it
to records/contests/<season>/ on a new branch via the GitHub API, and opens a
PR — review-then-merge IS the review queue, and the merge triggers the rebuild.

Environment (Vercel project settings):
    FH_GITHUB_TOKEN   fine-grained token, contents:write + pull_requests:write
    FH_REPO           e.g. quarterback/prep-network
    FH_BASE_BRANCH    the branch PRs target
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.request
from http.server import BaseHTTPRequestHandler

KNOWN_TYPES = {"org.prepnet.temp.contest.dual", "org.prepnet.temp.contest.meet"}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "x"


def gh(path: str, method: str = "GET", body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ['FH_GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "fieldhouse-submit",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"{}")


def validate(record: dict) -> str | None:
    if record.get("$type") not in KNOWN_TYPES:
        return "unknown record type"
    if not record.get("name") or not record.get("date"):
        return "name and date are required"
    if record["$type"].endswith(".dual"):
        if not record.get("home") or not record.get("away"):
            return "home and away schools are required"
        if not record.get("lines"):
            return "at least one line is required"
    return None


def open_pr(record: dict) -> str:
    repo = os.environ["FH_REPO"]
    base = os.environ.get("FH_BASE_BRANCH", "main")
    season = record.get("season") or "undated"
    stamp = int(time.time())
    slug = slugify(record["name"])
    branch = f"records/{slug}-{stamp}"
    path = f"records/contests/{season}/{slug}-{stamp}.json"

    base_sha = gh(f"/repos/{repo}/git/ref/heads/{base}")["object"]["sha"]
    gh(f"/repos/{repo}/git/refs", "POST", {"ref": f"refs/heads/{branch}", "sha": base_sha})
    gh(
        f"/repos/{repo}/contents/{path}",
        "PUT",
        {
            "message": f"records: {record['name']} ({record.get('date')})",
            "content": base64.b64encode(
                (json.dumps(record, indent=1) + "\n").encode()
            ).decode(),
            "branch": branch,
        },
    )
    pr = gh(
        f"/repos/{repo}/pulls",
        "POST",
        {
            "title": f"Result: {record['name']} ({record.get('date')})",
            "head": branch,
            "base": base,
            "body": "Submitted from the entry form. Merging publishes the result.",
        },
    )
    return pr["html_url"]


class handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - Vercel contract
        try:
            length = int(self.headers.get("Content-Length", 0))
            record = json.loads(self.rfile.read(length))
        except Exception:
            return self._json(400, {"error": "invalid JSON"})

        err = validate(record)
        if err:
            return self._json(400, {"error": err})
        # provenance is stamped server-side; the form never asserts it
        record["provenance"] = {
            "sourceUri": "form:report/dual",
            "adapter": "entry_form",
            "extractedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "confidence": 1.0,
            "reviewState": "needs_review",
        }
        try:
            pr = open_pr(record)
        except Exception as exc:  # surfaced, not swallowed
            return self._json(502, {"error": f"github: {exc}"})
        return self._json(200, {"pr": pr})

    def _json(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
