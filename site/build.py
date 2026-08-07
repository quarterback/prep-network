"""
Static site build: parsed records -> one self-contained HTML file.

No framework and no server. This is the projection layer of the architecture:
records in, plain HTML out, deployable on anything that can serve a file (and
viewable from a file:// open — the entire site, fonts included, is one file).
It fills the same role the owner's other sites give to small build scripts run
by a workflow: the page is committed and served as-is.

Usage:
    python3 site/build.py            # writes dist/index.html
"""

from __future__ import annotations

import base64
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ingest.adapters import hytek_pdf  # noqa: E402

SPECIMEN = ROOT / "ingest/fixtures/specimens/hytek-meetmanager8-track.pdf"
OUT = ROOT / "dist/index.html"

BRAND = "FIELDHOUSE"  # working title — swap here when the real name lands

FONTS = [
    ("PP Valve", 800, "italic", "PPValve-PlainExtraboldItalic.woff2"),
    ("PP Neue Montreal", 400, "normal", "PPNeueMontreal-Book.woff2"),
    ("PP Neue Montreal", 500, "normal", "PPNeueMontreal-Medium.woff2"),
    ("PP Neue Montreal", 600, "normal", "PPNeueMontreal-Semibold.woff2"),
]


def esc(text: str | None) -> str:
    return html.escape(clean(text or ""), quote=True)


def clean(text: str) -> str:
    """Collapse the double spaces the printout carries ('Kaycee  High School')."""
    return re.sub(r"\s{2,}", " ", text).strip()


def display_name(name: str) -> str:
    """'Davis, Alaina' -> 'Alaina Davis'. Relay legs arrive already flipped."""
    name = clean(name)
    if ", " in name:
        last, _, first = name.partition(", ")
        if first:
            return f"{first} {last}"
    return name


def font_css() -> str:
    rules = []
    for family, weight, style, filename in FONTS:
        data = base64.b64encode((ROOT / "site/fonts" / filename).read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"font-style:{style};font-display:swap;"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
        )
    return "\n".join(rules)


# ------------------------------------------------------------------ sections


def render_team_ranks(meet) -> str:
    groups: dict[tuple[str, str], list] = {}
    for t in meet.team_scores:
        groups.setdefault((t.gender or "", t.division or ""), []).append(t)
    if not groups:
        return ""
    cards = []
    for (gender, division), rows in groups.items():
        rows.sort(key=lambda t: t.rank or 99)
        body = "".join(
            f"<tr><td class='pl'>{t.rank}</td><td>{esc(t.school)}</td>"
            f"<td class='pts'>{t.points:g}</td></tr>"
            for t in rows
        )
        cards.append(
            f"<div class='rank-card'><span class='label'>{esc(gender)} · "
            f"{esc(division)} · Team scores</span><table>{body}</table></div>"
        )
    return f"<div class='rank-grid'>{''.join(cards)}</div>"


def render_event(ev) -> str:
    win = next((e for e in ev.entries if e.place == 1), None)
    win_html = ""
    if win is not None:
        who = display_name(win.competitors[0].name) if win.competitors else clean(win.school)
        # The specimen has one Finals winner with a genuinely blank mark column
        # (Event 1, 1A-2A East). Faithful extraction renders no mark rather
        # than inventing one — so don't print a dangling separator either.
        mark = esc(win.mark.raw) if win.mark and win.mark.raw else ""
        tail = f" · <b>{mark}</b>" if mark else ""
        win_html = f"<span class='ev-win'>{esc(who)}{tail}</span>"

    round_chip = (
        "<span class='ev-round'>Prelims</span>" if ev.round == "Preliminaries" else ""
    )

    rec_html = ""
    if ev.records:
        r = ev.records[0]
        bits = [f"{esc(r.scope)} record <b>{esc(r.mark.raw)}</b>"]
        if r.holder:
            bits.append(esc(display_name(r.holder)))
        if r.date:
            bits.append(esc(r.date))
        rec_html = f"<p class='ev-record'>{' · '.join(bits)}</p>"

    rows = []
    for e in ev.entries:
        if e.is_relay:
            legs = ", ".join(display_name(c.name) for c in e.competitors)
            athlete = f"{esc(e.school)}<span class='legs'>{esc(legs)}</span>"
            year = ""
        else:
            athlete = esc(display_name(e.competitors[0].name)) if e.competitors else "—"
            year = esc(e.competitors[0].year or "") if e.competitors else ""
        q = f"<span class='q'>{esc(e.qualifier)}</span>" if e.qualifier else ""
        mark = esc(e.mark.raw) if e.mark else ""
        pts = f"{e.points:g}" if e.points is not None else ""
        cls = " class='r1'" if e.place == 1 else ""
        rows.append(
            f"<tr{cls}><td class='n'>{e.place}</td><td>{athlete}</td>"
            f"<td class='n'>{year}</td><td>{esc(e.school)}</td>"
            f"<td class='mark'>{mark}{q}</td><td class='pts'>{pts}</td></tr>"
        )

    return (
        "<details class='event'><summary>"
        f"<span class='ev-name'>{esc(ev.name)}{round_chip}</span>{win_html}"
        "</summary>"
        f"{rec_html}"
        "<div class='tablewrap'><table class='results'>"
        "<thead><tr><th>Pl</th><th>Athlete</th><th>Yr</th><th>School</th>"
        "<th>Mark</th><th>Pts</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></details>"
    )


def render_meet(meet, index: int, selected: bool) -> str:
    groups: dict[tuple[str, str], list] = {}
    for ev in meet.events:
        groups.setdefault((ev.gender or "", ev.division or ""), []).append(ev)

    order = {"Girls": 0, "Women": 0, "Boys": 1, "Men": 1}
    sections = []
    for (gender, division) in sorted(
        groups, key=lambda k: (order.get(k[0], 2), k[1])
    ):
        evs = sorted(
            groups[(gender, division)],
            key=lambda e: (e.number or 0, e.round == "Preliminaries"),
        )
        events_html = "".join(render_event(e) for e in evs)
        sections.append(
            f"<h3 class='group-head'>{esc(gender)} · {esc(division)}</h3>{events_html}"
        )

    n_results = sum(len(e.entries) for e in meet.events)
    dates = esc(meet.date or "")
    if meet.end_date:
        dates += f" – {esc(meet.end_date)}"
    hidden = "" if selected else " hidden"
    return (
        f"<div class='meet-panel' id='meet-{index}' role='tabpanel'{hidden}>"
        f"<div class='meet-meta'><span><b>{esc(meet.venue or '')}</b></span>"
        f"<span>{dates}</span>"
        f"<span>{len(meet.events)} events</span><span>{n_results:,} results</span></div>"
        f"{render_team_ranks(meet)}{''.join(sections)}</div>"
    )


def short_tab(name: str) -> str:
    name = clean(name)
    name = re.sub(r"^WHSAA\s+", "", name)
    name = re.sub(r"\s+(Regional|Track)?\s*(Meet|Track Meet)$", "", name)
    name = name.replace(" Track & Field Championships", " Championships")
    return name


# ---------------------------------------------------------------------- page


def build() -> None:
    meets = hytek_pdf.parse(str(SPECIMEN))
    total = sum(len(e.entries) for m in meets for e in m.events)
    relays = sum(1 for m in meets for e in m.events if "Relay" in e.name)
    schools = {clean(s) for m in meets for s in m.schools}
    events = sum(len(m.events) for m in meets)
    prov = meets[0].provenance

    tabs, panels = [], []
    for i, meet in enumerate(meets):
        sel = "true" if i == 0 else "false"
        tabs.append(
            f"<button class='meet-tab' role='tab' aria-selected='{sel}' "
            f"aria-controls='meet-{i}'>{esc(short_tab(meet.name))}</button>"
        )
        panels.append(render_meet(meet, i, selected=(i == 0)))

    css = (ROOT / "site/style.css").read_text()

    page = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{BRAND.title()} — every result, every sport, one file</title>
<style>
{font_css()}
{css}
</style>

<header class="masthead"><div class="wrap">
  <a class="wordmark" href="#">{BRAND}<span class="tld">.</span></a>
  <nav class="tiers" aria-label="Tenant tiers">
    <span class="tier tier--live">State site — live</span>
    <span class="tier">Conference — same records</span>
    <span class="tier">School — same records</span>
  </nav>
</div></header>

<main class="wrap">

<section class="hero">
  <p class="label">Product demo · spring track &amp; field · state association tier</p>
  <p class="hero-stat">{total:,}<span class="accent">.</span></p>
  <h1>Results recovered from one published PDF — and served to any phone.</h1>
  <p class="dek">State associations run their meets in software that knows every
  place, mark, grade and heat — then publish a printout and throw the structure
  away. <strong>{BRAND.title()}</strong> reads the printout back into records and
  renders this site from them. No manual entry, no vendor silo, no app to
  install.</p>
  <div class="provenance">
    <span>source <b>{esc(pathlib.Path(prov.source_uri).name)}</b> · 237 pages</span>
    <span>adapter <b>{esc(prov.adapter)}</b></span>
    <span>extracted <b>{esc(prov.extracted_at[:16])}Z</b></span>
    <span>manual entry <b>none</b></span>
  </div>
</section>
</main>

<section class="stats"><div class="wrap">
  <div class="stat"><b>{len(meets)}</b><span class="label">meets in the file</span></div>
  <div class="stat"><b>{events}</b><span class="label">events</span></div>
  <div class="stat"><b>{relays}</b><span class="label">relays, legs intact</span></div>
  <div class="stat"><b>{len(schools)}</b><span class="label">schools</span></div>
</div></section>

<main class="wrap">

<section class="section" id="season">
  <div class="section-head"><h2>The postseason</h2>
  <span class="label">one file · seven meets</span></div>
  <div class="meet-tabs" role="tablist" aria-label="Meets">{''.join(tabs)}</div>
  {''.join(panels)}
</section>

<section class="section">
  <div class="section-head"><h2>How it got here</h2>
  <span class="label">the pipeline</span></div>
  <div class="pipeline">
    <div class="pipe"><span class="label">01 · Source</span>
      <b>A published PDF</b>
      <p>The Hy-Tek printout an association actually posts. Uploads, links and
      direct entry land in the same lane.</p></div>
    <div class="pipe"><span class="label">02 · Records</span>
      <b>Structured, owned, portable</b>
      <p>Every result becomes a record with provenance — source, adapter,
      confidence — in the school's own repository, not a vendor's silo.</p></div>
    <div class="pipe"><span class="label">03 · Surfaces</span>
      <b>This page</b>
      <p>State, conference and school sites are projections of the same
      records. This entire site is one static file.</p></div>
  </div>
</section>

<section class="section">
  <div class="section-head"><h2>One model, three surfaces</h2>
  <span class="label">same records throughout</span></div>
  <div class="tiergrid">
    <div class="tiercard"><span class="label live">● Live — this demo</span>
      <h3>State association</h3>
      <p>Full postseason: classifications, team scores, standing records,
      every event of every meet.</p></div>
    <div class="tiercard"><span class="label">Next build</span>
      <h3>Conference</h3>
      <p>The same records scoped to a league, under its own brand — standings
      and results with zero re-entry.</p></div>
    <div class="tiercard"><span class="label">Next build</span>
      <h3>School</h3>
      <p>A program's own athletics site — schedule, results, rosters — with no
      maintenance beyond playing the season.</p></div>
  </div>
</section>

</main>

<footer><div class="wrap">
  <span><b>{BRAND.title()}</b> — working title</span>
  <span>Demo data: a real published state-meet PDF, kept as a format specimen</span>
  <span><a href="https://github.com/quarterback/prep-network">github.com/quarterback/prep-network</a></span>
</div></footer>

<script>
(function () {{
  var tabs = document.querySelectorAll(".meet-tab");
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
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")
    print(f"  {len(meets)} meets · {total:,} results · {relays} relays · {len(schools)} schools")


if __name__ == "__main__":
    build()
