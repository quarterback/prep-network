"""
The site's name, in one place.

The name is not settled. Everything that renders it — page titles, the
masthead, the favicon letter, the standard.site publication record, the report
form — reads from here, so renaming is this file and nothing else.

`WORDMARK` is set independently of `NAME` rather than derived: a name that
wants mixed case or a different mark in the masthead shouldn't have to fight an
`.upper()` somewhere in the renderer.
"""

NAME = "Fieldhouse"
WORDMARK = "FIELDHOUSE"
ASSOC = "JHSAA"

TITLE = f"{NAME}: the official site of the {ASSOC}"


def page_title(what: str) -> str:
    """Inner pages name themselves first — a tab reading "Boys Basketball
    standings" is findable in a row of twenty; one reading the site name is
    not."""
    return f"{what} — {NAME}"
