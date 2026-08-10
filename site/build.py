"""
Static reference-site build: JHSAA records -> a cross-linked page tree.

Page types: front · scoreboard · sport landings · meet/game/dual contest pages
· school pages · conference mini-fronts · athlete pages. Every page carries the
persistent score rail. The build fails on a broken internal link.

Pages are rendered one at a time and written as they go, never all held at
once — see `page_routes`. The link check runs on the hrefs harvested during
that pass, against the route table rather than against retained page text.

    python3 site/build.py        # writes dist/site/ (+ dist/index.html preview)
    FH_ONLY=front,tour ...       # only those page kinds; partial, not for deploy
"""

from __future__ import annotations

import base64
import hashlib
import json
import html
import multiprocessing
import os
import pathlib
import re
import shutil
import sys
import zlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import postseason, records_io  # noqa: E402
from app.shapes import Dual, Game, Meet, TournamentFormat, TournamentStatus  # noqa: E402
from app.brand import ASSOC, NAME, TITLE, WORDMARK, page_title  # noqa: E402
from app.sports import BY_KEY, CATALOG, CLASSES, meet_scoring  # noqa: E402

import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("fh_news", ROOT / "site/news.py")
news = _ilu.module_from_spec(_spec); _spec.loader.exec_module(news)
_ispec = _ilu.spec_from_file_location("fh_icons", ROOT / "site/icons.py")
icons = _ilu.module_from_spec(_ispec); _ispec.loader.exec_module(icons)
_pspec = _ilu.spec_from_file_location("fh_sponsors", ROOT / "site/sponsors.py")
sponsors = _ilu.module_from_spec(_pspec); _pspec.loader.exec_module(sponsors)
_mspec = _ilu.spec_from_file_location("fh_marks", ROOT / "site/marks.py")
marks = _ilu.module_from_spec(_mspec); _mspec.loader.exec_module(marks)
_sspec = _ilu.spec_from_file_location("fh_stdsite", ROOT / "site/standardsite.py")
stdsite = _ilu.module_from_spec(_sspec); _sspec.loader.exec_module(stdsite)

RECORDS = ROOT / "records"
OUT = ROOT / "dist/site"
FAVICON = "/favicon.svg"   # replaced in build() if site/favicon.* exists
TODAY = "2027-05-13"          # the demo date the generator built around
SEASON_ID = "2026-27"
SEASON_LABEL = "2026–27"

#: The network's real Bluesky account. The site never fakes a feed: pages
#: render a follow card, and a small script swaps in the live posts from the
#: PUBLIC AppView API (no key, CORS-open) when the reader's browser can reach
#: it. Empty account, failed fetch, JS off — all leave the honest card.
BSKY_HANDLE = "varsityapex.com"
BSKY_URL = f"https://bsky.app/profile/{BSKY_HANDLE}"
BSKY_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
CREST_CLASSES = 12
CLASS_LABEL = {"9": "Fr", "10": "So", "11": "Jr", "12": "Sr"}
SEASON_ORDER = {"fall": 0, "winter": 1, "spring": 2}

# utility-layer staff names, picked by name hash so they never reshuffle
ATHLETIC_FIRST = ["Dana", "Marcus", "Elena", "Troy", "Renee", "Victor", "Gail",
                  "Howard", "Priya", "Sam", "Teresa", "Doug", "Alma", "Chris"]
ATHLETIC_LAST = ["Okafor", "Whitmore", "Salinas", "Beckett", "Rowe", "Iwata",
                 "Padgett", "McCray", "Voss", "Lantz", "Herrera", "Quist"]


def esc(t): return html.escape(re.sub(r"\s{2,}", " ", (t or "")).strip(), quote=True)
def slugify(t): return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-") or "x"


def contest_key(c):
    """Must agree with generators.jefferson.postseason.contest_key — it is the
    join between a matchup and the page its result lives on."""
    return f"{c.sport}:{c.date}:{c.name}"


def crest_class(name):
    return f"c{int(hashlib.md5(name.encode()).hexdigest(), 16) % CREST_CLASSES}"


def monogram(name):
    words = [w for w in name.split() if w[0].isalpha()]
    return (words[0][0] + words[1][0]).upper() if len(words) > 1 else words[0][:2].upper()


def class_chip(cls):
    if not cls:
        return ""
    return f"<span class='fh-badge c{esc(cls.split('-')[0])}'>{esc(cls)}</span>"


def nice_date(iso):
    if not iso:
        return ""
    import datetime as dt
    d = dt.date.fromisoformat(iso)
    return d.strftime("%a %b %-d")


# ─────────────────────────────────────────────────────────────────── registry


class Registry:
    def __init__(self):
        schools, confs = records_io.load_orgs(RECORDS)
        self.schools = {s["name"]: {**s, "slug": slugify(s["name"])} for s in schools}
        self.confs = {c["slug"]: c for c in confs}
        self.conf_of = {s["name"]: s["conference"] for s in schools}
        self.conf_slug = {c["name"]: c["slug"] for c in confs}

        self.contests = records_io.load_contests(RECORDS)
        self.by_sport: dict[str, list] = defaultdict(list)
        self.by_school: dict[str, list] = defaultdict(list)
        self.contest_url: dict[int, str] = {}
        self.athletes: dict[tuple[str, str], dict] = {}
        used: dict[str, int] = {}

        for c in self.contests:
            kind = "meets" if isinstance(c, Meet) else "duals" if isinstance(c, Dual) else "games"
            base = f"{c.date}-{slugify(c.name)[:70]}"
            n = used.get(base, 0)
            used[base] = n + 1
            slug = base if not n else f"{base}-{n+1}"
            self.contest_url[id(c)] = f"/{kind}/{slug}/"
            self.by_sport[c.sport].append(c)
            for s in self.contest_schools(c):
                if s in self.schools:
                    self.by_school[s].append(c)
            self.index_athletes(c)

        aused: dict[str, int] = {}
        for a in self.athletes.values():
            n = aused.get(a["slug"], 0)
            aused[a["slug"]] = n + 1
            if n:
                a["slug"] = f"{a['slug']}-{n+1}"

        # ---- the editorial layer: honors, milestones, announcements.
        #      Indexed three ways because the same item is a school headline,
        #      a league honor roll entry and a statewide award — one record,
        #      three tenants, which is the whole point of the scope field.
        self.items: list[dict] = []
        ed = RECORDS / "editorial" / SEASON_ID / "items.json"
        if ed.exists():
            self.items = json.loads(ed.read_text())
        self.items_by_school: dict[str, list] = defaultdict(list)
        self.items_by_conf: dict[str, list] = defaultdict(list)
        self.items_state: list[dict] = []
        for it in self.items:
            if it["scope"] == "state":
                self.items_state.append(it)
            elif it["scope"] == "conference":
                if it["conference"]:
                    self.items_by_conf[it["conference"]].append(it)
            elif it["school"]:
                self.items_by_school[it["school"]].append(it)
        # A conference's own page shows its schools' honors too — that is what
        # makes it the shared newsroom rather than a standings table.
        for it in self.items:
            if it["scope"] == "school" and it.get("conference"):
                self.items_by_conf[it["conference"]].append(it)
        for lst in list(self.items_by_conf.values()) + list(self.items_by_school.values()):
            lst.sort(key=lambda d: d["date"], reverse=True)

        # ---- the postseason layer
        self.by_key = {contest_key(c): c for c in self.contests}
        self.tournaments = records_io.load_tournaments(RECORDS)
        self.tour_url: dict[str, str] = {}
        self.tour_by_sport: dict[str, list] = defaultdict(list)
        self.tour_of_contest: dict[str, tuple] = {}
        self.titles: dict[str, list] = defaultdict(list)
        for t in self.tournaments:
            self.tour_url[t.id] = f"/championships/{t.sport}/{slugify(t.group)}/"
            self.tour_by_sport[t.sport].append(t)
            for r in t.rounds:
                for m in r.matchups:
                    if m.contest_key:
                        self.tour_of_contest[m.contest_key] = (t, r, m)
            if t.meet_key:
                self.tour_of_contest[t.meet_key] = (t, None, None)
            if t.champion:
                self.titles[t.champion].append(t)
        for lst in self.tour_by_sport.values():
            lst.sort(key=lambda t: postseason._group_order(t.group))

    def tournament_for(self, contest):
        """The championship a contest belongs to, if any."""
        return self.tour_of_contest.get(contest_key(contest))

    def contest_for(self, key):
        return self.by_key.get(key or "")

    def contest_href(self, key):
        c = self.by_key.get(key or "")
        return self.contest_url.get(id(c)) if c is not None else None

    def contest_schools(self, c):
        if isinstance(c, Meet):
            return c.schools
        return [c.home, c.away]

    def index_athletes(self, c):
        def add(comp, row):
            if comp.school not in self.schools:
                return
            key = (comp.name, comp.school)
            a = self.athletes.setdefault(key, {
                "name": comp.name, "school": comp.school,
                "slug": f"{slugify(comp.name)}-{slugify(comp.school)[:24]}",
                "year": comp.year, "rows": []})
            if comp.year:
                a["year"] = comp.year
            a["rows"].append(row)

        if isinstance(c, Meet):
            for ev in c.events:
                for e in ev.entries:
                    for comp in e.competitors:
                        add(comp, (c, ev, e))
        elif isinstance(c, Dual):
            for line in c.lines:
                for comp in line.home + line.away:
                    add(comp, (c, line, None))

    # links
    def url(self, c):
        return self.contest_url[id(c)]

    def school_url(self, name):
        s = self.schools.get(name)
        return f"/schools/{s['slug']}/" if s else ""

    def school_link(self, name):
        u = self.school_url(name)
        return f"<a href='{u}'>{esc(name)}</a>" if u else esc(name)

    def athlete_link(self, name, school):
        a = self.athletes.get((name, school))
        return f"<a href='/athletes/{a['slug']}/'>{esc(name)}</a>" if a else esc(name)

    def crest(self, name, size="sm"):
        """The school's athletic mark: monogram on its own colors. Colors are
        identity, not theme — they stay fixed across schemes, the way a real
        mark does. Hash classes remain the fallback for schools with no
        branding record (out-of-state opponents never get here)."""
        if name not in self.schools:
            return ""
        colors = self.schools[name].get("colors")
        if colors:
            return (f"<span class='fh-crest {size}' style='background:{colors[0]}'>"
                    f"{esc(monogram(name))}</span>")
        return f"<span class='fh-crest {size} {crest_class(name)}'>{esc(monogram(name))}</span>"

    def mark(self, name, size=72):
        if name not in self.schools:
            return ""
        return marks.school_mark(self.schools[name], size)

    def records_for(self, sport_key):
        """Derived W-L(-T) per school for a GAME/DUAL sport."""
        rec: dict[str, dict] = defaultdict(lambda: dict(w=0, l=0, t=0, cw=0, cl=0))
        for c in self.by_sport.get(sport_key, []):
            if isinstance(c, Meet):
                continue
            if isinstance(c, Game):
                if c.status != "final" or c.home_score is None:
                    continue
                pairs = [(c.home, c.home_score, c.away), (c.away, c.away_score, c.home)]
                if c.home_score == c.away_score:
                    for s, _, _ in pairs:
                        if s in self.schools:
                            rec[s]["t"] += 1
                    continue
            else:
                if c.home_points is None:
                    continue
                pairs = [(c.home, c.home_points, c.away), (c.away, c.away_points, c.home)]
            winner = max(pairs[:2], key=lambda p: p[1])[0]
            for s, _, opp in pairs:
                if s not in self.schools:
                    continue
                won = s == winner
                rec[s]["w" if won else "l"] += 1
                if self.conf_of.get(s) and self.conf_of.get(s) == self.conf_of.get(opp):
                    rec[s]["cw" if won else "cl"] += 1
        return rec


# ────────────────────────────────────────────────────────────────── facets
#
# The faceted-filter schema, borrowed from dense-information SaaS: a sticky
# segmented control over a large list, live result counts, multi-facet AND
# semantics, deep-linkable state, and an escape hatch back to "All".
#
#   Linear / GitHub / Airtable   segmented controls, live counts, URL state
#   Datadog / Retool             multi-facet AND across independent dimensions
#   ESPN / OSAA standings        classification as the primary cut
#
# Contract, so any page opts in without new JS:
#   1. Wrap the list in  <div class="fh-filterable" id="X">
#   2. Give each filterable child  data-f-<facet>="value"  (space-separated when
#      multi-valued, e.g. an invitational spanning several classifications)
#   3. Render  facet_bar("X", [(facet, label, [(value, display), ...]), ...])


def facet_bar(target, groups, note="", exclusive=False):
    """`exclusive` drops the All chip and pre-selects the first value — for
    products like rankings where "every classification at once" is not a view,
    it's the failure mode. Scripting-off still shows everything, which is the
    right degradation."""
    out = []
    for key, label, values in groups:
        chips = "".join(
            f"<button type='button' data-facet='{esc(key)}' data-value='{esc(v)}'"
            f"{' class=on' if exclusive and i == 0 else ''}>{disp}</button>"
            for i, (v, disp) in enumerate(values))
        allchip = ("" if exclusive else
                   f"<button type='button' data-facet='{esc(key)}' data-value='' class='on'>All</button>")
        out.append(
            f"<div class='fh-facet'><span class='lb'>{esc(label)}</span>"
            f"<div class='chips'>{allchip}{chips}</div></div>")
    tail = f"<span class='fh-facetnote'>{esc(note)}</span>" if note else ""
    return (f"<div class='fh-facets' data-target='{esc(target)}'>{''.join(out)}"
            f"<span class='fh-facetcount' data-count-for='{esc(target)}'></span>{tail}</div>")


FACET_JS = """
(function () {
  document.querySelectorAll(".fh-facets").forEach(function (bar) {
    var target = document.getElementById(bar.dataset.target);
    if (!target) return;
    function faceted(nodes) {
      return [].slice.call(nodes).filter(function (n) {
        return [].some.call(n.attributes, function (a) { return a.name.indexOf("data-f-") === 0; });
      });
    }
    var groups = [].slice.call(target.children).filter(function (n) {
      return n.classList.contains("fh-day") || n.classList.contains("fh-areablock");
    });
    var items = faceted(target.children);
    if (groups.length) {
      items = [];
      groups.forEach(function (g) { items = items.concat(faceted(g.children)); });
    }
    var counter = document.querySelector('[data-count-for="' + bar.dataset.target + '"]');
    var state = {};
    bar.querySelectorAll("button[data-facet].on").forEach(function (b) {
      if (b.dataset.value) state[b.dataset.facet] = b.dataset.value;
    });
    function apply() {
      var shown = 0;
      items.forEach(function (el) {
        var ok = Object.keys(state).every(function (k) {
          if (!state[k]) return true;
          var v = el.getAttribute("data-f-" + k) || "";
          return (" " + v + " ").indexOf(" " + state[k] + " ") !== -1;
        });
        el.hidden = !ok;
        if (ok) shown++;
      });
      groups.forEach(function (g) {
        g.hidden = faceted(g.children).every(function (n) { return n.hidden; });
      });
      if (counter) counter.textContent = shown === items.length ? "" : shown + " shown";
      var active = Object.keys(state).filter(function (k) { return state[k]; })
        .map(function (k) { return k + ":" + state[k]; }).join(",");
      history.replaceState(null, "", active ? "#" + active : location.pathname);
    }
    bar.querySelectorAll("button[data-facet]").forEach(function (b) {
      b.addEventListener("click", function () {
        state[b.dataset.facet] = b.dataset.value;
        bar.querySelectorAll('button[data-facet="' + b.dataset.facet + '"]')
          .forEach(function (o) { o.classList.toggle("on", o === b); });
        apply();
      });
    });
    if (location.hash.length > 1) {
      location.hash.slice(1).split(",").forEach(function (pair) {
        var kv = pair.split(":");
        if (kv.length !== 2) return;
        var b = bar.querySelector('button[data-facet="' + kv[0] + '"][data-value="' + kv[1] + '"]');
        if (b) b.click();
      });
    }
    apply();
  });
})();
"""


# ─────────────────────────────────────────────────────────────── shell + rail


def result_label(c):
    if isinstance(c, Meet):
        return "Results" if c.events else ""
    if isinstance(c, Game):
        if c.status == "final":
            return f"{c.home_score}–{c.away_score}"
        return {"cancelled": "CANC", "postponed": "PPD"}.get(c.status, "")
    if c.home_points is not None:
        return f"{c.home_points:g}–{c.away_points:g}"
    return ""


def build_rail(reg: Registry) -> str:
    import datetime as dt
    t = dt.date.fromisoformat(TODAY)
    lo, hi = (t - dt.timedelta(days=4)).isoformat(), (t + dt.timedelta(days=4)).isoformat()
    window = [c for c in reg.contests if c.date and lo <= c.date <= hi]
    # diverse: round-robin across sports, finals first
    by_sport = defaultdict(list)
    for c in sorted(window, key=lambda c: (c.date or "")):
        by_sport[c.sport].append(c)
    cells, i = [], 0
    while len(cells) < 36 and any(by_sport.values()):
        for k in sorted(by_sport):
            if by_sport[k]:
                cells.append(by_sport[k].pop(0))
        i += 1
        if i > 40:
            break
    cells.sort(key=lambda c: (c.date or "", c.sport))
    out = []
    for c in cells[:36]:
        sport = BY_KEY[c.sport].name if c.sport in BY_KEY else c.sport
        if isinstance(c, Meet):
            status = "FT" if c.events else nice_date(c.date)
            rows = (f"<span class='rr'><span class='nm'>{esc(c.name[:26])}</span></span>"
                    f"<span class='rr'><span class='nm sub'>{esc((c.host or '')[:24])}</span></span>")
        else:
            fin = isinstance(c, Game) and c.status == "final" or \
                  isinstance(c, Dual) and c.home_points is not None
            status = "FT" if fin else {"cancelled": "CANC", "postponed": "PPD"}.get(
                getattr(c, "status", ""), nice_date(c.date))
            hs = as_ = ""
            if isinstance(c, Game) and c.status == "final":
                hs, as_ = c.home_score, c.away_score
            elif isinstance(c, Dual) and c.home_points is not None:
                hs, as_ = f"{c.home_points:g}", f"{c.away_points:g}"
            rows = (f"<span class='rr'>{reg.crest(c.away, 'xs')}<span class='nm'>{esc(c.away)}</span><b>{as_}</b></span>"
                    f"<span class='rr'>{reg.crest(c.home, 'xs')}<span class='nm'>{esc(c.home)}</span><b>{hs}</b></span>")
        out.append(f"<a class='fh-railcell' href='{reg.url(c)}'>"
                   f"<span class='rh'><span>{esc(nice_date(c.date))}</span><span>{esc(status)}</span></span>"
                   f"{rows}<span class='rs'>{esc(sport)}</span></a>")
    return ("<div class='fh-rail'><div class='fh-railtrack'>" + "".join(out) +
            "<a class='fh-railcell more' href='/scoreboard/'><span class='rh'><span>Scoreboard</span></span>"
            "<span class='rr'><span class='nm'>All of this week →</span></span></a></div></div>")


RAIL = ""        # populated in build()
SPORT_MENU = ""   # nav dropdowns, populated in build()
RES_MENU = ""
DRAWER_SPORTS = ""  # mobile drawer, same material as the dropdowns
DRAWER_RES = ""


def _base_name(sp):
    """A sport's name with the gender off — "Boys Basketball" -> "Basketball"."""
    for p in ("Boys ", "Girls "):
        if sp.name.startswith(p):
            return sp.name[len(p):]
    return sp.name


def collapse_pairs(keys, season=None):
    """`keys` as [(label, key)], same-season gendered PAIRS COLLAPSED.

    Only collapses where BOTH halves are in the set handed in. The set is
    scoped by tier — the state front has every activity, a school has the ones
    it sponsors — and a school that fields girls lacrosse and not boys has to
    go on saying "Girls Lacrosse", because for that school it is not half of
    anything.
    """
    sports = [BY_KEY[k] for k in dict.fromkeys(keys) if k in BY_KEY]
    if season:
        sports = [s for s in sports if s.season == season]
    by = defaultdict(list)
    for sp in sports:
        by[(sp.season, _base_name(sp))].append(sp)
    out = []
    for (_, base), group in by.items():
        lead = min(group, key=lambda s: s.name)
        out.append((base if len(group) > 1 else lead.name, lead.key))
    return sorted(out)


def season_menu(reg, season):
    """One season's activities, as (label, href) — gendered PAIRS COLLAPSED.

    Fifty activities listed one gender at a time is a nav that cannot be
    scanned and, at nineteen rows in a column, could not even be displayed:
    the panel capped its own height and quietly hid the bottom of every
    column behind a hover-scroll.

    So where BOTH genders of a sport run in the SAME season — basketball,
    wrestling, swimming, the two skiings, fencing, hockey, soccer, cross
    country, water polo, lacrosse, track — the menu carries the sport ONCE,
    under its plain name, and the boys/girls split happens on the page
    (`gender_switch`). Where they run in DIFFERENT seasons they are genuinely
    different entries in the calendar and stay separate: girls tennis is a
    fall sport and boys tennis a spring one, and collapsing those would say
    something untrue about when they are played.
    """
    return collapse_pairs([sp.key for sp in CATALOG if reg.by_sport.get(sp.key)],
                          season)


def gendered_pair(reg, sp):
    """The other gender of `sp`, if it runs in the same season. Else None."""
    if not sp.name.startswith(("Boys ", "Girls ")):
        return None
    base = _base_name(sp)
    return next((o for o in CATALOG
                 if o.key != sp.key and o.season == sp.season
                 and _base_name(o) == base and reg.by_sport.get(o.key)), None)


def build_menus(reg):
    """Nav dropdowns: sports by season, resources by audience."""
    global SPORT_MENU, RES_MENU, DRAWER_SPORTS, DRAWER_RES
    cols = []
    for season in ("fall", "winter", "spring"):
        links = "".join(
            f"<a href='/sports/{key}/'>{icons.icon(key, 'fh-ic sm')}{esc(label)}</a>"
            for label, key in season_menu(reg, season))
        cols.append(f"<div><h4>{season.title()}</h4>{links}</div>")
    SPORT_MENU = f"<div class='fh-dropcols'>{''.join(cols)}</div>"
    rcols = []
    for title, links in news.RESOURCES:
        items = "".join(
            (f"<a href='{href}'>{esc(label)}</a>" if href else f"<span>{esc(label)}</span>")
            for label, href in links)
        rcols.append(f"<div><h4>{esc(title)}</h4>{items}</div>")
    RES_MENU = f"<div class='fh-dropcols'>{''.join(rcols)}</div>"

    # the drawer carries the same material, as open sections rather than hovers
    dsec = []
    for season in ("fall", "winter", "spring"):
        links = "".join(
            f"<a href='/sports/{key}/'>{icons.icon(key, 'fh-ic sm')}{esc(label)}</a>"
            for label, key in season_menu(reg, season))
        dsec.append(f"<details><summary>{season.title()} sports</summary>"
                    f"<div class='items'>{links}</div></details>")
    DRAWER_SPORTS = "".join(dsec)
    rsec = []
    for title, links in news.RESOURCES:
        items = "".join(
            (f"<a href='{href}'>{esc(label)}</a>" if href else f"<span>{esc(label)}</span>")
            for label, href in links)
        rsec.append(f"<details><summary>{esc(title)}</summary>"
                    f"<div class='items'>{items}</div></details>")
    DRAWER_RES = "".join(rsec)


def sponsor_rail() -> str:
    """Sponsor wordmarks, set in the site's faces. No hrefs — these are
    fictional businesses, and a dead link in a footer is worse than none."""
    return "".join(
        f"<span class='fh-logo lm-{s['style']}'>{esc(s['name'])}</span>"
        for s in sponsors.SPONSORS)


#: Where this build will be served. Social cards need ABSOLUTE urls — a
#: relative og:image resolves to nothing when the link is pasted into Bluesky,
#: Slack or iMessage, which is the entire point of having one. Override for a
#: preview deployment with FH_SITE_URL.
SITE_URL = os.environ.get("FH_SITE_URL", "https://varsityapex.com").rstrip("/")

#: The default share image. An athletics site's card image is its photography
#: — the platform draws the headline and description beside it, so the picture
#: does not need to carry text. Drop site/img/og.jpg to override, the same way
#: a favicon is overridden.
OG_FALLBACK = "/img/sports/gym-generic.jpg"

#: Replaced per page at write time in build(), which is the only place that
#: knows a page's url. Threading a url through twenty-one shell() call sites
#: to say the same thing would be twenty-one chances to say it wrong.
OG_URL_TOKEN = "__FH_PAGE_URL__"


def og_image() -> str:
    return "/img/og.jpg" if (ROOT / "site/img/og.jpg").exists() else OG_FALLBACK


_OG_DIMS: dict[str, tuple[int, int] | None] = {}


def image_size(path: str) -> tuple[int, int] | None:
    """(w, h) read out of the JPEG's own SOF marker.

    og:image:width/height let a platform reserve the right box before the
    image arrives, so a hard-coded 1200x630 over a 1024x593 photo is a lie
    that shows up as a jumping card. Cheap enough to measure: the header is
    the first few hundred bytes.
    """
    if path in _OG_DIMS:
        return _OG_DIMS[path]
    # the drop folder is served flat at /img/additions/ but lives one level
    # deeper in the tree, so the naive join misses every photograph in it and
    # the card it feeds ships without a box to reserve
    f = (ADDITIONS / path.split("/img/additions/")[-1]
         if path.startswith("/img/additions/")
         else ROOT / "site" / path.lstrip("/"))
    dims = None
    try:
        d = f.read_bytes()
        i = 2
        while i < len(d) - 9 and dims is None:
            if d[i] != 0xFF:
                i += 1
                continue
            m = d[i + 1]
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                dims = (int.from_bytes(d[i + 7:i + 9], "big"),
                        int.from_bytes(d[i + 5:i + 7], "big"))
            elif m == 0xD8 or 0xD0 <= m <= 0xD7:
                i += 2
                continue
            else:
                i += 2 + int.from_bytes(d[i + 2:i + 4], "big")
                continue
            break
    except (OSError, IndexError, ValueError):
        dims = None
    _OG_DIMS[path] = dims
    return dims


def social_head(title, desc, image, kind, published=None) -> str:
    """Meta description, Open Graph and Twitter card.

    One block feeds all three surfaces: search results read `description`,
    Bluesky/Slack/Discord/LinkedIn read Open Graph, Twitter reads its own
    names and falls back to OG for the rest. `summary_large_image` is the
    card a result or a bracket deserves — the small square variant crops a
    team photo into abstraction.
    """
    url = SITE_URL + OG_URL_TOKEN
    rel = image or og_image()
    img = image if str(image).startswith("http") else SITE_URL + rel
    dims = image_size(rel)
    tags = [
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:site_name" content="{esc(NAME)}">',
        f'<meta property="og:type" content="{kind}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{img}">',
        *([f'<meta property="og:image:width" content="{dims[0]}">',
           f'<meta property="og:image:height" content="{dims[1]}">'] if dims else []),
        f'<meta property="og:image:alt" content="{esc(title)}">',
        '<meta property="og:locale" content="en_US">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{img}">',
    ]
    if published:
        tags.append(f'<meta property="article:published_time" content="{esc(published)}">')
    return "\n".join(tags)


#: What the site is, for any page that does not say something better.
SITE_DESC = ("Official results, schedules, standings and championships for the "
             "Jefferson High School Activities Association — 840 member schools, "
             "45 sanctioned activities, published as open records.")


#: The colour schemes, in picker order: (key, name, what it is made of).
#: `varsity` is the default and carries no data-theme attribute.
SCHEMES = [
    ("default",   "Ensign",    "Deep twilight · cobalt · white · red"),
    ("banner",    "Banner",    "Indigo · ocean blue · flag red · amber"),
    ("apex",      "Apex",      "Prussian · steel blue · amber · flag red"),
    ("rally",     "Rally",     "Blue bell · aqua · lemon · racing red"),
    ("meadow",    "Meadow",    "Mint · teal · sunflower"),
    ("evergreen", "Evergreen", "Deep green · orange"),
    ("harbor",    "Harbor",    "Dark teal · peach · red"),
    ("citrus",    "Citrus",    "Aqua · beige · pumpkin"),
    ("pitch",     "Pitch",     "Mint · sea green · amber · black"),
]


def theme_menu(drawer=False) -> str:
    """The scheme picker, NAMED.

    It was seven unlabelled 20px squares in a row, which failed twice over:
    nobody could tell which square was which palette, and the whole row lived
    in `.fh-mast-nav`, which is `display:none` below 860px — so on a phone
    there was no way to reach any scheme at all, and on a school or conference
    page (whose compact masthead never carried the row) there was none at any
    width. A named menu in the site's own dropdown grammar fixes all three.
    """
    rows = "".join(
        f"<button type='button' class='fh-themerow' data-theme-choice='{k}' "
        f"aria-pressed='{'true' if k == 'default' else 'false'}'>"
        f"<span class='fh-swatch' data-theme-choice='{k}' aria-hidden='true'></span>"
        f"<span class='tn'>{esc(name)}</span><span class='td'>{esc(desc)}</span>"
        f"</button>" for k, name, desc in SCHEMES)
    if drawer:
        return (f"<details class='fh-themedrawer'><summary>Appearance</summary>"
                f"<div class='items fh-themelist'>{rows}</div></details>")
    return (f"<div class='fh-menu fh-thememenu'>"
            f"<button type='button' aria-label='Colour scheme'>Theme ▾</button>"
            f"<div class='fh-drop fh-themelist'>{rows}</div></div>")


def shell(title, body, crumb="", back="", story=None, org=False,
          desc=None, image=None, kind="website", published=None):
    pill = ""
    if back:
        label, url = back.split("|")
        pill = f"<a class='fh-pill' href='{url}'>{esc(label)}</a>"
    toolbar = f"<div class='fh-toolbar'><span class='fh-crumb'>{crumb}</span>{pill}</div>" if crumb else ""
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="only light">
<title>{esc(title)}</title>
{social_head(title, desc or SITE_DESC, image, kind, published)}
<link rel="stylesheet" href="/style.css">
{favicon_tag()}{stdsite.head_links(story)}
<script defer src="/_vercel/insights/script.js"></script>
<script>try{{var t=localStorage.getItem('fh-theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
{icons.sprite()}
<input type="checkbox" id="fh-navtoggle" class="fh-navtoggle" hidden>
<!--M--><header class="fh-mast"><div class="wrap">
  <a class="fh-wordmark" href="/">{WORDMARK}</a>
  <label class="fh-burger" for="fh-navtoggle" aria-label="Menu">
    <span></span><span></span><span></span>
  </label>
  <nav class="fh-mast-nav">
    <a href="/scoreboard/">Scores</a>
    <div class="fh-menu"><button type="button">Sports &amp; Activities ▾</button><div class="fh-drop">{SPORT_MENU}</div></div>
    <div class="fh-menu"><button type="button">Schools ▾</button><div class="fh-drop cols">
      <a href="/schools/">All member schools</a><a href="/conferences/">Conferences</a>
      {''.join(f"<a href='/schools/#{c}'>{c}</a>" for c in CLASSES)}</div></div>
    <a href="/championships/">Championships</a>
    <a href="/news/">News</a>
    <a href="/tour/">Tour</a>
    <div class="fh-menu"><button type="button">Resources ▾</button><div class="fh-drop">{RES_MENU}</div></div>
    <span class="fh-season">{ASSOC} · {SEASON_LABEL}</span>
    {theme_menu()}
    <a class="fh-socialink" href="{BSKY_URL}" target="_blank" rel="noopener"
       aria-label="VarsityApex on Bluesky">{icons.bsky()}</a>
  </nav>
</div></header><!--/M-->
<label class="fh-scrim" for="fh-navtoggle" aria-hidden="true"></label>
<nav class="fh-drawer" aria-label="Site menu">
  <div class="fh-drawerhead">
    <span class="fh-wordmark">{WORDMARK}</span>
    <label class="fh-drawerclose" for="fh-navtoggle" aria-label="Close menu">×</label>
  </div>
  <a class="top" href="/scoreboard/">Scores</a>
  <a class="top" href="/championships/">Championships</a>
  <a class="top" href="/news/">News</a>
  <a class="top" href="/schools/">Schools</a>
  <a class="top" href="/conferences/">Conferences</a>
  <a class="top" href="/tour/">Tour</a>
  {DRAWER_SPORTS}
  {DRAWER_RES}
  {theme_menu(drawer=True)}
  <a class="top" href="{BSKY_URL}" target="_blank" rel="noopener">
    {icons.bsky()} @{BSKY_HANDLE}</a>
</nav>
{RAIL}
<main class="wrap">
{toolbar}
{body}
</main>
<script>{FACET_JS}{CONF_PICKER_JS}</script>
<script>
(function () {{
  // The row is the control now; the swatch inside it is decoration. There
  // are two of these on a page (masthead menu + mobile drawer), so both get
  // their pressed state updated from one apply().
  var rows = document.querySelectorAll(".fh-themerow");
  function apply(name) {{
    if (name === "default") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", name);
    rows.forEach(function (c) {{
      c.setAttribute("aria-pressed", c.getAttribute("data-theme-choice") === name ? "true" : "false");
    }});
    try {{ localStorage.setItem("fh-theme", name === "default" ? "" : name); }} catch (e) {{}}
  }}
  rows.forEach(function (c) {{
    c.addEventListener("click", function () {{ apply(c.getAttribute("data-theme-choice")); }});
  }});
  var t = null;
  try {{ t = localStorage.getItem("fh-theme"); }} catch (e) {{}}
  // "ensign" was an alternate before it became the site default; "varsity"
  // and "bloom" are retired names. All three resolve to the default now.
  if (t === "ensign" || t === "varsity" || t === "bloom") t = "";
  if (t) apply(t);
}})();
</script>
<footer class="fh-foot"><div class="wrap">
  <div class="fh-sponsors">{sponsor_rail()}</div>
  <div class="fh-footrow"><span class="fh-footmark">{WORDMARK}</span>
    <span class="fh-foottag">The official site of the {ASSOC}</span>
    <span class="fh-social"><a href="{BSKY_URL}" target="_blank" rel="noopener">
      {icons.bsky()} @{BSKY_HANDLE}</a></span></div>
</div></footer>
</body>
</html>
"""
    if org:
        # Network utility bar: on a school or conference page the local
        # organization owns the masthead. VarsityApex explains the connected
        # network; it doesn't visually own the page.
        compact = f"""<header class="fh-mast compact"><div class="wrap">
  <a class="fh-wordmark" href="/">{WORDMARK}</a>
  <label class="fh-burger" for="fh-navtoggle" aria-label="Menu">
    <span></span><span></span><span></span>
  </label>
  <nav class="fh-mast-nav">
    <a class="fh-backassoc" href="/">← {ASSOC}</a>
    <a href="/scoreboard/">Scores</a>
    <a href="/schools/">Schools</a>
    <a href="/conferences/">Conferences</a>
    <a href="/championships/">Championships</a>
    <a href="/news/">News</a>
    {theme_menu()}
    <a class="fh-socialink" href="{BSKY_URL}" target="_blank" rel="noopener"
       aria-label="VarsityApex on Bluesky">{icons.bsky()}</a>
  </nav>
</div></header>"""
        import re as _re
        page = _re.sub(r"<!--M-->.*?<!--/M-->", compact.replace("\\", "\\\\"), page, flags=_re.S)
    return page.replace("<!--M-->", "").replace("<!--/M-->", "")


# ─────────────────────────────────────────────────────────── contest pieces


def score_row(href, who, when):
    """A linked result row whose text carries its own links. An <a> cannot nest
    an <a> — the parser closes the outer one and the row shatters — so the row
    is a div with a stretched overlay link, inner links above it."""
    return (f"<div class='fh-scorerow'><a class='m' href='{href}'></a>"
            f"<span class='who'>{who}</span><span class='when'>{when}</span></div>")


def score_line(reg, c):
    """A result a reader can use: winner first, both schools, both scores.
    "Netherwood 3, Larch Ridge Union 1" — never a bare winner's name."""
    if isinstance(c, Game):
        if c.status != "final" or c.home_score is None:
            return ""
        pairs = [(c.home, c.home_score), (c.away, c.away_score)]
    else:
        if c.home_points is None:
            return ""
        pairs = [(c.home, f"{c.home_points:g}"), (c.away, f"{c.away_points:g}")]
    pairs.sort(key=lambda p: -float(p[1]))

    def n(v):
        return f"<b class='tnum{' frac' if '.' in str(v) else ''}'>{v}</b>"

    return (f"{reg.school_link(pairs[0][0])} {n(pairs[0][1])}, "
            f"{reg.school_link(pairs[1][0])} {n(pairs[1][1])}")


def meet_line(reg, c):
    """The useful result for a meet-shaped activity, in its own terms."""
    if not getattr(c, "events", None):
        return ""
    top = next((t for t in c.team_scores if t.rank == 1), None)
    if top:
        return f"{esc(c.name)} — won by {reg.school_link(top.school)}"
    return esc(c.name)


def share_desc(reg, c) -> str:
    """What a pasted link should say about a contest, in plain text.

    A share card is read as a sentence, not parsed as markup, so this is the
    one description that cannot reuse `score_line` — the anchors and <b> would
    ship verbatim into the Bluesky card. Says the result when there is one and
    the fixture when there is not, because "Norview at Ashbrook, Friday" is a
    useful card and "Norview at Ashbrook" alone is not.
    """
    sp = BY_KEY[c.sport].name
    when = nice_date(c.date) if c.date else ""
    if isinstance(c, Meet):
        top = next((t for t in c.team_scores if t.rank == 1), None)
        where = f" at {c.host}" if c.host else ""
        if top:
            unit = meet_scoring(c.sport)[2].lower()
            return (f"{top.school} won the {c.name} with {top.points:g} {unit} — "
                    f"{len(c.events)} events, {len(c.schools)} schools. {sp}, {when}.")
        return f"{c.name}{where} — {sp}, {when}. Entries and results as they post."
    scored = (isinstance(c, Game) and c.status == "final" and c.home_score is not None) \
        or (isinstance(c, Dual) and c.home_points is not None)
    if scored:
        if isinstance(c, Game):
            pairs = [(c.home, c.home_score), (c.away, c.away_score)]
        else:
            pairs = [(c.home, f"{c.home_points:g}"), (c.away, f"{c.away_points:g}")]
        pairs.sort(key=lambda p: -float(p[1]))
        tail = ""
        ctx = reg.tournament_for(c)
        if ctx:
            t, r, _m = ctx
            tail = f" {t.group} {sp} {(r.name if r else 'championship').lower()}."
        elif getattr(c, "box", None):
            tail = " Full box score and scoring by period."
        if getattr(c, "result", None):
            return f"{c.result} — {sp}, {when}.{tail}"
        return (f"Final: {pairs[0][0]} {pairs[0][1]}, {pairs[1][0]} {pairs[1][1]} "
                f"— {sp}, {when}.{tail}")
    return f"{c.away} at {c.home} — {sp}, {when}. Result posts when the contest is final."


def matchup_line(reg, c, with_date=True):
    when = f" · {esc(nice_date(c.date))}" if with_date else ""
    if isinstance(c, Meet):
        host = f" at {esc(c.host)}" if c.host else ""
        return f"{esc(c.name)}{host}{when}"
    return f"{reg.school_link(c.away)} at {reg.school_link(c.home)}{when}"


def contest_facets(reg, c):
    """Facet values a contest row can be filtered on."""
    if isinstance(c, Meet):
        divs = sorted({reg.schools[s]["classification"] for s in c.schools if s in reg.schools})
        status = "final" if c.events else "upcoming"
    else:
        divs = sorted({reg.schools[s]["classification"]
                       for s in (c.home, c.away) if s in reg.schools})
        if isinstance(c, Game):
            status = {"final": "final", "scheduled": "upcoming"}.get(c.status, "changed")
        else:
            status = "final" if c.home_points is not None else "upcoming"
    return " ".join(divs), status


def contest_row(reg, c, show_sport=True, facets=False):
    label = result_label(c)
    sport = BY_KEY[c.sport].name if show_sport and c.sport in BY_KEY else ""
    if isinstance(c, Meet):
        who = f"<span class='fh-name'><a href='{reg.url(c)}'>{esc(c.name)}</a></span>"
        vs = f"<span class='fh-plain fh-dim'>{esc(c.host or '')}</span>"
    else:
        who = (f"<span class='fh-plain'>{reg.school_link(c.away)} "
               f"<span class='fh-dim'>at</span> {reg.school_link(c.home)}</span>")
        vs = f"<span class='fh-name'><a href='{reg.url(c)}'>{esc(label) or 'Preview'}</a></span>"
    attrs = ""
    if facets:
        divs, status = contest_facets(reg, c)
        attrs = (f" data-f-division='{esc(divs)}' data-f-status='{status}'"
                 f" data-f-sport='{esc(c.sport)}'")
    return (f"<div class='fh-row'{attrs} style='--grid-cols:86px minmax(200px,2fr) minmax(80px,1fr) minmax(90px,1fr)'>"
            f"<span class='fh-dim tnum'>{esc(nice_date(c.date))}</span>{who}{vs}"
            f"<span class='fh-plain fh-dim'>{esc(sport)}</span></div>")


def contest_table(reg, contests, show_sport=True, fid=None):
    rows = "".join(contest_row(reg, c, show_sport, facets=bool(fid)) for c in contests)
    body_cls = f"fh-filterable' id='{fid}" if fid else ""
    return ("<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:86px minmax(200px,2fr) minmax(80px,1fr) minmax(90px,1fr)'>"
            "<div class='fh-thead'><span class='fh-th'>Date</span><span class='fh-th'>Matchup</span>"
            "<span class='fh-th'>Result</span><span class='fh-th'>" +
            ("Sport" if show_sport else "") + "</span></div>"
            + (f"<div class='fh-filterable' id='{fid}'>{rows}</div>" if fid else rows)
            + "</div></div>")


def standings_tables(reg, sport):
    """Conference standings — one table per league.

    The page used to rank every school in a classification against every other
    and truncate at 16, with conference relegated to a trailing column. That is
    a statewide power ranking, not standings: nothing in it is a competition
    anyone is actually in. A league is the unit that plays a round robin and
    produces a champion, so the league is the table. Conference record leads;
    overall follows. Jefferson's conferences mix classifications by design, so
    each row carries its school's class chip and the division facet keys on the
    set of classes present in that league.
    """
    rec = reg.records_for(sport.key)
    if not rec:
        return ""
    by_conf = defaultdict(list)
    for school, r in rec.items():
        conf = reg.conf_of.get(school)
        if conf:
            by_conf[conf].append((school, r))

    cols = "26px 24px minmax(150px,1fr) 34px 62px 62px"
    blocks = []
    for conf in sorted(by_conf):
        rows = sorted(by_conf[conf],
                      key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], -kv[1]["w"], kv[1]["l"], kv[0]))
        divisions = sorted({sport.champ_group(reg.schools[s]["classification"])
                            for s, _ in rows})
        body = "".join(
            f"<div class='fh-row{' first' if i == 0 else ''}' style='--grid-cols:{cols}'>"
            f"<span class='fh-rank'>{i+1}</span>{reg.crest(s,'xs')}"
            f"<span class='fh-name'>{reg.school_link(s)}</span>"
            f"<span class='fh-plain'>{class_chip(reg.schools[s]['classification'])}</span>"
            f"<span class='fh-num tnum'>{r['cw']}-{r['cl']}</span>"
            f"<span class='fh-num tnum fh-dim'>{_wlt(r)}</span></div>"
            for i, (s, r) in enumerate(rows))
        slug = reg.conf_slug.get(conf, "")
        head = f"<a href='/conferences/{slug}/'>{esc(conf)}</a>" if slug else esc(conf)
        blocks.append(
            f"<div class='fh-section' data-key='{esc(conf)}'>"
            f"<div class='fh-group'><h3>{head}</h3></div>"
            f"<div class='fh-tablescroll'><div class='fh-table' style='--grid-cols:{cols}'>"
            "<div class='fh-thead'><span class='fh-th'></span><span class='fh-th'></span>"
            "<span class='fh-th'>School</span><span class='fh-th'></span>"
            "<span class='fh-th'>Conf</span><span class='fh-th'>Overall</span></div>"
            f"{body}</div></div></div>")
    return "".join(blocks)


def _wlt(r):
    return f"{r['w']}-{r['l']}" + (f"-{r['t']}" if r.get("t") else "")


# ─────────────────────────────────────────────────────────────────── pages


def tournament_context(reg, c):
    """The postseason banner above a contest that belongs to a championship.

    This is what turns a result page into a record: the same 26-17 means one
    thing on a Friday in October and another as a state final, and until the
    tournament layer existed the page could not tell you which.
    """
    found = reg.tournament_for(c)
    if not found:
        return "", ""
    t, rnd, m = found
    href = reg.tour_url[t.id]
    label = rnd.name if rnd is not None else "Championship meet"
    kicker = (f"<div class='fh-tourbar'>"
              f"<a class='tn' href='{href}'>{esc(t.name)}</a>"
              f"<span class='rd'>{esc(label.upper())}</span>"
              f"<a class='bk' href='{href}'>View full bracket →</a></div>"
              if t.format is TournamentFormat.BRACKET else
              f"<div class='fh-tourbar'><a class='tn' href='{href}'>{esc(t.name)}</a>"
              f"<span class='rd'>{esc(label.upper())}</span></div>")

    # After the result: who this crowned, and the neighbouring rounds.
    after = ""
    if rnd is not None and m is not None and m.decided:
        is_final = rnd.index == len(t.rounds) - 1
        if is_final and t.champion:
            after += (f"<div class='fh-champbanner'>{reg.crest(t.champion,'lg')}"
                      f"<div><span class='kk'>{esc(t.group)} State Champions</span>"
                      f"<span class='hd'>{reg.school_link(t.champion)}</span></div></div>")
        links = []
        if rnd.index > 0:
            prev = [f for f in t.rounds[rnd.index - 1].matchups
                    if f.slot // 2 == m.slot and f.winner in (m.home, m.away)]
            for f in prev:
                h = reg.contest_href(f.contest_key)
                if h:
                    links.append(f"<a href='{h}'>← {esc(t.rounds[rnd.index-1].name)} result</a>")
        links.append(f"<a href='{href}'>Full bracket</a>")
        links.append(f"<a href='/sports/{c.sport}/champions/'>Championship history</a>")
        after += f"<nav class='fh-tourlinks'>{' · '.join(links)}</nav>"
    return kicker, after


def provenance_note(reg, c):
    """Where this record came from, on the record's own page.

    Provenance that only exists in the JSON is a promise; provenance a reader
    can see is a property of the product. Imported contests say so.
    """
    p = getattr(c, "provenance", None)
    if p is None or p.adapter.startswith("jefferson."):
        return ""
    bits = [f"<b>{esc(p.source_name)}</b>",
            f"{esc(p.source_type.value)} via <code>{esc(p.adapter)}</code> "
            f"v{esc(p.adapter_version)}"]
    if p.external_ids:
        bits.append(" · ".join(f"{esc(k)} {esc(v)}" for k, v in p.external_ids.items()))
    if p.source_sha256:
        bits.append(f"sha256 {esc(p.source_sha256[:16])}…")
    bits.append(f"imported {esc((p.extracted_at or '')[:10])}")
    flag = ""
    if p.review_state.value != "published":
        flag = (f"<span class='fh-reviewflag'>Needs review"
                + (f" — {esc(p.notes)}" if p.notes else "") + "</span>")
    return (f"<div class='fh-section'><h2>Source</h2>"
            f"<div class='fh-prov'>{flag}<p>{' · '.join(bits)}</p>"
            f"<p class='fh-dim'>Imported from the file the source system produced. "
            f"Nothing on this page was retyped.</p></div></div>")


def box_score_tables(reg, c: Game):
    """The box score as the source printed it — its columns, its order.

    The renderer does not know what "3pt" means and does not need to. Team
    totals are the source's own row, shown as printed; where they disagree with
    the player lines the import is already flagged.
    """
    box = c.box
    if not box:
        return ""

    def table(school, side, section, totals):
        cols = box.columns_for(section)
        lines = box.rows(side, section)
        if not lines:
            return ""
        grid = f"minmax(150px,1.6fr) 30px repeat({len(cols)},minmax(44px,1fr))"
        head = "".join(f"<span class='fh-th'>{esc(k.upper())}</span>" for k in cols)
        rows = []
        for s in lines:
            cells = "".join(
                f"<span class='fh-num tnum'>{esc(s.get(k))}</span>" for k in cols)
            rows.append(
                f"<div class='fh-row'><span class='fh-name'>"
                f"{reg.athlete_link(s.competitor.name, school)}</span>"
                f"<span class='fh-dim'>{esc(CLASS_LABEL.get(s.competitor.year or '', ''))}</span>"
                f"{cells}</div>")
        # A section's totals only make sense when the source printed them for
        # that section's columns; a shared totals row is shown once, on the
        # single-table sports.
        if totals and any(k in totals for k in cols):
            cells = "".join(
                f"<span class='fh-num tnum'>{esc(totals.get(k, ''))}</span>" for k in cols)
            rows.append(f"<div class='fh-row totals'><span class='fh-name'>Team totals</span>"
                        f"<span class='fh-dim'></span>{cells}</div>")
        label = f"<h5 class='fh-boxsec'>{esc(section)}</h5>" if section else ""
        return (f"{label}<div class='fh-tablescroll'><div class='fh-table narrow' "
                f"style='--grid-cols:{grid}'>"
                f"<div class='fh-thead'><span class='fh-th'>Player</span>"
                f"<span class='fh-th'></span>{head}</div>{''.join(rows)}</div></div>")

    tables = []
    for school, side, totals in ((c.away, "away", box.away_totals),
                                 (c.home, "home", box.home_totals)):
        parts = [table(school, side, sec, totals) for sec in box.section_names()]
        parts = [p for p in parts if p]
        if parts:
            tables.append(
                f"<h4 class='fh-boxhd'>{reg.crest(school,'xs')} {esc(school)}</h4>"
                + "".join(parts))
    starters = sum(1 for s in box.home + box.away if s.starter)
    bits = [f"{len(box.home) + len(box.away)} rows"]
    if box.sections:
        bits.append(f"{len(box.sections)} tables: {', '.join(box.sections)}")
    elif starters:
        bits.append(f"{starters} starters")
    bits.append("columns as printed by the source scorebook")
    note = f"<p class='fh-dim'>{esc(' · '.join(bits))}.</p>"
    return (f"<div class='fh-section'><h2>Box score</h2>{''.join(tables)}{note}</div>")


def render_game(reg, c: Game):
    periods = ""
    if c.periods:
        head = "".join(f"<span class='fh-th'>{esc(p.label)}</span>" for p in c.periods)
        rowa = "".join(f"<span class='fh-num tnum'>{p.away}</span>" for p in c.periods)
        rowh = "".join(f"<span class='fh-num tnum'>{p.home}</span>" for p in c.periods)
        cols = f"minmax(140px,1fr) repeat({len(c.periods)},48px)"
        periods = (f"<div class='fh-section'><h2>By period</h2><div class='fh-tablescroll'>"
                   f"<div class='fh-table narrow' style='--grid-cols:{cols}'>"
                   f"<div class='fh-thead'><span class='fh-th'></span>{head}</div>"
                   f"<div class='fh-row'><span class='fh-name'>{reg.school_link(c.away)}</span>{rowa}</div>"
                   f"<div class='fh-row'><span class='fh-name'>{reg.school_link(c.home)}</span>{rowh}</div>"
                   f"</div></div></div>")
    status = {"scheduled": "Scheduled", "cancelled": "Cancelled", "postponed": "Postponed"}.get(c.status, "Final")
    score = f"{c.away_score}&nbsp;–&nbsp;{c.home_score}" if c.home_score is not None else "—"
    sport = BY_KEY[c.sport]
    kicker, after = tournament_context(reg, c)
    body = f"""
{kicker}
<div class="fh-score">
  <div class="side">{reg.crest(c.away,'lg')}<div class="tn">{reg.school_link(c.away)}</div></div>
  <div class="mid"><div class="big tnum">{score}</div>
  <div class="st">{esc(status)} · {esc(nice_date(c.date))}</div>
  {f'<div class="rs">{esc(c.result)}</div>' if getattr(c, "result", None) else ''}</div>
  <div class="side">{reg.crest(c.home,'lg')}<div class="tn">{reg.school_link(c.home)}</div></div>
</div>
{after}
{periods}
{box_score_tables(reg, c)}
{provenance_note(reg, c)}
"""
    crumb = (f"<a href='/'>{NAME}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}")
    return shell(f"{c.name} — {sport.name}", body, crumb, f"← {sport.name}|/sports/{sport.key}/",
                 desc=share_desc(reg, c), kind="article",
                 # salted per contest, so 45,000 result cards do not all paste
                 # the same frame of the same sport
                 image=sport_photo(c.sport, salt=reg.url(c))[0],
                 published=c.date)


def render_dual(reg, c: Dual):
    sport = BY_KEY[c.sport]
    rows = []
    for line in c.lines:
        hw = line.winner == "home"
        aw = line.winner == "away"
        drew = line.winner == "draw"
        hn = ", ".join(reg.athlete_link(p.name, c.home) for p in line.home) or "—"
        an = ", ".join(reg.athlete_link(p.name, c.away) for p in line.away) or "—"
        rows.append(
            f"<div class='fh-row' style='--grid-cols:56px minmax(140px,1fr) minmax(140px,1fr) 96px'>"
            f"<span class='fh-rank'>{esc(str(line.kind)[:8].title() if not str(line.kind).isdigit() else line.kind)} {line.slot if line.kind in ('singles','doubles') else ''}</span>"
            f"<span class='fh-plain{' fh-mark' if aw else ''}'>{an}</span>"
            f"<span class='fh-plain{' fh-mark' if hw else ''}'>{hn}</span>"
            f"<span class='fh-num tnum{' fh-dim' if drew else ''}'>"
            f"{esc(line.score or '')}</span></div>")
    score = (f"{c.away_points:g}&nbsp;–&nbsp;{c.home_points:g}" if c.home_points is not None else "—")
    big = "big tnum frac" if "." in score else "big tnum"
    body = f"""
<div class="fh-score">
  <div class="side">{reg.crest(c.away,'lg')}<div class="tn">{reg.school_link(c.away)}</div></div>
  <div class="mid"><div class="{big}">{score}</div>
  <div class="st">{esc(nice_date(c.date))}</div></div>
  <div class="side">{reg.crest(c.home,'lg')}<div class="tn">{reg.school_link(c.home)}</div></div>
</div>
<div class="fh-section"><h2>Lines</h2>
<div class="fh-tablescroll"><div class="fh-table" style="--grid-cols:56px minmax(140px,1fr) minmax(140px,1fr) 96px">
<div class="fh-thead"><span class="fh-th"></span><span class="fh-th">{esc(c.away)}</span>
<span class="fh-th">{esc(c.home)}</span><span class="fh-th">Score</span></div>
{''.join(rows)}</div></div></div>
{provenance_note(reg, c)}
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}"
    return shell(f"{c.name} — {sport.name}", body, crumb, f"← {sport.name}|/sports/{sport.key}/",
                 desc=share_desc(reg, c), kind="article",
                 # salted per contest, so 45,000 result cards do not all paste
                 # the same frame of the same sport
                 image=sport_photo(c.sport, salt=reg.url(c))[0],
                 published=c.date)


def meet_results_tables(reg, c: Meet, limit_events=None):
    """A meet's events as result tables.

    Shared by the meet page and the championship page, so a meet-decided title
    shows the same results in both places rather than a summary in one and the
    real thing in the other.

    Relays and doubles print every competitor: an entry whose competitor list is
    truncated to the first name silently turns a relay into an individual.
    """
    grouped = c.events if limit_events is None else c.events[:limit_events]
    cols = "34px minmax(150px,1.2fr) 36px minmax(130px,1fr) 90px"
    blocks = []
    for ev in grouped:
        rows = []
        for e in ev.entries[:30]:
            if e.competitors:
                who = ", ".join(reg.athlete_link(p.name, e.school) for p in e.competitors)
                yr = CLASS_LABEL.get(e.competitors[0].year or "", "") if len(e.competitors) == 1 else ""
            else:
                who, yr = "—", ""
            mark = esc(e.mark.raw) if e.mark and e.mark.raw else ""
            note = f"<span class='fh-splits'>{esc(e.note)}</span>" if e.note else ""
            rows.append(
                f"<div class='fh-row{' first' if e.place == 1 else ''}' "
                f"style='--grid-cols:{cols}'>"
                f"<span class='fh-rank'>{e.place or ''}</span>"
                f"<span class='fh-name'>{who}{note}</span>"
                f"<span class='fh-dim'>{yr}</span>"
                f"<span class='fh-plain'>{reg.school_link(e.school)}</span>"
                f"<span class='fh-mark'>{mark}</span></div>")
        head = esc(ev.name)
        if ev.gender:
            head = f"{esc(ev.gender)} {head}"
        if ev.round and ev.round != "Finals":
            head += f" <span class='rnd'>{esc(ev.round)}</span>"
        blocks.append(
            f"<div class='fh-evhead'><h4>{head}</h4></div>"
            f"<div class='fh-tablescroll'><div class='fh-table' style='--grid-cols:{cols}'>"
            "<div class='fh-thead'><span class='fh-th'>Pl</span><span class='fh-th'>Athlete</span>"
            "<span class='fh-th'>Yr</span><span class='fh-th'>School</span><span class='fh-th'>Mark</span></div>"
            f"{''.join(rows)}</div></div>")
    if limit_events is not None and len(c.events) > limit_events:
        blocks.append(f"<p class='fh-more'><a href='{reg.url(c)}'>"
                      f"All {len(c.events)} events →</a></p>")
    return "".join(blocks)


def render_meet(reg, c: Meet):
    sport = BY_KEY[c.sport]
    scores = ""
    if c.team_scores:
        cols = "26px minmax(150px,1fr) 66px"
        # A team score is in the sport's OWN unit — 326 strokes, 2,290 pinfall,
        # 77 points — so the column says which. Unlabelled, the same table
        # reads as five different numbers meaning the same thing.
        unit = meet_scoring(c.sport)[2] if c.sport in BY_KEY else "Points"
        rows = "".join(
            f"<div class='fh-row{' first' if t.rank == 1 else ''}' style='--grid-cols:{cols}'>"
            f"<span class='fh-rank'>{t.rank}</span><span class='fh-name'>{reg.school_link(t.school)}</span>"
            f"<span class='fh-num fh-mark'>{t.points:g}</span></div>"
            for t in sorted(c.team_scores, key=lambda t: t.rank or 99)[:14])
        scores = (f"<div class='fh-section'><h2>Team scores</h2>"
                  f"<div class='fh-panel' style='max-width:470px'><div class='fh-table narrow' "
                  f"style='--grid-cols:{cols}'>"
                  f"<div class='fh-thead'><span class='fh-th'></span>"
                  f"<span class='fh-th'>School</span><span class='fh-th'>{esc(unit)}</span></div>"
                  + rows + "</div></div></div>")
    blocks = [meet_results_tables(reg, c)]
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">{esc(c.name)}</div>
  <div class="meta">{esc(nice_date(c.date))} · {esc(c.host or '')} · <a href='/sports/{sport.key}/'>{esc(sport.name)}</a></div></div>
  <div class="side"></div>
</div>
{tournament_context(reg, c)[0]}
{scores}
<div class="fh-section"><h2>{'Results' if c.events else 'Scheduled'}</h2>{''.join(blocks) or ''}</div>
{provenance_note(reg, c)}
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}"
    return shell(f"{c.name} — {sport.name}", body, crumb, f"← {sport.name}|/sports/{sport.key}/",
                 desc=share_desc(reg, c), kind="article",
                 # salted per contest, so 45,000 result cards do not all paste
                 # the same frame of the same sport
                 image=sport_photo(c.sport, salt=reg.url(c))[0],
                 published=c.date)


def sport_nav(sp, active):
    """Sub-navigation for a sport hub.

    Rankings and standings are different products and never share a page:
    rankings answer "who are the best teams in 5A?", statewide, one
    classification at a time; standings answer "who is winning the Larch
    Conference?", one league at a time. MEET-shaped activities have season
    leaders instead of either.
    """
    if sp.shape.value == "meet":
        items = [("", "Overview"), ("standings/", "Season leaders"),
                 ("schedule/", "Schedule & results"), ("champions/", "Championships")]
    else:
        items = [("", "Overview"), ("rankings/", "Rankings"), ("standings/", "Standings"),
                 ("schedule/", "Schedule & results"), ("champions/", "Championships")]
    links = "".join(
        f"<a href='/sports/{sp.key}/{path}'{' class=on' if path == active else ''}>{esc(label)}</a>"
        for path, label in items)
    return f"<nav class='fh-subnav'>{links}</nav>"


def gender_switch(reg, sp, active=""):
    """Boys · Girls, where both run in the same season.

    The nav lists such a sport ONCE, under its plain name, so this is where
    the split actually happens — the page you land on has to be able to reach
    the other half, and a reader who wants "basketball" should not have to
    know which of two entries they clicked.
    """
    other = gendered_pair(reg, sp)
    if other is None:
        return ""
    # `active` already carries its trailing slash ("rankings/"), and a pair is
    # always the same shape, so the sub-page exists on both sides
    pair = sorted((sp, other), key=lambda s: s.name)
    return "<div class='fh-gsw'>" + "".join(
        (f"<span class='on'>{esc(s.name.split(' ', 1)[0])}</span>" if s.key == sp.key
         else f"<a href='/sports/{s.key}/{active}'>{esc(s.name.split(' ', 1)[0])}</a>")
        for s in pair) + "</div>"


def sport_header(reg, sp, active=""):
    groups = list(dict.fromkeys(sp.champ_group(c) for c in tuple(CLASSES)))
    chips = "".join(class_chip(g) if g[0].isdigit() else f"<span class='fh-tag'>{esc(g)}</span>"
                    for g in groups)
    # a paired sport shows its plain name and lets the switch carry the gender;
    # an unpaired one keeps its full name, because "Softball" and "Gymnastics"
    # are not halves of anything
    other = gendered_pair(reg, sp)
    title = _base_name(sp) if other is not None else sp.name
    return f"""
<div class="fh-idhdr sport">
  <span class="fh-sportmark">{icons.icon(sp.key, 'fh-ic lg')}</span>
  <div><div class="name">{esc(title)}</div>
  <div class="meta">{esc(sp.season.title())} · {SEASON_LABEL} · championship divisions: {chips}</div></div>
  <div class="side">{gender_switch(reg, sp, active)}</div>
</div>
{sport_nav(sp, active)}
"""


def sport_groups(sp):
    return list(dict.fromkeys(sp.champ_group(c) for c in tuple(CLASSES)))


def rankings_by_group(reg, sp, limit=10):
    """Statewide rankings, one list per championship division. Win percentage,
    then wins — a record, not a rating; the site never invents a computer poll."""
    rec = reg.records_for(sp.key)
    by_group = defaultdict(list)
    for school, r in rec.items():
        if school in reg.schools:
            by_group[sp.champ_group(reg.schools[school]["classification"])].append((school, r))
    out = {}
    for grp, rows in by_group.items():
        rows.sort(key=lambda kv: (-(kv[1]["w"] / max(1, kv[1]["w"] + kv[1]["l"])),
                                  -kv[1]["w"], kv[1]["l"], kv[0]))
        out[grp] = rows[:limit]
    return out


def ranking_table(reg, sp, grp, rows, compact=False):
    cols = "30px 24px minmax(150px,1fr) 62px" if compact else \
           "30px 24px minmax(160px,1fr) 70px minmax(120px,1fr)"
    body = "".join(
        f"<div class='fh-row{' first' if i == 0 else ''}' style='--grid-cols:{cols}'>"
        f"<span class='fh-rank'>{i+1}</span>{reg.crest(s,'xs')}"
        f"<span class='fh-name'>{reg.school_link(s)}</span>"
        f"<span class='fh-num tnum'>{_wlt(r)}</span>"
        + ("" if compact else f"<span class='fh-plain fh-dim'>{esc(reg.conf_of.get(s,''))}</span>")
        + "</div>"
        for i, (s, r) in enumerate(rows))
    head = ("<div class='fh-thead'><span class='fh-th'>Rk</span><span class='fh-th'></span>"
            "<span class='fh-th'>School</span><span class='fh-th'>Record</span>"
            + ("" if compact else "<span class='fh-th'>Conference</span>") + "</div>")
    narrow = " narrow" if compact else ""
    return (f"<div class='fh-tablescroll'><div class='fh-table{narrow}' style='--grid-cols:{cols}'>"
            f"{head}{body}</div></div>")


def render_sport_rankings(reg, sp):
    ranked = rankings_by_group(reg, sp)
    groups = [g for g in sport_groups(sp) if ranked.get(g)]
    if groups:
        blocks = "".join(
            f"<div class='fh-section' data-f-division='{esc(g)}'>"
            f"<div class='fh-group'><h3>{grp_chip(g)}</h3></div>"
            + ranking_table(reg, sp, g, ranked[g]) + "</div>"
            for g in groups)
        bar = facet_bar(f"rk-{sp.key}", [("division", "Classification",
                                          [(g, class_chip(g) if g[0].isdigit() else esc(g)) for g in groups])],
                        exclusive=True) if len(groups) > 1 else ""
        inner = bar + f"<div class='fh-filterable' id='rk-{sp.key}'>{blocks}</div>"
    else:
        inner = "<p class='fh-lede'>Rankings post once results are in.</p>"
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sp.key}/'>{esc(sp.name)}</a> › Rankings"
    return shell(page_title(f"{sp.name} rankings"),
                 sport_header(reg, sp, "rankings/") + inner, crumb, f"← {sp.name}|/sports/{sp.key}/")


CONF_PICKER_JS = """
(function () {
  document.querySelectorAll("select[data-pick]").forEach(function (sel) {
    var wrap = document.getElementById(sel.dataset.pick);
    if (!wrap) return;
    function apply() {
      [].forEach.call(wrap.children, function (n) {
        n.hidden = n.getAttribute("data-key") !== sel.value;
      });
    }
    sel.addEventListener("change", apply);
    apply();
  });
})();
"""


def render_sport_standings(reg, sp):
    if sp.shape.value == "meet":
        wins = defaultdict(int)
        for c in reg.by_sport.get(sp.key, []):
            top = next((t for t in getattr(c, "team_scores", []) if t.rank == 1), None)
            if top:
                wins[top.school] += 1
        rows = "".join(
            f"<div class='fh-row{' first' if i == 0 else ''}' style='--grid-cols:26px 24px minmax(160px,1fr) 70px minmax(110px,1fr)'>"
            f"<span class='fh-rank'>{i+1}</span>{reg.crest(sch,'xs')}"
            f"<span class='fh-name'>{reg.school_link(sch)}</span>"
            f"<span class='fh-num tnum'>{n}</span>"
            f"<span class='fh-plain fh-dim'>{esc(reg.conf_of.get(sch,''))}</span></div>"
            for i, (sch, n) in enumerate(sorted(wins.items(), key=lambda kv: (-kv[1], kv[0]))[:25]))
        inner = ("<div class='fh-tablescroll'><div class='fh-table' "
                 "style='--grid-cols:26px 24px minmax(160px,1fr) 70px minmax(110px,1fr)'>"
                 "<div class='fh-thead'><span class='fh-th'></span><span class='fh-th'></span>"
                 "<span class='fh-th'>School</span><span class='fh-th'>Meet wins</span>"
                 f"<span class='fh-th'>Conference</span></div>{rows}</div></div>"
                 ) if rows else "<p class='fh-lede'>Team scoring posts as meets are held.</p>"
    else:
        tables = standings_tables(reg, sp)
        if tables:
            confs = sorted({reg.conf_of[s] for s in reg.records_for(sp.key) if reg.conf_of.get(s)})
            opts = "".join(f"<option>{esc(c)}</option>" for c in confs)
            inner = (f"<div class='fh-pickbar'><label for='conf-pick'>Conference</label>"
                     f"<select id='conf-pick' data-pick='st-{sp.key}'>{opts}</select></div>"
                     f"<div id='st-{sp.key}'>{tables}</div>")
        else:
            inner = "<p class='fh-lede'>Standings post once conference play begins.</p>"
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sp.key}/'>{esc(sp.name)}</a> › Standings"
    label = "Season leaders" if sp.shape.value == "meet" else "Standings"
    return shell(page_title(f"{sp.name} {label.lower()}"),
                 sport_header(reg, sp, "standings/") + inner, crumb, f"← {sp.name}|/sports/{sp.key}/")


def render_sport_schedule(reg, sp):
    contests = sorted(reg.by_sport.get(sp.key, []), key=lambda c: c.date or "")
    played = [c for c in contests if (c.date or "") <= TODAY]
    upcoming = [c for c in contests if (c.date or "") > TODAY]
    rows = list(reversed(played))[:80] + upcoming[:40]
    rows.sort(key=lambda c: c.date or "", reverse=True)
    bar = facet_bar(f"sch-{sp.key}", [
        ("division", "Classification", [(v, class_chip(v)) for v in CLASSES]),
        ("status", "Status", [("final", "Final"), ("upcoming", "Upcoming"),
                              ("changed", "Postponed / cancelled")]),
    ])
    inner = f"<div class='fh-section'>{bar}{contest_table(reg, rows, False, fid=f'sch-{sp.key}')}</div>"
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sp.key}/'>{esc(sp.name)}</a> › Schedule"
    return shell(page_title(f"{sp.name} schedule"),
                 sport_header(reg, sp, "schedule/") + inner, crumb, f"← {sp.name}|/sports/{sp.key}/")


def render_sport_champs(reg, sp):
    mine = [(g, c) for s2, g, c in champ_finals(reg) if s2.key == sp.key]
    rows = []
    for grp, c in sorted(mine, key=lambda t: t[0]):
        if isinstance(c, Game):
            winner = c.winner
            runner = c.away if c.winner == c.home else c.home
            line = f"{max(c.home_score, c.away_score)}\u2013{min(c.home_score, c.away_score)}"
        else:
            order = sorted(c.team_scores, key=lambda t: t.rank or 99)
            winner = order[0].school if order else ""
            runner = order[1].school if len(order) > 1 else ""
            line = "Results"
        rows.append(
            f"<div class='fh-row' style='--grid-cols:70px 24px minmax(160px,1fr) minmax(150px,1fr) 90px'>"
            f"<span>{grp_chip(grp)}</span>"
            f"{reg.crest(winner,'xs')}<span class='fh-name'>{reg.school_link(winner)}</span>"
            f"<span class='fh-plain fh-dim'>{reg.school_link(runner) if runner else ''}</span>"
            f"<span class='fh-plain'><a href='{reg.url(c)}'>{esc(line)}</a></span></div>")
    if rows:
        inner = ("<div class='fh-tablescroll'><div class='fh-table' "
                 "style='--grid-cols:70px 24px minmax(160px,1fr) minmax(150px,1fr) 90px'>"
                 "<div class='fh-thead'><span class='fh-th'>Division</span><span class='fh-th'></span>"
                 "<span class='fh-th'>Champion</span><span class='fh-th'>Runner-up</span>"
                 f"<span class='fh-th'>Final</span></div>{''.join(rows)}</div></div>")
    else:
        when = {"fall": "concluded in November", "winter": "conclude in March",
                "spring": "conclude in June"}[sp.season]
        inner = (f"<p class='fh-lede'>{esc(sp.name)} championships {esc(when)}. "
                 f"Brackets and qualifying information post as the postseason approaches.</p>")
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sp.key}/'>{esc(sp.name)}</a> › Championships"
    return shell(page_title(f"{sp.name} championships"),
                 sport_header(reg, sp, "champions/") + inner, crumb, f"← {sp.name}|/sports/{sp.key}/")


def render_sport(reg, sport):
    """The sport front. Sections exist only where content does, and every
    result names both sides — the overview composes Latest, a rankings
    preview, Next, and championship state, sized by the season."""
    contests = sorted(reg.by_sport.get(sport.key, []), key=lambda c: c.date or "")
    played = list(reversed([c for c in contests if (c.date or "") <= TODAY]))
    upcoming = [c for c in contests if (c.date or "") > TODAY]

    sections = []

    # Latest — real results, both sides.
    latest = []
    for c in played:
        line = meet_line(reg, c) if isinstance(c, Meet) else score_line(reg, c)
        if line:
            latest.append(score_row(reg.url(c), line, esc(nice_date(c.date))))
        if len(latest) >= 8:
            break
    if latest:
        sections.append(("Latest", "".join(latest),
                         f"/sports/{sport.key}/schedule/", "All results"))

    # Rankings preview (GAME/DUAL) or leaders (MEET) — first division only.
    if sport.shape.value != "meet":
        ranked = rankings_by_group(reg, sport, limit=5)
        first = next((g for g in sport_groups(sport) if ranked.get(g)), None)
        if first:
            preview = (f"<div class='fh-group'><h3>{grp_chip(first)}</h3></div>"
                       + ranking_table(reg, sport, first, ranked[first], compact=True))
            sections.append(("Rankings", preview,
                             f"/sports/{sport.key}/rankings/", "All classifications"))
    else:
        recent = [c for c in played if getattr(c, "team_scores", None)][:6]
        if recent:
            preview = "".join(
                score_row(reg.url(c), f"{meet_line(reg, c)}", f"{esc(nice_date(c.date))}") for c in recent)
            sections.append(("Season leaders", preview,
                             f"/sports/{sport.key}/standings/", "Full list"))

    # Next — matchups with both schools and the league they matter to.
    nxt = []
    for c in upcoming[:8]:
        league = ""
        if not isinstance(c, Meet):
            ch, ca = reg.conf_of.get(c.home, ""), reg.conf_of.get(c.away, "")
            league = ch if ch and ch == ca else "Non-conference"
        nxt.append(
            score_row(reg.url(c), f"{matchup_line(reg, c)}", f"{esc(league)}"))
    if nxt:
        sections.append(("Next", "".join(nxt),
                         f"/sports/{sport.key}/schedule/", "Full schedule"))

    # Championship — actual champions when decided, otherwise nothing loud.
    champs = [(g, c) for s2, g, c in champ_finals(reg) if s2.key == sport.key]
    if champs:
        rows = "".join(
            score_row(reg.url(c), f"{grp_chip(g)} {reg.school_link(_champ_winner(c))}", "Champion")
            for g, c in sorted(champs, key=lambda t: t[0]))
        sections.append(("Championships", rows,
                         f"/sports/{sport.key}/champions/", "Championship detail"))

    if not sections:
        body_inner = "<p class='fh-lede'>The season has not started. The schedule posts here.</p>"
    else:
        cols = "".join(
            f"<section><h2>{esc(title)}</h2><div class='fh-results'>{inner}</div>"
            f"<p class='fh-more'><a href='{href}'>{esc(more)} →</a></p></section>"
            for title, inner, href, more in sections)
        body_inner = f"<div class='fh-overview n{min(3, len(sections))}'>{cols}</div>"

    body = sport_header(reg, sport) + body_inner
    crumb = f"<a href='/'>{NAME}</a> › {esc(sport.name)}"
    # 51 sport fronts are the most-linked pages on the site after the schools,
    # and every one of them was pasting as the generic fallback card
    return shell(page_title(f"{sport.name}"), body, crumb,
                 desc=(f"JHSAA {sport.name} — {SEASON_LABEL} results, schedule, "
                       f"standings and the state championship, every "
                       f"classification."),
                 image=sport_photo(sport.key)[0])


def _champ_winner(c):
    if isinstance(c, Game):
        return c.winner or c.home
    order = sorted(c.team_scores, key=lambda t: t.rank or 99)
    return order[0].school if order else ""


def event_card(reg, c, final):
    """ScoreCard / UpcomingEvent: marks, names, scores or date — the same row
    at state, conference and school scope."""
    sp = BY_KEY[c.sport]
    if isinstance(c, Meet):
        line = meet_line(reg, c) if final else esc(c.name)
        return (f"<div class='fh-card'><span class='st'>{'FINAL' if final else esc(nice_date(c.date))}</span>"
                f"<div class='mrow one'>{line}</div>"
                f"<span class='sp'>{esc(sp.name)} · <a href='{reg.url(c)}'>"
                f"{'Result' if final else 'Details'} →</a></span></div>")
    home, away = c.home, c.away
    if final:
        hs = c.home_score if isinstance(c, Game) else c.home_points
        as_ = c.away_score if isinstance(c, Game) else c.away_points
        rows = (f"<div class='mrow'>{reg.crest(away,'xs')}<span class='nm'>{reg.school_link(away)}</span>"
                f"<b class='tnum'>{as_ if as_ is not None else ''}</b></div>"
                f"<div class='mrow'>{reg.crest(home,'xs')}<span class='nm'>{reg.school_link(home)}</span>"
                f"<b class='tnum'>{hs if hs is not None else ''}</b></div>")
        head = "FINAL"
    else:
        rows = (f"<div class='mrow'>{reg.crest(away,'xs')}<span class='nm'>{reg.school_link(away)}</span></div>"
                f"<div class='mrow at'>at</div>"
                f"<div class='mrow'>{reg.crest(home,'xs')}<span class='nm'>{reg.school_link(home)}</span></div>")
        head = esc(nice_date(c.date))
    return (f"<div class='fh-card'><span class='st'>{head}</span>{rows}"
            f"<span class='sp'>{esc(sp.name)} · <a href='{reg.url(c)}'>"
            f"{'Box →' if final else 'Preview →'}</a></span></div>")


def feature_panel(kicker, hd, dk, colors, watermark="", photo=None):
    """FeaturedStory: real photography under the organization's color — every
    news-shaped surface carries a photograph (owner rule). The color arrives
    as a gradient overlay so identity survives on top of the image; the photo
    credit prints in the corner, as the license requires."""
    c1, _c2 = colors
    if photo:
        url, credit = photo
        style = (f"background:linear-gradient(100deg, {c1}f2 30%, {c1}99 62%, {c1}55), "
                 f"url('{url}') center/cover no-repeat")
        cr = f"<span class='cr'>Photo: {esc(credit)}</span>" if credit else ""
        return (f"<div class='fh-feature photo' style=\"{style}\">"
                f"<span class='kk'>{kicker}</span><span class='hd'>{hd}</span>"
                f"<span class='dk'>{dk}</span>{cr}</div>")
    return (f"<div class='fh-feature' style='background:{c1}'>"
            f"<div class='wm'>{watermark}</div>"
            f"<span class='kk'>{kicker}</span><span class='hd'>{hd}</span>"
            f"<span class='dk'>{dk}</span></div>")


# ══════════════════════════════════════════════ homepage components
#
# One set, three tenants. What changes between a school front, a conference
# front and the association front is the DATA SCOPE passed in, not the
# component — school -> its own items, conference -> its members', state ->
# everything. Composition differs by tenant; the pieces do not.


def item_href(reg, it):
    """Where an editorial item points.

    Honors are about people, so an item naming one athlete links to that
    athlete's page — the season behind the honor, which is the thing worth
    reading. Otherwise the sport, the school or nothing.
    """
    if it.get("href"):
        return it["href"]
    if len(it.get("people") or ()) == 1 and it.get("school"):
        a = reg.athletes.get((it["people"][0], it["school"]))
        if a:
            return f"/athletes/{a['slug']}/"
    if it.get("sport") and it["kind"] in ("title", "qualified", "state-title",
                                          "conf-tournament", "conf-champion"):
        return f"/championships/{it['sport']}/"
    if it.get("sport"):
        return f"/sports/{it['sport']}/"
    return reg.school_url(it["school"]) if it.get("school") else "/news/"


def headline_list(reg, items, limit=5, show_school=False):
    """HeadlineList — compact editorial rows. Headlines, not cards.

    Five of these occupy the space one news card used to, which is the whole
    argument: an athletics front page is information-dense by nature, and a
    department that recognises somebody every week has more to say than one
    story's worth.
    """
    rows = []
    for it in items[:limit]:
        where = ""
        if show_school and it.get("school"):
            where = f"<span class='wh'>{esc(it['school'])}</span>"
        rows.append(
            f"<a class='fh-hl' href='{item_href(reg, it)}'>"
            f"<span class='kk'>{esc(it['label'])}{where}</span>"
            f"<span class='hd'>{esc(it['headline'])}</span>"
            f"<span class='dt'>{esc(nice_date(it['date']))}</span></a>")
    return "".join(rows)


def event_row(reg, c):
    """EventRow — one contest in three compact lines, not the six a card took.

    Sport, the matchup or the result, then when. Five to seven of these fit
    where four cards did, and a schedule column that shows two events is not
    a schedule column.
    """
    sp = BY_KEY[c.sport]
    final = ((isinstance(c, Game) and c.status == "final" and c.home_score is not None)
             or (isinstance(c, Dual) and c.home_points is not None)
             or (isinstance(c, Meet) and bool(c.events)))
    kicker = f"{esc(sp.name)}{' · FINAL' if final else ''}"
    if isinstance(c, Meet):
        line = meet_line(reg, c) if final else esc(c.name)
    elif final:
        line = score_line(reg, c)
    else:
        line = f"{reg.school_link(c.away)} at {reg.school_link(c.home)}"
    when = nice_date(c.date) if c.date else ""
    if not final and getattr(c, "time", None):
        when += f" · {c.time}"
    return (f"<div class='fh-evrow{' final' if final else ''}'>"
            f"<a class='m' href='{reg.url(c)}'></a>"
            f"<span class='kk'>{kicker}</span>"
            f"<span class='ln'>{line}</span>"
            f"<span class='dt'>{esc(when)}</span></div>")


def standings_preview(reg, sport_key, scope=None, limit=5, heading=None):
    """StandingsPreview — the top of one table, not the table.

    `scope` is the set of schools that count: a conference's members at league
    scale, everybody at state scale. A school's own position is a different
    component (`standing_lines`) because "where do we sit" is a different
    question from "who is leading".
    """
    rec = reg.records_for(sport_key)
    rows = sorted(((s, r) for s, r in rec.items() if scope is None or s in scope),
                  key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], -kv[1]["w"], kv[1]["l"], kv[0]))[:limit]
    if not rows:
        return ""
    sp = BY_KEY[sport_key]
    body = "".join(
        f"<div class='fh-stline{' first' if i == 0 else ''}'>"
        f"<span class='rk'>{i + 1}</span>{reg.crest(s, 'xs')}"
        f"<span class='nm'>{reg.school_link(s)}</span>"
        f"<span class='tnum'>{r['cw']}-{r['cl']}</span></div>"
        for i, (s, r) in enumerate(rows))
    head = heading or sp.name
    return (f"<div class='fh-mod'><h3>{esc(head)}</h3>{body}"
            f"<p class='fh-more'><a href='/sports/{sport_key}/standings/'>"
            f"Full standings →</a></p></div>")


def standing_lines(reg, school, sports, limit=4):
    """Where this school sits, across its teams — the school-scope standings."""
    rows = []
    for key in sports:
        if BY_KEY[key].shape.value == "meet":
            continue
        pos = conf_position(reg, key, school)
        if not pos:
            continue
        rank, r, size = pos
        if r["cw"] + r["cl"] == 0:
            continue
        rows.append((rank, key,
                     f"<div class='fh-stline'>"
                     f"<span class='rk'>{_ordinal(rank)}</span>"
                     f"{icons.icon(key, 'fh-ic sm')}"
                     f"<span class='nm'>{esc(BY_KEY[key].name)}</span>"
                     f"<span class='tnum'>{r['cw']}-{r['cl']}</span></div>"))
    rows.sort(key=lambda t: (t[0], BY_KEY[t[1]].name))
    return "".join(h for _r, _k, h in rows[:limit])


def honor_spotlight(reg, items):
    """HonorSpotlight — one person, named and pictured by their mark.

    The recognition module a department leads with. Falls back to nothing
    rather than to a placeholder: a spotlight with nobody in it is worse than
    a column that ends early.
    """
    it = next((i for i in items if i.get("people")), None)
    if not it:
        return ""
    who = it["people"][0]
    crest = reg.crest(it["school"], "sm") if it.get("school") else ""
    where = it.get("school") or ""
    if it.get("sport") in BY_KEY:
        where = f"{where} · {BY_KEY[it['sport']].name}" if where else BY_KEY[it["sport"]].name
    return (f"<div class='fh-mod fh-spot'><h3>{esc(it['label'])}</h3>"
            f"<a class='fh-spotrow' href='{item_href(reg, it)}'>{crest}"
            f"<span class='who'>{esc(who)}</span>"
            f"<span class='wh'>{esc(where)}</span></a>"
            f"<p class='dk'>{esc(it['dek'])}</p></div>")


def awards_list(reg, items, limit=4, heading="Awards & honors", show_school=False):
    """AwardsList — recognitions as a list, with what each one is."""
    if not items:
        return ""
    rows = []
    for it in items[:limit]:
        where = (f"<span class='wh'>{esc(it['school'])}</span>"
                 if show_school and it.get("school") else "")
        rows.append(f"<a class='fh-award' href='{item_href(reg, it)}'>"
                    f"<span class='lb'>{esc(it['label'])}</span>"
                    f"<span class='hd'>{esc(it['headline'])}</span>{where}</a>")
    return f"<div class='fh-mod'><h3>{esc(heading)}</h3>{''.join(rows)}</div>"


def championship_status(reg, tours, limit=4, heading="Postseason"):
    """ChampionshipStatus — where each bracket stands, in one line apiece."""
    if not tours:
        return ""
    rows = []
    for t in tours[:limit]:
        state = (t.champion and f"Won by {t.champion}") or \
            (postseason.live_label(t) if t.status is TournamentStatus.IN_PROGRESS else None) or \
            (f"Opens {nice_date(t.start_date)}" if t.start_date else "Field set")
        rows.append(
            f"<a class='fh-chstat {t.status.value}' href='{reg.tour_url[t.id]}'>"
            f"{icons.icon(t.sport, 'fh-ic sm')}"
            f"<span class='nm'>{esc(t.group)} {esc(BY_KEY[t.sport].name)}</span>"
            f"<span class='st'>{esc(state)}</span></a>")
    return f"<div class='fh-mod'><h3>{esc(heading)}</h3>{''.join(rows)}</div>"


def record_performance(reg, items, heading="Record performances", limit=3):
    """RecordPerformance — marks, as marks. The number is the point."""
    recs = [i for i in items if i["kind"] in ("school-record", "state-record",
                                              "conf-record")]
    if not recs:
        return ""
    rows = "".join(
        f"<a class='fh-award' href='{item_href(reg, it)}'>"
        f"<span class='lb'>{esc(it['label'])}</span>"
        f"<span class='hd'>{esc(it['headline'])}</span></a>"
        for it in recs[:limit])
    return f"<div class='fh-mod'><h3>{esc(heading)}</h3>{rows}</div>"


def quick_links(links, heading="Athletics information"):
    """QuickLinks — the utility layer, compact. Tickets, forms, contacts."""
    rows = "".join(f"<span class='fh-ql'><b>{esc(k)}</b>{v}</span>"
                   for k, v in links)
    return f"<div class='fh-mod'><h3>{esc(heading)}</h3>{rows}</div>"


def editorial_front(feature, headlines, events, head_more, ev_more,
                    head_title="News & honors", ev_title="Schedule & results"):
    """The first viewport: feature ~48%, headlines ~27%, events ~25%.

    Three simultaneous jobs — what just happened, what is coming, who was
    recognised — visible before a scroll. The page this replaces gave the
    whole width to one feature and a four-item rail, which is why it read as
    empty on any day nobody played.
    """
    return f"""
<div class="fh-front">
  <div class="fh-front-lead">{feature}</div>
  <section class="fh-front-news">
    <h2>{esc(head_title)}</h2>
    {headlines}
    {head_more}
  </section>
  <section class="fh-front-events">
    <h2>{esc(ev_title)}</h2>
    {events}
    {ev_more}
  </section>
</div>"""


def module_row(*mods):
    """The dense band under the ribbon. Empty modules drop out rather than
    printing a heading over nothing."""
    live = [m for m in mods if m]
    return f"<div class='fh-modrow n{min(len(live), 4)}'>{''.join(live)}</div>" if live else ""


def conf_position(reg, sport_key, school):
    """(rank, w, l, size) of `school` inside its conference for one sport."""
    rec = reg.records_for(sport_key)
    conf = reg.conf_of.get(school)
    if not conf or school not in rec:
        return None
    rows = sorted(((s, r) for s, r in rec.items() if reg.conf_of.get(s) == conf),
                  key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], -kv[1]["w"], kv[1]["l"], kv[0]))
    for i, (s, r) in enumerate(rows):
        if s == school:
            return i + 1, r, len(rows)
    return None


def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def org_nav(items):
    return "<nav class='fh-orgnav'>" + "".join(
        f"<a href='{href}'>{esc(label)}</a>" for label, href in items) + "</nav>"


def render_school(reg, s):
    """The school's athletics site, not its database row. Identity first, then
    the lead, the week, the teams, standing in the league, championships, and
    the utility layer — the SIDEARM shape at high-school scale."""
    name = s["name"]
    primary = (s.get("colors") or ["var(--ink)"])[0]
    conf = reg.conf_of.get(name, "")
    conf_html = f"<a href='/conferences/{reg.conf_slug.get(conf,'')}/'>{esc(conf)}</a>" if conf else ""
    contests = sorted(reg.by_school.get(name, []), key=lambda c: c.date or "")
    played = [c for c in reversed(contests) if (c.date or "") <= TODAY]
    upcoming = [c for c in contests if (c.date or "") > TODAY]

    # ---- the school's own editorial layer, newest first ----
    my_items = reg.items_by_school.get(name, [])

    # ---- lead: a story, which is USUALLY NOT A SCORE. A department leads
    #      with a title, a milestone, a signing, a record — and a score only
    #      when nothing bigger happened. The old page always led with the last
    #      final, which is why every school front read the same.
    LEAD_KINDS = ("title", "state-record", "coach-milestone", "school-record",
                  "all-state", "qualified", "hall-of-fame", "signing",
                  "coach-of-year", "athlete-of-week")
    lead_item = min(
        (i for i in my_items if i["kind"] in LEAD_KINDS),
        key=lambda i: (LEAD_KINDS.index(i["kind"]), -int(i["date"].replace("-", ""))),
        default=None)
    lead_c = next((c for c in played if "Championship" in (c.name or "")), None) or \
             (played[0] if played else None)
    lead, lead_photo = "", None
    if lead_item is not None:
        photo = lead_photo = sport_photo(lead_item["sport"], salt=name) \
            if lead_item.get("sport") in BY_KEY else sport_photo("football", salt=name)
        lead = feature_panel(
            f"{esc(lead_item['label'])} · {esc(nice_date(lead_item['date']))}",
            esc(lead_item["headline"]),
            f"{esc(lead_item['dek'])} <a href='{item_href(reg, lead_item)}'>More →</a>",
            s.get("colors") or ["#14294e", "#c8ccd4"],
            watermark=reg.mark(name, 200), photo=photo)
    elif lead_c is not None:
        kicker = f"{BY_KEY[lead_c.sport].name} · {nice_date(lead_c.date)}"
        # a div, not an anchor: the line helpers carry school links, and an
        # anchor inside an anchor splits the markup
        if isinstance(lead_c, Meet):
            hd = esc(lead_c.name)
            dk = meet_line(reg, lead_c).replace(f"{esc(lead_c.name)} — ", "", 1)
            dk = dk[0].upper() + dk[1:] if dk else "Final"
        else:
            hd = score_line(reg, lead_c)
            dk = "Final"
        lead = feature_panel(esc(kicker), hd,
                             f"{dk} · <a href='{reg.url(lead_c)}'>Full result →</a>",
                             s.get("colors") or ["#14294e", "#c8ccd4"],
                             watermark=reg.mark(name, 200),
                             photo=(lead_photo := sport_photo(lead_c.sport, salt=name)))

    recent_rows = [event_card(reg, c, final=True) for c in played[:4]]
    next_rows = [event_card(reg, c, final=False) for c in upcoming[:4]]
    strip = ""
    if recent_rows or next_rows:
        cols = []
        if recent_rows:
            cols.append("<section><h2>Recent</h2><div class='fh-results'>"
                        + "".join(recent_rows)
                        + "</div><p class='fh-more'><a href='#results'>All results →</a></p></section>")
        if next_rows:
            cols.append("<section><h2>Upcoming</h2><div class='fh-results'>"
                        + "".join(next_rows)
                        + "</div><p class='fh-more'><a href='#schedule'>Full schedule →</a></p></section>")
        strip = f"<div class='fh-overview n{len(cols)}'>{''.join(cols)}</div>"

    # ---- teams by season ----
    by_sport = defaultdict(list)
    for c in contests:
        by_sport[c.sport].append(c)
    team_rows = defaultdict(list)
    for key in sorted(s.get("sports", []), key=lambda k: BY_KEY[k].name):
        sp = BY_KEY[key]
        rec = reg.records_for(key).get(name) if sp.shape.value != "meet" else None
        rec_html = f"<span class='tnum'>{_wlt(rec)}</span>" if rec else ""
        team_rows[sp.season].append(
            f"<a class='fh-teamrow' href='#t-{key}'>{icons.icon(key, 'fh-ic sm')}"
            f"<span class='nm'>{esc(sp.name)}</span>{rec_html}</a>")
    seasons = "".join(
        f"<div class='fh-teamseason'><h3>{ssn.title()}</h3>{''.join(team_rows[ssn])}</div>"
        for ssn in ("fall", "winter", "spring") if team_rows.get(ssn))

    # ---- conference standings preview: this school's position per team ----
    standing_rows = []
    for key in sorted(s.get("sports", []), key=lambda k: BY_KEY[k].name):
        sp = BY_KEY[key]
        if sp.shape.value == "meet" or sp.season != "winter":
            continue
        pos = conf_position(reg, key, name)
        if pos:
            rank, r, size = pos
            standing_rows.append(
                f"<a class='fh-teamrow' href='/conferences/{reg.conf_slug.get(conf,'')}/#standings'>"
                f"{icons.icon(key, 'fh-ic sm')}<span class='nm'>{esc(sp.name)}</span>"
                f"<span class='tnum'>{_ordinal(rank)} · {r['cw']}-{r['cl']} conf</span></a>")
    standings_prev = ""
    if standing_rows and conf:
        standings_prev = (f"<div class='fh-section' id='standings'>"
                          f"<div class='fh-group'><h2>{conf_html}</h2></div>"
                          f"<div class='fh-teamgrid'><div class='fh-teamseason'>"
                          f"{''.join(standing_rows)}</div></div></div>")

    # ---- championships this school appeared in ----
    champ_rows = []
    for c in played:
        if "Championship" in (c.name or ""):
            line = meet_line(reg, c) if isinstance(c, Meet) else score_line(reg, c)
            champ_rows.append(score_row(reg.url(c), line,
                                        f"{esc(c.name)} · {esc(nice_date(c.date))}"))
    champs = ""
    if champ_rows:
        champs = (f"<div class='fh-section' id='championships'><div class='fh-group'>"
                  f"<h2>Championships</h2></div><div class='fh-results'>"
                  + "".join(champ_rows[:6]) + "</div></div>")

    # ---- per-team detail: schedule & results ----
    sections = []
    for key in sorted(s.get("sports", []), key=lambda k: (SEASON_ORDER.get(BY_KEY[k].season, 3), BY_KEY[k].name)):
        sp = BY_KEY[key]
        mine = sorted(by_sport.get(key, []), key=lambda c: c.date or "")
        if not mine:
            continue
        rec = reg.records_for(key).get(name)
        rec_html = f" · <span class='tnum'>{rec['w']}-{rec['l']}</span>" if rec else ""
        sections.append(
            f"<div class='fh-section' id='t-{key}'><div class='fh-group'>"
            f"<h3><a href='/sports/{key}/'>{esc(sp.name)}</a></h3>"
            f"<span class='fh-tag'>{esc(sp.season.title())}</span>{rec_html}</div>"
            + contest_table(reg, mine[-14:], show_sport=False) + "</div>")

    # ---- utility layer: deterministic staff/venue from the name hash ----
    h = zlib.crc32(name.encode())
    ad = f"{ATHLETIC_FIRST[h % len(ATHLETIC_FIRST)]} {ATHLETIC_LAST[(h >> 8) % len(ATHLETIC_LAST)]}"
    info = f"""
<div class="fh-section" id="info"><div class="fh-group"><h2>Athletics information</h2></div>
<div class="fh-infogrid">
  <div><h4>Athletic director</h4><span>{esc(ad)}</span></div>
  <div><h4>Home facilities</h4><span>{esc(name)} Gymnasium · {esc(name)} Field</span></div>
  <div><h4>Contact</h4><span>athletics@{esc(s['slug'])}.jhsaa.example</span></div>
  <div><h4>Resources</h4><span>Tickets · Forms · Eligibility · Sportsmanship</span></div>
</div></div>"""
    # `ad` is read by the module row above, which is assembled after this.

    ribbon = season_ribbon(sorted(s.get("sports", [])), link=lambda k: f"#t-{k}")

    # ---- the editorial front: feature, headlines, events, all above the fold
    others = [i for i in my_items if i is not lead_item]
    # the next three fixtures then the last four finals: what is coming and
    # what just happened, in the same column, which is how a reader reads it
    ev = [event_row(reg, c) for c in upcoming[:3]] + \
         [event_row(reg, c) for c in played[:4]]
    feature_grid = editorial_front(
        lead, headline_list(reg, others, 5), "".join(ev[:7]),
        "<p class='fh-more'><a href='#honors'>All honors →</a></p>" if others else "",
        "<p class='fh-more'><a href='#schedule'>Full schedule →</a></p>")

    # ---- the dense band: standing, recognition, postseason, utility
    my_tours = sorted(
        (t for t in reg.tournaments if any(e.school == name for e in t.entrants)),
        key=lambda t: (t.status is not TournamentStatus.IN_PROGRESS, t.final_date or ""))
    st_lines = standing_lines(reg, name, sorted(s.get("sports", [])))
    mods = module_row(
        (f"<div class='fh-mod'><h3>{esc(conf) or 'Standing'}</h3>{st_lines}"
         f"<p class='fh-more'><a href='/conferences/{reg.conf_slug.get(conf,'')}/#standings'>"
         f"League standings →</a></p></div>") if st_lines else "",
        honor_spotlight(reg, others),
        championship_status(reg, my_tours),
        quick_links([("Athletic director", esc(ad)),
                     ("Home facilities", f"{esc(name)} Gymnasium"),
                     ("Contact", f"athletics@{esc(s['slug'])}.jhsaa.example"),
                     ("Resources", "Tickets · Forms · Eligibility")]))

    # ---- the honors section proper, below the fold
    honors_sec = ""
    if others:
        honors_sec = (
            f"<div class='fh-section' id='honors'><div class='fh-group'>"
            f"<h2>Awards &amp; honors</h2></div>"
            + module_row(awards_list(reg, [i for i in others if i["kind"] not in
                                           ("school-record", "state-record")], 5),
                         awards_list(reg, [i for i in others if i["kind"] in
                                           ("all-conference", "all-state",
                                            "scholar-athlete", "academic-team")],
                                     5, heading="Academic & all-league"),
                         record_performance(reg, others),
                         awards_list(reg, [i for i in others if i["kind"] in
                                           ("staff", "hall-of-fame", "signing")],
                                     5, heading="Department & alumni"))
            + "</div>")

    body = f"""
<header class="fh-orghead" style="border-color:{primary}">
  {reg.mark(name, 76)}
  <div class="id">
    <div class="name">{esc(name)} <span class="ath">Athletics</span></div>
    <div class="nick" style="color:{primary}">{esc(s['mascot'])}</div>
    <div class="meta">{esc(s['city'])} · {conf_html} · {class_chip(s['classification'])}</div>
  </div>
</header>
{org_nav([("Home", "#"), ("Teams", "#teams"), ("Schedule", "#schedule"),
          ("Results", "#results"), ("Honors", "#honors"),
          ("Championships", "#championships" if champs else "#schedule"),
          ("Athletics Info", "#info")])}
{feature_grid}
{mods}
{ribbon}
<div id="results"></div>
{strip}
{honors_sec}
<div class="fh-section" id="teams"><div class="fh-group"><h2>Teams</h2></div>
<div class="fh-teamgrid">{seasons}</div></div>
{standings_prev}
{champs}
<div id="schedule"></div>
{''.join(sections)}
{info}
{SEASON_JS}
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/schools/'>Schools</a> › {esc(name)}"
    # THE CARD IS THE PANEL'S PHOTOGRAPH, not a second derivation of it. These
    # picked their lead independently — the panel prefers an editorial item and
    # the card preferred the last result — so a school leading on a lacrosse
    # honour pasted as a baseball card.
    card = lead_photo or sport_photo(
        (sorted(s.get("sports", ())) or ["football"])[0], salt=name)
    return shell(page_title(f"{name} Athletics"), body, crumb, "← Schools|/schools/", org=True,
                 desc=(f"{name} {s['mascot']} athletics — {s['city']}, "
                       f"{s['classification']}{f', {conf}' if conf else ''}. Schedules, "
                       f"results, standings and championship history across "
                       f"{len(s.get('sports', ()))} sports."),
                 image=card[0])


def render_conference(reg, conf):
    """The conference's own site, not a schedule table with a heading: who we
    are, who our members are, the standings race, the composite week, recent
    results, champions — the MAAC shape at league scale."""
    import datetime as _dt
    members = sorted(conf["members"])
    mset = set(members)
    today = _dt.date.fromisoformat(TODAY)

    # ---- member strip: marks first — the league IS its schools ----
    strip = "".join(
        f"<a class='fh-member' href='{reg.school_url(m)}'>{reg.mark(m, 44)}"
        f"<span>{esc(m)}</span></a>"
        for m in members if m in reg.schools)

    # ---- sports the members sponsor ----
    conf_sports = sorted({k for m in members if m in reg.schools
                          for k in reg.schools[m].get("sports", [])})
    ribbon = season_ribbon(conf_sports)

    # ---- standings, one sport at a time ----
    def conf_table(key, limit=4):
        rec = reg.records_for(key)
        rows = sorted(((s, r) for s, r in rec.items() if s in mset),
                      key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], -kv[1]["w"], kv[1]["l"], kv[0]))[:limit]
        if not rows:
            return ""
        cols = "26px 24px minmax(150px,1fr) 62px 62px"
        body = "".join(
            f"<div class='fh-row{' first' if i == 0 else ''}' style='--grid-cols:{cols}'>"
            f"<span class='fh-rank'>{i+1}</span>{reg.crest(s,'xs')}"
            f"<span class='fh-name'>{reg.school_link(s)}</span>"
            f"<span class='fh-num tnum'>{r['cw']}-{r['cl']}</span>"
            f"<span class='fh-num tnum fh-dim'>{_wlt(r)}</span></div>"
            for i, (s, r) in enumerate(rows))
        return (f"<div class='fh-tablescroll'><div class='fh-table' style='--grid-cols:{cols}'>"
                "<div class='fh-thead'><span class='fh-th'></span><span class='fh-th'></span>"
                "<span class='fh-th'>School</span><span class='fh-th'>Conf</span>"
                f"<span class='fh-th'>Overall</span></div>{body}</div></div>")

    standing_sports = []
    for sp in sorted(CATALOG, key=lambda s: s.name):
        if sp.shape.value == "meet" or sp.key not in conf_sports:
            continue
        tbl = conf_table(sp.key)
        if tbl:
            standing_sports.append((sp, tbl))
    default_key = next((k for k, _ in [(sp.key, 0) for sp, _ in standing_sports]
                        if k in ("boys-basketball", "girls-basketball")),
                       standing_sports[0][0].key if standing_sports else None)
    standings = ""
    if standing_sports:
        opts = "".join(
            f"<option value='{sp.key}'{' selected' if sp.key == default_key else ''}>"
            f"{esc(sp.name)}</option>" for sp, _ in standing_sports)
        tables = "".join(
            f"<div data-conf-standings='{sp.key}'{'' if sp.key == default_key else ' hidden'}>"
            f"{tbl}<p class='fh-more'><a href='/sports/{sp.key}/standings/'>"
            f"Full standings →</a></p></div>"
            for sp, tbl in standing_sports)
        standings = f"""
<div class="fh-section" id="standings"><div class="fh-group"><h2>Standings</h2>
<select class="fh-select" id="conf-standings-pick">{opts}</select></div>
{tables}</div>
<script>
(function () {{
  var pick = document.getElementById("conf-standings-pick");
  if (!pick) return;
  pick.addEventListener("change", function () {{
    document.querySelectorAll("[data-conf-standings]").forEach(function (d) {{
      d.hidden = d.dataset.confStandings !== pick.value;
    }});
  }});
}})();
</script>"""

    # ---- the league's newsroom: its own honors plus its members' ----
    conf_items = reg.items_by_conf.get(conf["name"], [])

    # ---- lead: the league's biggest story. A conference publishes about
    #      champions, players of the year and its own tournaments; the
    #      standings race is the fallback, not the default.
    LEAD_KINDS = ("conf-champion", "conf-player-of-year", "conf-tournament",
                  "conf-record", "conf-coach-of-year", "conf-team-of-week",
                  "conf-athlete-of-week", "conf-all-conference")
    lead_item = min(
        (i for i in conf_items if i["kind"] in LEAD_KINDS),
        key=lambda i: (LEAD_KINDS.index(i["kind"]), -int(i["date"].replace("-", ""))),
        default=None)
    lead = ""
    if lead_item is not None:
        lead = feature_panel(
            f"{esc(lead_item['label'])} · {esc(nice_date(lead_item['date']))}",
            esc(lead_item["headline"]),
            f"{esc(lead_item['dek'])} <a href='{item_href(reg, lead_item)}'>More →</a>",
            marks.conf_colors(conf["name"]),
            watermark=marks.conf_mark(conf["name"], 200),
            photo=sport_photo(lead_item.get("sport") or default_key or "football",
                              salt=conf["name"]))
    elif default_key:
        rec = reg.records_for(default_key)
        rows = sorted(((s, r) for s, r in rec.items() if s in mset),
                      key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], kv[0]))
        if len(rows) >= 2:
            (s1, r1), (s2, r2) = rows[0], rows[1]
            sp = BY_KEY[default_key]
            lead = feature_panel(
                f"{esc(sp.name)} · Standings race",
                f"{reg.school_link(s1)} leads at <span class='tnum'>{r1['cw']}-{r1['cl']}</span>",
                f"{reg.school_link(s2)} sits second at {r2['cw']}-{r2['cl']} "
                f"in {esc(conf['name'])} play · <a href='#standings'>Standings →</a>",
                marks.conf_colors(conf["name"]),
                watermark=marks.conf_mark(conf["name"], 200),
                photo=sport_photo(default_key, salt=conf["name"]))

    # ---- composite week, grouped by day ----
    week = sorted((c for c in reg.contests if c.date and
                   0 <= (_dt.date.fromisoformat(c.date) - today).days <= 6 and
                   any(sch in mset for sch in reg.contest_schools(c))),
                  key=lambda c: (c.date, BY_KEY[c.sport].name))
    by_day = {}
    for c in week:
        by_day.setdefault(c.date, []).append(c)
    day_blocks = []
    shown = 0
    for d in sorted(by_day):
        if shown >= 12:
            break
        label = "Today" if d == TODAY else _dt.date.fromisoformat(d).strftime("%A")
        rows = []
        for c in by_day[d][: 12 - shown]:
            rows.append(score_row(reg.url(c), matchup_line(reg, c, with_date=False),
                                  esc(BY_KEY[c.sport].name)))
            shown += 1
        day_blocks.append(f"<h3 class='fh-dayhead sm'>{esc(label)}</h3>"
                          f"<div class='fh-results'>{''.join(rows)}</div>")
    this_week = ""
    if day_blocks:
        this_week = (f"<div class='fh-section' id='schedule'><div class='fh-group'>"
                     f"<h2>This week</h2></div>{''.join(day_blocks)}"
                     f"<p class='fh-more'><a href='/scoreboard/'>Full schedule →</a></p></div>")

    # ---- recent results, separate from what's coming ----
    finals = sorted((c for c in reg.contests if c.date and
                     0 <= (today - _dt.date.fromisoformat(c.date)).days <= 6 and
                     (c.date or "") <= TODAY and
                     any(sch in mset for sch in reg.contest_schools(c))),
                    key=lambda c: c.date, reverse=True)
    result_rows = [event_card(reg, c, final=True) for c in finals[:6]]
    recent = ""
    if result_rows:
        recent = (f"<div class='fh-section' id='results'><div class='fh-group'>"
                  f"<h2>Recent results</h2></div><div class='fh-cardrow'>"
                  + "".join(result_rows) + "</div></div>")

    # ---- fall champions: the completed season's league winners ----
    champ_rows = []
    for sp in sorted(CATALOG, key=lambda s: s.name):
        if sp.season != "fall" or sp.shape.value == "meet" or sp.key not in conf_sports:
            continue
        rec = reg.records_for(sp.key)
        rows = sorted(((s, r) for s, r in rec.items() if s in mset),
                      key=lambda kv: (-kv[1]["cw"], kv[1]["cl"], kv[0]))
        if rows and rows[0][1]["cw"] > 0:
            s0, r0 = rows[0]
            champ_rows.append(
                f"<a class='fh-teamrow' href='/sports/{sp.key}/'>"
                f"{icons.icon(sp.key, 'fh-ic sm')}<span class='nm'>{esc(sp.name)}</span>"
                f"{reg.crest(s0,'xs')}<span>{esc(s0)}</span>"
                f"<span class='tnum'>{r0['cw']}-{r0['cl']}</span></a>")
    champs = ""
    if champ_rows:
        champs = (f"<div class='fh-section' id='championships'><div class='fh-group'>"
                  f"<h2>Fall champions</h2></div><div class='fh-teamgrid'>"
                  f"<div class='fh-teamseason'>{''.join(champ_rows)}</div></div></div>")

    cc1, _cc2 = marks.conf_colors(conf["name"])

    # ---- the editorial front: league story, league newsroom, composite week
    others = [i for i in conf_items if i is not lead_item]
    composite = [event_row(reg, c) for c in week[:4]] + \
                [event_row(reg, c) for c in finals[:4]]
    feature_grid = editorial_front(
        lead, headline_list(reg, others, 6, show_school=True),
        "".join(composite[:7]),
        "<p class='fh-more'><a href='#honors'>All league honors →</a></p>" if others else "",
        "<p class='fh-more'><a href='#schedule'>Composite schedule →</a></p>",
        head_title="League news & honors", ev_title="Composite schedule")

    # ---- the dense band: the race, this week's honoree, the postseason,
    #      and what the league has handed out lately
    conf_tours = sorted(
        (t for t in reg.tournaments
         if any(e.school in mset for e in t.entrants)),
        key=lambda t: (t.status is not TournamentStatus.IN_PROGRESS, t.final_date or ""))
    weekly = [i for i in conf_items
              if i["kind"] in ("conf-athlete-of-week", "conf-team-of-week")]
    admin = [i for i in conf_items
             if i["kind"] in ("conf-all-academic", "conf-sportsmanship",
                              "conf-announcement", "conf-record")]
    mods = module_row(
        standings_preview(reg, default_key, mset, 5,
                          heading=f"{BY_KEY[default_key].name} race") if default_key else "",
        honor_spotlight(reg, weekly or others),
        championship_status(reg, conf_tours, heading="Championships"),
        awards_list(reg, admin, 4, heading="League business"))

    honors_sec = ""
    if others:
        honors_sec = (
            f"<div class='fh-section' id='honors'><div class='fh-group'>"
            f"<h2>Honors &amp; recognition</h2></div>"
            + module_row(
                awards_list(reg, [i for i in others if i["kind"] in
                                  ("conf-player-of-year", "conf-newcomer",
                                   "conf-athlete-of-week", "all-state")],
                            5, heading="Athletes", show_school=True),
                awards_list(reg, [i for i in others if i["kind"] in
                                  ("conf-all-conference", "all-conference")],
                            5, heading="All-conference", show_school=True),
                awards_list(reg, [i for i in others if i["kind"] in
                                  ("conf-all-academic", "scholar-athlete",
                                   "academic-team")],
                            5, heading="Academic", show_school=True),
                awards_list(reg, [i for i in others if i["kind"] in
                                  ("coach-of-year", "coach-milestone",
                                   "conf-sportsmanship")],
                            5, heading="Coaches & sportsmanship", show_school=True))
            + "</div>")

    body = f"""
<header class="fh-orghead" style="border-color:{cc1}">
  {marks.conf_mark(conf['name'], 64)}
  <div class="id">
    <div class="name">{esc(conf['name'])}</div>
    <div class="meta">{esc(conf['area'])}</div>
  </div>
</header>
{org_nav([("Home", "#"), ("Schools", "#schools"), ("Standings", "#standings"),
          ("Schedule", "#schedule"), ("Honors", "#honors"),
          ("Championships", "#championships" if champs else "#standings")])}
<div class="fh-memberstrip tight" id="schools">{strip}</div>
{feature_grid}
{mods}
{ribbon}
{honors_sec}
{standings}
{this_week}
{recent}
{champs}
{SEASON_JS}
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/#conferences'>Conferences</a> › {esc(conf['name'])}"
    return shell(page_title(f"{conf['name']}"), body, crumb, "← Conferences|/#conferences", org=True,
                 desc=(f"{conf['name']} — {len(members)} member schools in "
                       f"{conf['area']}. Standings, the composite schedule, league "
                       f"champions and results across {len(conf_sports)} sports."),
                 image=sport_photo(default_key or "football", salt=conf["name"])[0])


def render_athlete(reg, a):
    name, school = a["name"], a["school"]
    by_sport = defaultdict(list)
    for row in a["rows"]:
        by_sport[row[0].sport].append(row)
    sections = []
    for key in sorted(by_sport, key=lambda k: (SEASON_ORDER.get(BY_KEY[k].season, 3), k)):
        sp = BY_KEY[key]
        rows = []
        for (c, ev_or_line, e) in sorted(by_sport[key], key=lambda r: r[0].date or ""):
            if isinstance(c, Meet):
                mark = esc(e.mark.raw) if e and e.mark and e.mark.raw else ""
                rows.append(
                    f"<div class='fh-row{' first' if e and e.place == 1 else ''}' "
                    f"style='--grid-cols:86px minmax(150px,1.4fr) minmax(110px,1fr) 34px 80px'>"
                    f"<span class='fh-dim tnum'>{esc(nice_date(c.date))}</span>"
                    f"<span class='fh-name'><a href='{reg.url(c)}'>{esc(c.name)}</a></span>"
                    f"<span class='fh-plain fh-dim'>{esc(ev_or_line.name)}</span>"
                    f"<span class='fh-rank'>{e.place if e else ''}</span>"
                    f"<span class='fh-mark'>{mark}</span></div>")
            else:
                line = ev_or_line
                on_home = any(p.name == name for p in line.home)
                won = line.winner != "draw" and (line.winner == "home") == on_home
                opp = c.away if on_home else c.home
                rows.append(
                    f"<div class='fh-row' style='--grid-cols:86px minmax(150px,1.4fr) minmax(110px,1fr) 34px 80px'>"
                    f"<span class='fh-dim tnum'>{esc(nice_date(c.date))}</span>"
                    f"<span class='fh-name'><a href='{reg.url(c)}'>vs {esc(opp)}</a></span>"
                    f"<span class='fh-plain fh-dim'>{esc(str(line.kind).title())} {line.slot if line.kind in ('singles','doubles') else ''}</span>"
                    f"<span class='fh-rank'>{'W' if won else 'L'}</span>"
                    f"<span class='fh-mark'>{esc(line.score or '')}</span></div>")
        sections.append(
            f"<div class='fh-section'><div class='fh-group'><h3><a href='/sports/{key}/'>{esc(sp.name)}</a></h3></div>"
            "<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:86px minmax(150px,1.4fr) minmax(110px,1fr) 34px 80px'>"
            "<div class='fh-thead'><span class='fh-th'>Date</span><span class='fh-th'>Contest</span>"
            "<span class='fh-th'>Event</span><span class='fh-th'>Pl</span><span class='fh-th'>Mark</span></div>"
            f"{''.join(rows)}</div></div></div>")
    yr = CLASS_LABEL.get(a.get("year") or "", a.get("year") or "")
    body = f"""
<div class="fh-idhdr">
  <span class="fh-crest lg {crest_class(school)}">{esc(monogram(school))}</span>
  <div><div class="name">{esc(name)}</div>
  <div class="meta">{reg.school_link(school)}{(' · ' + esc(yr)) if yr else ''}</div></div>
  <div class="side">{class_chip(reg.schools[school]['classification'])}</div>
</div>
{''.join(sections)}
"""
    crumb = f"<a href='/'>{NAME}</a> › {reg.school_link(school)} › {esc(name)}"
    return shell(f"{name} — {school}", body, crumb, f"← {school}|{reg.school_url(school)}",
                 desc=(f"{name}, {school} — every result, mark and box-score line "
                       f"this season, with the contest each came from."))


def _first(reg, used, kind, pred, note):
    """The first contest of `kind` matching `pred` that the tour has not used."""
    for c in reg.contests:
        if isinstance(c, kind) and pred(c) and reg.url(c) not in used:
            used.add(reg.url(c))
            extra = f"{len(c.events)} events · " if isinstance(c, Meet) else ""
            return (reg.url(c), c.name, extra + note)
    return None


def render_tour(reg):
    """`/tour/` — one live link to every page type the site can produce.

    A build of 50,000 pages hides its own range. Every capability here is real
    and reachable, but "reachable" is not the same as findable: a box score
    exists on a quarter of games, a bye only appears in brackets with an odd
    field, and a needs-review import is one record in thirty thousand. Without
    an index you learn what the product does by hunting for it.

    Every link is RESOLVED FROM THE RECORDS at build time, not hard-coded, so
    the page cannot rot into a list of 404s the next time the state is
    regenerated. If a category has no example, it says so instead of linking
    nowhere — which is itself the useful signal.
    """
    from app.shapes import TournamentFormat as TF, TournamentStatus as TS

    # Each row should send you somewhere you have not already been: several
    # predicates legitimately match the same record (the smallest bracket is
    # often also the first upcoming one), and two rows pointing at one page
    # spends a line of the index proving nothing.
    used: set[str] = set()

    def game_where(pred, note=""):
        for c in reg.contests:
            if isinstance(c, Game) and pred(c) and reg.url(c) not in used:
                used.add(reg.url(c))
                return (reg.url(c), f"{c.away} {c.away_score}–{c.home_score} {c.home}", note)
        return None

    def tour_of(pred):
        for t in reg.tournaments:
            href = reg.tour_url[t.id]
            if pred(t) and href not in used:
                used.add(href)
                return (href, t.name, "")
        return None

    def has_box(c, family=None):
        if not getattr(c, "box", None):
            return False
        return family is None or c.sport == family

    imported = lambda c: c.provenance and c.provenance.adapter in (  # noqa: E731
        "scorebook_csv", "dual_card", "hytek_swim", "hytek_pdf")

    school = reg.schools.get("Ashbrook") or next(iter(reg.schools.values()))
    conf_slug = next(iter(sorted(reg.confs)))
    athlete = next((a for a in reg.athletes.values() if len(a["rows"]) > 3),
                   next(iter(reg.athletes.values()), None))

    SECTIONS = [
        ("Results", [
            ("Game with a box score", game_where(
                lambda c: has_box(c, "boys-basketball"),
                "period scoring, full player box, team totals")),
            ("Football — four stat tables", game_where(
                lambda c: has_box(c, "football"),
                "passing, rushing, receiving, defense: different columns each")),
            ("Hockey — skaters and goaltending", game_where(
                lambda c: has_box(c, "boys-ice-hockey"),
                "two tables, the second all rate stats")),
            ("Baseball — batting and pitching", game_where(
                lambda c: has_box(c, "baseball"), "two tables")),
            ("Volleyball — sets, not points", game_where(
                lambda c: has_box(c, "girls-volleyball"),
                "the final is sets won; the linescore is points")),
            ("Dual match", _first(
                reg, used, Dual, lambda c: bool(c.lines) and not imported(c),
                "line-by-line, singles and doubles")),
            ("Meet", _first(
                reg, used, Meet, lambda c: len(c.events) > 8 and not imported(c),
                "a full event card")),
        ]),
        # The formats added to find where the three shapes stop bending. Each
        # row is a thing the model could not express before it was asked to.
        ("Formats the shapes had to stretch for", [
            ("Chess — a DRAWN board", _first(
                reg, used, Dual,
                lambda c: c.sport == "chess" and any(l.winner == "draw" for l in c.lines),
                "a line with no winner: the point splits, 2.5-2.5 is ordinary")),
            ("Cricket — two innings", game_where(
                lambda c: has_box(c, "cricket"),
                "batting and bowling cards belonging to opposite sides, and a "
                "result sentence: runs if defended, wickets if chased")),
            ("Rugby sevens", game_where(
                lambda c: has_box(c, "boys-rugby") or has_box(c, "girls-rugby"),
                "tries, conversions and penalties that sum to the scoreline")),
            ("Badminton — one co-ed squad", _first(
                reg, used, Dual, lambda c: c.sport == "badminton",
                "five lines off eight players: boys, girls, two mixed, one singles")),
            ("Squash — a five-line ladder", _first(
                reg, used, Dual, lambda c: c.sport == "squash",
                "singles 1 through 5 in strength order; an odd card cannot tie")),
        ]),
        ("Ingestion", [
            ("Imported box score", game_where(
                lambda c: imported(c) and getattr(c, "box", None),
                "scorebook CSV — see the Source block at the foot")),
            ("Imported dual", _first(reg, used, Dual, imported,
                                     "fixed-width match card")),
            ("Imported Hy-Tek meet", _first(reg, used, Meet, imported,
                                            "MEET MANAGER text report, with splits")),
        ]),
        ("Postseason", [
            ("Championships hub", ("/championships/", "All championships",
                                   "sport, then classification")),
            ("Completed bracket", tour_of(
                lambda t: t.status is TS.COMPLETE and t.format is TF.BRACKET
                and t.size >= 16)),
            ("In-progress bracket", tour_of(lambda t: t.status is TS.IN_PROGRESS)),
            ("Upcoming bracket", tour_of(lambda t: t.status is TS.UPCOMING
                                         and t.format is TF.BRACKET)),
            ("Bracket with byes", tour_of(
                lambda t: t.format is TF.BRACKET and t.byes and t.size >= 24)),
            ("Smallest bracket", tour_of(
                lambda t: t.format is TF.BRACKET and t.size == 4)),
            ("Title decided by a meet", tour_of(
                lambda t: t.format is TF.MEET and t.meet_key)),
            ("Title decided by a SWISS", tour_of(lambda t: t.format is TF.SWISS)),
        ]),
        ("Organisations", [
            ("School athletics site", (f"/schools/{school['slug']}/",
                                       f"{school['name']} Athletics",
                                       "school masthead; JHSAA collapses to a link-back")),
            ("Conference site", (f"/conferences/{conf_slug}/",
                                 reg.confs[conf_slug]["name"], "same treatment")),
            ("Athlete", (f"/athletes/{athlete['slug']}/", athlete["name"],
                         "results across the season") if athlete else None),
            ("Sport hub", ("/sports/boys-basketball/", "Basketball",
                           "paired sport: the nav lists it once, the page "
                           "carries the Boys / Girls switch")),
            ("Standings", ("/sports/boys-basketball/standings/", "League tables", "")),
            ("Scoreboard", ("/scoreboard/", "Every result, filterable", "")),
        ]),
    ]

    blocks = []
    for title, rows in SECTIONS:
        items = []
        for label, found in rows:
            if not found:
                items.append(f"<div class='fh-tourrow none'><span class='lb'>{esc(label)}</span>"
                             f"<span class='ex'>no example in the current state</span></div>")
                continue
            href, what, note = found
            items.append(
                f"<a class='fh-tourrow' href='{href}'>"
                f"<span class='lb'>{esc(label)}</span>"
                f"<span class='ex'>{esc(what)}</span>"
                f"<span class='nt'>{esc(note)}</span></a>")
        blocks.append(f"<section class='fh-toursec'><h2>{esc(title)}</h2>"
                      f"{''.join(items)}</section>")

    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">Product tour</div></div>
  <div class="side"></div>
</div>
{''.join(blocks)}
"""
    crumb = f"<a href='/'>{NAME}</a> › Tour"
    return shell(page_title("Product tour"), body, crumb)


def render_scoreboard(reg):
    """The week, day by day. A row reads matchup-first — the matchup and the
    result are the news; sport and status are the caption under them."""
    import datetime as dt
    t = dt.date.fromisoformat(TODAY)
    lo, hi = (t - dt.timedelta(days=6)).isoformat(), (t + dt.timedelta(days=6)).isoformat()
    window = [c for c in reg.contests if c.date and lo <= c.date <= hi]
    by_sport = defaultdict(list)
    for c in window:
        by_sport[c.sport].append(c)
    sport_vals = [(k, esc(BY_KEY[k].name)) for k in
                  sorted(by_sport, key=lambda k: BY_KEY[k].name)]
    bar = facet_bar("sb", [
        ("sport", "Sport", sport_vals),
        ("division", "Classification", [(v, class_chip(v)) for v in CLASSES]),
        ("status", "Status", [("final", "Final"), ("upcoming", "Upcoming"),
                              ("changed", "Postponed / cancelled")]),
    ])
    by_day = defaultdict(list)
    for c in window:
        by_day[c.date].append(c)
    days = []
    for day in sorted(by_day):
        rows = []
        for c in sorted(by_day[day], key=lambda c: (BY_KEY[c.sport].name, c.name)):
            divs, status = contest_facets(reg, c)
            line = meet_line(reg, c) if isinstance(c, Meet) else score_line(reg, c)
            if not line:
                line = matchup_line(reg, c, with_date=False)
            tag = {"final": "Final", "upcoming": "", "changed": "Postponed"}.get(status, "")
            sub = " · ".join(x for x in (BY_KEY[c.sport].name, tag) if x)
            rows.append(
                f"<div class='fh-scoreline' data-f-sport='{esc(c.sport)}'"
                f" data-f-division='{esc(divs)}' data-f-status='{status}'>"
                f"<a class='m' href='{reg.url(c)}'></a>"
                f"<span class='who'>{line}</span><span class='sub'>{esc(sub)}</span></div>")
        long_day = dt.date.fromisoformat(day).strftime("%A, %B %-d")
        days.append(f"<div class='fh-day' data-f-day='{esc(day)}'>"
                    f"<h2 class='fh-dayhead'>{esc(long_day)}</h2>{''.join(rows)}</div>")
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">Scoreboard</div>
  <div class="meta">This week across Jefferson</div></div>
  <div class="side"></div>
</div>
{bar}
<div class="fh-filterable fh-scoredays" id="sb">{''.join(days)}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › Scoreboard"
    return shell(page_title(f"Scoreboard"), body, crumb,
                 desc=("Every JHSAA result and fixture, all 50 activities on one "
                       "board — filter by sport, classification, conference and day."))


def champ_finals(reg):
    out = []
    for c in reg.contests:
        if isinstance(c, Game) and "Championship" in c.name and c.status == "final":
            grp = c.name.split("JHSAA ")[1].split(" Championship")[0] if "JHSAA " in c.name else ""
            out.append((BY_KEY[c.sport], grp, c))
        elif isinstance(c, Meet) and "Championships" in c.name and c.team_scores:
            grp = ""
            if "JHSAA " in c.name:
                grp = c.name.split("JHSAA ")[1].split(f" {BY_KEY[c.sport].name}")[0]
            out.append((BY_KEY[c.sport], grp, c))
    return out


def grp_chip(grp):
    if grp and grp[0].isdigit():
        return class_chip(grp)
    return f"<span class='fh-tag'>{esc(grp or 'Open')}</span>"


def _seed_chip(n):
    return f"<span class='sd'>{n}</span>" if n else "<span class='sd'></span>"


def bracket_side(reg, school, seed, score, won, decided):
    """One team's row inside a bracket card."""
    if not school:
        return ("<span class='tm tbd'><span class='sd'></span>"
                "<span class='nm'>TBD</span><span class='sc'></span></span>")
    cls = "tm" + (" won" if decided and won else "") + (" out" if decided and not won else "")
    return (f"<span class='{cls}'>{_seed_chip(seed)}{reg.crest(school,'xs')}"
            f"<span class='nm'>{esc(school)}</span>"
            f"<span class='sc tnum'>{'' if score is None else score}</span></span>")


def bracket_card(reg, m, final=False):
    """A matchup as a card. Clicking it opens the contest record.

    A bye is drawn as the team advancing on its own — no opponent row, because
    there was no opponent. Inventing one would put a school that does not exist
    into a page that links schools.
    """
    if m.bye:
        return (f"<div class='fh-brk-card bye' style='--y:{m._y:.0f}px'>"
                f"{bracket_side(reg, m.home, m.home_seed, None, True, False)}"
                f"<span class='mt'>Bye</span></div>")

    decided = m.decided
    top = bracket_side(reg, m.home, m.home_seed, m.home_score, m.winner == m.home, decided)
    bot = bracket_side(reg, m.away, m.away_seed, m.away_score, m.winner == m.away, decided)

    if decided:
        meta = "Final"
    elif m.ready:
        meta = " · ".join(x for x in (nice_date(m.date), m.time) if x)
    else:
        meta = nice_date(m.date) if m.date else "TBD"

    href = reg.contest_href(m.contest_key)
    cls = "fh-brk-card" + (" final" if final else "")
    inner = f"{top}{bot}<span class='mt'>{esc(meta)}</span>"
    if href:
        return f"<a class='{cls}' href='{href}' style='--y:{m._y:.0f}px'>{inner}</a>"
    return f"<div class='{cls}' style='--y:{m._y:.0f}px'>{inner}</div>"


def render_bracket(reg, t):
    """The elimination tree, positioned server-side.

    Cards and the SVG elbows are placed from ONE layout pass in
    ``app.postseason``, so they cannot drift apart. Desktop scrolls the canvas
    horizontally when the tree is wider than the viewport; below the breakpoint
    the columns become a round-at-a-time list driven by the radio tabs, because
    a 32-team tree has no honest small-screen layout as a tree.
    """
    canvas = postseason.layout(t)
    if canvas is None:
        return ""

    # Hand each matchup its y so the card markup stays a pure function of it.
    for card in canvas.cards:
        card.matchup._y = card.y

    last = len(canvas.columns) - 1
    # The radios are siblings of BOTH the tab strip and the canvas, not children
    # of the tab strip: `#brkr0:checked ~ .fh-brk-scroll .c0` only reaches a
    # later sibling, so nesting them inside the strip leaves every column hidden
    # on mobile with the tabs still rendering — a bracket page with no bracket.
    radios, tabs, cols = [], [], []
    for col in canvas.columns:
        checked = " checked" if col.index == 0 else ""
        radios.append(
            f"<input type='radio' name='brkr' id='brkr{col.index}'{checked}>")
        tabs.append(f"<label for='brkr{col.index}'>{esc(col.name)}</label>")
        cards = "".join(
            bracket_card(reg, c.matchup, final=(col.index == last))
            for c in canvas.cards if c.col == col.index)
        cols.append(
            f"<div class='fh-brk-col c{col.index}' style='--x:{col.x:.0f}px'>"
            f"<div class='fh-brk-hd'>{esc(col.name)}</div>{cards}</div>")

    paths = "".join(
        f"<path d='{l.d}' class='lk{' on' if l.live else ''}'/>" for l in canvas.links)
    svg = (f"<svg class='fh-brk-links' width='{canvas.width:.0f}' "
           f"height='{canvas.height:.0f}' viewBox='0 0 {canvas.width:.0f} "
           f"{canvas.height:.0f}' aria-hidden='true'>{paths}</svg>")

    return (f"<div class='fh-brk' style='--bw:{canvas.width:.0f}px;"
            f"--bh:{canvas.height:.0f}px;--cw:{canvas.card_w}px;--ch:{canvas.card_h}px'>"
            f"{''.join(radios)}"
            f"<div class='fh-brk-tabs'>{''.join(tabs)}</div>"
            f"<div class='fh-brk-scroll'><div class='fh-brk-canvas'>{svg}"
            f"{''.join(cols)}</div></div></div>")


def render_qualifiers(reg, t):
    """The field, as the committee set it."""
    if not t.entrants:
        return ""
    rows = "".join(
        f"<div class='fh-row' style='--grid-cols:34px minmax(150px,1fr) 90px 110px'>"
        f"<span class='fh-rank'>{e.seed or ''}</span>"
        f"<span class='fh-name'>{reg.crest(e.school,'xs')} {reg.school_link(e.school)}</span>"
        f"<span class='fh-num tnum'>{esc(e.record or '')}</span>"
        f"<span class='fh-dim'>{esc(e.qualifier or '')}</span></div>"
        for e in sorted(t.entrants, key=lambda e: e.seed or 99))
    return (f"<div class='fh-section' id='qualifiers'><h2>Qualifiers</h2>"
            "<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:34px minmax(150px,1fr) 90px 110px'>"
            "<div class='fh-thead'><span class='fh-th'>Seed</span>"
            "<span class='fh-th'>School</span><span class='fh-th'>Record</span>"
            f"<span class='fh-th'>Qualified</span></div>{rows}</div></div></div>")


def render_champ_schedule(reg, t):
    """Every matchup by round — the same records the bracket draws, as a list.
    A bracket is a picture; this is the part you can scan on a phone."""
    blocks = []
    for r in t.rounds:
        rows = []
        for m in r.matchups:
            if m.bye:
                rows.append(score_row("", f"{reg.school_link(m.home)} — bye", "No contest"))
                continue
            if not m.ready:
                continue
            href = reg.contest_href(m.contest_key) or ""
            if m.decided:
                who = (f"{reg.crest(m.away,'xs')} {reg.school_link(m.away)} "
                       f"<b class='tnum'>{m.away_score}</b> at "
                       f"{reg.crest(m.home,'xs')} {reg.school_link(m.home)} "
                       f"<b class='tnum'>{m.home_score}</b>")
                when = "Final"
            else:
                who = (f"{reg.crest(m.away,'xs')} {reg.school_link(m.away)} at "
                       f"{reg.crest(m.home,'xs')} {reg.school_link(m.home)}")
                when = " · ".join(x for x in (nice_date(m.date), m.time) if x)
            rows.append(score_row(href, who, esc(when)))
        if rows:
            blocks.append(f"<h4 class='fh-rndhd'>{esc(r.name)}</h4>"
                          f"<div class='fh-results'>{''.join(rows)}</div>")
    if not blocks:
        return ""
    return (f"<div class='fh-section' id='schedule'><h2>Schedule &amp; results</h2>"
            f"{''.join(blocks)}</div>")


def champ_state_chip(t):
    label = {
        TournamentStatus.COMPLETE: "Complete",
        TournamentStatus.IN_PROGRESS: postseason.live_label(t) or "In progress",
        TournamentStatus.UPCOMING: "Upcoming",
    }[t.status]
    return f"<span class='fh-state {t.status.value}'>{esc(label)}</span>"


def render_tournament(reg, t):
    """One championship: the tournament IS the page, not a game with a label."""
    sp = BY_KEY[t.sport]
    champ = ""
    if t.champion:
        champ = (f"<div class='fh-champbanner'>{reg.crest(t.champion,'lg')}"
                 f"<div><span class='kk'>{esc(t.group)} State Champions</span>"
                 f"<span class='hd'>{reg.school_link(t.champion)}</span>"
                 + (f"<span class='dk'>def. {reg.school_link(t.runner_up)} "
                    f"{max(t.final.home_score or 0, t.final.away_score or 0)}–"
                    f"{min(t.final.home_score or 0, t.final.away_score or 0)}</span>"
                    if t.runner_up and t.final and t.final.home_score is not None else "")
                 + "</div></div>")

    facts = []
    if t.final_date:
        facts.append(("Championship", nice_date(t.final_date)))
    if t.final_venue:
        facts.append(("Site", t.final_venue))
    if t.format is TournamentFormat.BRACKET and t.entrants:
        byes = f" · {t.byes} byes" if t.byes else ""
        facts.append(("Field", f"{t.size} teams{byes}"))
    if t.format is TournamentFormat.SWISS and t.entrants:
        facts.append(("Field", f"{t.size} teams · {len(t.rounds)} rounds"))
    if t.start_date and t.format in (TournamentFormat.BRACKET, TournamentFormat.SWISS):
        facts.append(("Opens", nice_date(t.start_date)))
    info = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(str(v))}</dd></div>" for k, v in facts)

    # A SWISS is standings first, then the rounds that produced them. There is
    # no tree to draw: nobody is eliminated, every school plays every round,
    # and the title is the top of the table rather than the winner of a final.
    if t.format is TournamentFormat.SWISS:
        rows = t.standings()
        played = sum(1 for r in t.rounds if r.complete)
        head = ("26px minmax(150px,1fr) 62px 62px")
        table = "".join(
            f"<div class='fh-row{' first' if i == 0 else ''}' style='--grid-cols:{head}'>"
            f"<span class='fh-rank'>{i + 1}</span>"
            f"<span class='fh-name'>{reg.crest(sc,'xs')} {reg.school_link(sc)}</span>"
            f"<span class='fh-num tnum'>{pts:g}</span>"
            f"<span class='fh-num tnum fh-dim'>{brd:g}</span></div>"
            for i, (sc, pts, brd) in enumerate(rows[:16]))
        rounds_html = []
        for r in t.rounds:
            lines = []
            for m in r.matchups:
                if m.bye:
                    lines.append(f"<div class='fh-evrow'><span class='kk'>Bye</span>"
                                 f"<span class='ln'>{reg.school_link(m.home)}</span>"
                                 f"<span class='dt'>1 point</span></div>")
                    continue
                href = reg.contest_href(m.contest_key)
                inner = (f"<a class='m' href='{href}'></a>" if href else "")
                res = (f"{m.home_score:g}–{m.away_score:g}"
                       if m.status == "final" and m.home_score is not None
                       else esc(m.time or "TBD"))
                lines.append(
                    f"<div class='fh-evrow{' final' if m.status == 'final' else ''}'>{inner}"
                    f"<span class='kk'>Board match</span>"
                    f"<span class='ln'>{reg.school_link(m.away)} at "
                    f"{reg.school_link(m.home)}</span>"
                    f"<span class='dt'>{res}</span></div>")
            rounds_html.append(
                f"<div class='fh-mod'><h3>{esc(r.name)}"
                f"{f' · {esc(nice_date(r.matchups[0].date))}' if r.matchups and r.matchups[0].date else ''}"
                f"</h3>{''.join(lines[:10])}</div>")
        body_main = (
            f"<div class='fh-section'><h2>Standings</h2>"
            f"<p class='fh-lede'>Five rounds of Swiss pairing over two days. "
            f"Every school plays every round; a match is five boards, a board "
            f"is a point and a drawn board is a half. {played} of "
            f"{len(t.rounds)} rounds complete.</p>"
            f"<div class='fh-tablescroll'><div class='fh-table' style='--grid-cols:{head}'>"
            f"<div class='fh-thead'><span class='fh-th'></span>"
            f"<span class='fh-th'>School</span><span class='fh-th'>Match</span>"
            f"<span class='fh-th'>Boards</span></div>{table}</div></div></div>"
            f"<div class='fh-section'><h2>Rounds</h2>"
            + module_row(*rounds_html[:4])
            + (module_row(*rounds_html[4:]) if len(rounds_html) > 4 else "")
            + "</div>")
        nav = "Standings · Rounds · Field"
    elif t.format is not TournamentFormat.BRACKET:
        meet = reg.contest_for(t.meet_key)
        if meet is not None:
            body_main = (
                f"<div class='fh-section'><h2>Championship meet</h2>"
                f"<p class='fh-lede'>This title is decided at a single meet, not a "
                f"bracket. <a href='{reg.contest_href(t.meet_key)}'>"
                f"{esc(meet.name)} →</a></p>"
                + meet_results_tables(reg, meet, limit_events=6) + "</div>")
        else:
            body_main = (f"<div class='fh-section'><h2>Championship meet</h2>"
                         f"<p class='fh-empty'>Results post when the meet is "
                         f"contested.</p></div>")
        nav = "Meet results · Qualifiers"
    else:
        body_main = render_bracket(reg, t) + render_champ_schedule(reg, t)
        nav = "Bracket · Schedule · Qualifiers"

    body = f"""
<div class="fh-idhdr champ">
  <div>{icons.icon(sp.key,'fh-ic lg')}</div>
  <div><div class="name">{esc(t.name)}</div>
  <div class="meta">{champ_state_chip(t)} · <a href='/sports/{sp.key}/'>{esc(sp.name)}</a>
  · <a href='/championships/'>All championships</a></div></div>
  <div class="side"></div>
</div>
{champ}
{f'<dl class="fh-facts">{info}</dl>' if info else ''}
<nav class="fh-champnav">{esc(nav)}</nav>
{body_main}
{render_qualifiers(reg, t)}
"""
    crumb = (f"<a href='/'>{NAME}</a> › <a href='/championships/'>Championships</a> › "
             f"<a href='/championships/{sp.key}/'>{esc(sp.name)}</a> › {esc(t.group)}")
    won = (f"{t.champion} are the champions." if t.champion else
           "Bracket, seeds and results." if t.status.value == "in_progress" else
           "The field is set.")
    return shell(page_title(t.name), body, crumb, f"← {sp.name} championships|/championships/{sp.key}/",
                 desc=(f"{t.name} — a {t.size}-team field"
                       f"{f' at {t.final_venue}' if t.final_venue else ''}. {won} "
                       f"Full bracket, seeds and every round's result."),
                 image=sport_photo(t.sport, salt=t.id)[0], kind="article", published=t.start_date)


def render_champ_sport(reg, sport):
    """Every classification's championship for one sport."""
    tours = reg.tour_by_sport.get(sport.key, [])
    cards = []
    for t in tours:
        line = ""
        if t.champion:
            line = (f"<span class='ch'>{reg.crest(t.champion,'xs')} "
                    f"{esc(t.champion)}</span>")
        elif t.format is TournamentFormat.BRACKET:
            rnd = t.current_round()
            if rnd is not None:
                ready = [m for m in rnd.matchups if m.ready]
                line = f"<span class='ch dim'>{len(ready)} in {esc(rnd.name.lower())}</span>"
        cards.append(
            f"<a class='fh-champcard' href='{reg.tour_url[t.id]}'>"
            f"<span class='dv'>{grp_chip(t.group)}</span>{champ_state_chip(t)}"
            f"{line}</a>")
    body = f"""
<div class="fh-idhdr">
  <div>{icons.icon(sport.key,'fh-ic lg')}</div>
  <div><div class="name">{esc(sport.name)} Championships</div>
  <div class="meta">{SEASON_LABEL} · {esc(sport.season.title())} ·
  <a href='/sports/{sport.key}/'>Season page</a></div></div>
  <div class="side"></div>
</div>
<div class="fh-champgrid">{''.join(cards) or "<p class='fh-empty'>No championship is scheduled.</p>"}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/championships/'>Championships</a> › {esc(sport.name)}"
    return shell(page_title(f"{sport.name} Championships"), body, crumb,
                 "← Championships|/championships/",
                 desc=(f"JHSAA {sport.name} state championships — brackets, seeds, "
                       f"qualifiers and champions in every classification."),
                 image=sport_photo(sport.key)[0])


def render_championships(reg):
    """The postseason hub: what is happening, and where the bracket is.

    Organised by sport and championship division, because that is what a reader
    is navigating to — "football, 1A, bracket". The page this replaces was a
    season filter over a list of finals, which can only answer "who won" and
    only after it is over. Live championships lead, since during February the
    thing a state association's front door is for is telling you that the
    semifinals are tonight.

    Divisions come from `Sport.groups` — a sport that consolidates 3A-1A into
    one championship shows one bracket there, not three empty ones.
    """
    live = [t for t in reg.tournaments if t.status is TournamentStatus.IN_PROGRESS]
    live.sort(key=lambda t: (SEASON_ORDER.get(BY_KEY[t.sport].season, 3), t.sport, t.group))

    lead = ""
    if live:
        seen, chips = set(), []
        for t in live:
            if t.sport in seen:
                continue
            seen.add(t.sport)
            chips.append(
                f"<a class='fh-livechip' href='/championships/{t.sport}/'>"
                f"{icons.icon(t.sport,'fh-ic sm')}<span class='sp'>{esc(BY_KEY[t.sport].name)}</span>"
                f"<span class='rd'>{esc(postseason.live_label(t) or 'In progress')}</span></a>")
        lead = (f"<section class='fh-livebar'><h2>Happening now</h2>"
                f"<div class='fh-liverow'>{''.join(chips)}</div></section>")

    blocks = []
    for season in ("fall", "winter", "spring"):
        sports = [sp for sp in CATALOG
                  if sp.season == season and reg.tour_by_sport.get(sp.key)]
        if not sports:
            continue
        rows = []
        for sp in sports:
            tours = reg.tour_by_sport[sp.key]
            chips = "".join(
                f"<a class='dvchip {t.status.value}' href='{reg.tour_url[t.id]}' "
                f"title='{esc(t.name)}'>{esc(t.group)}</a>" for t in tours)
            rows.append(
                f"<div class='fh-champrow'>"
                f"<a class='sp' href='/championships/{sp.key}/'>"
                f"{icons.icon(sp.key,'fh-ic sm')} {esc(sp.name)}</a>"
                f"<div class='dvs'>{chips}</div></div>")
        blocks.append(
            f"<section class='fh-champseason' data-f-season='{season}'>"
            f"<h2>{season.title()}</h2>{''.join(rows)}</section>")

    bar = facet_bar("ch", [
        ("season", "Season", [("fall", "Fall"), ("winter", "Winter"), ("spring", "Spring")]),
    ])
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">Championships</div>
  <div class="meta">{SEASON_LABEL} · {len(reg.tournaments)} state championships across
  {len(reg.tour_by_sport)} activities</div></div>
  <div class="side"></div>
</div>
{lead}
{bar}
<div class="fh-filterable fh-champbook" id="ch">{''.join(blocks)}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › Championships"
    return shell(page_title("Championships"), body, crumb,
                 desc=(f"Every JHSAA state championship — {len(reg.tournaments)} "
                       f"across {len(reg.tour_by_sport)} activities, by sport and "
                       f"classification. Live brackets, results and champions."))


def render_schools_index(reg):
    """Grouped by conference — the state's competitive geography, made visible.

    A conference is who a school actually plays; the directory should read as
    that map. Conferences group under their region, members carry their class
    in parentheses (mixed-class leagues are normal here), and classification
    is a filter over the same view, not a competing hierarchy.
    """
    by_area = defaultdict(list)
    for conf in reg.confs.values():
        by_area[conf["area"]].append(conf)

    blocks = []
    for area in sorted(by_area):
        groups = []
        for conf in sorted(by_area[area], key=lambda c: c["name"]):
            members = sorted((reg.schools[m] for m in conf["members"] if m in reg.schools),
                             key=lambda s: s["name"])
            classes = " ".join(sorted({m["classification"] for m in members}))
            links = "".join(
                f"<a class='fh-schoollink' href='/schools/{m['slug']}/'>"
                f"{esc(m['name'])} <span class='cl'>({esc(m['classification'])})</span>"
                f"<span class='ct'>{esc(m['city'])}</span></a>"
                for m in members)
            cslug = reg.conf_slug.get(conf["name"], "")
            groups.append(
                f"<div class='fh-confgroup' data-f-division='{esc(classes)}'>"
                f"<h4><a href='/conferences/{cslug}/'>{esc(conf['name'])}</a></h4>"
                f"<div class='fh-schoollinks'>{links}</div></div>")
        aid = slugify(area)
        # Conference groups are DIRECT children: the facet engine reads a
        # group's own children for data-f-* rows, and an empty read hides the
        # whole area ([].every() is true).
        blocks.append(
            f"<section class='fh-areablock' id='{aid}'>"
            f"<h2 class='fh-areahead'>{esc(area)}</h2>{''.join(groups)}</section>")

    bar = facet_bar("schools-map", [("division", "Classification",
                                     [(v, class_chip(v)) for v in tuple(CLASSES)])],
                    note="Shows conferences with a member in that class")
    jump = "".join(f"<a href='#{slugify(a)}'>{esc(a)}</a>" for a in sorted(by_area))
    body = f"""
<div class="fh-idhdr">
  <div></div><div><div class="name">Member schools</div>
  <div class="meta">By conference · leagues are geographic and mix classifications</div></div>
  <div class="side"></div>
</div>
<nav class="fh-jump">{jump}</nav>
{bar}
<div class="fh-filterable fh-areas" id="schools-map">{''.join(blocks)}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › Schools"
    return shell(page_title(f"Schools"), body, crumb,
                 desc=(f"All {len(reg.schools)} JHSAA member schools by conference and "
                       f"classification, each with its own athletics site."))


def render_confs_index(reg):
    by_area = defaultdict(list)
    for slug, c in reg.confs.items():
        by_area[c["area"]].append((slug, c))
    blocks = []
    for area in sorted(by_area):
        rows = "".join(
            f"<a class='fh-conflink' href='/conferences/{slug}/'>"
            f"<span class='nm'>{esc(c['name'])}</span>"
            f"<span class='ct'>{esc(', '.join(sorted({reg.schools[m]['classification'] for m in c['members'] if m in reg.schools}, key=CLASSES.index)))}</span></a>"
            for slug, c in sorted(by_area[area], key=lambda kv: kv[1]["name"]))
        blocks.append(f"<div class='fh-confgroup'><h4>{esc(area)}</h4>"
                      f"<div class='fh-schoollinks'>{rows}</div></div>")
    body = f"""
<div class="fh-idhdr">
  <div></div><div><div class="name">Conferences</div>
  <div class="meta"><a href='/schools/'>Schools by classification</a></div></div>
  <div class="side"></div>
</div>
<div class="fh-confgrid">{''.join(blocks)}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › Conferences"
    return shell(page_title(f"Conferences"), body, crumb,
                 desc=(f"All {len(reg.confs)} JHSAA conferences — members, standings "
                       f"and the composite schedule for each league."))


SPORTS_IMG = ROOT / "site/img/sports"


def _credits(path):
    """A credits sidecar, or an empty one. Missing credits must not stop a
    build; a *misread* one silently dropping every credit is the failure that
    matters, so the read is narrow rather than a bare `except`."""
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


SPORTS_CREDITS = _credits(SPORTS_IMG / "credits.json")

# sport key -> photo in the action library; news-style surfaces carry a real
# photograph, per the owner's rule
SPORT_PHOTO = {}
for _k, _names in {
    "football": ("football", "girls-flag-football"),
    "soccer": ("boys-soccer", "girls-soccer"),
    "volleyball": ("girls-volleyball", "boys-volleyball"),
    "trail": ("boys-cross-country", "girls-cross-country", "mountain-biking"),
    # racquet sports: badminton and squash have no stock picture of their own,
    # and a racquet on a court is a much closer miss than the archive photo
    # they were falling through to
    "tennis": ("girls-tennis", "boys-tennis", "badminton", "squash"),
    "golf": ("boys-golf", "girls-golf"),
    # `baseball.jpg` has been in the library since the first build and nothing
    # pointed at it — both diamond sports were resolving to `gym-generic`
    "baseball": ("baseball", "softball", "cricket"),
    "aquatic": ("boys-water-polo", "girls-water-polo", "boys-swimming", "girls-swimming"),
    "basketball": ("boys-basketball", "girls-basketball"),
    "wrestling": ("boys-wrestling", "girls-wrestling"),
    "hockey": ("boys-ice-hockey", "girls-ice-hockey"),
    "ski": ("boys-alpine-skiing", "girls-alpine-skiing", "boys-nordic-skiing", "girls-nordic-skiing"),
    "bowling": ("bowling",),
    "fencing": ("boys-fencing", "girls-fencing"),
    "gymnastics": ("gymnastics", "competitive-spirit"),
    "track": ("winter-track", "boys-track", "girls-track"),
    "performing": ("marching-band", "choir"),
    "field": ("boys-lacrosse", "girls-lacrosse", "field-hockey", "ultimate",
              "boys-rugby", "girls-rugby"),
    "gym-generic": ("debate", "chess"),
}.items():
    for _n in _names:
        SPORT_PHOTO[_n] = _k


#: A drop folder. Anything named for a SPORT KEY (`cricket.jpg`), a NEWS SLUG
#: (`tennis-semifinals-preview.jpg`) or a photo family (`track.jpg`) wins over
#: the stock library without touching any code — which is the point, because
#: the person choosing the pictures should not have to edit a Python file to
#: use one. Credits go in `additions/credits.json`, same shape as the others.
#:
#: A name may carry VARIANTS — `baseball.jpg`, `baseball-2.jpg`,
#: `baseball-3.jpg`. All of them are that sport's photo; which one a given
#: surface gets is chosen by a stable hash of the caller's `salt` (a school
#: name, a conference), so 840 school fronts leading on baseball do not all
#: lead on the same frame. No salt means variant one, every time.
ADDITIONS = ROOT / "site/img/news/additions"
_ADDITION_EXTS = ("jpg", "jpeg", "png", "webp")


def _variants(name):
    """Every file in the drop folder that is `name` or `name-<n>`, in order."""
    out = []
    for ext in _ADDITION_EXTS:
        if (ADDITIONS / f"{name}.{ext}").exists():
            out.append(f"{name}.{ext}")
    n = 2
    while True:
        hit = [f"{name}-{n}.{ext}" for ext in _ADDITION_EXTS
               if (ADDITIONS / f"{name}-{n}.{ext}").exists()]
        if not hit:
            break
        out += hit
        n += 1
    return out


def _addition(*names, salt=""):
    """The first of `names` present in the drop folder, as (url, credit)."""
    for n in names:
        if not n:
            continue
        files = _variants(n)
        if not files:
            continue
        f = files[zlib.crc32(salt.encode()) % len(files)] if salt else files[0]
        c = ADDITION_CREDITS.get(f.rsplit(".", 1)[0], ADDITION_CREDITS.get(n, {}))
        credit = " · ".join(x for x in (c.get("credit", ""),
                                        c.get("license", "")) if x)
        return f"/img/additions/{f}", credit
    return None


def sport_photo(sport_key, salt=""):
    """(url, credit line) for the sport's action photograph.

    The drop folder is checked first, by sport key, then by the key with its
    gender prefix off, then by the family the stock library groups it under.
    So `boys-squash.jpg` serves boys squash, `squash.jpg` serves both, and
    `cricket.jpg` serves a sport the library has no picture for at all.

    The middle step exists because the sport keys are gendered and the
    photographs mostly are not — without it, one squash court has to be
    committed twice under two names, or named for a family it does not belong
    to. It is checked BELOW the exact key, so a genuinely gendered pair still
    wins where somebody has supplied one.
    """
    k = SPORT_PHOTO.get(sport_key, "gym-generic")
    base = (sport_key.split("-", 1)[1]
            if sport_key.startswith(("boys-", "girls-")) else None)
    hit = _addition(sport_key, base, k, salt=salt)
    if hit:
        return hit
    if not (SPORTS_IMG / f"{k}.jpg").exists():
        k = "gym-generic"
    c = SPORTS_CREDITS.get(k, {})
    credit = " · ".join(x for x in (c.get("credit", ""), c.get("license", "")) if x)
    return f"/img/sports/{k}.jpg", credit


NEWS_IMG = ROOT / "site/img/news"
ADDITION_CREDITS = _credits(ADDITIONS / "credits.json")
NEWS_CREDITS = _credits(NEWS_IMG / "credits.json")


def story_photo(st, salt=""):
    """(url, credit) for a story — its own photograph, or its sport's.

    Only eleven of the stories have a picture of their own. Without a
    fallback the ones that do not lead the front page as a flat colour
    block, which reads as a bug rather than a choice.
    """
    hit = _addition(st["slug"], salt=salt)
    if hit:
        return hit
    if (NEWS_IMG / f"{st['slug']}.jpg").exists():
        c = NEWS_CREDITS.get(st["slug"], {})
        credit = " · ".join(x for x in (c.get("credit", ""), c.get("license", "")) if x)
        return f"/img/news/{st['slug']}.jpg", credit
    return sport_photo(st.get("sport") or "gym-generic", salt=salt)


def story_img(st, cls=""):
    """The story's photograph. Every credit renders — the licenses require it,
    and a real newsroom would print it anyway.

    This used to look only in `img/news/`, so a story whose picture arrived in
    the drop folder ran its article page with no image at all while the same
    photograph led the front page.
    """
    src = _addition(st["slug"]) or (
        (f"/img/news/{st['slug']}.jpg",
         " · ".join(x for x in (NEWS_CREDITS.get(st["slug"], {}).get("credit", ""),
                                NEWS_CREDITS.get(st["slug"], {}).get("license", "")) if x))
        if (NEWS_IMG / f"{st['slug']}.jpg").exists() else None)
    if not src:
        return ""
    url, credit = src
    cap = f"<figcaption>Photo: {esc(credit)}</figcaption>" if credit else ""
    return (f"<figure class='fh-figure {cls}'>"
            f"<img src='{url}' alt='' loading='lazy'>{cap}</figure>")


def render_story(reg, st):
    paras = "".join(f"<p>{esc(b)}</p>" for b in st["body"])
    others = [s for s in news.STORIES if s["slug"] != st["slug"]][:6]
    more = "".join(
        f"<a href='/news/{s['slug']}/'><span class='kk'>{esc(s['kicker'])}</span>"
        f"{esc(s['head'])}</a>" for s in others)
    body = f"""
<div class="fh-articlegrid">
<article class="fh-article">
  <div class="kk">{esc(st['kicker'])} · {esc(nice_date(st['date']))}</div>
  <h1>{esc(st['head'])}</h1>
  <p class="dek">{esc(st['dek'])}</p>
  {story_img(st)}
  {paras}
  <p class="fh-more"><a href="/news/">More from the association →</a></p>
</article>
<aside class="fh-morestories">
  <h2>More stories</h2>
  {more}
</aside>
</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/news/'>News</a> › {esc(st['kicker'])}"
    return shell(page_title(f"{st['head']}"), body, crumb, "← News|/news/", story=st,
                 desc=st["dek"], kind="article", published=st["date"],
                 image=(f"/img/news/{st['slug']}.jpg"
                        if (NEWS_IMG / f"{st['slug']}.jpg").exists() else None))


def render_news_index(reg):
    """Two lanes: activity/results coverage and association administration."""
    def lane(kind, title, blurb):
        def thumb(st):
            if not (NEWS_IMG / f"{st['slug']}.jpg").exists():
                return ""
            return f"<span class='th'><img src='/img/news/{st['slug']}.jpg' alt='' loading='lazy'></span>"
        items = "".join(
            f"<a class='fh-storyrow{' pic' if thumb(st) else ''}' href='/news/{st['slug']}/'>{thumb(st)}"
            f"<span class='kk'>{esc(st['kicker'])} · {esc(nice_date(st['date']))}</span>"
            f"<span class='hd'>{esc(st['head'])}</span>"
            f"<span class='dk'>{esc(st['dek'])}</span></a>"
            for st in news.STORIES if st.get("kind") == kind)
        return (f"<section><div class='fh-group' style='margin-top:0'><h3>{esc(title)}</h3></div>"
                f"<p class='fh-lede'>{esc(blurb)}</p><div class='fh-storylist'>{items}</div></section>")

    body = f"""
<div class="fh-idhdr">
  <div></div><div><div class="name">News &amp; notices</div>
  <div class="meta">Competition coverage and association announcements</div></div>
  <div class="side"></div>
</div>
<div class="fh-newslanes">
{lane('activity', 'Activities & competition', 'Championships, schedules and student-athletes.')}
{lane('association', 'Association business', 'Eligibility, officiating, participation and board decisions.')}
</div>
<div class="fh-newsbsky">{bsky_panel()}</div>
{BSKY_JS}
"""
    crumb = f"<a href='/'>{NAME}</a> › News"
    return shell(page_title(f"News"), body, crumb,
                 desc=("Competition coverage and association business from the "
                       "JHSAA — championships, eligibility, officiating and "
                       "participation."))


SEASON_JS = """
<script>
(function () {
  document.querySelectorAll(".fh-seasons").forEach(function (root) {
    var tabs = root.querySelectorAll(".fh-seasontabs button");
    if (!tabs.length) return;
    var panes = root.querySelectorAll("[data-season-pane]");
    function show(sn) {
      panes.forEach(function (p) { p.hidden = p.dataset.seasonPane !== sn; });
      tabs.forEach(function (o) { o.classList.toggle("on", o.dataset.season === sn); });
    }
    root.querySelectorAll(".fh-seasonlabel").forEach(function (h) { h.hidden = true; });
    var start = root.querySelector(".fh-seasontabs button.on");
    show(start ? start.dataset.season : "winter");
    tabs.forEach(function (b) {
      b.addEventListener("click", function () { show(b.dataset.season); });
    });
  });
})();
</script>"""


def bsky_panel():
    """The network's Bluesky feed, as a rail module.

    What ships in the HTML is only what is TRUE without a network: the handle,
    the link, and a follow card. The script asks the public AppView API for
    the account's recent posts and swaps them in — reader-side, so a static
    page shows a live feed without the build knowing anything about it. Every
    failure mode (empty account, blocked fetch, JS off) leaves the card, which
    is a working link rather than a broken feed.
    """
    return f"""
<section class="fh-bsky">
  <h2>{icons.bsky()} From the network</h2>
  <div id="bsky-feed" data-actor="{BSKY_HANDLE}">
    <a class="fh-bskyfollow" href="{BSKY_URL}" target="_blank" rel="noopener">
      <span class="hd">@{BSKY_HANDLE}</span>
      <span class="dk">Scores, championship nights and records news on Bluesky.</span>
      <span class="fl">Follow →</span>
    </a>
  </div>
</section>"""


BSKY_JS = f"""
<script>
(function () {{
  var box = document.getElementById("bsky-feed");
  if (!box || !window.fetch) return;
  var actor = box.getAttribute("data-actor");
  fetch("{BSKY_API}?actor=" + encodeURIComponent(actor) +
        "&limit=4&filter=posts_no_replies")
    .then(function (r) {{ if (!r.ok) throw 0; return r.json(); }})
    .then(function (data) {{
      var posts = (data.feed || []).filter(function (it) {{ return !it.reason; }});
      if (!posts.length) return;                 // empty feed: keep the card
      box.innerHTML = posts.map(function (it) {{
        var p = it.post, rec = p.record || {{}};
        var url = "https://bsky.app/profile/" + actor + "/post/" + p.uri.split("/").pop();
        var d = new Date(rec.createdAt || p.indexedAt);
        var t = document.createElement("span");
        t.textContent = rec.text || "";          // escape by assignment
        return "<a class='fh-bskypost' href='" + url + "' target='_blank' rel='noopener'>" +
          "<span class='tx'>" + t.innerHTML + "</span>" +
          "<span class='mt'>" + d.toLocaleDateString(undefined, {{month: "short", day: "numeric"}}) +
          " · " + (p.likeCount || 0) + " likes · " + (p.repostCount || 0) + " reposts</span></a>";
      }}).join("") +
      "<p class='fh-more'><a href='https://bsky.app/profile/" + actor +
      "' target='_blank' rel='noopener'>Follow @" + actor + " →</a></p>";
    }})
    .catch(function () {{}});
}})();
</script>"""


def season_ribbon(sport_keys, current="winter", link=None, tail=""):
    """Season tabs + one swipeable icon ribbon per season, scoped to
    `sport_keys` — the same component at every tier: the state front shows
    everything, a conference its members' sports, a school its own programs.
    `link` maps a sport key to an href (default: the sport hub)."""
    link = link or (lambda k: f"/sports/{k}/")
    seasons = [sn for sn in ("fall", "winter", "spring")
               if any(BY_KEY[k].season == sn for k in sport_keys)]
    if current not in seasons and seasons:
        current = seasons[0]
    tabs = "".join(
        f"<button type='button' data-season='{sn}'{' class=on' if sn == current else ''}>"
        f"{sn.title()}</button>" for sn in seasons)
    panes = []
    for sn in seasons:
        # same collapsing as the nav: a ribbon that lists Boys and Girls
        # Basketball as two tiles says the school runs two sports
        items = "".join(
            f"<a class='fh-ribbonitem' href='{link(key)}' title='{esc(label)}'>"
            f"{icons.icon(key)}<span>{esc(label)}</span></a>"
            for label, key in collapse_pairs(sport_keys, sn))
        panes.append(f"<div class='fh-sportribbon' data-season-pane='{sn}'>"
                     f"<h3 class='fh-seasonlabel'>{sn.title()}</h3>{items}</div>")
    return f"""
<section class="fh-seasons">
  <div class="fh-seasontabs">{tabs}{tail}</div>
  {''.join(panes)}
</section>"""


def season_of(day: str) -> str:
    """Which season a date falls in, by the calendar this state keeps."""
    m = int(day[5:7])
    return "fall" if 8 <= m <= 11 else "winter" if m == 12 or m <= 2 else "spring"


def season_chooser(reg, current=None):
    current = current or season_of(TODAY)
    keys = [sp.key for sp in CATALOG if reg.by_sport.get(sp.key)]
    return season_ribbon(keys, current,
                         tail="<a class='all' href='/scoreboard/'>Scoreboard →</a>")


#: The season tabs already sit above the fold; this moves the newsroom with
#: them. Kept separate from SEASON_JS because those panes are scoped inside
#: the ribbon and the news column is not.
NEWS_SEASON_JS = """
<script>
(function () {
  var panes = document.querySelectorAll("[data-news-season]");
  var tabs = document.querySelectorAll(".fh-seasontabs button");
  if (!panes.length || !tabs.length) return;
  tabs.forEach(function (b) {
    b.addEventListener("click", function () {
      panes.forEach(function (p) { p.hidden = p.dataset.newsSeason !== b.dataset.season; });
    });
  });
})();
</script>"""


def render_404(reg):
    """The not-found page.

    Written to ``404.html`` at the root rather than through the page map:
    Vercel serves that file for any unmatched path on a static deployment,
    and a page at ``/404/`` would be a real url that answers 200. It is kept
    out of the sitemap for the same reason, and carries `noindex` so a
    crawler that reaches it anyway does not file it as content.

    An athletics site's 404 gets traffic from stale bookmarks and old
    brackets, so it offers the four places that are almost always the answer
    instead of only apologising.
    """
    links = [("Scores & schedule", "/scoreboard/"), ("Championships", "/championships/"),
             ("Member schools", "/schools/"), ("Product tour", "/tour/")]
    body = f"""
<div class="fh-404">
  <div class="num" aria-hidden="true">404</div>
  <h1>You made a wrong turn, go back?</h1>
  <p class="dk">That page isn't here. It may have moved when the season
     rolled over, or the link may have been mistyped.</p>
  <div class="fh-404links">
    <button type="button" class="fh-pill back" id="go-back">← Go back</button>
    {''.join(f"<a class='fh-pill' href='{u}'>{esc(t)}</a>" for t, u in links)}
  </div>
</div>
<script>
(function () {{
  var b = document.getElementById("go-back");
  if (!b) return;
  // No history to go back to means the reader arrived here cold — send them
  // home rather than nowhere.
  b.addEventListener("click", function () {{
    if (document.referrer && history.length > 1) history.back();
    else location.href = "/";
  }});
}})();
</script>
"""
    page = shell(page_title("Page not found"), body,
                 desc="That page isn't here. Scores, schedules, championships "
                      "and every member school's athletics site are one link away.")
    return page.replace('<meta charset="utf-8">',
                        '<meta charset="utf-8">\n<meta name="robots" content="noindex">', 1)


def render_front(reg):
    """The front is a publication: one lead, secondaries at half its weight,
    briefs at a line each — then the structured material (scores, finder) in
    the rail beside it. Hierarchy, not a grid of equal cards."""
    import datetime as dt
    t = dt.date.fromisoformat(TODAY)

    # ---- ONE NEWS COLUMN PER SEASON, switched by the season tabs.
    #      Every story in this file was dated the same January week, so at a
    #      May clock the front page led with a four-month-old fencing result
    #      and had nothing to say about fall or spring at all. Season is now
    #      a property of a story, and the tabs that already sit above the
    #      fold move the newsroom with them.
    stories = sorted(news.STORIES, key=lambda s: s["date"], reverse=True)
    now = season_of(TODAY)

    def news_column(season):
        pool = [st for st in stories if st.get("season") == season] or stories
        lead, second, briefs = pool[0], pool[1:3], pool[3:9]
        img, _credit = story_photo(lead)
        lead_html = (
            f"<a class='fh-hero' href='/news/{lead['slug']}/'>"
            f"<span class='ph'><img src='{img}' alt=''></span>"
            f"<span class='kk'>{esc(lead['kicker'])} · {esc(nice_date(lead['date']))}</span>"
            f"<span class='hd'>{esc(lead['head'])}</span>"
            f"<span class='dk'>{esc(lead['dek'])}</span></a>")
        second_html = "".join(
            f"<a class='fh-second' href='/news/{st['slug']}/'>"
            f"<span class='kk'>{esc(st['kicker'])}</span>"
            f"<span class='hd'>{esc(st['head'])}</span>"
            f"<span class='dk'>{esc(st['dek'])}</span></a>"
            for st in second)
        briefs_html = "".join(
            f"<a class='fh-brief' href='/news/{st['slug']}/'>"
            f"<span class='kk'>{esc(st['kicker'])}</span>"
            f"<span class='hd'>{esc(st['head'])}</span>"
            f"<span class='dt'>{esc(nice_date(st['date']))}</span></a>"
            for st in briefs)
        return (f"<div data-news-season='{season}'{'' if season == now else ' hidden'}>"
                f"{lead_html}<div class='fh-seconds'>{second_html}</div>"
                f"<div class='fh-briefs'><h2>{season.title()} from the JHSAA</h2>"
                f"{briefs_html}"
                f"<p class='fh-more'><a href='/news/'>All news →</a></p></div></div>")

    lead = next((st for st in stories if st.get("season") == now), stories[0])
    news_cols = "".join(news_column(sn) for sn in ("fall", "winter", "spring"))

    # Latest — the most recent finals, winner first, both scores. Recency is
    # relative to the calendar the season actually kept, not a fixed window.
    finals = []
    for c in sorted((c for c in reg.contests if c.date and c.date <= TODAY),
                    key=lambda c: (c.date or ""), reverse=True):
        line = score_line(reg, c) if not isinstance(c, Meet) else ""
        if line:
            finals.append(score_row(reg.url(c), f"{line}", f"{esc(BY_KEY[c.sport].name)}"))
        if len(finals) >= 7:
            break

    # ---- the association's editorial layer at statewide scope ----
    state_honors = reg.items_state
    live_tours = sorted(
        (t for t in reg.tournaments if t.status is TournamentStatus.IN_PROGRESS),
        key=lambda t: t.final_date or "") or sorted(
        (t for t in reg.tournaments if t.champion),
        key=lambda t: t.final_date or "", reverse=True)
    state_mods = module_row(
        awards_list(reg, [i for i in state_honors if i["kind"] == "state-title"],
                    5, heading="State champions", show_school=True),
        awards_list(reg, [i for i in state_honors if i["kind"] == "state-honor"],
                    5, heading="Athletes of the year", show_school=True),
        record_performance(reg, state_honors, heading="Record performances", limit=4),
        awards_list(reg, [i for i in state_honors if i["kind"] in
                          ("state-academic", "state-official",
                           "state-sportsmanship")],
                    4, heading="Association recognition"))

    opts = "".join(
        f"<a class='fh-schoolhit' href='/schools/{s['slug']}/' "
        f"data-n='{esc((s['name'] + ' ' + s['city'] + ' ' + s['conference']).lower())}'>"
        f"{reg.crest(s['name'],'xs')}<span class='nm'>{esc(s['name'])}</span>"
        f"<span class='ct'>{esc(s['city'])}</span></a>"
        for s in sorted(reg.schools.values(), key=lambda s: s["name"]))

    body = f"""
{season_chooser(reg)}

<div class="fh-top">
  <div class="fh-newscol">{news_cols}</div>
  <aside class="fh-side">
    <section class="fh-latest">
      <h2>Latest scores</h2>
      <div class="fh-results">{''.join(finals)}</div>
      <p class="fh-more"><a href="/scoreboard/">Full scoreboard →</a></p>
    </section>
    <section class="fh-latest">
      <h2>Statewide honors</h2>
      {headline_list(reg, state_honors, 4, show_school=True)}
      <p class="fh-more"><a href="/championships/">Championships →</a></p>
    </section>
    {bsky_panel()}
    <section class="fh-finder">
      <h2>Find your school</h2>
      <input id="school-q" type="search" placeholder="School, town or conference"
             autocomplete="off" aria-label="Search member schools">
      <div class="fh-schoolhits" id="school-hits">{opts}</div>
      <p class="fh-more"><a href="/schools/">By conference</a> · <a href="/championships/">Championships</a></p>
    </section>
  </aside>
</div>

{state_mods}
{SEASON_JS}
{NEWS_SEASON_JS}
{BSKY_JS}
<script>
(function () {{
  var q = document.getElementById("school-q"), hits = document.getElementById("school-hits");
  if (!q) return;
  var rows = [].slice.call(hits.children);
  q.addEventListener("input", function () {{
    var v = q.value.trim().toLowerCase();
    if (!v) {{ hits.classList.remove("open"); return; }}
    var n = 0;
    rows.forEach(function (r) {{
      var ok = n < 8 && r.dataset.n.indexOf(v) !== -1;
      r.style.display = ok ? "" : "none";
      if (ok) n++;
    }});
    hits.classList.add("open");
  }});
}})();
</script>
"""
    return shell(TITLE, body, desc=SITE_DESC,
                 image=(f"/img/news/{lead['slug']}.jpg"
                        if (NEWS_IMG / f"{lead['slug']}.jpg").exists() else None))


# ──────────────────────────────────────────────────────────── write + verify


def favicon_tag() -> str:
    kind = ' type="image/svg+xml"' if FAVICON.endswith(".svg") else ""
    return f'\n<link rel="icon" href="{FAVICON}"{kind}>'


#: The owner's mark (owner note 2027-08). When this file exists it IS the
#: favicon, published as /favicon.png; until it lands the fallbacks below
#: keep the tab from going blank.
APEX_MARK = ROOT / "site/img/sports/apex-blue.png"


def pick_favicon() -> str:
    """The apex mark when present; else any favicon.* dropped into site/;
    else the wordmark's initial so the tab is never blank mid-rename.
    Resolved before the pages render (they carry the href) and written after
    the output tree is cleared."""
    if APEX_MARK.exists():
        return "/favicon.png"
    found = sorted((ROOT / "site").glob("favicon.*"))
    return "/" + found[0].name if found else "/favicon.svg"


def write_favicon(out: pathlib.Path) -> None:
    if APEX_MARK.exists():
        shutil.copy(APEX_MARK, out / "favicon.png")
        return
    src = ROOT / "site" / FAVICON.lstrip("/")
    if src.exists():
        shutil.copy(src, out / src.name)
    else:
        (out / "favicon.svg").write_text(_letter_favicon())


def _letter_favicon() -> str:
    """SVG rather than a raster: there's no font rasteriser here, and a tab icon
    that's a letter has to stay crisp at 16px and on a retina bookmark bar."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="12" fill="#1b4a8f"/>'
        f'<text x="32" y="33" fill="#faf7f0" font-size="42" font-weight="800"'
        ' text-anchor="middle" dominant-baseline="central"'
        ' font-family="Helvetica Neue,Helvetica,Arial,sans-serif"'
        f'>{WORDMARK[0]}</text></svg>\n'
    )


HREF = re.compile(r"href=['\"](/[^'\"#]*)")


def link_check(refs, targets):
    """`refs` maps each internal href the build emitted to one page carrying
    it; `targets` is every url the site knows how to serve.

    Split in two because the build no longer keeps the rendered pages around
    to re-scan at the end — hrefs are harvested as each page is written and
    the page text is dropped. Checking against the route table rather than
    against what was rendered is also what lets a partial build still prove
    its links point at real urls.
    """
    ok = set(targets) | {"/style.css", FAVICON}
    broken = []
    for href, src in sorted(refs.items()):
        if href.startswith("/fonts/"):
            if not (ROOT / "site/fonts" / href.split("/")[-1]).exists():
                broken.append(f"{src} -> {href}")
        elif href.startswith("/report/"):
            if not (ROOT / href.lstrip("/")).exists():
                broken.append(f"{src} -> {href}")
        elif href not in ok:
            broken.append(f"{src} -> {href}")
    return broken


def inline_preview(front):
    css = (ROOT / "site/style.css").read_text()

    def font_uri(m):
        data = base64.b64encode((ROOT / "site/fonts" / m.group(1)).read_bytes()).decode()
        return f"url(data:font/woff2;base64,{data})"

    css = re.sub(r"url\('fonts/([^']+)'\)", font_uri, css)
    return front.replace('<link rel="stylesheet" href="/style.css">', f"<style>\n{css}\n</style>")


def write_sitemap(out: pathlib.Path, pages) -> None:
    """A sitemap index plus shards, because 58,000 urls is past the 50,000 a
    single sitemap may carry — a crawler drops the whole file when it is over,
    so the limit is not advisory."""
    urls = sorted(pages)
    shards = [urls[i:i + 40000] for i in range(0, len(urls), 40000)]
    for n, shard in enumerate(shards, 1):
        body = "".join(f"<url><loc>{SITE_URL}{html.escape(u)}</loc></url>" for u in shard)
        (out / f"sitemap-{n}.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{body}</urlset>\n")
    index = "".join(f"<sitemap><loc>{SITE_URL}/sitemap-{n}.xml</loc></sitemap>"
                    for n in range(1, len(shards) + 1))
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{index}</sitemapindex>\n")


def page_routes(reg):
    """Every url the site serves, paired with the thunk that renders it.

    The table is built whole and rendered lazily, which buys two things. The
    build can hold one page in memory at a time instead of all 58,000 — the
    dict of rendered pages this replaced peaked at 7 GB, most of it the same
    masthead, rail and icon sprite repeated on every page. And a partial build
    can still link-check against the complete url space, because the routes
    exist here whether or not anything renders them.
    """
    r: dict[str, tuple[str, object]] = {}
    r["/"] = ("front", lambda: render_front(reg))
    r["/scoreboard/"] = ("scoreboard", lambda: render_scoreboard(reg))
    r["/tour/"] = ("tour", lambda: render_tour(reg))
    r["/schools/"] = ("index", lambda: render_schools_index(reg))
    r["/conferences/"] = ("index", lambda: render_confs_index(reg))
    r["/championships/"] = ("index", lambda: render_championships(reg))
    r["/news/"] = ("index", lambda: render_news_index(reg))
    for st in news.STORIES:
        r[f"/news/{st['slug']}/"] = ("news", lambda st=st: render_story(reg, st))
    for c in reg.contests:
        fn = (render_meet if isinstance(c, Meet) else
              render_dual if isinstance(c, Dual) else render_game)
        r[reg.url(c)] = ("contest", lambda c=c, fn=fn: fn(reg, c))
    for sp in CATALOG:
        # A hub exists for every activity somebody sponsors, even with no
        # contests yet — school pages link to it, and an empty season is a
        # state a real association site has to show anyway.
        if reg.by_sport.get(sp.key) or any(sp.key in s.get("sports", ())
                                           for s in reg.schools.values()):
            r[f"/sports/{sp.key}/"] = ("sport", lambda sp=sp: render_sport(reg, sp))
            r[f"/sports/{sp.key}/standings/"] = (
                "sport", lambda sp=sp: render_sport_standings(reg, sp))
            if sp.shape.value != "meet":
                r[f"/sports/{sp.key}/rankings/"] = (
                    "sport", lambda sp=sp: render_sport_rankings(reg, sp))
            r[f"/sports/{sp.key}/schedule/"] = (
                "sport", lambda sp=sp: render_sport_schedule(reg, sp))
            r[f"/sports/{sp.key}/champions/"] = (
                "sport", lambda sp=sp: render_sport_champs(reg, sp))
    for sp in CATALOG:
        if reg.tour_by_sport.get(sp.key):
            r[f"/championships/{sp.key}/"] = (
                "championship", lambda sp=sp: render_champ_sport(reg, sp))
    for t in reg.tournaments:
        r[reg.tour_url[t.id]] = ("championship", lambda t=t: render_tournament(reg, t))
    for s in reg.schools.values():
        r[f"/schools/{s['slug']}/"] = ("school", lambda s=s: render_school(reg, s))
    for slug, conf in reg.confs.items():
        r[f"/conferences/{slug}/"] = ("conference", lambda conf=conf: render_conference(reg, conf))
    for a in reg.athletes.values():
        r[f"/athletes/{a['slug']}/"] = ("athlete", lambda a=a: render_athlete(reg, a))
    return r


#: Set by build() before any worker forks, so the children inherit the whole
#: route table — and the registry the thunks close over — as copy-on-write
#: pages rather than pickling it across a pipe.
ROUTES: dict[str, tuple[str, object]] = {}


def render_slice(urls, stage):
    """Render, write and drop each page in `urls`; return the hrefs it emitted.

    The unit of parallelism. A page depends on nothing but the registry and
    the module globals, both fixed before the fork, so slices cannot interact:
    every worker writes to a distinct path, and the only thing that comes back
    is href -> one page carrying it, which the parent merges for the link
    check. The front page comes back with it because `dist/index.html` inlines
    that exact text, before the og:url substitution.
    """
    refs: dict[str, str] = {}
    front = ""
    for url in urls:
        text = ROUTES[url][1]()
        for href in HREF.findall(text):
            refs.setdefault(href, url)
        rel = "index.html" if url == "/" else url.strip("/") + "/index.html"
        p = stage / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        # og:url and rel=canonical are the one thing in the head only this
        # loop knows. Substituted here rather than threaded through every
        # renderer's signature.
        p.write_text(text.replace(OG_URL_TOKEN, url))
        if url == "/":
            front = text
        # `text` is the last reference to this page and dies with the
        # iteration. Retaining all of them to link-check at the end was the
        # whole of the build's memory footprint.
    return refs, front


def render_all(picked, stage, jobs):
    """`render_slice` over `jobs` forked workers, or inline when jobs == 1."""
    if jobs == 1:
        return render_slice(picked, stage)

    # Round-robin, not contiguous blocks: the expensive pages cluster by kind
    # (840 school pages each rendering a full season are most of the tail), so
    # a block split leaves one worker running long after the others are idle.
    slices = [picked[i::jobs] for i in range(jobs)]
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(jobs) as pool:
        results = pool.starmap(render_slice, [(s, stage) for s in slices])

    refs: dict[str, str] = {}
    front = ""
    for slice_refs, slice_front in results:      # slice order, so the link
        for href, url in slice_refs.items():     # check reports the same
            refs.setdefault(href, url)           # source page every run
        front = front or slice_front
    return refs, front


def worker_count(n_pages):
    """`FH_JOBS` if set, else one per core, capped.

    Capped at 4 because each worker's copy-on-write share of the registry
    diverges as CPython touches refcounts, so peak memory grows with workers
    while wall time stops improving once the writes go I/O-bound. Small builds
    stay serial — forking to render 18 pages costs more than it saves.
    """
    env = os.environ.get("FH_JOBS")
    if env:
        return max(1, int(env))
    if not hasattr(os, "fork") or n_pages < 500:
        return 1
    return max(1, min(4, len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity")
                      else (os.cpu_count() or 1)))


def build():
    global RAIL, FAVICON, ROUTES
    reg = Registry()
    FAVICON = pick_favicon()
    RAIL = build_rail(reg)
    build_menus(reg)

    ROUTES = routes = page_routes(reg)
    only = {k.strip() for k in os.environ.get("FH_ONLY", "").split(",") if k.strip()}
    if only - {kind for kind, _ in routes.values()}:
        raise SystemExit(f"FH_ONLY: no such page kind {sorted(only - {k for k, _ in routes.values()})}; "
                         f"known kinds are {sorted({k for k, _ in routes.values()})}")
    picked = [u for u, (kind, _) in routes.items() if not only or kind in only]

    # Staged, not written straight into OUT: pages now go to disk before the
    # link check can run, and a build that fails its check must leave the last
    # good tree standing rather than a half-written one.
    (ROOT / "dist").mkdir(exist_ok=True)
    stage = OUT.parent / (OUT.name + ".staging")
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)

    jobs = worker_count(len(picked))
    refs, front = render_all(picked, stage, jobs)

    broken = link_check(refs, routes)
    if broken:
        for b in broken[:20]:
            print("BROKEN:", b)
        shutil.rmtree(stage, ignore_errors=True)
        raise SystemExit(f"{len(broken)} broken internal links")

    shutil.copy(ROOT / "site/style.css", stage / "style.css")
    # Not a route: it must land at 404.html, not 404/index.html, and it must
    # stay out of the sitemap.
    (stage / "404.html").write_text(render_404(reg).replace(OG_URL_TOKEN, "/404"))
    write_favicon(stage)
    shutil.copytree(ROOT / "site/fonts", stage / "fonts")
    if NEWS_IMG.exists():
        # `additions` is a child of this folder but is published at its own
        # path below — copying it here too would ship every photograph twice
        shutil.copytree(NEWS_IMG, stage / "img/news",
                        ignore=shutil.ignore_patterns("credits.json", "additions"))
    if SPORTS_IMG.exists():
        shutil.copytree(SPORTS_IMG, stage / "img/sports", ignore=shutil.ignore_patterns("credits.json"))
    if ADDITIONS.exists():
        # served flat at /img/additions/ though it lives inside img/news/, so
        # a photograph dropped in one folder never collides with a story slug
        shutil.copytree(ADDITIONS, stage / "img/additions",
                        ignore=shutil.ignore_patterns("credits.json", "*.md", "*.txt"))
    if (ROOT / "site/img/og.jpg").exists():
        shutil.copy(ROOT / "site/img/og.jpg", stage / "img/og.jpg")
    (stage / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    if only:
        # A sitemap listing urls this run did not write would advertise 404s.
        print(f"FH_ONLY={','.join(sorted(only))}: {len(picked):,} of {len(routes):,} pages, "
              "no sitemap — a partial tree, for local work, not for deploy")
    else:
        write_sitemap(stage, picked)
    shutil.copytree(ROOT / "report", stage / "report")
    for f in (stage / "report").glob("*.html"):
        f.write_text(f.read_text().replace("{{WORDMARK}}", WORDMARK)
                     .replace("{{NAME}}", NAME).replace("{{FAVICON}}", favicon_tag().strip()))
    n_rec = stdsite.write_records(ROOT, news.STORIES)
    wk = stdsite.write_well_known(stage)

    shutil.rmtree(OUT, ignore_errors=True)
    stage.rename(OUT)
    if front:
        (ROOT / "dist/index.html").write_text(inline_preview(front))
    print(f"{len(picked):,} pages · {len(reg.schools)} schools · {len(reg.athletes):,} athletes"
          f" · {jobs} worker{'s' if jobs > 1 else ''} · links OK")
    print(f"standard.site: {n_rec} records"
          + (f" · published as {stdsite.PUB_URI}" if wk else " · unpublished (FH_PUB_URI unset)"))

if __name__ == "__main__":
    build()
