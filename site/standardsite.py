"""
standard.site — the site and its articles, published as AT Protocol records.

Scope is deliberately the publication layer, not the results layer. A
`site.standard.document` has a title, a date and a path; there is no field in
it that could hold "Alder Creek 36, Salmonberry Prairie 61." Contest records
stay in `org.prepnet.*` where they belong, and if scores ever want to reach the
network they go out as ordinary posts from an account. What travels here is
what the lexicon was built for: this is a publication, these are its articles,
here is where they live.

The lexicons come from standard.site — Leaflet, pckt.blog and Offprint found
they had each invented incompatible schemas for the same thing and agreed on
one instead. Adopting it means the association's newsroom is legible to
everything already reading those records (Bluesky renders previews for them;
WordPress, EmDash and Sequoia publish them) without anyone at the association
knowing the protocol exists.

Two records:

    site.standard.publication   name, url, description, basicTheme
    site.standard.document      site (AT-URI), title, publishedAt, path

Ownership is claimed twice over, and a consumer can check either: the
`/.well-known/site.standard.publication` endpoint returns the publication's
AT-URI, and every page carries it again in a <link> tag.

Nothing here contacts a PDS. The build writes the records to disk so they can
be read, diffed and reviewed like every other record in this repo;
`scripts/publish_standardsite.py` is what puts them in a repo, and it needs an
identity this project does not yet have. Until `FH_PUB_URI` names a real
record, the <link> tags and the .well-known file are omitted rather than
emitted with a placeholder — an unresolvable AT-URI in a rel tag is worse than
an absent one, because a consumer will try to fetch it.
"""

from __future__ import annotations

import json
import os
import pathlib

SITE_URL = os.environ.get("FH_SITE_URL", "https://prep-network.vercel.app").rstrip("/")

# at://<did>/site.standard.publication/<rkey> once the record exists. Unset in
# the demo build; see the module docstring for why that omits rather than fakes.
PUB_URI = os.environ.get("FH_PUB_URI", "")

PUBLICATION_TYPE = "site.standard.publication"
DOCUMENT_TYPE = "site.standard.document"
THEME_TYPE = "site.standard.theme.basic"

NAME = "Fieldhouse"
DESCRIPTION = ("Results, standings and championship coverage for Jefferson High "
               "School Activities Association member schools.")

# The varsity scheme's prussian blue on linen, matching what a reader sees.
_THEME = {
    "$type": THEME_TYPE,
    "background": {"r": 250, "g": 247, "b": 240},
    "foreground": {"r": 16, "g": 28, "b": 56},
    "accent": {"r": 27, "g": 74, "b": 143},
    "accentForeground": {"r": 250, "g": 247, "b": 240},
}


def publication() -> dict:
    return {
        "$type": PUBLICATION_TYPE,
        "name": NAME,
        "url": SITE_URL,
        "description": DESCRIPTION,
        "basicTheme": _THEME,
        "preferences": {"showInDiscover": True},
    }


def document(story: dict) -> dict:
    """One article. `site` binds it to the publication; `path` is site-relative.

    `publishedAt` must be RFC3339. Stories carry a plain date, so they publish
    at midnight UTC — the association posts by day, not by minute, and a
    fabricated clock time would be the only invented field in the record.
    """
    return {
        "$type": DOCUMENT_TYPE,
        "site": PUB_URI,
        "title": story["head"],
        "description": story["dek"],
        "publishedAt": f"{story['date']}T00:00:00Z",
        "path": f"/news/{story['slug']}/",
    }


def rkey(story: dict) -> str:
    """Record key. The slug is already stable and unique — reuse it, so
    republishing an edited story updates its record instead of adding one."""
    return story["slug"]


def head_links(story: dict | None = None) -> str:
    """<link> tags for the page head — publication on every page, document on
    the article it belongs to. Empty until the publication record exists."""
    if not PUB_URI:
        return ""
    tags = f'\n<link rel="{PUBLICATION_TYPE}" href="{PUB_URI}">'
    if story is not None:
        did = PUB_URI.split("/")[2]
        tags += (f'\n<link rel="{DOCUMENT_TYPE}" '
                 f'href="at://{did}/{DOCUMENT_TYPE}/{rkey(story)}">')
    return tags


def write_records(root: pathlib.Path, stories: list[dict]) -> int:
    """Records to disk, reviewable in a pull request like everything else here."""
    out = root / "records/atproto"
    out.mkdir(parents=True, exist_ok=True)
    _dump(out / "publication.json", publication())
    docs = out / "documents"
    docs.mkdir(exist_ok=True)
    for st in stories:
        _dump(docs / f"{rkey(st)}.json", document(st))
    return 1 + len(stories)


def write_well_known(out: pathlib.Path) -> bool:
    """The endpoint a consumer hits to confirm this domain claims that record."""
    if not PUB_URI:
        return False
    wk = out / ".well-known"
    wk.mkdir(parents=True, exist_ok=True)
    (wk / PUBLICATION_TYPE).write_text(PUB_URI + "\n")
    return True


def _dump(path: pathlib.Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
