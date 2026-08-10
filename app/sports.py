"""
The JHSAA activities catalog: 45 sanctioned activities over three shapes.

Two ideas carry this file:

1. Every activity is a configuration over GAME / DUAL / MEET — nothing downstream
   knows what sport it is looking at beyond this catalog.
2. **`classification` is not `championship_group`.** A school carries one base
   class (6A–1A, by enrollment); each sport maps those classes onto its own
   championship divisions, consolidating where participation doesn't support six
   brackets. Tennis runs 7A/6A/5A/4A/3A-1A; swimming runs 7A-5A/4A-1A; skiing and
   fencing run open divisions. `champ_group()` is the single authority.

Associations sanction *activities*, not just sports — marching band, choir and
debate crown state champions under the same body, on the same calendar, in the
same classifications. They are MEETs whose marks aren't numbers: band is judged
POINTS, choir is an adjudicated RATING (I–IV), debate is pure ORDINAL placing.
Nothing downstream needed changing to carry them, which is the point of a mark
type wider than a stopwatch.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.shapes import MarkType, Shape

CLASSES = ["7A", "6A", "5A", "4A", "3A", "2A", "1A"]


@dataclass(frozen=True)
class Sport:
    key: str                 # slug: "girls-tennis"
    name: str                # "Girls Tennis"
    season: str              # "fall" | "winter" | "spring"
    gender: str              # "Boys" | "Girls" | "Coed"
    shape: Shape
    mark_type: MarkType | None   # MEET sports only
    groups: tuple[tuple[str, ...], ...]  # championship divisions, as class tuples
    reach: str               # participation: "broad" | "metro" | "mountain" | "aquatic"
    lower_is_better: bool = False        # MEET team scoring direction (XC/golf/ski)

    def champ_group(self, classification: str) -> str:
        for grp in self.groups:
            if classification in grp:
                if len(grp) == 1:
                    return grp[0]
                if len(grp) == len(CLASSES):
                    return "Open"
                return f"{grp[0]}-{grp[-1]}"   # consolidated span: "3A-1A"
        return "Open"


def _g(*specs: str) -> tuple[tuple[str, ...], ...]:
    """'6A 5A 4A 3A-1A' -> ((6A,),(5A,),(4A,),(3A,2A,1A))."""
    out = []
    for token in specs:
        for part in token.split():
            if "-" in part and part not in CLASSES:
                a, b = part.split("-")
                i, j = CLASSES.index(a), CLASSES.index(b)
                out.append(tuple(CLASSES[i : j + 1]))
            else:
                out.append((part,))
    return tuple(out)


ALL_CLASSES = _g("7A 6A 5A 4A 3A 2A 1A")
OPEN = (tuple(CLASSES),)   # one open division

S = Shape
M = MarkType

CATALOG: list[Sport] = [
    # ---- fall ----
    Sport("football", "Football", "fall", "Boys", S.GAME, None, ALL_CLASSES, "broad"),
    Sport("marching-band", "Marching Band", "fall", "Coed", S.MEET, M.POINTS, _g("7A-5A 4A-3A 2A-1A"), "broad"),
    Sport("boys-soccer", "Boys Soccer", "fall", "Boys", S.GAME, None, _g("7A 6A 5A 4A 3A 2A-1A"), "broad"),
    Sport("girls-soccer", "Girls Soccer", "fall", "Girls", S.GAME, None, _g("7A 6A 5A 4A 3A 2A-1A"), "broad"),
    Sport("field-hockey", "Field Hockey", "fall", "Girls", S.GAME, None, _g("7A-5A 4A-1A"), "metro"),
    Sport("girls-volleyball", "Girls Volleyball", "fall", "Girls", S.GAME, None, ALL_CLASSES, "broad"),
    Sport("boys-cross-country", "Boys Cross Country", "fall", "Boys", S.MEET, M.TIME, ALL_CLASSES, "broad", lower_is_better=True),
    Sport("girls-cross-country", "Girls Cross Country", "fall", "Girls", S.MEET, M.TIME, ALL_CLASSES, "broad", lower_is_better=True),
    Sport("girls-tennis", "Girls Tennis", "fall", "Girls", S.DUAL, None, _g("7A 6A 5A 4A 3A-1A"), "broad"),
    Sport("boys-golf", "Boys Golf", "fall", "Boys", S.MEET, M.STROKES, _g("7A 6A 5A 4A 3A-1A"), "broad", lower_is_better=True),
    Sport("mountain-biking", "Mountain Biking", "fall", "Coed", S.MEET, M.TIME, OPEN, "mountain", lower_is_better=True),
    Sport("girls-rugby", "Girls Rugby Sevens", "fall", "Girls", S.GAME, None, _g("7A-5A 4A-1A"), "metro"),
    # T10 cricket: ten overs a side, one innings each. A GAME whose box score
    # is two INNINGS, each with a batting card and a bowling card. A boys'
    # sport with no girls' counterpart, the way baseball is.
    Sport("cricket", "Cricket", "fall", "Boys", S.GAME, None, _g("7A-4A 3A-1A"), "metro"),
    Sport("boys-water-polo", "Boys Water Polo", "fall", "Boys", S.GAME, None, OPEN, "aquatic"),
    Sport("girls-water-polo", "Girls Water Polo", "fall", "Girls", S.GAME, None, OPEN, "aquatic"),
    # ---- winter ----
    Sport("boys-basketball", "Boys Basketball", "winter", "Boys", S.GAME, None, ALL_CLASSES, "broad"),
    Sport("girls-basketball", "Girls Basketball", "winter", "Girls", S.GAME, None, ALL_CLASSES, "broad"),
    Sport("boys-wrestling", "Boys Wrestling", "winter", "Boys", S.DUAL, None, _g("7A 6A 5A 4A 3A 2A-1A"), "broad"),
    Sport("girls-wrestling", "Girls Wrestling", "winter", "Girls", S.DUAL, None, _g("7A 6A 5A 4A 3A 2A-1A"), "broad"),
    Sport("boys-swimming", "Boys Swimming & Diving", "winter", "Boys", S.MEET, M.TIME, _g("7A-5A 4A-1A"), "aquatic"),
    Sport("girls-swimming", "Girls Swimming & Diving", "winter", "Girls", S.MEET, M.TIME, _g("7A-5A 4A-1A"), "aquatic"),
    Sport("boys-ice-hockey", "Boys Ice Hockey", "winter", "Boys", S.GAME, None, OPEN, "mountain"),
    Sport("girls-ice-hockey", "Girls Ice Hockey", "winter", "Girls", S.GAME, None, OPEN, "mountain"),
    Sport("boys-alpine-skiing", "Boys Alpine Skiing", "winter", "Boys", S.MEET, M.TIME, OPEN, "mountain", lower_is_better=True),
    Sport("girls-alpine-skiing", "Girls Alpine Skiing", "winter", "Girls", S.MEET, M.TIME, OPEN, "mountain", lower_is_better=True),
    Sport("boys-nordic-skiing", "Boys Nordic Skiing", "winter", "Boys", S.MEET, M.TIME, OPEN, "mountain", lower_is_better=True),
    Sport("girls-nordic-skiing", "Girls Nordic Skiing", "winter", "Girls", S.MEET, M.TIME, OPEN, "mountain", lower_is_better=True),
    Sport("bowling", "Bowling", "winter", "Coed", S.MEET, M.PINFALL, _g("7A-4A 3A-1A"), "broad"),
    Sport("boys-fencing", "Boys Fencing", "winter", "Boys", S.DUAL, None, OPEN, "metro"),
    Sport("girls-fencing", "Girls Fencing", "winter", "Girls", S.DUAL, None, OPEN, "metro"),
    Sport("gymnastics", "Gymnastics", "winter", "Girls", S.MEET, M.POINTS, _g("7A-5A 4A-1A"), "metro"),
    Sport("competitive-spirit", "Competitive Spirit", "winter", "Coed", S.MEET, M.POINTS, _g("7A 6A 5A 4A-1A"), "broad"),
    Sport("winter-track", "Winter Track", "winter", "Coed", S.MEET, M.TIME, OPEN, "metro"),
    # A five-player singles LADDER, #1 through #5, clinching at three. Five is
    # deliberate: it cannot tie, and it fits two courts in an hour where the
    # traditional seven-player ladder needs four courts for two. CO-ED — one
    # ladder, best five players in the school, which is how the sport is
    # actually run where a school has two courts and not two programs.
    Sport("squash", "Squash", "winter", "Coed", S.DUAL, None, _g("7A-5A 4A-1A"), "metro"),
    Sport("debate", "Debate", "winter", "Coed", S.MEET, M.ORDINAL, _g("7A-4A 3A-1A"), "metro", lower_is_better=True),

    # ---- spring ----
    Sport("baseball", "Baseball", "spring", "Boys", S.GAME, None, ALL_CLASSES, "broad"),
    Sport("softball", "Softball", "spring", "Girls", S.GAME, None, ALL_CLASSES, "broad"),
    Sport("boys-lacrosse", "Boys Lacrosse", "spring", "Boys", S.GAME, None, _g("7A 6A 5A-4A 3A-1A"), "metro"),
    Sport("girls-lacrosse", "Girls Lacrosse", "spring", "Girls", S.GAME, None, _g("7A 6A 5A-4A 3A-1A"), "metro"),
    Sport("boys-tennis", "Boys Tennis", "spring", "Boys", S.DUAL, None, _g("7A 6A 5A 4A 3A-1A"), "broad"),
    Sport("boys-volleyball", "Boys Volleyball", "spring", "Boys", S.GAME, None, _g("7A 6A 5A-1A"), "metro"),
    Sport("girls-flag-football", "Girls Flag Football", "spring", "Girls", S.GAME, None, _g("7A 6A 5A 4A-1A"), "metro"),
    # Badminton is CO-ED and runs five lines off an eight-player squad — four
    # boys, four girls, everyone in exactly one line. The full CIF format is
    # twenty-one lines off a much bigger roster; five is the same shape at a
    # size a high school with one gym can actually field.
    Sport("badminton", "Badminton", "spring", "Coed", S.DUAL, None, _g("7A 6A 5A 4A-1A"), "metro"),
    # Rugby sevens, split across the calendar the way the sport is played.
    Sport("boys-rugby", "Boys Rugby Sevens", "spring", "Boys", S.GAME, None, _g("7A-5A 4A-1A"), "metro"),
    Sport("ultimate", "Ultimate", "spring", "Coed", S.GAME, None, _g("7A-4A 3A-1A"), "metro"),
    Sport("choir", "Choir", "spring", "Coed", S.MEET, M.RATING, _g("7A-5A 4A-3A 2A-1A"), "broad", lower_is_better=True),
    Sport("girls-golf", "Girls Golf", "spring", "Girls", S.MEET, M.STROKES, _g("7A 6A 5A 4A 3A-1A"), "broad", lower_is_better=True),
    Sport("boys-track", "Boys Track & Field", "spring", "Boys", S.MEET, M.TIME, ALL_CLASSES, "broad"),
    Sport("girls-track", "Girls Track & Field", "spring", "Girls", S.MEET, M.TIME, ALL_CLASSES, "broad"),
    # Chess is a DUAL: eight boards in order, a point a board, and boards that
    # DRAW — the only sanctioned activity here whose team score is routinely a
    # half (4.5-3.5). It runs one open championship rather than one per
    # classification, and its reach is deliberately "broad" with no small-school
    # penalty: the real Oregon association this is modelled on has been won by
    # Cottage Grove, Clatskanie, Sweet Home and South Umpqua as often as by the
    # big suburban programs, which is true of no other activity in the catalog.
    Sport("chess", "Chess", "spring", "Coed", S.DUAL, None, OPEN, "broad"),
]

BY_KEY: dict[str, Sport] = {s.key: s for s in CATALOG}


#: How a MEET sport derives its TEAM result, keyed by sport family:
#: ``(rule, how many count, what the column is called)``.
#:
#:   places       add the school's best N finishing PLACES in each event. Low
#:                wins. Cross country, and the racing sports that score the
#:                same way.
#:   best-marks   add the school's best N MARKS in each event: strokes, pinfall,
#:                judged points, adjudicated ratings. Direction follows the mark.
#:   place-points 10-8-6-5-4-3-2-1 by place, a relay worth double. High wins.
#:
#: This lives with the catalog rather than in the generator because both sides
#: need it: the generator computes the score and the renderer labels the
#: column. Split across the two, a golf team's 326 gets a header reading
#: "Points" and the page contradicts itself.
MEET_SCORING: dict[str, tuple[str, int, str]] = {
    "cross-country": ("places", 5, "Points"),
    "alpine-skiing": ("places", 3, "Points"),
    "nordic-skiing": ("places", 3, "Points"),
    "mountain-biking": ("places", 4, "Points"),
    "golf": ("best-marks", 4, "Strokes"),
    "bowling": ("best-marks", 4, "Pinfall"),
    "gymnastics": ("best-marks", 3, "Score"),
    "competitive-spirit": ("best-marks", 1, "Score"),
    "marching-band": ("best-marks", 1, "Score"),
    "choir": ("best-marks", 1, "Rating"),
    "swimming": ("place-points", 0, "Points"),
    "winter-track": ("place-points", 0, "Points"),
    "track": ("place-points", 0, "Points"),
    "debate": ("place-points", 0, "Points"),
}


def meet_family(sport_key: str) -> str:
    """The scoring/event family a MEET sport belongs to.

    ``winter-track`` is checked first: "track" is a substring of both, and the
    loose match hands a February meet the outdoor card — javelin, indoors.
    """
    for fam in ("winter-track", *MEET_SCORING):
        if fam in sport_key:
            return fam
    return "cross-country"


def meet_scoring(sport_key: str) -> tuple[str, int, str]:
    return MEET_SCORING[meet_family(sport_key)]


def champ_group(sport_key: str, classification: str) -> str:
    return BY_KEY[sport_key].champ_group(classification)
