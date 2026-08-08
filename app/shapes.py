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


class SourceType(str, Enum):
    """What produced the file we parsed.

    The *format family*, not the vendor's product name: a Hy-Tek MEET MANAGER
    printout and a Hy-Tek TEAM MANAGER printout share a layout engine, and an
    adapter written for one is a starting point for the other. Knowing the
    family is what lets a reviewer judge an extraction without reopening the
    source.
    """

    HYTEK_PDF = "hytek_pdf"          # MEET MANAGER / TEAM MANAGER printout
    HYTEK_HY3 = "hytek_hy3"          # Hy-Tek interchange
    BOXSCORE_CSV = "boxscore_csv"    # scorebook / statbook export
    DUAL_CSV = "dual_csv"            # match card export
    MANUAL = "manual"                # typed into an entry form
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Provenance:
    """Where a record came from. Mandatory — extraction is never anonymous.

    Because nothing rendered is model-generated, there is no prose layer to hide
    a bad extraction behind. An unreviewed extraction is not a result.

    Enough here to *audit the record later without the operator who ran it*:

        source_type      the format family, so a reviewer knows what to expect
        source_uri       filename or URL, whichever the import actually had
        source_sha256    content hash — proves which bytes produced this record
        source_page      where in a 237-page bundle this contest was found
        external_ids     the source's own identity for the contest (meet id,
                         event numbers, game id) — the join key for a re-import
        adapter          which parser ran
        adapter_version  and which version of it, because a reparse of the same
                         bytes by a later parser is a different claim
        extracted_at     when

    ``external_ids`` is what makes a second import an *update* rather than a
    duplicate: the source's own key survives normalisation.
    """

    source_uri: str
    adapter: str
    extracted_at: str
    confidence: float = 1.0
    review_state: ReviewState = ReviewState.PUBLISHED
    source_type: SourceType = SourceType.UNKNOWN
    source_sha256: str | None = None
    source_page: int | None = None
    adapter_version: str = "0"
    external_ids: dict[str, str] = field(default_factory=dict)
    notes: str | None = None

    def publishable(self, threshold: float = 0.9) -> bool:
        return (
            self.review_state is ReviewState.PUBLISHED
            and self.confidence >= threshold
        )

    @property
    def source_name(self) -> str:
        """The bare filename, for display. A URL keeps its last segment."""
        return (self.source_uri or "").rstrip("/").rsplit("/", 1)[-1]

    @property
    def is_url(self) -> bool:
        return (self.source_uri or "").startswith(("http://", "https://"))


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

    if type is MarkType.RATING:
        # Adjudicated panels print Roman numerals: a Division I rating is the
        # best a choir can earn. Comparable value = the numeral, so lower wins.
        roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
        if cleaned.upper() in roman:
            return Mark(raw=text, type=type, value=float(roman[cleaned.upper()]))

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
class StatLine:
    """One player's row in a box score.

    ``stats`` is an open dict rather than named fields because a box score's
    columns are a property of the *sport and the scorebook*, not of the model:
    basketball prints MIN/FG/3PT/FT/REB/PTS, volleyball prints K/E/TA/AST/DIG,
    hockey prints G/A/PIM. Naming them here would put a sport in the schema —
    the one thing this model is built to avoid. The column ORDER lives on the
    box score so the renderer prints the source's own columns, in the source's
    own order, without knowing what they mean.
    """

    competitor: Competitor
    stats: dict[str, str] = field(default_factory=dict)
    starter: bool = False

    def get(self, column: str) -> str:
        return self.stats.get(column, "")


@dataclass
class BoxScore:
    """Per-player statistics for a GAME, plus the team totals row.

    Totals are kept as printed rather than summed: a scorebook's total row is a
    CHECKSUM for the extraction (the same rule team scores follow in a MEET).
    :meth:`totals_agree` is what a review queue reads.
    """

    columns: list[str] = field(default_factory=list)
    home: list[StatLine] = field(default_factory=list)
    away: list[StatLine] = field(default_factory=list)
    home_totals: dict[str, str] = field(default_factory=dict)
    away_totals: dict[str, str] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.home or self.away)

    def totals_agree(self, column: str) -> bool | None:
        """Does the printed total match the sum of the player rows?

        ``None`` when the column isn't numeric or isn't totalled — plenty of
        columns (a jersey number, a shooting line like ``7-14``) are neither.
        """
        out = []
        for lines, totals in ((self.home, self.home_totals), (self.away, self.away_totals)):
            printed = totals.get(column)
            if printed is None:
                return None
            try:
                summed = sum(float(l.stats[column]) for l in lines if l.stats.get(column))
                out.append(abs(summed - float(printed)) < 0.01)
            except ValueError:
                return None
        return all(out)


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
    box: BoxScore | None = None

    @property
    def winner(self) -> str | None:
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score == self.away_score:
            return None
        return self.home if self.home_score > self.away_score else self.away

    def periods_agree(self) -> bool | None:
        """Do the period splits add to the final score? A checksum, not a source."""
        if not self.periods or self.home_score is None or self.away_score is None:
            return None
        return (
            sum(p.home for p in self.periods) == self.home_score
            and sum(p.away for p in self.periods) == self.away_score
        )


# ----------------------------------------------------------------- postseason

#: How a championship is decided. The postseason is NOT a fourth contest shape —
#: it is a *structure over* contests, which is why a tournament points at GAME /
#: DUAL / MEET records rather than restating them. An association crowns champions
#: in more than one way and a model that assumes single elimination silently
#: excludes swimming, track, cross country, golf and every judged activity.
class TournamentFormat(str, Enum):
    BRACKET = "bracket"      # single elimination: GAME or DUAL per matchup
    MEET = "meet"            # one championship meet decides it: a MEET record
    SERIES = "series"        # multi-day aggregate (golf 36-hole, ski combined)


class TournamentStatus(str, Enum):
    UPCOMING = "upcoming"        # field set, nothing played
    IN_PROGRESS = "in_progress"  # some rounds final
    COMPLETE = "complete"        # champion decided


@dataclass
class Entrant:
    """One qualified team in a championship field.

    ``seed`` is None for an unseeded field — plenty of associations qualify
    teams without ranking them, and a model that requires a seed invents one.
    """

    school: str
    seed: int | None = None
    qualifier: str | None = None    # "Conference champion", "At-large", "Play-in"
    record: str | None = None       # "11-1" as the committee saw it
    conference: str | None = None


@dataclass
class Matchup:
    """One node in an elimination tree.

    Holds only what the BRACKET needs to draw itself and to find the contest.
    The result itself lives in the GAME/DUAL record that ``contest_key`` points
    at — a matchup that restated the score would be a second source of truth for
    it, and the two would drift.

    A **bye is structural**: ``away is None`` with :attr:`bye` set. The seeded
    team advances without a contest, which is what actually happened; inventing a
    "BYE" opponent would put a school that does not exist into the schools index,
    the standings and every school page that counts opponents.
    """

    round: int                       # 0 = first round played
    slot: int                        # position within the round, top to bottom
    home: str | None = None
    away: str | None = None
    home_seed: int | None = None
    away_seed: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    contest_key: str | None = None   # -> the GAME/DUAL record
    date: str | None = None
    time: str | None = None
    venue: str | None = None
    status: str = "scheduled"        # "scheduled" | "final"
    bye: bool = False

    @property
    def winner(self) -> str | None:
        if self.bye:
            return self.home
        if self.status != "final":
            return None
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score == self.away_score:
            return None
        return self.home if self.home_score > self.away_score else self.away

    @property
    def loser(self) -> str | None:
        w = self.winner
        if w is None or self.bye:
            return None
        return self.away if w == self.home else self.home

    @property
    def decided(self) -> bool:
        return self.winner is not None

    @property
    def resolved(self) -> bool:
        """Nothing further will happen here.

        A cancelled contest is not decided — there is no winner and inventing
        one would be a lie — but it is finished, and a bracket that treats it as
        merely undecided reports itself as still being played forever. The state
        has exactly one of these: a 3A girls soccer final that was called off.
        """
        return self.decided or self.status == "cancelled"

    @property
    def ready(self) -> bool:
        """Both sides known — the matchup can be shown as a real fixture."""
        return bool(self.home and self.away)


@dataclass
class Round:
    """One column of the tree. ``index`` 0 is the first round played."""

    index: int
    name: str                        # "First Round", "Quarterfinals", …
    matchups: list[Matchup] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return bool(self.matchups) and all(m.resolved for m in self.matchups)

    @property
    def started(self) -> bool:
        # A bye is decided the moment the field is drawn. Counting it as play
        # would show a bracket as "in progress" before anyone had taken a court.
        return any(m.decided and not m.bye for m in self.matchups)


#: Round names counted BACK from the final, which is how they are actually
#: named: the round with 8 matchups is only "the quarterfinals" if 4 teams come
#: out of it. Indexing from the front names a 32-team first round "quarterfinal".
_ROUND_NAMES = {1: "Championship", 2: "Semifinals", 3: "Quarterfinals"}


def round_name(matchups_in_round: int, total_rounds: int, index: int) -> str:
    """Name a round by how far it is from the final."""
    from_end = total_rounds - index
    if from_end in _ROUND_NAMES:
        return _ROUND_NAMES[from_end]
    if index == 0:
        return "First Round"
    return f"Round of {matchups_in_round * 2}"


@dataclass
class Tournament:
    """A championship: the field, the structure, and where it points.

    This is the record an association publishes and the one the incumbents keep
    only as a printed bracket image. It is deliberately not sport-specific —
    ``format`` decides whether it renders as a tree or hands off to a meet.
    """

    id: str = ""                     # "2026-27-football-1a"
    name: str = ""                   # "2026 JHSAA 1A Football State Championship"
    sport: str = ""                  # sport key
    season: str = ""                 # "2026-27"
    group: str = ""                  # championship division: "1A", "3A-1A", "Open"
    format: TournamentFormat = TournamentFormat.BRACKET
    entrants: list[Entrant] = field(default_factory=list)
    rounds: list[Round] = field(default_factory=list)
    meet_key: str | None = None      # MEET-format: -> the championship MEET record
    final_venue: str | None = None
    final_date: str | None = None
    start_date: str | None = None
    provenance: Provenance | None = None

    @property
    def size(self) -> int:
        return len(self.entrants)

    @property
    def bracket_size(self) -> int:
        """Slots in the tree — the next power of two at or above the field."""
        n = max(self.size, 1)
        p = 1
        while p < n:
            p *= 2
        return p

    @property
    def byes(self) -> int:
        return self.bracket_size - self.size

    @property
    def status(self) -> TournamentStatus:
        if self.format is not TournamentFormat.BRACKET:
            # A meet-decided title has no rounds to inspect. It is finished when
            # the meet it points at exists; before that it is a date on the
            # calendar. Falling through to the bracket logic reports every
            # swimming and cross-country championship as permanently upcoming.
            return (TournamentStatus.COMPLETE if self.meet_key
                    else TournamentStatus.UPCOMING)
        if not self.rounds:
            return TournamentStatus.UPCOMING
        # COMPLETE means the postseason is over, which is not quite the same as
        # "there is a champion": a cancelled final ends the tournament without
        # crowning anyone, and callers must handle `champion is None`.
        if self.champion or all(r.complete for r in self.rounds):
            return TournamentStatus.COMPLETE
        if any(r.started for r in self.rounds):
            return TournamentStatus.IN_PROGRESS
        return TournamentStatus.UPCOMING

    @property
    def final(self) -> Matchup | None:
        if not self.rounds or not self.rounds[-1].matchups:
            return None
        return self.rounds[-1].matchups[0]

    @property
    def champion(self) -> str | None:
        f = self.final
        return f.winner if f else None

    @property
    def runner_up(self) -> str | None:
        f = self.final
        return f.loser if f else None

    def seed_of(self, school: str) -> int | None:
        return next((e.seed for e in self.entrants if e.school == school), None)

    def current_round(self) -> Round | None:
        """The round in play: the first that isn't finished."""
        return next((r for r in self.rounds if not r.complete), None)

    def schools(self) -> list[str]:
        return [e.school for e in self.entrants]

    def matchup_for(self, contest_key: str) -> Matchup | None:
        for r in self.rounds:
            for m in r.matchups:
                if m.contest_key and m.contest_key == contest_key:
                    return m
        return None


def seed_order(bracket_size: int) -> list[int]:
    """Classic bracket seeding: 1 meets the lowest seed, and the top two can
    only meet in the final.

    Built by repeated reflection — ``[1,2]`` → ``[1,4,2,3]`` → ``[1,8,4,5,2,7,3,6]``
    — which is the standard construction, not a table to get wrong by hand.
    """
    order = [1]
    while len(order) < bracket_size:
        n = len(order) * 2
        order = [s for pair in ((x, n + 1 - x) for x in order) for s in pair]
    return order


def build_bracket(entrants: list[Entrant]) -> list[Round]:
    """Lay a seeded field out as an empty single-elimination tree.

    Byes fall out of the seeding rather than being placed: seed *s* meets seed
    ``bracket_size + 1 - s``, and when that opponent is past the end of the field
    the matchup IS the bye. So a 12-team field gives the top four byes without
    anyone deciding that it should.
    """
    n = len(entrants)
    if n < 2:
        return []
    size = 1
    while size < n:
        size *= 2
    by_seed = {e.seed: e for e in entrants if e.seed}
    if len(by_seed) != n:                      # unseeded field: keep source order
        by_seed = {i + 1: e for i, e in enumerate(entrants)}

    order = seed_order(size)
    total_rounds = size.bit_length() - 1

    first: list[Matchup] = []
    for slot in range(size // 2):
        hi, lo = order[2 * slot], order[2 * slot + 1]
        top, bottom = by_seed.get(hi), by_seed.get(lo)
        if top is None and bottom is None:
            continue
        if bottom is None:                     # the opponent is past the field
            first.append(Matchup(round=0, slot=slot, home=top.school,
                                 home_seed=top.seed, bye=True, status="final"))
        elif top is None:
            first.append(Matchup(round=0, slot=slot, home=bottom.school,
                                 home_seed=bottom.seed, bye=True, status="final"))
        else:
            first.append(Matchup(round=0, slot=slot, home=top.school, away=bottom.school,
                                 home_seed=top.seed, away_seed=bottom.seed))

    rounds = [Round(index=0, name=round_name(len(first), total_rounds, 0),
                    matchups=first)]
    count = size // 2
    for idx in range(1, total_rounds):
        count //= 2
        rounds.append(Round(index=idx, name=round_name(count, total_rounds, idx),
                            matchups=[Matchup(round=idx, slot=s) for s in range(count)]))
    return rounds


def advance(tournament: Tournament) -> None:
    """Push every decided winner into the slot it feeds.

    Idempotent, and the ONE place advancement happens: a matchup's teams are
    derived from its feeders rather than stored twice. Slot *k* of round *r+1*
    receives slots *2k* and *2k+1* of round *r* — the same halving the bracket
    was built with, so the tree cannot disagree with itself.
    """
    for r in range(len(tournament.rounds) - 1):
        src, dst = tournament.rounds[r], tournament.rounds[r + 1]
        for m in dst.matchups:
            feeders = [f for f in src.matchups if f.slot // 2 == m.slot]
            feeders.sort(key=lambda f: f.slot)
            top = next((f.winner for f in feeders if f.slot % 2 == 0), None)
            bot = next((f.winner for f in feeders if f.slot % 2 == 1), None)
            m.home, m.away = top, bot
            m.home_seed = tournament.seed_of(top) if top else None
            m.away_seed = tournament.seed_of(bot) if bot else None


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
