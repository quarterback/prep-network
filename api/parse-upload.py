"""
Upload writer: source file in -> parsed records PR out.

Vercel Python function for the sports that DO have tools. Body is the raw file;
`?filename=` names it and `?adapter=` picks the parser (hytek_pdf today). Every
contest found in the file lands as a record on one branch, one PR.

Same environment as api/submit.py.
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from api.submit import gh, slugify  # noqa: E402  (shared GitHub plumbing)
from app import records_io  # noqa: E402
from ingest.adapters import hytek_pdf  # noqa: E402

ADAPTERS = {"hytek_pdf": hytek_pdf.parse}
MAX_BYTES = 25 * 1024 * 1024


class handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - Vercel contract
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        adapter = (q.get("adapter") or ["hytek_pdf"])[0]
        filename = (q.get("filename") or ["upload"])[0]
        if adapter not in ADAPTERS:
            return self._json(400, {"error": f"unknown adapter {adapter!r}"})

        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_BYTES:
            return self._json(400, {"error": "file missing or too large"})
        blob = self.rfile.read(length)

        with tempfile.NamedTemporaryFile(suffix=pathlib.Path(filename).suffix, delete=False) as f:
            f.write(blob)
            tmp = f.name
        try:
            contests = ADAPTERS[adapter](tmp, source_uri=f"upload:{filename}")
        except Exception as exc:
            return self._json(422, {"error": f"parse failed: {exc}"})
        if not contests:
            return self._json(422, {"error": "no contests found in file"})

        repo = os.environ["FH_REPO"]
        base = os.environ.get("FH_BASE_BRANCH", "main")
        stamp = int(time.time())
        branch = f"records/upload-{slugify(filename)}-{stamp}"
        try:
            base_sha = gh(f"/repos/{repo}/git/ref/heads/{base}")["object"]["sha"]
            gh(f"/repos/{repo}/git/refs", "POST", {"ref": f"refs/heads/{branch}", "sha": base_sha})
            names = []
            for i, contest in enumerate(contests):
                doc = records_io.meet_to_dict(contest, sequence=i)
                season = doc.get("season") or (doc.get("date") or "undated")[-4:]
                path = f"records/contests/{season}/{slugify(contest.name)}-{stamp}.json"
                gh(
                    f"/repos/{repo}/contents/{path}",
                    "PUT",
                    {
                        "message": f"records: {contest.name}",
                        "content": base64.b64encode(
                            (json.dumps(doc, indent=1) + "\n").encode()
                        ).decode(),
                        "branch": branch,
                    },
                )
                names.append(contest.name)
            pr = gh(
                f"/repos/{repo}/pulls",
                "POST",
                {
                    "title": f"Upload: {filename} ({len(contests)} contest(s))",
                    "head": branch,
                    "base": base,
                    "body": "Parsed from an uploaded file:\n\n"
                    + "\n".join(f"- {n}" for n in names)
                    + "\n\nMerging publishes the results.",
                },
            )
        except Exception as exc:
            return self._json(502, {"error": f"github: {exc}"})
        return self._json(200, {"pr": pr["html_url"], "contests": names})

    def _json(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
