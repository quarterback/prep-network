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
from app.sports import BY_KEY, CATALOG  # noqa: E402

RECORDS = ROOT / "records"
OUT = ROOT / "dist/site"
BRAND = "FIELDHOUSE"
ASSOC = "JHSAA"
STATE = "Jefferson"
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


RAIL = ""  # populated in build()


def shell(title, body, crumb="", back=""):
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
<script>try{{var t=localStorage.getItem('fh-theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
<header class="fh-mast"><div class="wrap">
  <a class="fh-wordmark" href="/">{BRAND}</a>
  <nav class="fh-mast-nav">
    <a href="/scoreboard/">Scores</a>
    <a href="/#sports">Sports</a>
    <a href="/#schools">Schools</a>
    <a href="/#conferences">Conferences</a>
    <span class="fh-season">{ASSOC} · {SEASON_LABEL}</span>
    <button class="fh-swatch" data-theme-choice="varsity" aria-pressed="true" aria-label="Varsity scheme"></button>
    <button class="fh-swatch" data-theme-choice="bloom" aria-pressed="false" aria-label="Bloom scheme"></button>
  </nav>
</div></header>
{RAIL}
<main class="wrap">
{toolbar}
{body}
</main>
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
  <span>{BRAND.title()} — working title · {STATE} is a fictional state; all schools and people are invented</span>
  <a href="https://github.com/quarterback/prep-network">github.com/quarterback/prep-network</a>
</div></footer>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────── contest pieces


def contest_row(reg, c, show_sport=True):
    label = result_label(c)
    sport = BY_KEY[c.sport].name if show_sport and c.sport in BY_KEY else ""
    if isinstance(c, Meet):
        who = f"<span class='fh-name'><a href='{reg.url(c)}'>{esc(c.name)}</a></span>"
        vs = f"<span class='fh-plain fh-dim'>{esc(c.host or '')}</span>"
    else:
        who = (f"<span class='fh-plain'>{reg.school_link(c.away)} "
               f"<span class='fh-dim'>at</span> {reg.school_link(c.home)}</span>")
        vs = f"<span class='fh-name'><a href='{reg.url(c)}'>{esc(label) or 'Preview'}</a></span>"
    return (f"<div class='fh-row' style='--grid-cols:86px minmax(200px,2fr) minmax(80px,1fr) minmax(90px,1fr)'>"
            f"<span class='fh-dim tnum'>{esc(nice_date(c.date))}</span>{who}{vs}"
            f"<span class='fh-plain fh-dim'>{esc(sport)}</span></div>")


def contest_table(reg, contests, show_sport=True):
    rows = "".join(contest_row(reg, c, show_sport) for c in contests)
    return ("<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:86px minmax(200px,2fr) minmax(80px,1fr) minmax(90px,1fr)'>"
            "<div class='fh-thead'><span class='fh-th'>Date</span><span class='fh-th'>Matchup</span>"
            "<span class='fh-th'>Result</span><span class='fh-th'>" +
            ("Sport" if show_sport else "") + "</span></div>" + rows + "</div></div>")


def standings_tables(reg, sport):
    rec = reg.records_for(sport.key)
    if not rec:
        return ""
    by_group = defaultdict(list)
    for school, r in rec.items():
        grp = sport.champ_group(reg.schools[school]["classification"])
        by_group[grp].append((school, r))
    blocks = []
    for grp in sorted(by_group, key=lambda g: (len(g), g)):
        rows = sorted(by_group[grp], key=lambda kv: (-(kv[1]["w"]), kv[1]["l"], kv[0]))
        body = "".join(
            f"<div class='fh-row{' first' if i == 0 else ''}' style='--grid-cols:26px 24px minmax(150px,1fr) 56px 56px minmax(90px,1fr)'>"
            f"<span class='fh-rank'>{i+1}</span>{reg.crest(s,'xs')}"
            f"<span class='fh-name'>{reg.school_link(s)}</span>"
            f"<span class='fh-num tnum'>{r['w']}-{r['l']}{('-'+str(r['t'])) if r.get('t') else ''}</span>"
            f"<span class='fh-num tnum fh-dim'>{r['cw']}-{r['cl']}</span>"
            f"<span class='fh-plain fh-dim'>{esc(reg.conf_of.get(s,''))}</span></div>"
            for i, (s, r) in enumerate(rows[:16]))
        blocks.append(
            f"<div class='fh-section'><div class='fh-group'><h3>{esc(grp)}</h3>{class_chip(grp) if grp[0].isdigit() else ''}</div>"
            "<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:26px 24px minmax(150px,1fr) 56px 56px minmax(90px,1fr)'>"
            "<div class='fh-thead'><span class='fh-th'></span><span class='fh-th'></span>"
            "<span class='fh-th'>School</span><span class='fh-th'>Overall</span>"
            "<span class='fh-th'>Conf</span><span class='fh-th'>Conference</span></div>"
            f"{body}</div></div></div>")
    return "".join(blocks)


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
    crumb = (f"<a href='/'>{BRAND.title()}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}")
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
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}"
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
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/sports/{sport.key}/'>{esc(sport.name)}</a> › {esc(c.name)}"
    return shell(f"{c.name} — {sport.name}", body, crumb, f"← {sport.name}|/sports/{sport.key}/")


def render_sport(reg, sport):
    contests = sorted(reg.by_sport.get(sport.key, []), key=lambda c: c.date or "")
    played = [c for c in contests if (c.date or "") <= TODAY]
    upcoming = [c for c in contests if (c.date or "") > TODAY]
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">{esc(sport.name)}</div>
  <div class="meta">{esc(sport.season.title())} · {SEASON_LABEL} · <span class="tnum">{len(contests):,}</span> contests</div></div>
  <div class="side">{''.join(class_chip(g) if g[0].isdigit() else f"<span class='fh-tag'>{esc(g)}</span>" for g in dict.fromkeys(sport.champ_group(c) for c in ("6A","5A","4A","3A","2A","1A")))}</div>
</div>
"""
    if sport.shape.value in ("game", "dual"):
        body += f"<div class='fh-section'><h2>Standings</h2>{standings_tables(reg, sport)}</div>"
    body += f"<div class='fh-section'><h2>Latest results</h2>{contest_table(reg, list(reversed(played[-25:])), show_sport=False)}</div>"
    if upcoming:
        body += f"<div class='fh-section'><h2>Upcoming</h2>{contest_table(reg, upcoming[:15], show_sport=False)}</div>"
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/#sports'>Sports</a> › {esc(sport.name)}"
    return shell(f"{sport.name} — {BRAND.title()}", body, crumb, "← All sports|/#sports")


def render_school(reg, s):
    name = s["name"]
    conf = reg.conf_of.get(name, "")
    conf_html = f"<a href='/conferences/{reg.conf_slug.get(conf,'')}/'>{esc(conf)}</a>" if conf else ""
    contests = reg.by_school.get(name, [])
    by_sport = defaultdict(list)
    for c in contests:
        by_sport[c.sport].append(c)
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
<div class="fh-idhdr">
  <span class="fh-crest lg {crest_class(name)}">{esc(monogram(name))}</span>
  <div><div class="name">{esc(name)}</div>
  <div class="meta">{esc(s['mascot'])} · {esc(s['city'])} · {conf_html} · enrollment <span class="tnum">{s['enrollment']:,}</span></div></div>
  <div class="side">{class_chip(s['classification'])}</div>
</div>
{''.join(sections)}
"""
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/#schools'>Schools</a> › {esc(name)}"
    return shell(f"{name} — {BRAND.title()}", body, crumb, "← Schools|/#schools")


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
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/#conferences'>Conferences</a> › {esc(conf['name'])}"
    return shell(f"{conf['name']} — {BRAND.title()}", body, crumb, "← Conferences|/#conferences")


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
    crumb = f"<a href='/'>{BRAND.title()}</a> › {reg.school_link(school)} › {esc(name)}"
    return shell(f"{name} — {school}", body, crumb, f"← {school}|{reg.school_url(school)}")


def render_scoreboard(reg):
    import datetime as dt
    t = dt.date.fromisoformat(TODAY)
    lo, hi = (t - dt.timedelta(days=6)).isoformat(), (t + dt.timedelta(days=6)).isoformat()
    window = [c for c in reg.contests if c.date and lo <= c.date <= hi]
    by_sport = defaultdict(list)
    for c in sorted(window, key=lambda c: c.date or ""):
        by_sport[c.sport].append(c)
    sections = []
    for key in sorted(by_sport, key=lambda k: (SEASON_ORDER.get(BY_KEY[k].season, 3), BY_KEY[k].name)):
        sp = BY_KEY[key]
        sections.append(
            f"<div class='fh-section'><div class='fh-group'><h3><a href='/sports/{key}/'>{esc(sp.name)}</a></h3>"
            f"<span class='fh-tag'>{len(by_sport[key])} contests</span></div>"
            + contest_table(reg, by_sport[key][:24], show_sport=False) + "</div>")
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">Scoreboard</div>
  <div class="meta">{esc(nice_date(lo))} – {esc(nice_date(hi))} · <span class="tnum">{len(window):,}</span> contests · <span class="tnum">{len(by_sport)}</span> sports</div></div>
  <div class="side"></div>
</div>
{''.join(sections)}
"""
    crumb = f"<a href='/'>{BRAND.title()}</a> › Scoreboard"
    return shell(f"Scoreboard — {BRAND.title()}", body, crumb)


def render_front(reg):
    # sport directory grouped by season
    groups = []
    for season in ("fall", "winter", "spring"):
        cards = "".join(
            f"<a class='fh-scard' href='/sports/{sp.key}/'>"
            f"<div class='mname'>{esc(sp.name)}</div>"
            f"<div class='mmeta'>{len(reg.by_sport.get(sp.key, [])):,} contests</div></a>"
            for sp in sorted(CATALOG, key=lambda s: s.name) if sp.season == season and reg.by_sport.get(sp.key))
        groups.append(f"<div class='fh-group'><h3>{season.title()}</h3></div><div class='fh-strip'>{cards}</div>")

    # fall champions
    champs = []
    for c in reg.contests:
        if isinstance(c, Game) and "Championship" in c.name and c.status == "final":
            sp = BY_KEY[c.sport]
            grp = c.name.split("JHSAA ")[1].split(" Championship")[0] if "JHSAA " in c.name else ""
            champs.append((sp.name, grp, c.winner, c))
        elif isinstance(c, Meet) and "Championships" in c.name and c.team_scores:
            sp = BY_KEY[c.sport]
            top = next((t for t in c.team_scores if t.rank == 1), None)
            if top:
                grp = c.name.split("JHSAA ")[1].split(f" {sp.name}")[0] if "JHSAA " in c.name else ""
                champs.append((sp.name, grp, top.school, c))
    champs.sort(key=lambda t: (t[0], t[1]))
    def grp_chip(grp):
        if grp and grp[0].isdigit():
            return class_chip(grp)
        return f"<span class='fh-tag'>{esc(grp or 'Open')}</span>"

    champ_rows = "".join(
        f"<div class='fh-row' style='--grid-cols:minmax(130px,1.1fr) 58px 24px minmax(150px,1fr) 90px'>"
        f"<span class='fh-plain fh-dim'>{esc(spname)}</span><span>{grp_chip(grp)}</span>"
        f"{reg.crest(winner,'xs')}<span class='fh-name'>{reg.school_link(winner)}</span>"
        f"<span class='fh-plain'><a href='{reg.url(c)}'>Final</a></span></div>"
        for spname, grp, winner, c in champs if winner)

    # directory
    dir_rows = "".join(
        f"<a class='fh-row' href='/schools/{s['slug']}/' "
        "style='--grid-cols:24px minmax(150px,1.2fr) 52px minmax(110px,1fr) minmax(110px,1fr) 44px'>"
        f"{reg.crest(s['name'],'xs')}<span class='fh-name'>{esc(s['name'])}</span>"
        f"<span>{class_chip(s['classification'])}</span>"
        f"<span class='fh-plain fh-dim'>{esc(s['city'])}</span>"
        f"<span class='fh-plain fh-dim'>{esc(s['conference'])}</span>"
        f"<span class='fh-num tnum'>{len(s.get('sports', []))}</span></a>"
        for s in sorted(reg.schools.values(), key=lambda s: s["name"]))
    conf_rows = "".join(
        f"<a class='fh-row' href='/conferences/{slug}/' style='--grid-cols:minmax(150px,1fr) minmax(100px,1fr) 44px'>"
        f"<span class='fh-name'>{esc(c['name'])}</span><span class='fh-plain fh-dim'>{esc(c['area'])}</span>"
        f"<span class='fh-num tnum'>{len(c['members'])}</span></a>"
        for slug, c in sorted(reg.confs.items(), key=lambda kv: kv[1]["name"]))

    body = f"""
<div class="fh-section" id="sports" style="margin-top:18px"><h2>Sports</h2>{''.join(groups)}</div>
<div class="fh-section"><h2>Fall champions</h2>
<div class="fh-tablescroll"><div class="fh-table" style="--grid-cols:minmax(130px,1.1fr) 58px 24px minmax(150px,1fr) 90px">
<div class="fh-thead"><span class="fh-th">Sport</span><span class="fh-th">Division</span><span class="fh-th"></span>
<span class="fh-th">Champion</span><span class="fh-th">Result</span></div>{champ_rows}</div></div></div>
<div class="fh-board">
  <div class="fh-section" id="schools" style="margin-top:0"><h2>Schools</h2>
  <div class="fh-tablescroll"><div class="fh-table" style="--grid-cols:24px minmax(150px,1.2fr) 52px minmax(110px,1fr) minmax(110px,1fr) 44px">
  <div class="fh-thead"><span class="fh-th"></span><span class="fh-th">School</span><span class="fh-th">Class</span>
  <span class="fh-th">City</span><span class="fh-th">Conference</span><span class="fh-th num">Sports</span></div>
  {dir_rows}</div></div></div>
  <div class="fh-rail"><div class="fh-section" id="conferences" style="margin-top:0"><h2>Conferences</h2>
  <div class="fh-panel"><div class="fh-table narrow" style="--grid-cols:minmax(150px,1fr) minmax(100px,1fr) 44px">
  <div class="fh-thead"><span class="fh-th">Conference</span><span class="fh-th">Area</span><span class="fh-th num">Schools</span></div>
  {conf_rows}</div></div></div></div>
</div>
"""
    return shell(f"{BRAND.title()} — {ASSOC} · {SEASON_LABEL}", body)


# ──────────────────────────────────────────────────────────── write + verify


def link_check(pages):
    targets = set(pages) | {"/style.css"}
    broken = []
    for url, text in pages.items():
        for href in re.findall(r"href=['\"](/[^'\"#]*)", text):
            if href.startswith("/fonts/"):
                if not (ROOT / "site/fonts" / href.split("/")[-1]).exists():
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
    global RAIL
    reg = Registry()
    RAIL = build_rail(reg)

    pages = {"/": render_front(reg), "/scoreboard/": render_scoreboard(reg)}
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
    shutil.copytree(ROOT / "site/fonts", OUT / "fonts")
    (ROOT / "dist").mkdir(exist_ok=True)
    (ROOT / "dist/index.html").write_text(inline_preview(pages["/"]))
    print(f"{len(pages):,} pages · {len(reg.schools)} schools · {len(reg.athletes):,} athletes · links OK")


if __name__ == "__main__":
    build()
