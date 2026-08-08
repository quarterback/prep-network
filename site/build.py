"""
Static reference-site build: JHSAA records -> a cross-linked page tree.

Page types: front · scoreboard · sport landings · meet/game/dual contest pages
· school pages · conference mini-fronts · athlete pages. Every page carries the
persistent score rail. The build fails on a broken internal link.

    python3 site/build.py        # writes dist/site/ (+ dist/index.html preview)
"""

from __future__ import annotations

import base64
import hashlib
import html
import pathlib
import re
import shutil
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import records_io  # noqa: E402
from app.shapes import Dual, Game, Meet  # noqa: E402
from app.brand import ASSOC, NAME, TITLE, WORDMARK, page_title  # noqa: E402
from app.sports import BY_KEY, CATALOG  # noqa: E402

import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("fh_news", ROOT / "site/news.py")
news = _ilu.module_from_spec(_spec); _spec.loader.exec_module(news)
_ispec = _ilu.spec_from_file_location("fh_icons", ROOT / "site/icons.py")
icons = _ilu.module_from_spec(_ispec); _ispec.loader.exec_module(icons)
_pspec = _ilu.spec_from_file_location("fh_sponsors", ROOT / "site/sponsors.py")
sponsors = _ilu.module_from_spec(_pspec); _pspec.loader.exec_module(sponsors)
_sspec = _ilu.spec_from_file_location("fh_stdsite", ROOT / "site/standardsite.py")
stdsite = _ilu.module_from_spec(_sspec); _sspec.loader.exec_module(stdsite)

RECORDS = ROOT / "records"
OUT = ROOT / "dist/site"
FAVICON = "/favicon.svg"   # replaced in build() if site/favicon.* exists
TODAY = "2027-01-16"          # the demo date the generator built around
SEASON_LABEL = "2026–27"
CREST_CLASSES = 12
CLASS_LABEL = {"9": "Fr", "10": "So", "11": "Jr", "12": "Sr"}
SEASON_ORDER = {"fall": 0, "winter": 1, "spring": 2}


def esc(t): return html.escape(re.sub(r"\s{2,}", " ", (t or "")).strip(), quote=True)
def slugify(t): return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-") or "x"


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
        if name not in self.schools:
            return ""
        return f"<span class='fh-crest {size} {crest_class(name)}'>{esc(monogram(name))}</span>"

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


def build_menus(reg):
    """Nav dropdowns: sports by season, resources by audience."""
    global SPORT_MENU, RES_MENU, DRAWER_SPORTS, DRAWER_RES
    cols = []
    for season in ("fall", "winter", "spring"):
        links = "".join(
            f"<a href='/sports/{sp.key}/'>{icons.icon(sp.key, 'fh-ic sm')}{esc(sp.name)}</a>"
            for sp in sorted(CATALOG, key=lambda s: s.name)
            if sp.season == season and reg.by_sport.get(sp.key))
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
            f"<a href='/sports/{sp.key}/'>{icons.icon(sp.key, 'fh-ic sm')}{esc(sp.name)}</a>"
            for sp in sorted(CATALOG, key=lambda s: s.name)
            if sp.season == season and reg.by_sport.get(sp.key))
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


def shell(title, body, crumb="", back="", story=None):
    pill = ""
    if back:
        label, url = back.split("|")
        pill = f"<a class='fh-pill' href='{url}'>{esc(label)}</a>"
    toolbar = f"<div class='fh-toolbar'><span class='fh-crumb'>{crumb}</span>{pill}</div>" if crumb else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="/style.css">
{favicon_tag()}{stdsite.head_links(story)}
<script>try{{var t=localStorage.getItem('fh-theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
{icons.sprite()}
<input type="checkbox" id="fh-navtoggle" class="fh-navtoggle" hidden>
<header class="fh-mast"><div class="wrap">
  <a class="fh-wordmark" href="/">{WORDMARK}</a>
  <label class="fh-burger" for="fh-navtoggle" aria-label="Menu">
    <span></span><span></span><span></span>
  </label>
  <nav class="fh-mast-nav">
    <a href="/scoreboard/">Scores</a>
    <div class="fh-menu"><button type="button">Sports &amp; Activities ▾</button><div class="fh-drop">{SPORT_MENU}</div></div>
    <div class="fh-menu"><button type="button">Schools ▾</button><div class="fh-drop cols">
      <a href="/schools/">All member schools</a><a href="/conferences/">Conferences</a>
      <a href="/schools/#6A">6A</a><a href="/schools/#5A">5A</a><a href="/schools/#4A">4A</a>
      <a href="/schools/#3A">3A</a><a href="/schools/#2A">2A</a><a href="/schools/#1A">1A</a></div></div>
    <a href="/championships/">Championships</a>
    <a href="/news/">News</a>
    <div class="fh-menu"><button type="button">Resources ▾</button><div class="fh-drop">{RES_MENU}</div></div>
    <span class="fh-season">{ASSOC} · {SEASON_LABEL}</span>
    <button class="fh-swatch" data-theme-choice="varsity" aria-pressed="true" aria-label="Varsity scheme"></button>
    <button class="fh-swatch" data-theme-choice="bloom" aria-pressed="false" aria-label="Bloom scheme"></button>
    <button class="fh-swatch" data-theme-choice="meadow" aria-pressed="false" aria-label="Meadow scheme"></button>
    <button class="fh-swatch" data-theme-choice="evergreen" aria-pressed="false" aria-label="Evergreen scheme"></button>
    <button class="fh-swatch" data-theme-choice="harbor" aria-pressed="false" aria-label="Harbor scheme"></button>
    <button class="fh-swatch" data-theme-choice="citrus" aria-pressed="false" aria-label="Citrus scheme"></button>
  </nav>
</div></header>
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
  {DRAWER_SPORTS}
  {DRAWER_RES}
</nav>
{RAIL}
<main class="wrap">
{toolbar}
{body}
</main>
<script>{FACET_JS}{CONF_PICKER_JS}</script>
<script>
(function () {{
  var chips = document.querySelectorAll(".fh-swatch");
  function apply(name) {{
    if (name === "varsity") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", name);
    chips.forEach(function (c) {{
      c.setAttribute("aria-pressed", c.getAttribute("data-theme-choice") === name ? "true" : "false");
    }});
    try {{ localStorage.setItem("fh-theme", name === "varsity" ? "" : name); }} catch (e) {{}}
  }}
  chips.forEach(function (c) {{
    c.addEventListener("click", function () {{ apply(c.getAttribute("data-theme-choice")); }});
  }});
  var t = null;
  try {{ t = localStorage.getItem("fh-theme"); }} catch (e) {{}}
  if (t) apply(t);
}})();
</script>
<footer class="fh-foot"><div class="wrap">
  <div class="fh-sponsors">{sponsor_rail()}</div>
  <div class="fh-footmark">{WORDMARK}</div>
</div></footer>
</body>
</html>
"""


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
    return (f"{reg.school_link(pairs[0][0])} <b class='tnum'>{pairs[0][1]}</b>, "
            f"{reg.school_link(pairs[1][0])} <b class='tnum'>{pairs[1][1]}</b>")


def meet_line(reg, c):
    """The useful result for a meet-shaped activity, in its own terms."""
    if not getattr(c, "events", None):
        return ""
    top = next((t for t in c.team_scores if t.rank == 1), None)
    if top:
        return f"{esc(c.name)} — won by {reg.school_link(top.school)}"
    return esc(c.name)


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
    body = f"""
<div class="fh-score">
  <div class="side">{reg.crest(c.away,'lg')}<div class="tn">{reg.school_link(c.away)}</div></div>
  <div class="mid"><div class="big tnum">{score}</div>
  <div class="st">{esc(status)} · {esc(nice_date(c.date))}</div></div>
  <div class="side">{reg.crest(c.home,'lg')}<div class="tn">{reg.school_link(c.home)}</div></div>
</div>
{periods}
"""
    crumb = (f"<a href='/'>{NAME}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}")
    return shell(f"{c.name} — {sport.name}", body, crumb, f"← {sport.name}|/sports/{sport.key}/")


def render_dual(reg, c: Dual):
    sport = BY_KEY[c.sport]
    rows = []
    for line in c.lines:
        hw = line.winner == "home"
        hn = ", ".join(reg.athlete_link(p.name, c.home) for p in line.home) or "—"
        an = ", ".join(reg.athlete_link(p.name, c.away) for p in line.away) or "—"
        rows.append(
            f"<div class='fh-row' style='--grid-cols:56px minmax(140px,1fr) minmax(140px,1fr) 96px'>"
            f"<span class='fh-rank'>{esc(str(line.kind)[:8].title() if not str(line.kind).isdigit() else line.kind)} {line.slot if line.kind in ('singles','doubles') else ''}</span>"
            f"<span class='fh-plain{' fh-mark' if not hw else ''}'>{an}</span>"
            f"<span class='fh-plain{' fh-mark' if hw else ''}'>{hn}</span>"
            f"<span class='fh-num tnum'>{esc(line.score or '')}</span></div>")
    score = (f"{c.away_points:g}&nbsp;–&nbsp;{c.home_points:g}" if c.home_points is not None else "—")
    body = f"""
<div class="fh-score">
  <div class="side">{reg.crest(c.away,'lg')}<div class="tn">{reg.school_link(c.away)}</div></div>
  <div class="mid"><div class="big tnum">{score}</div>
  <div class="st">{esc(nice_date(c.date))}</div></div>
  <div class="side">{reg.crest(c.home,'lg')}<div class="tn">{reg.school_link(c.home)}</div></div>
</div>
<div class="fh-section"><h2>Lines</h2>
<div class="fh-tablescroll"><div class="fh-table" style="--grid-cols:56px minmax(140px,1fr) minmax(140px,1fr) 96px">
<div class="fh-thead"><span class="fh-th"></span><span class="fh-th">{esc(c.away)}</span>
<span class="fh-th">{esc(c.home)}</span><span class="fh-th">Score</span></div>
{''.join(rows)}</div></div></div>
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}"
    return shell(f"{c.name} — {sport.name}", body, crumb, f"← {sport.name}|/sports/{sport.key}/")


def render_meet(reg, c: Meet):
    sport = BY_KEY[c.sport]
    scores = ""
    if c.team_scores:
        rows = "".join(
            f"<div class='fh-row{' first' if t.rank == 1 else ''}' style='--grid-cols:26px minmax(150px,1fr) 56px'>"
            f"<span class='fh-rank'>{t.rank}</span><span class='fh-name'>{reg.school_link(t.school)}</span>"
            f"<span class='fh-num fh-mark'>{t.points:g}</span></div>"
            for t in sorted(c.team_scores, key=lambda t: t.rank or 99)[:14])
        scores = (f"<div class='fh-section'><h2>Team scores</h2>"
                  "<div class='fh-panel' style='max-width:460px'><div class='fh-table narrow' "
                  "style='--grid-cols:26px minmax(150px,1fr) 56px'>" + rows + "</div></div></div>")
    blocks = []
    for ev in c.events:
        rows = []
        for e in ev.entries[:30]:
            who = reg.athlete_link(e.competitors[0].name, e.school) if e.competitors else "—"
            yr = CLASS_LABEL.get((e.competitors[0].year or "") if e.competitors else "", "")
            mark = esc(e.mark.raw) if e.mark and e.mark.raw else ""
            rows.append(
                f"<div class='fh-row{' first' if e.place == 1 else ''}' "
                f"style='--grid-cols:34px minmax(150px,1.2fr) 36px minmax(130px,1fr) 90px'>"
                f"<span class='fh-rank'>{e.place or ''}</span><span class='fh-name'>{who}</span>"
                f"<span class='fh-dim'>{yr}</span>"
                f"<span class='fh-plain'>{reg.school_link(e.school)}</span>"
                f"<span class='fh-mark'>{mark}</span></div>")
        blocks.append(
            f"<div class='fh-evhead'><h4>{esc(ev.name)}</h4></div>"
            "<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:34px minmax(150px,1.2fr) 36px minmax(130px,1fr) 90px'>"
            "<div class='fh-thead'><span class='fh-th'>Pl</span><span class='fh-th'>Athlete</span>"
            "<span class='fh-th'>Yr</span><span class='fh-th'>School</span><span class='fh-th'>Mark</span></div>"
            f"{''.join(rows)}</div></div>")
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">{esc(c.name)}</div>
  <div class="meta">{esc(nice_date(c.date))} · {esc(c.host or '')} · <a href='/sports/{sport.key}/'>{esc(sport.name)}</a></div></div>
  <div class="side"></div>
</div>
{scores}
<div class="fh-section"><h2>{'Results' if c.events else 'Scheduled'}</h2>{''.join(blocks) or ''}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}"
    return shell(f"{c.name} — {sport.name}", body, crumb, f"← {sport.name}|/sports/{sport.key}/")


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


def sport_header(reg, sp, active=""):
    groups = list(dict.fromkeys(sp.champ_group(c) for c in ("6A", "5A", "4A", "3A", "2A", "1A")))
    chips = "".join(class_chip(g) if g[0].isdigit() else f"<span class='fh-tag'>{esc(g)}</span>"
                    for g in groups)
    return f"""
<div class="fh-idhdr sport">
  <span class="fh-sportmark">{icons.icon(sp.key, 'fh-ic lg')}</span>
  <div><div class="name">{esc(sp.name)}</div>
  <div class="meta">{esc(sp.season.title())} · {SEASON_LABEL} · championship divisions: {chips}</div></div>
  <div class="side"></div>
</div>
{sport_nav(sp, active)}
"""


def sport_groups(sp):
    return list(dict.fromkeys(sp.champ_group(c) for c in ("6A", "5A", "4A", "3A", "2A", "1A")))


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
        ("division", "Classification", [(v, class_chip(v)) for v, _ in [('6A', '6A'), ('5A', '5A'), ('4A', '4A'), ('3A', '3A'), ('2A', '2A'), ('1A', '1A')]]),
        ("status", "Status", [("final", "Final"), ("upcoming", "Upcoming"),
                              ("changed", "Postponed / cancelled")]),
    ], note="Filters combine; links are shareable")
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
    return shell(page_title(f"{sport.name}"), body, crumb)


def _champ_winner(c):
    if isinstance(c, Game):
        return c.winner or c.home
    order = sorted(c.team_scores, key=lambda t: t.rank or 99)
    return order[0].school if order else ""


def render_school(reg, s):
    """A school page is a team hub: who we are, what just happened, what's
    next, where we stand — then every team, season by season."""
    name = s["name"]
    conf = reg.conf_of.get(name, "")
    conf_html = f"<a href='/conferences/{reg.conf_slug.get(conf,'')}/'>{esc(conf)}</a>" if conf else ""
    contests = sorted(reg.by_school.get(name, []), key=lambda c: c.date or "")
    played = [c for c in reversed(contests) if (c.date or "") <= TODAY]
    upcoming = [c for c in contests if (c.date or "") > TODAY]

    latest = []
    for c in played:
        line = meet_line(reg, c) if isinstance(c, Meet) else score_line(reg, c)
        if line:
            latest.append(score_row(reg.url(c), line,
                                    f"{esc(BY_KEY[c.sport].name)} · {esc(nice_date(c.date))}"))
        if len(latest) >= 6:
            break
    nxt = [score_row(reg.url(c), f"{matchup_line(reg, c)}", f"{esc(BY_KEY[c.sport].name)}")
           for c in upcoming[:6]]

    hub = ""
    if latest or nxt:
        cols = []
        if latest:
            cols.append(f"<section><h2>Latest</h2><div class='fh-results'>{''.join(latest)}</div></section>")
        if nxt:
            cols.append(f"<section><h2>Next</h2><div class='fh-results'>{''.join(nxt)}</div></section>")
        hub = f"<div class='fh-overview n{len(cols)}'>{''.join(cols)}</div>"

    # Teams, season by season — the school's full sponsorship with records.
    by_sport = defaultdict(list)
    for c in contests:
        by_sport[c.sport].append(c)
    team_rows = defaultdict(list)
    for key in sorted(s.get("sports", []), key=lambda k: BY_KEY[k].name):
        sp = BY_KEY[key]
        rec = reg.records_for(key).get(name) if sp.shape.value != "meet" else None
        rec_html = f"<span class='tnum'>{_wlt(rec)}</span>" if rec else ""
        team_rows[sp.season].append(
            f"<a class='fh-teamrow' href='/sports/{key}/'>{icons.icon(key, 'fh-ic sm')}"
            f"<span class='nm'>{esc(sp.name)}</span>{rec_html}</a>")
    seasons = "".join(
        f"<div class='fh-teamseason'><h3>{ssn.title()}</h3>{''.join(team_rows[ssn])}</div>"
        for ssn in ("fall", "winter", "spring") if team_rows.get(ssn))

    sections = []
    for key in sorted(s.get("sports", []), key=lambda k: (SEASON_ORDER.get(BY_KEY[k].season, 3), BY_KEY[k].name)):
        sp = BY_KEY[key]
        mine = sorted(by_sport.get(key, []), key=lambda c: c.date or "")
        if not mine:
            continue
        rec = reg.records_for(key).get(name)
        rec_html = f" · <span class='tnum'>{rec['w']}-{rec['l']}</span>" if rec else ""
        sections.append(
            f"<div class='fh-section'><div class='fh-group'><h3><a href='/sports/{key}/'>{esc(sp.name)}</a></h3>"
            f"<span class='fh-tag'>{esc(sp.season.title())}</span>{rec_html}</div>"
            + contest_table(reg, mine[-14:], show_sport=False) + "</div>")

    body = f"""
<div class="fh-idhdr school">
  <span class="fh-crest lg {crest_class(name)}">{esc(monogram(name))}</span>
  <div><div class="name">{esc(name)}</div>
  <div class="meta">{esc(s['mascot'])} · {esc(s['city'])} · {conf_html}</div></div>
  <div class="side">{class_chip(s['classification'])}</div>
</div>
{hub}
<div class="fh-section"><div class="fh-group"><h2>Teams</h2></div>
<div class="fh-teamgrid">{seasons}</div></div>
{''.join(sections)}
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/schools/'>Schools</a> › {esc(name)}"
    return shell(page_title(f"{name}"), body, crumb, "← Schools|/schools/")


def render_conference(reg, conf):
    members = sorted(conf["members"])
    member_rows = "".join(
        f"<a class='fh-row' href='{reg.school_url(m)}' style='--grid-cols:24px minmax(150px,1fr) 52px minmax(110px,1fr) 56px'>"
        f"{reg.crest(m,'xs')}<span class='fh-name'>{esc(m)}</span>"
        f"<span>{class_chip(reg.schools[m]['classification'])}</span>"
        f"<span class='fh-plain fh-dim'>{esc(reg.schools[m]['city'])}</span>"
        f"<span class='fh-num tnum'>{len(reg.schools[m].get('sports', []))}</span></a>"
        for m in members if m in reg.schools)
    mset = set(members)
    week = [c for c in reg.contests
            if c.date and abs((__import__('datetime').date.fromisoformat(c.date) -
                               __import__('datetime').date.fromisoformat(TODAY)).days) <= 6
            and any(sch in mset for sch in reg.contest_schools(c))]
    week.sort(key=lambda c: c.date or "")
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">{esc(conf['name'])}</div>
  <div class="meta">{esc(conf['area'])} · <span class="tnum">{len(members)}</span> member schools</div></div>
  <div class="side"></div>
</div>
<div class="fh-board">
  <div><div class="fh-section" style="margin-top:0"><h2>This week</h2>{contest_table(reg, week[:20])}</div></div>
  <div class="fh-rail"><div class="fh-section" style="margin-top:0"><h2>Members</h2>
  <div class="fh-tablescroll"><div class="fh-table narrow" style="--grid-cols:24px minmax(150px,1fr) 52px minmax(110px,1fr) 56px">
  <div class="fh-thead"><span class="fh-th"></span><span class="fh-th">School</span><span class="fh-th">Class</span>
  <span class="fh-th">City</span><span class="fh-th num">Sports</span></div>{member_rows}</div></div></div></div>
</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/#conferences'>Conferences</a> › {esc(conf['name'])}"
    return shell(page_title(f"{conf['name']}"), body, crumb, "← Conferences|/#conferences")


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
                won = (line.winner == "home") == on_home
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
    return shell(f"{name} — {school}", body, crumb, f"← {school}|{reg.school_url(school)}")


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
        ("division", "Classification", [(v, class_chip(v)) for v in ('6A', '5A', '4A', '3A', '2A', '1A')]),
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
    return shell(page_title(f"Scoreboard"), body, crumb)


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


def render_championships(reg):
    """A championship record book: sports as headings, divisions as lines.
    One striped mega-table read as a query response; this reads as the page an
    association would print."""
    by_sport = defaultdict(list)
    for sp, grp, c in champ_finals(reg):
        by_sport[sp].append((grp, c))

    blocks = []
    for sp in sorted(by_sport, key=lambda s: (SEASON_ORDER.get(s.season, 3), s.name)):
        lines = []
        for grp, c in sorted(by_sport[sp], key=lambda t: t[0]):
            if isinstance(c, Game):
                winner, detail = c.winner, f"{c.home_score}\u2013{c.away_score}"
            else:
                top = next((t2 for t2 in c.team_scores if t2.rank == 1), None)
                winner, detail = (top.school if top else None), "Results"
            if not winner:
                continue
            lines.append(
                f"<div class='fh-champline' data-f-division='{esc(grp)}'>"
                f"<span class='dv'>{grp_chip(grp)}</span>"
                f"{reg.crest(winner,'xs')}"
                f"<span class='ch'>{reg.school_link(winner)}</span>"
                f"<a class='rs' href='{reg.url(c)}'>{esc(detail)}</a></div>")
        if lines:
            blocks.append(
                f"<section class='fh-champblock' data-f-season='{esc(sp.season)}'>"
                f"<h2>{icons.icon(sp.key, 'fh-ic sm')} <a href='/sports/{sp.key}/champions/'>{esc(sp.name)}</a>"
                f"<span class='ssn'>{esc(sp.season.title())}</span></h2>"
                f"{''.join(lines)}</section>")

    bar = facet_bar("ch", [
        ("season", "Season", [("fall", "Fall"), ("winter", "Winter"), ("spring", "Spring")]),
    ])
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">Championships</div>
  <div class="meta">{SEASON_LABEL} · winter and spring titles decide as those seasons end</div></div>
  <div class="side"></div>
</div>
{bar}
<div class="fh-filterable fh-champbook" id="ch">{''.join(blocks)}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › Championships"
    return shell(page_title(f"Championships"), body, crumb)


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
                                     [(v, class_chip(v)) for v in ("6A", "5A", "4A", "3A", "2A", "1A")])],
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
    return shell(page_title(f"Schools"), body, crumb)


def render_confs_index(reg):
    by_area = defaultdict(list)
    for slug, c in reg.confs.items():
        by_area[c["area"]].append((slug, c))
    blocks = []
    for area in sorted(by_area):
        rows = "".join(
            f"<a class='fh-conflink' href='/conferences/{slug}/'>"
            f"<span class='nm'>{esc(c['name'])}</span>"
            f"<span class='ct'>{esc(', '.join(sorted({reg.schools[m]['classification'] for m in c['members'] if m in reg.schools}, key=lambda x: '654321'.find(x[0]))))}</span></a>"
            for slug, c in sorted(by_area[area], key=lambda kv: kv[1]["name"]))
        blocks.append(f"<div class='fh-confgroup'><h4>{esc(area)}</h4>"
                      f"<div class='fh-schoollinks'>{rows}</div></div>")
    body = f"""
<div class="fh-idhdr">
  <div></div><div><div class="name">Conferences</div>
  <div class="meta">By region · leagues are geographic and mix classifications · <a href='/schools/'>browse by class</a></div></div>
  <div class="side"></div>
</div>
<div class="fh-confgrid">{''.join(blocks)}</div>
"""
    crumb = f"<a href='/'>{NAME}</a> › Conferences"
    return shell(page_title(f"Conferences"), body, crumb)


def render_story(reg, st):
    paras = "".join(f"<p>{esc(b)}</p>" for b in st["body"])
    body = f"""
<article class="fh-article">
  <div class="kk">{esc(st['kicker'])} · {esc(nice_date(st['date']))}</div>
  <h1>{esc(st['head'])}</h1>
  <p class="dek">{esc(st['dek'])}</p>
  {paras}
</article>
<p class="fh-more"><a href="/news/">More from the association →</a></p>
"""
    crumb = f"<a href='/'>{NAME}</a> › <a href='/news/'>News</a> › {esc(st['kicker'])}"
    return shell(page_title(f"{st['head']}"), body, crumb, "← News|/news/", story=st)


def render_news_index(reg):
    """Two lanes: activity/results coverage and association administration."""
    def lane(kind, title, blurb):
        items = "".join(
            f"<a class='fh-storyrow' href='/news/{st['slug']}/'>"
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
"""
    crumb = f"<a href='/'>{NAME}</a> › News"
    return shell(page_title(f"News"), body, crumb)


def season_chooser(reg, current="winter"):
    """Season tabs + that season's sports, at the top of the page.

    The first question is which season you are here for; the second is which
    sport or activity. Answer both above the fold, then get out of the way.
    """
    tabs = "".join(
        f"<button type='button' data-season='{sn}'{' class=on' if sn == current else ''}>"
        f"{sn.title()}</button>" for sn in ("fall", "winter", "spring"))
    panes = []
    for sn in ("fall", "winter", "spring"):
        tiles = "".join(
            f"<a class='fh-sporttile' href='/sports/{sp.key}/'>{icons.icon(sp.key)}"
            f"<span>{esc(sp.name)}</span></a>"
            for sp in sorted(CATALOG, key=lambda s: s.name)
            if sp.season == sn and reg.by_sport.get(sp.key))
        # every pane renders; JS collapses the inactive ones on load, so with
        # scripting off the visitor gets all three seasons rather than none
        panes.append(f"<div class='fh-sportgrid' data-season-pane='{sn}'>"
                     f"<h3 class='fh-seasonlabel'>{sn.title()}</h3>{tiles}</div>")
    return f"""
<section class="fh-seasons">
  <div class="fh-seasontabs">{tabs}<a class="all" href="/scoreboard/">Scoreboard →</a></div>
  {''.join(panes)}
</section>"""


def render_front(reg):
    """The front is a publication: one lead, secondaries at half its weight,
    briefs at a line each — then the structured material (scores, finder) in
    the rail beside it. Hierarchy, not a grid of equal cards."""
    import datetime as dt
    t = dt.date.fromisoformat(TODAY)

    stories = sorted(news.STORIES, key=lambda s: s["date"], reverse=True)
    lead, second = stories[0], stories[1:3]
    briefs = stories[3:9]

    lead_html = (
        f"<a class='fh-hero' href='/news/{lead['slug']}/'>"
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

    opts = "".join(
        f"<a class='fh-schoolhit' href='/schools/{s['slug']}/' "
        f"data-n='{esc((s['name'] + ' ' + s['city'] + ' ' + s['conference']).lower())}'>"
        f"{reg.crest(s['name'],'xs')}<span class='nm'>{esc(s['name'])}</span>"
        f"<span class='ct'>{esc(s['city'])}</span></a>"
        for s in sorted(reg.schools.values(), key=lambda s: s["name"]))

    body = f"""
{season_chooser(reg)}

<div class="fh-top">
  <div class="fh-newscol">
    {lead_html}
    <div class="fh-seconds">{second_html}</div>
    <div class="fh-briefs">
      <h2>Latest from the JHSAA</h2>
      {briefs_html}
      <p class="fh-more"><a href="/news/">All news →</a></p>
    </div>
  </div>
  <aside class="fh-side">
    <section class="fh-latest">
      <h2>Latest scores</h2>
      <div class="fh-results">{''.join(finals)}</div>
      <p class="fh-more"><a href="/scoreboard/">Full scoreboard →</a></p>
    </section>
    <section class="fh-finder">
      <h2>Find your school</h2>
      <input id="school-q" type="search" placeholder="School, town or conference"
             autocomplete="off" aria-label="Search member schools">
      <div class="fh-schoolhits" id="school-hits">{opts}</div>
      <p class="fh-more"><a href="/schools/">By conference</a> · <a href="/championships/">Championships</a></p>
    </section>
  </aside>
</div>

<script>
(function () {{
  var tabs = document.querySelectorAll(".fh-seasontabs button");
  document.querySelectorAll("[data-season-pane]").forEach(function (p) {{
    p.hidden = p.dataset.seasonPane !== "winter";
  }});
  document.querySelectorAll(".fh-seasonlabel").forEach(function (h) {{ h.hidden = true; }});
  tabs.forEach(function (b) {{
    b.addEventListener("click", function () {{
      tabs.forEach(function (o) {{ o.classList.toggle("on", o === b); }});
      document.querySelectorAll("[data-season-pane]").forEach(function (p) {{
        p.hidden = p.dataset.seasonPane !== b.dataset.season;
      }});
    }});
  }});
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
    return shell(TITLE, body)


# ──────────────────────────────────────────────────────────── write + verify


def favicon_tag() -> str:
    kind = ' type="image/svg+xml"' if FAVICON.endswith(".svg") else ""
    return f'\n<link rel="icon" href="{FAVICON}"{kind}>'


def pick_favicon() -> str:
    """Drop any favicon.* into site/ and it wins; otherwise fall back to the
    wordmark's initial so the tab is never blank mid-rename. Resolved before
    the pages render (they carry the href) and written after the output tree is
    cleared."""
    found = sorted((ROOT / "site").glob("favicon.*"))
    return "/" + found[0].name if found else "/favicon.svg"


def write_favicon(out: pathlib.Path) -> None:
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


def link_check(pages):
    targets = set(pages) | {"/style.css", FAVICON}
    broken = []
    for url, text in pages.items():
        for href in re.findall(r"href=['\"](/[^'\"#]*)", text):
            if href.startswith("/fonts/"):
                if not (ROOT / "site/fonts" / href.split("/")[-1]).exists():
                    broken.append(f"{url} -> {href}")
            elif href.startswith("/report/"):
                if not (ROOT / href.lstrip("/")).exists():
                    broken.append(f"{url} -> {href}")
            elif href not in targets:
                broken.append(f"{url} -> {href}")
    return broken


def inline_preview(front):
    css = (ROOT / "site/style.css").read_text()

    def font_uri(m):
        data = base64.b64encode((ROOT / "site/fonts" / m.group(1)).read_bytes()).decode()
        return f"url(data:font/woff2;base64,{data})"

    css = re.sub(r"url\('fonts/([^']+)'\)", font_uri, css)
    return front.replace('<link rel="stylesheet" href="/style.css">', f"<style>\n{css}\n</style>")


def build():
    global RAIL, FAVICON
    reg = Registry()
    FAVICON = pick_favicon()
    RAIL = build_rail(reg)
    build_menus(reg)

    pages = {"/": render_front(reg), "/scoreboard/": render_scoreboard(reg),
             "/schools/": render_schools_index(reg), "/conferences/": render_confs_index(reg),
             "/championships/": render_championships(reg),
             "/news/": render_news_index(reg)}
    for st in news.STORIES:
        pages[f"/news/{st['slug']}/"] = render_story(reg, st)
    for c in reg.contests:
        u = reg.url(c)
        if isinstance(c, Meet):
            pages[u] = render_meet(reg, c)
        elif isinstance(c, Dual):
            pages[u] = render_dual(reg, c)
        else:
            pages[u] = render_game(reg, c)
    for sp in CATALOG:
        if reg.by_sport.get(sp.key):
            pages[f"/sports/{sp.key}/"] = render_sport(reg, sp)
            pages[f"/sports/{sp.key}/standings/"] = render_sport_standings(reg, sp)
            if sp.shape.value != "meet":
                pages[f"/sports/{sp.key}/rankings/"] = render_sport_rankings(reg, sp)
            pages[f"/sports/{sp.key}/schedule/"] = render_sport_schedule(reg, sp)
            pages[f"/sports/{sp.key}/champions/"] = render_sport_champs(reg, sp)
    for s in reg.schools.values():
        pages[f"/schools/{s['slug']}/"] = render_school(reg, s)
    for slug, conf in reg.confs.items():
        pages[f"/conferences/{slug}/"] = render_conference(reg, conf)
    for a in reg.athletes.values():
        pages[f"/athletes/{a['slug']}/"] = render_athlete(reg, a)

    broken = link_check(pages)
    if broken:
        for b in broken[:20]:
            print("BROKEN:", b)
        raise SystemExit(f"{len(broken)} broken internal links")

    shutil.rmtree(OUT, ignore_errors=True)
    for url, text in pages.items():
        rel = "index.html" if url == "/" else url.strip("/") + "/index.html"
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    shutil.copy(ROOT / "site/style.css", OUT / "style.css")
    write_favicon(OUT)
    shutil.copytree(ROOT / "site/fonts", OUT / "fonts")
    shutil.copytree(ROOT / "report", OUT / "report")
    for f in (OUT / "report").glob("*.html"):
        f.write_text(f.read_text().replace("{{WORDMARK}}", WORDMARK)
                     .replace("{{NAME}}", NAME).replace("{{FAVICON}}", favicon_tag().strip()))
    n_rec = stdsite.write_records(ROOT, news.STORIES)
    wk = stdsite.write_well_known(OUT)
    (ROOT / "dist").mkdir(exist_ok=True)
    (ROOT / "dist/index.html").write_text(inline_preview(pages["/"]))
    print(f"{len(pages):,} pages · {len(reg.schools)} schools · {len(reg.athletes):,} athletes · links OK")
    print(f"standard.site: {n_rec} records"
          + (f" · published as {stdsite.PUB_URI}" if wk else " · unpublished (FH_PUB_URI unset)"))


if __name__ == "__main__":
    build()
