"""
The canonical contest model: three shapes, and the marks they carry.

Every activity a state association sanctions is a configuration over one of
three shapes. Nothing downstream — standings, records, the renderer, the
lexicons — knows what sport it is looking at.

    MEET   N teams, M events. Each entry carries a mark and a place; the team
           score is DERIVED from a placing table rather than recorded.
           cross country, track, swimming, wrestling tournaments, gymnastics,
           spirit, skiing, stroke-play golf, speech/debate, music adjudication

    DUAL   2 teams, N ordered lines, each line its own result, one team point
           per line, clinch rules.
           tennis, wrestling duals, match-play golf

    GAME   2 teams, one score each, optional period splits, optional box score.
           football, volleyball, soccer, basketball, baseball, ice hockey,
           esports

MEET is the shape that matters and the one nobody models well. GAME is a MEET
with two entrants and no events; building GAME first yields a schema that cannot
express a track meet, which is the mistake the incumbents made.

Why MarkType is wider than "a number"
-------------------------------------
Surveying a sport-rich association (CHSAA sanctions ~30 activities) shows the
model has to hold more than measured performance:

    measured    a time, a distance, a height        track, swimming, skiing
    judged      a score awarded by officials        gymnastics, spirit
    adjudicated an ordinal rating, not a number     music (I/II/III/IV)
    ordinal     a placing with no mark at all       speech, debate
    tallied     strokes, pinfall, points            golf, bowling

An association sanctions *activities*, not just sports. A model that assumes
every result reduces to a number silently excludes a third of the calendar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Shape(str, Enum):
    MEET = "meet"
    DUAL = "dual"
    GAME = "game"


class MarkType(str, Enum):
    TIME = "time"           # 13.49, 2:05.44, 17:32.1
    DISTANCE = "distance"   # 16-11.75, 45.72m
    HEIGHT = "height"       # 5-04.00
    POINTS = "points"       # judged: gymnastics, spirit
    RATING = "rating"       # adjudicated: music, I/II/III/IV
    ORDINAL = "ordinal"     # placing only: speech, debate
    STROKES = "strokes"     # golf
    PINFALL = "pinfall"     # bowling


#: Mark types where a LOWER value is better.
LOWER_IS_BETTER = {MarkType.TIME, MarkType.STROKES, MarkType.ORDINAL, MarkType.RATING}


class ReviewState(str, Enum):
    PUBLISHED = "published"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Provenance:
    """Where a record came from. Mandatory — extraction is never anonymous.

    Because nothing rendered is model-generated, there is no prose layer to hide
    a bad extraction behind. An unreviewed extraction is not a result.
    """

    source_uri: str
    adapter: str
    extracted_at: str
    confidence: float = 1.0
    review_state: ReviewState = ReviewState.PUBLISHED

    def publishable(self, threshold: float = 0.9) -> bool:
        return (
            self.review_state is ReviewState.PUBLISHED
            and self.confidence >= threshold
        )


# ------------------------------------------------------------------- marks

_TIME = re.compile(r"^(?:(\d+):)?(\d{1,2})\.(\d{1,3})$")
_TIME_HMS = re.compile(r"^(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$")
_FEET_IN = re.compile(r"^(\d+)-(\d{1,2}(?:\.\d+)?)$")
_METRIC = re.compile(r"^(\d+(?:\.\d+)?)\s*m$", re.I)
_PLAIN = re.compile(r"^\d+(?:\.\d+)?$")

#: Results that carry no mark. Hy-Tek and its peers all use these.
NON_MARKS = {
    "NT", "NM", "NH", "DNF", "DNS", "DQ", "SCR", "FS", "NP", "--", "X", "FOUL",
}


@dataclass(frozen=True)
class Mark:
    """A performance, kept alongside the string it was printed as.

    ``raw`` is never discarded. A mark that round-trips to its source string is
    auditable; one that has been normalised into a float and thrown away is not.
    """

    raw: str
    type: MarkType
    value: float | None = None      # seconds, inches, points — comparable
    scored: bool = True             # False for DQ/DNF/NM and friends

    @property
    def lower_is_better(self) -> bool:
        return self.type in LOWER_IS_BETTER

    def better_than(self, other: "Mark") -> bool:
        if self.value is None or other.value is None:
            return False
        return (
            self.value < other.value
            if self.lower_is_better
            else self.value > other.value
        )

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.raw


def parse_mark(raw: str, type: MarkType) -> Mark:
    """Parse a printed mark into a comparable value, keeping the original.

    Handles the forms meet-management software actually emits:
      time      ``13.49``  ``2:05.44``  ``1:02:33.4``   -> seconds
      distance  ``16-11.75`` (feet-inches)  ``45.72m``  -> inches
      other     a plain number
    Anything in :data:`NON_MARKS` is kept as an unscored mark rather than
    dropped, because "she was disqualified" is information.
    """
    text = (raw or "").strip()
    cleaned = text.lstrip("@#*Jj ").strip()

    if not cleaned or cleaned.upper() in NON_MARKS:
        return Mark(raw=text, type=type, value=None, scored=False)

    if type is MarkType.TIME:
        m = _TIME_HMS.match(cleaned)
        if m:
            h, mm, ss, frac = m.groups()
            v = int(h) * 3600 + int(mm) * 60 + int(ss) + float(f"0.{frac or 0}")
            return Mark(raw=text, type=type, value=v)
        m = _TIME.match(cleaned)
        if m:
            mins, secs, frac = m.groups()
            v = (int(mins or 0) * 60) + int(secs) + float(f"0.{frac}")
            return Mark(raw=text, type=type, value=v)

    if type in (MarkType.DISTANCE, MarkType.HEIGHT):
        m = _FEET_IN.match(cleaned)
        if m:
            feet, inches = m.groups()
            return Mark(raw=text, type=type, value=int(feet) * 12 + float(inches))
        m = _METRIC.match(cleaned)
        if m:
            return Mark(raw=text, type=type, value=float(m.group(1)) * 39.3701)

    if _PLAIN.match(cleaned):
        return Mark(raw=text, type=type, value=float(cleaned))

    return Mark(raw=text, type=type, value=None, scored=False)


# ------------------------------------------------------------- participants


@dataclass(frozen=True)
class Competitor:
    """One athlete. ``year`` is a grade level and is often absent or ``--``."""

    name: str
    school: str
    year: str | None = None


@dataclass
class Entry:
    """One line of an event's results.

    ``competitors`` holds more than one entry for a relay or a doubles pair,
    which is why it is a list rather than a field on the entry itself.
    """

    place: int | None
    school: str
    mark: Mark | None = None
    competitors: list[Competitor] = field(default_factory=list)
    points: float | None = None
    heat: int | None = None
    qualifier: str | None = None   # "Q" automatic, "q" time-qualifier
    note: str | None = None

    @property
    def is_relay(self) -> bool:
        return len(self.competitors) > 1


@dataclass
class StandingRecord:
    """A record line printed above an event ("1A2A East: 18-05 @ 2022 …")."""

    scope: str
    mark: Mark
    holder: str | None = None
    school: str | None = None
    date: str | None = None


@dataclass
class Event:
    """One scored event within a MEET."""

    number: int | None
    name: str
    gender: str | None = None
    division: str | None = None      # classification: 1A, 4A, …
    round: str | None = None         # "Finals", "Preliminaries"
    mark_type: MarkType = MarkType.TIME
    entries: list[Entry] = field(default_factory=list)
    records: list[StandingRecord] = field(default_factory=list)

    def podium(self, n: int = 3) -> list[Entry]:
        return [e for e in self.entries if e.place and e.place <= n]


@dataclass
class TeamScore:
    """A derived team result. Never authoritative — recomputed from entries."""

    school: str
    points: float
    rank: int | None = None
    gender: str | None = None
    division: str | None = None


# ------------------------------------------------------------------ contests


@dataclass
class Contest:
    """Base for the three shapes. ``key`` is the stable identity of the event."""

    # Every field carries a default so the three shape subclasses can redeclare
    # `shape` with one of their own without stranding the fields after it.
    shape: Shape = Shape.MEET
    name: str = ""
    date: str | None = None
    end_date: str | None = None
    venue: str | None = None
    sport: str | None = None
    season: str | None = None
    provenance: Provenance | None = None

    @property
    def key(self) -> str:
        return f"{self.date or 'undated'}:{self.name}"


@dataclass
class Meet(Contest):
    """N teams, M events, derived team scores."""

    shape: Shape = Shape.MEET
    events: list[Event] = field(default_factory=list)
    team_scores: list[TeamScore] = field(default_factory=list)
    host: str | None = None

    @property
    def schools(self) -> list[str]:
        seen: dict[str, None] = {}
        for ev in self.events:
            for e in ev.entries:
                seen.setdefault(e.school, None)
        return list(seen)

    def scored_events(self) -> list[Event]:
        return [e for e in self.events if any(x.points for x in e.entries)]


@dataclass
class Line:
    """One flight of a DUAL — singles 3, doubles 1, the 145lb bout."""

    slot: int
    kind: str                       # "singles" | "doubles" | weight class
    home: list[Competitor] = field(default_factory=list)
    away: list[Competitor] = field(default_factory=list)
    winner: str | None = None       # "home" | "away"
    score: str | None = None        # "6-4, 3-6, 10-8" / "Fall 3:21"
    team_point: float = 1.0


@dataclass
class Dual(Contest):
    """2 teams, N ordered lines. The shape cheesybook already implements."""

    shape: Shape = Shape.DUAL
    home: str = ""
    away: str = ""
    lines: list[Line] = field(default_factory=list)
    home_points: float | None = None
    away_points: float | None = None
    clinched_at: int | None = None

    def compute_points(self) -> tuple[float, float]:
        h = sum(l.team_point for l in self.lines if l.winner == "home")
        a = sum(l.team_point for l in self.lines if l.winner == "away")
        return h, a


@dataclass
class Period:
    label: str                      # "1", "OT", "Set 2"
    home: int
    away: int


@dataclass
class Game(Contest):
    """2 teams, one score each. The trivial case, kept last on purpose."""

    shape: Shape = Shape.GAME
    home: str = ""
    away: str = ""
    home_score: int | None = None
    away_score: int | None = None
    periods: list[Period] = field(default_factory=list)
    status: str = "final"

    @property
    def winner(self) -> str | None:
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score == self.away_score:
            return None
        return self.home if self.home_score > self.away_score else self.away


# --------------------------------------------------------------- team scoring

#: Places-to-points tables. Which one applies is a property of the meet, not the
#: sport — an association picks a table and the same sport scores differently
#: across state lines. Never hard-code one.
PLACING_TABLES: dict[str, list[float]] = {
    "track_16": [10, 8, 6, 5, 4, 3, 2, 1],
    "track_dual": [5, 3, 1],
    "swim_16": [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1],
    "xc_top5": [1, 2, 3, 4, 5, 6, 7],   # cross country: low score wins
}


def score_meet(meet: Meet, table: str = "track_16") -> list[TeamScore]:
    """Recompute team scores from entries.

    Team scores are always derived, never trusted from the source. A printed
    team-score table is a checksum for the extraction, not an input to it.
    """
    points = PLACING_TABLES[table]
    totals: dict[tuple[str, str | None, str | None], float] = {}

    for ev in meet.events:
        for entry in ev.entries:
            if not entry.place or entry.place > len(points):
                continue
            if entry.mark is not None and not entry.mark.scored:
                continue
            key = (entry.school, ev.gender, ev.division)
            totals[key] = totals.get(key, 0.0) + points[entry.place - 1]

    scores = [
        TeamScore(school=s, points=p, gender=g, division=d)
        for (s, g, d), p in totals.items()
    ]
    scores.sort(key=lambda t: (t.gender or "", t.division or "", -t.points))

    rank = 0
    prev: tuple[str | None, str | None] | None = None
    for t in scores:
        bucket = (t.gender, t.division)
        rank = 1 if bucket != prev else rank + 1
        t.rank = rank
        prev = bucket
    return scores
