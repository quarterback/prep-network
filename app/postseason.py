"""
Bracket geometry: an elimination tree laid out on one coordinate canvas.

Adapted from the NCAA bracket in the `tennis-team-manager` repo, which learned
the load-bearing lesson the hard way and wrote it down: **cards and connector
lines must share one coordinate system, computed server-side.** A bracket whose
boxes are laid out by document flow and whose elbows are drawn by CSS will drift
apart at some viewport width, and every attempt to fix the drift in CSS moves it
somewhere else. Here both come out of the same pass, so they cannot disagree.

The rule that positions everything: the widest full round is the leaf column and
is spaced evenly; every later matchup is centred on the average of the two
feeders that can send it a team. That is what makes a bracket *read* — a card
sits between the two cards it can receive from, so the eye follows the path a
team takes without needing the lines at all.

Byes are laid out, not skipped. A 12-team field has four first-round matchups
and four byes; the byes occupy their slots so that the quarterfinal a bye feeds
sits where the tree says it should, rather than sliding up against a
first-round game it has nothing to do with.

This module is geometry only — no HTML, no CSS classes, no escaping. The
renderer decides what a card looks like; this decides where it goes.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.shapes import Matchup, Round, Tournament

#: Card metrics, in the canvas's own units (which the renderer treats as px).
CARD_W = 232
CARD_H = 58
GUTTER = 46          # horizontal space between columns, where the elbows live
LEAF_GAP = 16        # vertical space between adjacent first-round cards
PAD_Y = 10


@dataclass(frozen=True)
class Card:
    matchup: Matchup
    x: float
    y: float
    col: int
    slot: int
    round_name: str

    @property
    def is_final(self) -> bool:
        return self.matchup.round >= 0 and self.round_name == "Championship"


@dataclass(frozen=True)
class Column:
    name: str
    x: float
    count: int
    index: int


@dataclass(frozen=True)
class Link:
    """One elbow: source right edge → mid-gutter → target y → target left edge."""

    d: str
    live: bool          # the feeder produced a winner now standing in the target
    school: str


@dataclass(frozen=True)
class Canvas:
    cards: tuple[Card, ...]
    columns: tuple[Column, ...]
    links: tuple[Link, ...]
    width: float
    height: float
    card_w: int = CARD_W
    card_h: int = CARD_H


def _centres(rounds: list[Round]) -> list[list[float]]:
    """Vertical centre of every card, column by column."""
    widest = max(len(r.matchups) for r in rounds)
    base = max(i for i, r in enumerate(rounds) if len(r.matchups) == widest)
    stride = CARD_H + LEAF_GAP

    out: list[list[float]] = [[] for _ in rounds]
    out[base] = [PAD_Y + i * stride + CARD_H / 2 for i in range(widest)]

    # Rightwards: centre each card between the two feeders it can receive from.
    for i in range(base + 1, len(rounds)):
        prev = out[i - 1]
        out[i] = [
            (prev[2 * k] + prev[2 * k + 1]) / 2
            if 2 * k + 1 < len(prev)
            else prev[min(2 * k, len(prev) - 1)]
            for k in range(len(rounds[i].matchups))
        ]

    # Leftwards: a play-in column feeds one destination each, so it sits level
    # with what it feeds rather than being spaced on its own.
    for i in range(base - 1, -1, -1):
        nxt = out[i + 1]
        out[i] = [
            nxt[k] if k < len(nxt) else PAD_Y + k * stride + CARD_H / 2
            for k in range(len(rounds[i].matchups))
        ]
    return out


def layout(tournament: Tournament) -> Canvas | None:
    """Position a tournament's rounds as an elimination tree."""
    rounds = [r for r in tournament.rounds if r.matchups]
    if not rounds:
        return None

    centres = _centres(rounds)
    cards: list[Card] = []
    columns: list[Column] = []
    links: list[Link] = []

    for i, rnd in enumerate(rounds):
        x = i * (CARD_W + GUTTER)
        columns.append(Column(name=rnd.name, x=x, count=len(rnd.matchups), index=i))
        for k, m in enumerate(rnd.matchups):
            cards.append(Card(matchup=m, x=x, y=centres[i][k] - CARD_H / 2,
                              col=i, slot=k, round_name=rnd.name))
        if i == 0:
            continue

        prev, prev_c = rounds[i - 1].matchups, centres[i - 1]
        px = (i - 1) * (CARD_W + GUTTER) + CARD_W
        mid = px + GUTTER / 2
        # Either one source per destination (a play-in) or the normal halving.
        pairs = (
            [(k, [k]) for k in range(len(rnd.matchups))]
            if len(prev) == len(rnd.matchups)
            else [(k, [2 * k, 2 * k + 1]) for k in range(len(rnd.matchups))]
        )
        for k, sources in pairs:
            for s in sources:
                if s >= len(prev):
                    continue
                src, dst = prev[s], rnd.matchups[k]
                y0, y1 = prev_c[s], centres[i][k]
                links.append(Link(
                    d=f"M {px} {y0:.1f} H {mid:.1f} V {y1:.1f} H {x}",
                    live=bool(src.winner) and src.winner in (dst.home, dst.away),
                    school=src.winner or "",
                ))

    height = max((c.y + CARD_H for c in cards), default=0) + PAD_Y
    return Canvas(
        cards=tuple(cards), columns=tuple(columns), links=tuple(links),
        width=len(rounds) * (CARD_W + GUTTER) - GUTTER, height=height,
    )


# ------------------------------------------------------------------ grouping


def live_label(t: Tournament) -> str | None:
    """What to say about a tournament that is happening right now.

    Named for the round in play rather than a generic "in progress", because
    "Semifinals" is the thing a reader is actually looking for.
    """
    from app.shapes import TournamentFormat, TournamentStatus

    status = t.status
    if status is TournamentStatus.COMPLETE:
        return None
    if t.format is not TournamentFormat.BRACKET:
        return "Final results" if t.meet_key else "Upcoming"
    rnd = t.current_round()
    if rnd is None:
        return None
    return rnd.name if rnd.started or t.status is TournamentStatus.IN_PROGRESS else None


def group_by_sport(tournaments: list[Tournament]) -> dict[str, list[Tournament]]:
    """Championships keyed by sport, each list in championship-division order."""
    out: dict[str, list[Tournament]] = {}
    for t in tournaments:
        out.setdefault(t.sport, []).append(t)
    for lst in out.values():
        lst.sort(key=lambda t: _group_order(t.group))
    return out


#: Championship divisions sort biggest-first (6A → 1A), with consolidated spans
#: ("3A-1A") landing on their first class and open divisions last.
def _group_order(group: str) -> tuple[int, str]:
    from app.sports import CLASSES

    head = (group or "").split("-")[0].strip()
    if head in CLASSES:
        return (CLASSES.index(head), group)
    return (len(CLASSES), group)
