"""
Static reference-site build: parsed records -> a cross-linked page tree.

No framework, no server. Five repeatable page types — front, meet, school,
conference, athlete — rendered from one registry pass over the parsed records.
Every athlete, school, conference and meet has a URL; every name in every table
is a link. The build fails on a broken internal link.

    python3 site/build.py

Output lands at the repo root (index.html + meets/ schools/ conferences/
athletes/ + style.css + fonts/) so a zero-config static host serves it as-is.
dist/preview.html is a self-contained copy of the front page for the artifact.
"""

from __future__ import annotations

import base64
import hashlib
import html
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ingest.adapters import hytek_pdf  # noqa: E402

SPECIMEN = ROOT / "ingest/fixtures/specimens/hytek-meetmanager8-track.pdf"
BRAND = "FIELDHOUSE"  # working title
SEASON = "Track & Field · Spring 2026"

CREST_COLORS = [
    "#1d4ed8", "#0f766e", "#b45309", "#9d174d", "#4d7c0f", "#6d28d9",
    "#0e7490", "#b91c1c", "#3f6212", "#7c2d12", "#1e40af", "#86198f",
]

CLASS_LABEL = {"9": "Fr", "10": "So", "11": "Jr", "12": "Sr"}


def esc(text: str | None) -> str:
    return html.escape(clean(text or ""), quote=True)


def clean(text: str) -> str:
    return re.sub(r"\s{2,}", " ", text).strip()


def display_name(name: str) -> str:
    name = clean(name)
    if ", " in name:
        last, _, first = name.partition(", ")
        if first:
            return f"{first} {last}"
    return name


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", clean(text).lower()).strip("-")
    return s or "x"


def short_school(name: str) -> str:
    """Dense-cell form: 'Kaycee High School' -> 'Kaycee'."""
    s = clean(name)
    s = re.sub(r"\s+High School$", "", s)
    s = re.sub(r"\s+HS$", "", s)
    return s


def monogram(name: str) -> str:
    words = [w for w in short_school(name).split() if w[0].isalpha()]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return words[0][:2].upper() if words else "??"


def crest_color(name: str) -> str:
    h = int(hashlib.md5(short_school(name).encode()).hexdigest(), 16)
    return CREST_COLORS[h % len(CREST_COLORS)]


def short_meet(name: str) -> str:
    name = clean(name)
    name = re.sub(r"^WHSAA\s+", "", name)
    name = name.replace(" Track & Field Championships", " Championships")
    name = re.sub(r"\s+Regional (Track )?Meet$", " Regional", name)
    name = re.sub(r"\s+Track Meet$", "", name)
    return name


def class_chip(division: str | None) -> str:
    if not division:
        return ""
    d = division.split("-")[0]
    return f"<span class='fh-badge c{esc(d)}'>{esc(division)}</span>"


def yr_label(year: str | None) -> str:
    return CLASS_LABEL.get((year or "").strip(), (year or "").strip())


# ────────────────────────────────────────────────────────────── registry pass


class Registry:
    def __init__(self, meets):
        self.meets = meets
        self.meet_slug = {m.name: slugify(short_meet(m.name)) for m in meets}

        # conferences = the regionals (stand-in leagues for the POC)
        self.conferences: dict[str, dict] = {}
        self.school_conf: dict[str, str] = {}
        for m in meets:
            if "State" in m.name:
                continue
            cname = short_meet(m.name).replace(" Regional", "")
            slug = slugify(cname)
            conf = self.conferences.setdefault(
                slug, {"name": cname, "meet": m, "members": set()}
            )
            for s in m.schools:
                s = clean(s)
                conf["members"].add(s)
                self.school_conf.setdefault(s, slug)

        # schools
        self.schools: dict[str, dict] = {}
        for m in meets:
            for ev in m.events:
                for e in ev.entries:
                    s = clean(e.school)
                    rec = self.schools.setdefault(
                        s,
                        {
                            "name": s,
                            "slug": slugify(short_school(s)),
                            "divisions": set(),
                            "athletes": set(),
                            "results": [],
                        },
                    )
                    if ev.division:
                        rec["divisions"].add(ev.division)
                    rec["results"].append((m, ev, e))

        # athletes — every competitor, relay legs included
        self.athletes: dict[tuple[str, str], dict] = {}
        for m in meets:
            for ev in m.events:
                for e in ev.entries:
                    s = clean(e.school)
                    for c in e.competitors:
                        nm = display_name(c.name)
                        key = (nm, s)
                        a = self.athletes.setdefault(
                            key,
                            {
                                "name": nm,
                                "school": s,
                                "slug": f"{slugify(nm)}-{slugify(short_school(s))}",
                                "year": None,
                                "rows": [],
                            },
                        )
                        if c.year:
                            a["year"] = c.year
                        a["rows"].append((m, ev, e))
                        self.schools[s]["athletes"].add(key)

        # slug collision guard (two athletes, same name+school slug)
        seen: dict[str, int] = {}
        for a in self.athletes.values():
            n = seen.get(a["slug"], 0)
            seen[a["slug"]] = n + 1
            if n:
                a["slug"] = f"{a['slug']}-{n + 1}"

    # link helpers
    def meet_url(self, m) -> str:
        return f"/meets/{self.meet_slug[m.name]}/"

    def resolve_school(self, name: str) -> str | None:
        """The printout is inconsistent about its own school names — the
        results column says 'Hem High School' where the team rankings say
        'HEM High School', and long names truncate at the column edge
        ('Lingle Ft. Laramie  High Schoo'). Resolve case-insensitively, then
        by prefix in either direction, before giving up."""
        n = clean(name)
        if n in self.schools:
            return n
        folded = {s.casefold(): s for s in self.schools}
        hit = folded.get(n.casefold())
        if hit:
            return hit
        nf = n.casefold()
        for f, s in folded.items():
            if f.startswith(nf) or nf.startswith(f):
                return s
        return None

    def school_url(self, name: str) -> str:
        s = self.resolve_school(name)
        return f"/schools/{self.schools[s]['slug']}/" if s else ""

    def conf_url_for_school(self, name: str) -> str | None:
        s = self.resolve_school(name)
        slug = self.school_conf.get(s or "")
        return f"/conferences/{slug}/" if slug else None

    def athlete_url(self, name: str, school: str) -> str | None:
        s = self.resolve_school(school)
        a = self.athletes.get((display_name(name), s or clean(school)))
        return f"/athletes/{a['slug']}/" if a else None

    def school_link(self, name: str, short: bool = True) -> str:
        label = esc(short_school(name) if short else clean(name))
        url = self.school_url(name)
        return f"<a href='{url}'>{label}</a>" if url else label

    def athlete_link(self, name: str, school: str) -> str:
        url = self.athlete_url(name, school)
        nm = esc(display_name(name))
        return f"<a href='{url}'>{nm}</a>" if url else nm


# ─────────────────────────────────────────────────────────────────── shell


def shell(title: str, body: str, crumb: str = "", back: str = "") -> str:
    toolbar = ""
    if crumb:
        pill = f"<a class='fh-pill' href='{back.split('|')[1]}'>{esc(back.split('|')[0])}</a>" if back else ""
        toolbar = f"<div class='fh-toolbar'><span class='fh-crumb'>{crumb}</span>{pill}</div>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="fh-mast"><div class="wrap">
  <a class="fh-wordmark" href="/">{BRAND}</a>
  <nav class="fh-mast-nav">
    <a href="/#meets">Meets</a>
    <a href="/#schools">Schools</a>
    <a href="/#conferences">Conferences</a>
    <span class="fh-season">{SEASON}</span>
  </nav>
</div></header>
<main class="wrap">
{toolbar}
{body}
</main>
<footer class="fh-foot"><div class="wrap">
  <span>{BRAND.title()} — working title</span>
  <span>Source: hytek-meetmanager8-track.pdf · hytek_pdf</span>
  <a href="https://github.com/quarterback/prep-network">github.com/quarterback/prep-network</a>
</div></footer>
</body>
</html>
"""


# ───────────────────────────────────────────────────────────── table pieces


def results_table(reg: Registry, entries, ev, meet=None, show_school=True) -> str:
    """One event's results as a grid table. Every athlete + school linked."""
    cols = "34px minmax(150px,1.3fr)" + (" 34px minmax(110px,1fr)" if show_school else " 34px") + " 88px 44px"
    rows = []
    for e in entries:
        cells = [f"<span class='fh-rank'>{e.place or ''}</span>"]
        if e.is_relay:
            who = reg.school_link(e.school)
            legs = ", ".join(reg.athlete_link(c.name, e.school) for c in e.competitors)
            leg_html = f"<span class='fh-legs'>{legs}</span>"
            yr = ""
        else:
            who = reg.athlete_link(e.competitors[0].name, e.school) if e.competitors else "—"
            yr = yr_label(e.competitors[0].year) if e.competitors else ""
            leg_html = ""
        cells.append(f"<span class='fh-name'>{who}</span>")
        cells.append(f"<span class='fh-dim tnum'>{esc(yr)}</span>")
        if show_school:
            cells.append(f"<span class='fh-plain'>{reg.school_link(e.school)}</span>")
        mark = esc(e.mark.raw) if e.mark and e.mark.raw else ""
        q = f"<span class='fh-q'>{esc(e.qualifier)}</span>" if e.qualifier else ""
        cells.append(f"<span class='fh-mark'>{mark}{q}</span>")
        pts = f"{e.points:g}" if e.points is not None else ""
        cells.append(f"<span class='fh-num'>{pts}</span>")
        cls = " first" if e.place == 1 else ""
        rows.append(f"<div class='fh-row{cls}'>{''.join(cells)}{leg_html}</div>")

    head_cells = ["<span class='fh-th'>Pl</span>", "<span class='fh-th'>Athlete</span>",
                  "<span class='fh-th'>Yr</span>"]
    if show_school:
        head_cells.append("<span class='fh-th'>School</span>")
    head_cells += ["<span class='fh-th'>Mark</span>", "<span class='fh-th num'>Pts</span>"]
    return (
        f"<div class='fh-tablescroll'><div class='fh-table' style=\"--grid-cols:{cols}\">"
        f"<div class='fh-thead'>{''.join(head_cells)}</div>{''.join(rows)}</div></div>"
    )


def team_scores_panel(reg: Registry, meet) -> str:
    groups: dict[tuple[str, str], list] = {}
    for t in meet.team_scores:
        groups.setdefault((t.gender or "", t.division or ""), []).append(t)
    if not groups:
        return ""
    panels = []
    for (g, d), rows in sorted(groups.items(), key=lambda k: (k[0][1], k[0][0])):
        rows.sort(key=lambda t: t.rank or 99)
        body = "".join(
            f"<div class='fh-row{' first' if t.rank == 1 else ''}' style='--grid-cols:26px 1fr 52px'>"
            f"<span class='fh-rank'>{t.rank}</span>"
            f"<span class='fh-name'>{reg.school_link(t.school)}</span>"
            f"<span class='fh-num fh-mark'>{t.points:g}</span></div>"
            for t in rows
        )
        panels.append(
            f"<div class='fh-panel'><div class='fh-panel-head'>"
            f"<span class='fh-panel-title'>{esc(g)} {class_chip(d)}</span>"
            f"<span class='fh-panel-meta'>team scores</span></div>"
            f"<div class='fh-table narrow'>{body}</div></div>"
        )
    return (
        "<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px'>"
        + "".join(panels) + "</div>"
    )


# ───────────────────────────────────────────────────────────────── renderers


def render_meet(reg: Registry, meet) -> str:
    dates = esc(meet.date or "")
    if meet.end_date:
        dates += f" – {esc(meet.end_date)}"
    order = {"Girls": 0, "Women": 0, "Boys": 1, "Men": 1}
    groups: dict[tuple[str, str], list] = {}
    for ev in meet.events:
        groups.setdefault((ev.gender or "", ev.division or ""), []).append(ev)

    sections = []
    for (g, d) in sorted(groups, key=lambda k: (order.get(k[0], 2), k[1])):
        evs = sorted(groups[(g, d)], key=lambda e: (e.number or 0, e.round == "Preliminaries"))
        blocks = [f"<div class='fh-group'><h3>{esc(g)}</h3>{class_chip(d)}</div>"]
        for ev in evs:
            rec = ""
            if ev.records:
                r = ev.records[0]
                bits = [f"{esc(r.scope)}: <b>{esc(r.mark.raw)}</b>"]
                if r.holder:
                    bits.append(esc(display_name(r.holder)))
                if r.date:
                    bits.append(esc(r.date))
                rec = f"<span class='rec'>{' · '.join(bits)}</span>"
            tag = " <span class='fh-tag'>Prelims</span>" if ev.round == "Preliminaries" else ""
            blocks.append(
                f"<div class='fh-evhead'><h4>{esc(ev.name)}</h4>{tag}{rec}</div>"
                + results_table(reg, ev.entries, ev)
            )
        sections.append("".join(blocks))

    n = sum(len(e.entries) for e in meet.events)
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">{esc(meet.name)}</div>
  <div class="meta">{dates} · {esc(meet.venue or '')} · <span class="tnum">{len(meet.events)}</span> events · <span class="tnum">{n:,}</span> results</div></div>
  <div class="side"></div>
</div>
<div class="fh-section"><h2>Team scores</h2>{team_scores_panel(reg, meet)}</div>
<div class="fh-section"><h2>Results</h2>{''.join(sections)}</div>
"""
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/#meets'>Meets</a> › {esc(short_meet(meet.name))}"
    return shell(f"{short_meet(meet.name)} — {BRAND.title()}", body, crumb, f"← All meets|/#meets")


def render_school(reg: Registry, rec) -> str:
    name = rec["name"]
    conf_slug = reg.school_conf.get(name)
    conf_html = ""
    if conf_slug:
        cname = reg.conferences[conf_slug]["name"]
        conf_html = f" · <a href='/conferences/{conf_slug}/'>{esc(cname)}</a>"
    chips = "".join(class_chip(d) for d in sorted(rec["divisions"]))

    # roster
    roster = sorted(
        (reg.athletes[k] for k in rec["athletes"]), key=lambda a: a["name"].split()[-1]
    )
    roster_rows = "".join(
        f"<div class='fh-row' style='--grid-cols:minmax(160px,1.4fr) 44px 1fr 44px'>"
        f"<span class='fh-name'><a href='/athletes/{a['slug']}/'>{esc(a['name'])}</a></span>"
        f"<span class='fh-dim'>{esc(yr_label(a['year']))}</span>"
        f"<span class='fh-dim'>{esc(', '.join(sorted({ev.name for (_, ev, _) in a['rows']})))}</span>"
        f"<span class='fh-num tnum'>{sum(1 for _ in a['rows'])}</span></div>"
        for a in roster
    )
    roster_html = (
        "<div class='fh-tablescroll'><div class='fh-table' style='--grid-cols:minmax(160px,1.4fr) 44px 1fr 44px'>"
        "<div class='fh-thead'><span class='fh-th'>Athlete</span><span class='fh-th'>Yr</span>"
        "<span class='fh-th'>Events</span><span class='fh-th num'>App</span></div>"
        f"{roster_rows}</div></div>"
    )

    # results ledger grouped by meet
    by_meet: dict[str, list] = {}
    for (m, ev, e) in rec["results"]:
        by_meet.setdefault(m.name, []).append((m, ev, e))
    ledger = []
    for mname, rows in by_meet.items():
        m = rows[0][0]
        body_rows = []
        for (_, ev, e) in rows:
            if e.is_relay:
                who = ", ".join(reg.athlete_link(c.name, name) for c in e.competitors)
            else:
                who = reg.athlete_link(e.competitors[0].name, name) if e.competitors else "—"
            tag = " <span class='fh-tag'>Prelims</span>" if ev.round == "Preliminaries" else ""
            mark = esc(e.mark.raw) if e.mark and e.mark.raw else ""
            pts = f"{e.points:g}" if e.points is not None else ""
            body_rows.append(
                f"<div class='fh-row{' first' if e.place == 1 else ''}' "
                f"style='--grid-cols:34px minmax(150px,1.3fr) minmax(130px,1fr) 88px 44px'>"
                f"<span class='fh-rank'>{e.place or ''}</span>"
                f"<span class='fh-name'>{who}</span>"
                f"<span class='fh-plain fh-dim'>{esc(ev.gender or '')} {esc(ev.name)} {esc(ev.division or '')}{tag}</span>"
                f"<span class='fh-mark'>{mark}</span><span class='fh-num'>{pts}</span></div>"
            )
        ledger.append(
            f"<div class='fh-section'><h2><a href='{reg.meet_url(m)}'>{esc(short_meet(mname))}</a></h2>"
            "<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:34px minmax(150px,1.3fr) minmax(130px,1fr) 88px 44px'>"
            "<div class='fh-thead'><span class='fh-th'>Pl</span><span class='fh-th'>Athlete</span>"
            "<span class='fh-th'>Event</span><span class='fh-th'>Mark</span><span class='fh-th num'>Pts</span></div>"
            f"{''.join(body_rows)}</div></div></div>"
        )

    body = f"""
<div class="fh-idhdr">
  <span class="fh-crest lg" style="background:{crest_color(name)}">{esc(monogram(name))}</span>
  <div><div class="name">{esc(short_school(name))}</div>
  <div class="meta">{esc(name)}{conf_html}</div></div>
  <div class="side">{chips}</div>
</div>
<div class="fh-section"><h2>Roster</h2>{roster_html}</div>
{''.join(ledger)}
"""
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/#schools'>Schools</a> › {esc(short_school(name))}"
    return shell(f"{short_school(name)} — {BRAND.title()}", body, crumb, "← Schools|/#schools")


def render_conference(reg: Registry, slug: str, conf) -> str:
    m = conf["meet"]
    members = sorted(conf["members"])
    member_rows = "".join(
        f"<a class='fh-row' href='{reg.school_url(s)}' "
        f"style='--grid-cols:28px minmax(160px,1fr) 60px 60px'>"
        f"<span class='fh-crest sm' style='background:{crest_color(s)}'>{esc(monogram(s))}</span>"
        f"<span class='fh-name'>{esc(short_school(s))}</span>"
        f"<span>{''.join(class_chip(d) for d in sorted(reg.schools[s]['divisions']))}</span>"
        f"<span class='fh-num tnum'>{len(reg.schools[s]['athletes'])}</span></a>"
        for s in members
    )
    members_html = (
        "<div class='fh-tablescroll'><div class='fh-table narrow' style='--grid-cols:28px minmax(160px,1fr) 60px 60px'>"
        "<div class='fh-thead'><span class='fh-th'></span><span class='fh-th'>School</span>"
        "<span class='fh-th'>Class</span><span class='fh-th num'>Athletes</span></div>"
        f"{member_rows}</div></div>"
    )
    body = f"""
<div class="fh-idhdr">
  <div></div>
  <div><div class="name">{esc(conf['name'])}</div>
  <div class="meta"><span class="tnum">{len(members)}</span> member schools · regional: <a href='{reg.meet_url(m)}'>{esc(short_meet(m.name))}</a></div></div>
  <div class="side"></div>
</div>
<div class="fh-board">
  <div><div class="fh-section" style="margin-top:0"><h2>Members</h2>{members_html}</div></div>
  <div class="fh-rail"><div class="fh-section" style="margin-top:0"><h2>League table</h2>{team_scores_panel(reg, m)}</div></div>
</div>
<div class="fh-note">Stand-in league for the POC — grouped from the regional; the specimen carries no league data.</div>
"""
    crumb = f"<a href='/'>{BRAND.title()}</a> › <a href='/#conferences'>Conferences</a> › {esc(conf['name'])}"
    return shell(f"{conf['name']} — {BRAND.title()}", body, crumb, "← Conferences|/#conferences")


def render_athlete(reg: Registry, a) -> str:
    name, school = a["name"], a["school"]
    rows = []
    for (m, ev, e) in a["rows"]:
        tag = " <span class='fh-tag'>Prelims</span>" if ev.round == "Preliminaries" else ""
        mark = esc(e.mark.raw) if e.mark and e.mark.raw else ""
        pts = f"{e.points:g}" if e.points is not None else ""
        extra = ""
        if e.is_relay:
            mates = [c for c in e.competitors if display_name(c.name) != name]
            with_html = ", ".join(reg.athlete_link(c.name, school) for c in mates)
            extra = f"<span class='fh-legs'>with {with_html}</span>"
        rows.append(
            f"<div class='fh-row{' first' if e.place == 1 else ''}' "
            f"style='--grid-cols:minmax(120px,1fr) minmax(140px,1.2fr) 34px 88px 44px'>"
            f"<span class='fh-plain'><a href='{reg.meet_url(m)}'>{esc(short_meet(m.name))}</a></span>"
            f"<span class='fh-plain fh-dim'>{esc(ev.name)} {esc(ev.division or '')}{tag}</span>"
            f"<span class='fh-rank'>{e.place or ''}</span>"
            f"<span class='fh-mark'>{mark}</span><span class='fh-num'>{pts}</span>{extra}</div>"
        )
    table = (
        "<div class='fh-tablescroll'><div class='fh-table' "
        "style='--grid-cols:minmax(120px,1fr) minmax(140px,1.2fr) 34px 88px 44px'>"
        "<div class='fh-thead'><span class='fh-th'>Meet</span><span class='fh-th'>Event</span>"
        "<span class='fh-th'>Pl</span><span class='fh-th'>Mark</span><span class='fh-th num'>Pts</span></div>"
        f"{''.join(rows)}</div></div>"
    )
    conf_slug = reg.school_conf.get(school)
    conf_html = ""
    if conf_slug:
        conf_html = f" · <a href='/conferences/{conf_slug}/'>{esc(reg.conferences[conf_slug]['name'])}</a>"
    yr = yr_label(a["year"])
    yr_html = f" · {esc(yr)}" if yr else ""
    body = f"""
<div class="fh-idhdr">
  <span class="fh-crest lg" style="background:{crest_color(school)}">{esc(monogram(school))}</span>
  <div><div class="name">{esc(name)}</div>
  <div class="meta"><a href='{reg.school_url(school)}'>{esc(short_school(school))}</a>{yr_html}{conf_html}</div></div>
  <div class="side">{''.join(class_chip(d) for d in sorted(reg.schools[school]['divisions']))}</div>
</div>
<div class="fh-section"><h2>2026 season</h2>{table}</div>
"""
    crumb = (
        f"<a href='/'>{BRAND.title()}</a> › "
        f"<a href='{reg.school_url(school)}'>{esc(short_school(school))}</a> › {esc(name)}"
    )
    return shell(
        f"{name} — {short_school(school)} — {BRAND.title()}",
        body, crumb, f"← {short_school(school)}|{reg.school_url(school)}",
    )


def render_front(reg: Registry) -> str:
    # scoreboard strip
    cards = []
    for m in reg.meets:
        tops = [t for t in m.team_scores if t.rank == 1]
        top_html = ""
        if tops:
            first = sorted(tops, key=lambda t: (t.division or "", t.gender or ""))[0]
            more = f" +{len(tops) - 1}" if len(tops) > 1 else ""
            top_html = f"<div class='mwin'><b>{esc(short_school(first.school))}</b> {esc(first.gender or '')} {esc(first.division or '')}{more}</div>"
        cards.append(
            f"<a class='fh-scard' href='{reg.meet_url(m)}'>"
            f"<div class='mname'>{esc(short_meet(m.name))}</div>"
            f"<div class='mmeta'>{esc(m.date or '')} · {esc(short_school(m.venue or ''))}</div>{top_html}</a>"
        )

    # state champions, tabbed by gender
    state = next(m for m in reg.meets if "State" in m.name)
    champs: dict[str, list] = {"Girls": [], "Boys": []}
    for ev in state.events:
        if ev.round == "Preliminaries":
            continue
        win = next((e for e in ev.entries if e.place == 1), None)
        if win is None or ev.gender not in champs:
            continue
        champs[ev.gender].append((ev, win))
    tab_buttons, tab_panels = [], []
    for i, g in enumerate(("Girls", "Boys")):
        rows = []
        for ev, e in sorted(champs[g], key=lambda t: (t[0].division or "", t[0].number or 0)):
            if e.is_relay:
                who = reg.school_link(e.school)
            else:
                who = reg.athlete_link(e.competitors[0].name, e.school) if e.competitors else "—"
            mark = esc(e.mark.raw) if e.mark and e.mark.raw else ""
            rows.append(
                "<div class='fh-row' style='--grid-cols:minmax(130px,1.2fr) 44px minmax(130px,1fr) minmax(110px,1fr) 80px'>"
                f"<span class='fh-plain fh-dim'>{esc(ev.name)}</span>"
                f"<span>{class_chip(ev.division)}</span>"
                f"<span class='fh-name'>{who}</span>"
                f"<span class='fh-plain'>{reg.school_link(e.school)}</span>"
                f"<span class='fh-mark'>{mark}</span></div>"
            )
        sel = "true" if i == 0 else "false"
        hidden = "" if i == 0 else " hidden"
        tab_buttons.append(
            f"<button class='fh-tab' role='tab' aria-selected='{sel}' aria-controls='champs-{g.lower()}'>{g}</button>"
        )
        tab_panels.append(
            f"<div id='champs-{g.lower()}' role='tabpanel'{hidden}>"
            "<div class='fh-tablescroll'><div class='fh-table' "
            "style='--grid-cols:minmax(130px,1.2fr) 44px minmax(130px,1fr) minmax(110px,1fr) 80px'>"
            "<div class='fh-thead'><span class='fh-th'>Event</span><span class='fh-th'>Class</span>"
            "<span class='fh-th'>Champion</span><span class='fh-th'>School</span><span class='fh-th'>Mark</span></div>"
            f"{''.join(rows)}</div></div></div>"
        )

    # directory
    dir_rows = "".join(
        f"<a class='fh-row' href='/schools/{rec['slug']}/' "
        "style='--grid-cols:28px minmax(150px,1fr) 64px minmax(90px,110px) 60px'>"
        f"<span class='fh-crest sm' style='background:{crest_color(s)}'>{esc(monogram(s))}</span>"
        f"<span class='fh-name'>{esc(short_school(s))}</span>"
        f"<span>{''.join(class_chip(d) for d in sorted(rec['divisions']))}</span>"
        f"<span class='fh-plain fh-dim'>{esc(reg.conferences[reg.school_conf[s]]['name']) if s in reg.school_conf else ''}</span>"
        f"<span class='fh-num tnum'>{len(rec['athletes'])}</span></a>"
        for s, rec in sorted(reg.schools.items(), key=lambda kv: short_school(kv[0]))
    )
    directory = (
        "<div class='fh-tablescroll'><div class='fh-table' "
        "style='--grid-cols:28px minmax(150px,1fr) 64px minmax(90px,110px) 60px'>"
        "<div class='fh-thead'><span class='fh-th'></span><span class='fh-th'>School</span>"
        "<span class='fh-th'>Class</span><span class='fh-th'>Conference</span><span class='fh-th num'>Athletes</span></div>"
        f"{dir_rows}</div></div>"
    )

    conf_rows = "".join(
        f"<a class='fh-row' href='/conferences/{slug}/' style='--grid-cols:minmax(140px,1fr) 70px'>"
        f"<span class='fh-name'>{esc(c['name'])}</span>"
        f"<span class='fh-num tnum'>{len(c['members'])}</span></a>"
        for slug, c in sorted(reg.conferences.items(), key=lambda kv: kv[1]["name"])
    )
    conferences = (
        "<div class='fh-panel'><div class='fh-table narrow' style='--grid-cols:minmax(140px,1fr) 70px'>"
        "<div class='fh-thead'><span class='fh-th'>Conference</span><span class='fh-th num'>Schools</span></div>"
        f"{conf_rows}</div></div>"
    )

    body = f"""
<div class="fh-section" id="meets" style="margin-top:20px"><h2>Postseason</h2>
<div class="fh-strip">{''.join(cards)}</div></div>

<div class="fh-section"><div style="display:flex;align-items:baseline;gap:12px">
<h2 style="margin:0">State champions</h2>
<div class="fh-tabs" role="tablist">{''.join(tab_buttons)}</div></div>
<div style="margin-top:10px">{''.join(tab_panels)}</div></div>

<div class="fh-board">
  <div class="fh-section" id="schools" style="margin-top:0"><h2>Schools</h2>{directory}</div>
  <div class="fh-rail"><div class="fh-section" id="conferences" style="margin-top:0"><h2>Conferences</h2>{conferences}</div></div>
</div>

<script>
(function () {{
  var tabs = document.querySelectorAll(".fh-tab");
  tabs.forEach(function (tab) {{
    tab.addEventListener("click", function () {{
      tabs.forEach(function (t) {{
        t.setAttribute("aria-selected", t === tab ? "true" : "false");
        document.getElementById(t.getAttribute("aria-controls")).hidden = t !== tab;
      }});
    }});
  }});
}})();
</script>
"""
    return shell(f"{BRAND.title()} — {SEASON}", body)


# ─────────────────────────────────────────────────────────── write + verify


def write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def link_check(pages: dict[str, str]) -> list[str]:
    """Every root-relative href must resolve to a generated page or asset."""
    targets = set(pages) | {"/style.css"}
    broken = []
    for url, html_text in pages.items():
        for href in re.findall(r"href=['\"](/[^'\"#]*)", html_text):
            if href.startswith("/fonts/"):
                if not (ROOT / href.lstrip("/")).exists():
                    broken.append(f"{url} -> {href}")
                continue
            if href not in targets:
                broken.append(f"{url} -> {href}")
    return broken


def inline_preview(front: str) -> str:
    """Self-contained copy of the front page for the published artifact."""
    css = (ROOT / "site/style.css").read_text()

    def font_uri(m):
        data = base64.b64encode((ROOT / "site/fonts" / m.group(1)).read_bytes()).decode()
        return f"url(data:font/woff2;base64,{data})"

    css = re.sub(r"url\('fonts/([^']+)'\)", font_uri, css)
    return front.replace('<link rel="stylesheet" href="/style.css">', f"<style>\n{css}\n</style>")


def build() -> None:
    meets = hytek_pdf.parse(str(SPECIMEN))
    reg = Registry(meets)

    pages: dict[str, str] = {"/": render_front(reg)}
    for m in meets:
        pages[reg.meet_url(m)] = render_meet(reg, m)
    for s, rec in reg.schools.items():
        pages[reg.school_url(s)] = render_school(reg, rec)
    for slug, conf in reg.conferences.items():
        pages[f"/conferences/{slug}/"] = render_conference(reg, slug, conf)
    for a in reg.athletes.values():
        pages[f"/athletes/{a['slug']}/"] = render_athlete(reg, a)

    broken = link_check(pages)
    if broken:
        for b in broken[:20]:
            print("BROKEN:", b)
        raise SystemExit(f"{len(broken)} broken internal links")

    # clear previous generated tree
    for d in ("meets", "schools", "conferences", "athletes", "fonts"):
        shutil.rmtree(ROOT / d, ignore_errors=True)
    for url, html_text in pages.items():
        rel = "index.html" if url == "/" else url.strip("/") + "/index.html"
        write(ROOT / rel, html_text)
    shutil.copy(ROOT / "site/style.css", ROOT / "style.css")
    shutil.copytree(ROOT / "site/fonts", ROOT / "fonts")
    write(ROOT / "dist/index.html", inline_preview(pages["/"]))

    total = sum(len(e.entries) for m in meets for e in m.events)
    print(f"{len(pages):,} pages · {len(reg.schools)} schools · {len(reg.athletes):,} athletes · {total:,} results · links OK")


if __name__ == "__main__":
    build()
