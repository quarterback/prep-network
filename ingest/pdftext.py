"""
Positioned text extraction from PDFs, standard library only.

Why this exists
---------------
State associations publish results as PDFs printed by meet-management software
(Hy-Tek MEET MANAGER, DirectAthletics MeetPro, TrackWrestling). The data was
fully structured inside that software and destroyed at print time. Recovering it
is a layout problem: the PDF knows *where* every string sits, and the columns are
stable, so the table can be rebuilt from coordinates.

No third-party dependency is needed. Content streams are zlib-compressed; text
positions come from the Tm/Td operators and the strings from Tj/TJ.

The one non-obvious thing
-------------------------
A PDF does not emit one string per table cell. Kerning splits a cell across
several show operators, and — critically — those fragments carry NO explicit
position of their own, because Tj/TJ advance the text cursor implicitly. A naive
extractor records them all at the last explicit anchor and then sorts by x,
which silently reorders them:

    "Davis," + " Alaina"        sorted by x  ->  " AlainaDavis,"
    "Salwa"  + "y, Taelynn"     sorted by x  ->  "y, TaelynnSalwa"

Both look plausible and both are wrong. Roughly every name containing a kerning
pair is corrupted this way.

The fix is exact and needs no font metrics: fragments sharing an anchor must be
concatenated in **emission order**. We therefore carry a monotonic sequence
number on every fragment and sort by (x, seq), never by x alone.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field

# ---------------------------------------------------------------- primitives


@dataclass(frozen=True)
class Frag:
    """One show-operator's worth of text at a position."""

    x: float
    y: float
    seq: int
    text: str


@dataclass
class Cell:
    """A run of fragments that belong to the same column."""

    x: float
    text: str

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.text


@dataclass
class Row:
    """One visual line of a page, split into columns."""

    y: float
    cells: list[Cell] = field(default_factory=list)

    def text(self) -> str:
        """The row as a single whitespace-joined string."""
        return " ".join(c.text for c in self.cells if c.text.strip())

    def at(self, x: float, tol: float = 4.0) -> str | None:
        """The cell anchored near ``x``, if any."""
        for c in self.cells:
            if abs(c.x - x) <= tol:
                return c.text
        return None

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.text()


# ---------------------------------------------------------------- decoding

# \ddd octal, or a single escaped character
_ESCAPE = re.compile(rb"\\([0-7]{1,3}|.)", re.S)
_SIMPLE = {
    b"n": b"\n",
    b"r": b"\r",
    b"t": b"\t",
    b"b": b"\b",
    b"f": b"\f",
    b"(": b"(",
    b")": b")",
    b"\\": b"\\",
}


def _unescape(raw: bytes) -> bytes:
    """Resolve PDF string escapes, including octal character codes."""

    def sub(m: "re.Match[bytes]") -> bytes:
        body = m.group(1)
        if body in _SIMPLE:
            return _SIMPLE[body]
        if body.isdigit() and all(c in b"01234567" for c in body):
            return bytes([int(body, 8) & 0xFF])
        if body in (b"\n", b"\r"):
            return b""  # line continuation
        return body

    return _ESCAPE.sub(sub, raw)


# A PDF literal string: balanced-free scan that respects backslash escapes.
_STRING = re.compile(rb"\((?:[^()\\]|\\.)*\)", re.S)


def _strings_in(chunk: bytes) -> list[bytes]:
    return [_unescape(m.group(0)[1:-1]) for m in _STRING.finditer(chunk)]


def _decode(raw: bytes) -> str:
    """PDF literal strings from these producers are PDFDocEncoding/latin-1."""
    return raw.decode("latin-1")


# ---------------------------------------------------------------- extraction

_NUM = rb"[-+]?[0-9]*\.?[0-9]+"

# Matched in one pass so operator ordering is preserved.
_OPS = re.compile(
    rb"(?P<tm>(?:%(n)s)\s+(?:%(n)s)\s+(?:%(n)s)\s+(?:%(n)s)\s+(?P<tmx>%(n)s)\s+(?P<tmy>%(n)s)\s+Tm)"
    rb"|(?P<td>(?P<tdx>%(n)s)\s+(?P<tdy>%(n)s)\s+T[dD])"
    rb"|(?P<tstar>T\*)"
    rb"|(?P<tl>(?P<tlv>%(n)s)\s+TL)"
    rb"|(?P<tj>\[(?P<tjbody>(?:[^\[\]\\]|\\.)*)\]\s*TJ)"
    rb"|(?P<sj>(?P<sjbody>\((?:[^()\\]|\\.)*\))\s*Tj)"
    rb"|(?P<bt>BT)"
    % {b"n": _NUM},
    re.S,
)

_STREAM = re.compile(rb"stream\r?\n?(.*?)\r?\n?endstream", re.S)


def content_streams(data: bytes) -> list[bytes]:
    """Every decompressed content stream that carries text operators."""
    out: list[bytes] = []
    for m in _STREAM.finditer(data):
        raw = m.group(1)
        try:
            body = zlib.decompress(raw)
        except zlib.error:
            body = raw  # uncompressed stream
        if b"BT" in body and (b"Tj" in body or b"TJ" in body):
            out.append(body)
    return out


def fragments(stream: bytes) -> list[Frag]:
    """Positioned text fragments from one content stream, in emission order."""
    frags: list[Frag] = []
    x = y = 0.0
    leading = 0.0
    seq = 0

    for m in _OPS.finditer(stream):
        if m.group("bt") is not None:
            x = y = 0.0
        elif m.group("tm") is not None:
            x, y = float(m.group("tmx")), float(m.group("tmy"))
        elif m.group("td") is not None:
            dy = float(m.group("tdy"))
            x += float(m.group("tdx"))
            y += dy
            if m.group("td").endswith(b"TD"):
                leading = -dy
        elif m.group("tl") is not None:
            leading = float(m.group("tlv"))
        elif m.group("tstar") is not None:
            y += leading
        else:
            if m.group("tj") is not None:
                parts = _strings_in(m.group("tjbody"))
            else:
                parts = _strings_in(m.group("sjbody"))
            text = _decode(b"".join(parts))
            if text:
                frags.append(Frag(x=x, y=y, seq=seq, text=text))
                seq += 1
    return frags


# ---------------------------------------------------------------- layout


def rows(frags: list[Frag], y_tol: float = 1.0, col_gap: float = 2.0) -> list[Row]:
    """
    Group fragments into visual lines, then into columns.

    ``y_tol``   how far apart two fragments can sit vertically and still count
                as the same line.
    ``col_gap`` how far apart two fragments must sit horizontally to start a new
                column. Fragments closer than this are the same cell — this is
                what re-joins kerning-split text.
    """
    if not frags:
        return []

    # --- lines, keyed by a tolerance-collapsed y
    buckets: dict[float, list[Frag]] = {}
    for f in sorted(frags, key=lambda f: (f.y, f.seq)):
        for key in buckets:
            if abs(key - f.y) <= y_tol:
                buckets[key].append(f)
                break
        else:
            buckets[f.y] = [f]

    out: list[Row] = []
    for y in sorted(buckets):
        # (x, seq) — never x alone. See module docstring.
        line = sorted(buckets[y], key=lambda f: (f.x, f.seq))
        cells: list[Cell] = []
        prev_x: float | None = None
        for f in line:
            if prev_x is not None and (f.x - prev_x) <= col_gap:
                cells[-1].text += f.text
            else:
                cells.append(Cell(x=f.x, text=f.text))
            prev_x = f.x
        for c in cells:
            c.text = c.text.strip()
        out.append(Row(y=y, cells=[c for c in cells if c.text]))
    return [r for r in out if r.cells]


def pages(data: bytes) -> list[list[Row]]:
    """Every text-bearing page of a PDF, as rows of cells.

    Note: this treats each text-bearing content stream as one page. That holds
    for the single-stream-per-page output of the meet-management software this
    targets. A document splitting one page across several /Contents streams
    would need the page tree walked instead.
    """
    return [rows(fragments(s)) for s in content_streams(data)]


def load(path: str) -> list[list[Row]]:
    with open(path, "rb") as fh:
        return pages(fh.read())
