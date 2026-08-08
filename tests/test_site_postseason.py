"""
Render-level tests for the postseason surfaces and the tenant brand split.

These build real pages through the real ``Registry`` rather than asserting on
strings assembled by hand, because both things they protect are properties of
the assembled page:

* the demo navigation actually resolves — a bracket whose matchups link to
  pages the site does not generate passes every data-level test and 404s in a
  browser;
* who owns the masthead. A school page that quietly regains the state masthead
  is not a crash, it is a product regression, and nothing else would catch it.

The module-scoped registry keeps this to one load of 8,000 records.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_build():
    spec = importlib.util.spec_from_file_location("fh_build", ROOT / "site/build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = _load_build()


@pytest.fixture(scope="module")
def reg():
    r = build.Registry()
    build.RAIL = build.build_rail(r)
    build.build_menus(r)
    return r


def _tournament(reg, tid):
    return next(t for t in reg.tournaments if t.id == tid)


# ------------------------------------------------------------- brand split


def _has_state_masthead(html):
    return bool(re.search(r"<header class=[\"']fh-mast[\"']", html))


def _has_org_masthead(html):
    """The state mast replaced by the network utility strip, with the local
    organisation's own header (`fh-orghead`) owning the page beneath it."""
    return "fh-utility" in html and "fh-orghead" in html


def test_a_school_page_is_the_schools_own_masthead(reg):
    school = reg.schools["Ashbrook"]
    html = build.render_school(reg, school)
    assert _has_org_masthead(html)
    assert not _has_state_masthead(html)
    assert "ASHBROOK" in html.upper()
    assert "← JHSAA" in html                      # the association collapses to a link-back
    assert "VarsityApex › Schools › Ashbrook" in re.sub(r"<[^>]+>", "", html)


def test_a_school_page_states_its_identity_once(reg):
    """The masthead carries the crest, the name and the nav. Printing them
    again in the body is what a subsection-turned-homepage looks like."""
    html = build.render_school(reg, reg.schools["Ashbrook"])
    body = html.split("</head>", 1)[-1]      # the <title> says it too
    assert body.count("fh-orghead") == 1
    assert body.count("fh-orgnav") == 1
    assert "fh-idhdr school" not in html


def test_a_conference_page_is_its_own_masthead(reg):
    slug, conf = next(iter(sorted(reg.confs.items())))
    html = build.render_conference(reg, conf)
    assert _has_org_masthead(html) and not _has_state_masthead(html)
    assert conf["name"] in html


def test_championship_pages_keep_the_association_masthead(reg):
    """A state tournament is an association property — this is the one place
    the JHSAA identity must stay dominant."""
    for html in (build.render_championships(reg),
                 build.render_tournament(reg, _tournament(reg, "2026-27-football-1a")),
                 build.render_champ_sport(reg, build.BY_KEY["football"])):
        assert _has_state_masthead(html)
        assert not _has_org_masthead(html)


def test_contest_pages_keep_the_association_masthead(reg):
    game = next(c for c in reg.contests
                if getattr(c, "box", None) and c.sport == "boys-basketball")
    assert _has_state_masthead(build.render_game(reg, game))


# ------------------------------------------------------- the demo paths


def test_championships_hub_lists_sports_and_divisions(reg):
    html = build.render_championships(reg)
    assert "/championships/football/" in html
    for group in build.CLASSES:                 # every class, 7A included
        assert f">{group}</a>" in html
    assert "Happening now" in html
    assert "0 shown" not in html


def test_hub_shows_consolidated_divisions_not_six_fabricated_ones(reg):
    """Field hockey crowns two champions, not one per classification."""
    sport = build.BY_KEY["field-hockey"]
    expected = {sport.champ_group(g[0]) for g in sport.groups}
    assert len(expected) < len(build.CLASSES)
    html = build.render_champ_sport(reg, sport)
    groups = set(re.findall(r"class='dv'>.*?>(\S+?)</span>", html))
    assert groups <= expected


def test_football_1a_bracket_renders_the_whole_tree(reg):
    t = _tournament(reg, "2026-27-football-1a")
    html = build.render_tournament(reg, t)
    assert html.count("fh-brk-card") == sum(len(r.matchups) for r in t.rounds)
    assert "Mabryville" in html and "Aspen Spur Union" in html
    assert "State Champions" in html
    for name in ("First Round", "Quarterfinals", "Semifinals", "Championship"):
        assert name in html


def test_the_bracket_links_to_the_championship_game_page(reg):
    """Championships → Football → 1A → click the final → the game page."""
    t = _tournament(reg, "2026-27-football-1a")
    href = reg.contest_href(t.final.contest_key)
    assert href, "the final has no page to link to"
    assert href in build.render_tournament(reg, t)


def test_the_championship_game_page_links_back_to_the_bracket(reg):
    """…and back again — the return leg of the demo path."""
    t = _tournament(reg, "2026-27-football-1a")
    game = reg.contest_for(t.final.contest_key)
    html = build.render_game(reg, game)
    assert reg.tour_url[t.id] in html
    assert "View full bracket" in html
    assert "CHAMPIONSHIP" in html
    assert "State Champions" in html


def test_every_bracket_matchup_links_somewhere_that_exists(reg):
    """A decided matchup that links nowhere is a dead end in the bracket."""
    missing = []
    for t in reg.tournaments:
        for r in t.rounds:
            for m in r.matchups:
                if m.decided and not m.bye and not reg.contest_href(m.contest_key):
                    missing.append((t.id, r.name, m.slot))
    assert not missing[:5], missing[:5]


def test_an_in_progress_bracket_shows_finals_and_fixtures(reg):
    t = next(t for t in reg.tour_by_sport["boys-basketball"]
             if t.status.value == "in_progress")
    html = build.render_tournament(reg, t)
    assert "SEMIFINALS" in html.upper()
    assert "Final" in html                      # rounds already played
    assert re.search(r"\d:\d\d [AP]M", html)    # and a tip-off time for one that is not
    assert "fh-champbanner" not in html      # nobody has won it yet


def test_a_bye_is_drawn_as_a_bye_not_as_an_opponent(reg):
    t = next(t for t in reg.tournaments if t.format.value == "bracket" and t.byes)
    html = build.render_tournament(reg, t)
    assert "fh-brk-card bye" in html
    # "Bye" is the card's status line. What must never appear is a TEAM called
    # that — the school-name slot is where a fake opponent would show up.
    assert "<span class='nm'>Bye</span>" not in html


def test_a_meet_championship_renders_results_not_an_empty_bracket(reg):
    t = next(t for t in reg.tournaments if t.format.value == "meet" and t.meet_key)
    html = build.render_tournament(reg, t)
    assert "fh-brk-card" not in html
    assert "Championship meet" in html
    assert reg.contest_href(t.meet_key) in html


# ----------------------------------------------------------- imported data


def test_an_imported_box_score_renders_under_the_score(reg):
    game = next(c for c in reg.contests
                if getattr(c, "box", None) and c.home == "Ansotegui Siding")
    html = build.render_game(reg, game)
    assert "Box score" in html
    assert "Team totals" in html
    assert "Ashworth, Devin" in html
    for column in ("PTS", "REB", "AST"):
        assert f">{column}<" in html
    assert "By period" in html


def test_an_imported_record_shows_where_it_came_from(reg):
    game = next(c for c in reg.contests
                if getattr(c, "box", None) and c.home == "Ansotegui Siding")
    html = build.render_game(reg, game)
    assert "scorebook-basketball-boxscore.csv" in html
    assert "scorebook_csv" in html
    assert "JHSAA-BB-2027-05422" in html
    assert "sha256" in html


def test_generated_records_do_not_claim_provenance_they_do_not_have(reg):
    """The fictional state is not an import and must not present itself as one."""
    game = next(c for c in reg.contests
                if c.provenance and c.provenance.adapter == "jefferson.postseason")
    assert "fh-prov" not in build.render_game(reg, game)


def test_the_imported_swim_meet_is_the_state_championship(reg):
    t = next(t for t in reg.tour_by_sport["girls-swimming"] if t.meet_key)
    meet = reg.contest_for(t.meet_key)
    assert meet is not None
    html = build.render_meet(reg, meet)
    assert "hytek-mm-swimming-results.txt" in html      # provenance survived
    assert "200 Yard Medley Relay" in html
    assert "Harkness, Elle" in html                     # a relay leg, not just the school
    assert "(28.33)" in html                            # splits


def test_the_split_kept_boys_events_off_the_girls_page(reg):
    """A combined Hy-Tek meet filed under one gendered key would carry the
    other gender's events onto that sport's page."""
    t = next(t for t in reg.tour_by_sport["girls-swimming"] if t.meet_key)
    meet = reg.contest_for(t.meet_key)
    assert {ev.gender for ev in meet.events} == {"Girls"}


def test_an_imported_dual_renders_its_lines(reg):
    dual = next(c for c in reg.contests
                if c.provenance and c.provenance.adapter == "dual_card")
    html = build.render_dual(reg, dual)
    assert "Marchetti, Enzo" in html
    assert "6-3, 6-4" in html
    assert "dual-tennis-match-card.txt" in html
