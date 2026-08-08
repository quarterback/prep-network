"""
Source strings -> the association's own school, team and athlete records.

This is the step between "we parsed the file" and "the result is on the site",
and it is the one that decides whether an import is worth anything. A meet
record naming ``Lingle Ft. Laramie  High Schoo`` is not attached to a school:
it will not appear on that school's page, will not join its conference
standings, and will index an athlete under a name no page links to. Parsing is
the visible half of ingestion; resolution is the half that makes it a record.

What the source actually gives you
----------------------------------
From the captured Hy-Tek specimen, in one document:

* ``Kaycee  High School`` — a doubled space from a fixed-width field
* ``Lingle Ft. Laramie  High Schoo`` — **truncated mid-word** at the column edge
* ``Southeast High School`` vs ``Southeast`` — suffix present and absent
* ``St. Mary's`` vs ``St Marys`` — punctuation that does not survive round trips

So matching is a ladder, tried in order, each rung recorded on the result:

    exact       the canonical name, unchanged
    normalized  after suffix-stripping and punctuation folding
    alias       a curated mapping, for names no rule can bridge
    prefix      the source is a truncation of exactly one school
    fuzzy       a single close match above a threshold
    (none)      unresolved — reported, never guessed

**Ambiguity is never resolved by picking the best one.** If two schools match a
rung equally, resolution FAILS at that rung and is reported. Silently choosing
between "Copper Lake" and "Copper Lake East" would put results on the wrong
school's page, and nothing downstream could detect it. An unresolved name is a
visible gap; a wrongly resolved one is invisible and wrong.
"""

from __future__ import annotations

import difflib
import json
import pathlib
import re
from dataclasses import dataclass, field

#: Suffixes a source may or may not print. Order matters — the longest first,
#: so "Senior High School" does not reduce to "Senior".
_SUFFIXES = [
    "senior high school", "junior senior high school", "high school",
    "secondary school", "senior high", "jr sr high", "academy high",
    "school", "high", "hs",
]

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")
#: Apostrophes are DELETED rather than spaced. Spacing them turns "St. Mary's"
#: into "st mary s", which no longer matches the same school printed "St Marys"
#: — the exact variation the fold exists to absorb. Curly forms included
#: because a name that has been through a word processor carries them.
_APOSTROPHE = re.compile(r"[’ʼ´'`]")


#: The last word of each suffix, for recognising one that was cut off by a
#: column edge. "Lingle Ft. Laramie  High Schoo" is a real line from the
#: specimen: the suffix is not absent, it is truncated, and a whole-word suffix
#: list does not see it.
_SUFFIX_TAILS = {s.split()[-1] for s in _SUFFIXES}


def normalize(name: str) -> str:
    """Fold a printed school name to a comparable key.

    Suffix stripping repeats, because one pass leaves "… High" behind after a
    truncated "Schoo" is removed.
    """
    text = (name or "").lower().strip()
    text = text.replace("&", " and ")
    text = _APOSTROPHE.sub("", text)
    text = _PUNCT.sub(" ", text)
    text = _WS.sub(" ", text).strip()

    while True:
        for suffix in _SUFFIXES:
            if text.endswith(" " + suffix):
                text = text[: -len(suffix) - 1].strip()
                break
        else:
            # No whole suffix matched. A trailing fragment counts only if it is
            # a strict prefix of a suffix word and long enough not to eat a real
            # name — "Schoo" and "Hig" yes, "S" and "So" (Port Meridian South)
            # never.
            m = re.search(r"\s(\S+)$", text)
            tail = m.group(1) if m else ""
            if len(tail) >= 3 and any(
                t.startswith(tail) and t != tail for t in _SUFFIX_TAILS
            ):
                text = text[: m.start()].strip()
                continue
            return text


@dataclass(frozen=True)
class Resolution:
    """One name, and what became of it."""

    raw: str
    school: str | None
    method: str                      # exact | normalized | alias | prefix | fuzzy | unresolved
    confidence: float
    candidates: tuple[str, ...] = ()  # populated when ambiguity caused a failure

    @property
    def ok(self) -> bool:
        return self.school is not None


@dataclass
class Report:
    """What an import did to the names it was given."""

    resolutions: dict[str, Resolution] = field(default_factory=dict)

    def add(self, r: Resolution) -> Resolution:
        self.resolutions.setdefault(r.raw, r)
        return r

    @property
    def resolved(self) -> list[Resolution]:
        return [r for r in self.resolutions.values() if r.ok]

    @property
    def unresolved(self) -> list[Resolution]:
        return [r for r in self.resolutions.values() if not r.ok]

    @property
    def inexact(self) -> list[Resolution]:
        return [r for r in self.resolved if r.method not in ("exact", "normalized")]

    def summary(self) -> str:
        total = len(self.resolutions)
        by: dict[str, int] = {}
        for r in self.resolutions.values():
            by[r.method] = by.get(r.method, 0) + 1
        parts = ", ".join(f"{k} {v}" for k, v in sorted(by.items()))
        return f"{len(self.resolved)}/{total} names resolved ({parts})"


class Resolver:
    """Resolves source names against the association's own org records."""

    #: Below this, a fuzzy match is not offered at all.
    FUZZY_FLOOR = 0.86

    def __init__(self, schools: list[dict], aliases: dict[str, str] | None = None):
        self.schools = [s["name"] for s in schools]
        self._by_exact = {s: s for s in self.schools}
        self._by_norm: dict[str, list[str]] = {}
        for s in self.schools:
            self._by_norm.setdefault(normalize(s), []).append(s)
        self._aliases = {normalize(k): v for k, v in (aliases or {}).items()}
        self.report = Report()

    # ------------------------------------------------------------- loading

    @classmethod
    def from_records(cls, records_dir: pathlib.Path) -> "Resolver":
        path = records_dir / "orgs" / "schools.json"
        schools = json.loads(path.read_text())["schools"] if path.exists() else []
        alias_path = records_dir / "orgs" / "aliases.json"
        aliases = {}
        if alias_path.exists():
            aliases = json.loads(alias_path.read_text()).get("schools", {})
        return cls(schools, aliases)

    # ------------------------------------------------------------ matching

    def resolve(self, raw: str) -> Resolution:
        raw = (raw or "").strip()
        if not raw:
            return self.report.add(Resolution(raw, None, "unresolved", 0.0))
        cached = self.report.resolutions.get(raw)
        if cached is not None:
            return cached

        if raw in self._by_exact:
            return self.report.add(Resolution(raw, raw, "exact", 1.0))

        key = normalize(raw)

        if key in self._aliases:
            return self.report.add(Resolution(raw, self._aliases[key], "alias", 1.0))

        hits = self._by_norm.get(key, [])
        if len(hits) == 1:
            return self.report.add(Resolution(raw, hits[0], "normalized", 0.99))
        if len(hits) > 1:
            return self.report.add(
                Resolution(raw, None, "unresolved", 0.0, tuple(sorted(hits))))

        # --- truncation: the source is a prefix of exactly one school.
        #     Guarded by a length floor because a 4-character prefix matches
        #     half the state, and by uniqueness because "Copper Lake" is a
        #     prefix of both "Copper Lake" and "Copper Lake East".
        if len(key) >= 8:
            pref = sorted({
                canon for norm, names in self._by_norm.items()
                for canon in names if norm.startswith(key)
            })
            if len(pref) == 1:
                return self.report.add(Resolution(raw, pref[0], "prefix", 0.95))
            if len(pref) > 1:
                return self.report.add(
                    Resolution(raw, None, "unresolved", 0.0, tuple(pref)))

        # --- last rung: closest normalized key, and only if it stands alone
        close = difflib.get_close_matches(key, list(self._by_norm), n=2,
                                          cutoff=self.FUZZY_FLOOR)
        if len(close) == 1 and len(self._by_norm[close[0]]) == 1:
            score = difflib.SequenceMatcher(None, key, close[0]).ratio()
            return self.report.add(
                Resolution(raw, self._by_norm[close[0]][0], "fuzzy", round(score, 3)))
        if len(close) > 1:
            cands = tuple(sorted(n for c in close for n in self._by_norm[c]))
            return self.report.add(Resolution(raw, None, "unresolved", 0.0, cands))

        return self.report.add(Resolution(raw, None, "unresolved", 0.0))

    def school(self, raw: str) -> str:
        """The canonical name, or the raw string when it cannot be resolved.

        Deliberately non-fatal: an unresolvable school still belongs in the
        record — dropping the entry would lose a real result — but it is in the
        report, and :meth:`Report.unresolved` is what the review queue reads.
        """
        r = self.resolve(raw)
        return r.school or raw


# --------------------------------------------------------------- applying


def apply_to_contest(contest, resolver: Resolver) -> None:
    """Rewrite every school reference on a parsed contest, in place.

    Athletes are keyed by ``(name, school)`` everywhere downstream, so a
    competitor whose school is rewritten without rewriting the competitor is a
    second, orphaned athlete. Every place a school name appears is rewritten
    here or not at all.
    """
    from app.shapes import Dual, Game, Meet

    if isinstance(contest, Meet):
        for ev in contest.events:
            for entry in ev.entries:
                entry.school = resolver.school(entry.school)
                for i, c in enumerate(entry.competitors):
                    entry.competitors[i] = _recompetitor(c, entry.school)
            for rec in ev.records:
                if rec.school:
                    rec.school = resolver.school(rec.school)
        for ts in contest.team_scores:
            ts.school = resolver.school(ts.school)
        if contest.host:
            contest.host = resolver.school(contest.host)

    elif isinstance(contest, Dual):
        contest.home = resolver.school(contest.home)
        contest.away = resolver.school(contest.away)
        for line in contest.lines:
            line.home = [_recompetitor(c, contest.home) for c in line.home]
            line.away = [_recompetitor(c, contest.away) for c in line.away]

    elif isinstance(contest, Game):
        contest.home = resolver.school(contest.home)
        contest.away = resolver.school(contest.away)
        if contest.box:
            for side, school in ((contest.box.home, contest.home),
                                 (contest.box.away, contest.away)):
                for s in side:
                    s.competitor = _recompetitor(s.competitor, school)


def _recompetitor(c, school: str):
    from app.shapes import Competitor

    return c if c.school == school else Competitor(name=c.name, school=school, year=c.year)
