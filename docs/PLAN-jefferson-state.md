# Jefferson (JHSAA) — the full fictional-state product demo

## Context

Wyoming's role ends as the demo dataset and continues as the real-world
ingestion/parser fixture. Jefferson exists to demonstrate the complete multi-sport
product: a statewide athletic ecosystem — dense score rail, ~35 activities, laddered
state → conference → school sites — rendered by the existing records → registry →
renderer architecture. No streaks, no generated rankings, no pro-sports apparatus:
association-site material only. This plan implements the owner's JHSAA spec as given.

## 0. Amendments and build state (resuming)

**Owner amendments to fold in:**

1. **Purpose stays the original goal.** The demo's purpose does not diverge from the
   founding plan and should not be restated as a new mission: this is still "one data
   model and one renderer serving state / conference / school from the same records,"
   proving a vendor category can be replaced cheaply. Jefferson is the dataset that
   makes that visible across a full calendar — the **laddered site** (a state site, a
   conference site, a school site, each able to stand alone inside a larger system) is
   the point, not a product pitch.
2. **School names span the full real-world spread.** Not just place-name schools:
   directional publics in quantity (North / South / East / West / Central / NW / SW /
   NE + city), people (surname schools), religious schools across denominations
   (Catholic saints, **Baptist, Episcopal, Methodist**, Lutheran, nondenominational
   Christian), colors, places, and things, plus academies and preps. Public schools
   dominate the count; the rest add texture.

**Already built before this pause (do not redo):**

- `app/sports.py` — 41-activity catalog with shape / season / gender / mark type, and
  `champ_group()` implementing the spec's per-sport championship consolidation
  (`Sport.groups`, span labels like `3A-1A`, `Open` for full-range divisions).
- `app/records_io.py` — `GAME_TYPE` serialization, `contest_to_dict` / `write_contest`
  dispatch across all three shapes, `write_orgs` / `load_orgs`, loader routing.
- `generators/jefferson/names.py` — town grammar (stems × endings), real-place
  blocklist, metro anchors, and the broad school-name pools (surnames, saints,
  Protestant denominations, civic words, directionals), mascots, athlete first/last
  name pools.
- `generators/` and `generators/jefferson/` package inits.

**Resuming at:** `geography.py` (regions → cities → schools → conferences), then the
season pipeline, then standings, then the site work.

---

## 1. Geography & settlement (`generators/jefferson/geography.py`)

Alternate-history state on the real county footprint the owner specified (southern
Oregon, northern California, NW Nevada, SW Idaho corner). **Geography real; every
city, school, league and institution fictional — no real city or school names.**

Settlement pattern per spec: one major inland metro (~700k–1m), one coastal city
(~250–400k), one Jefferson-side city of the Boise bi-state metro (~150–250k), 5–8
secondary cities (40–150k), plus mountain/resort, ag-valley, coastal, high-desert,
and remote communities. Interior deliberately denser than the real regions.

**Naming grammar, not hand-invention**: stems (Alder, Juniper, Granite, Copper, Sage,
Elk, Bear, Lost…) × endings (Falls, Ridge, Basin, Junction, Harbor, Mesa, Bluff,
Crossing…) × civic constructions, with collision checks and a blocklist of real
western cities/schools. Deterministic from one seed; two runs → identical records.

**School names span the full real-world spread** (owner amendment): directional
publics (North/South/East/West/Central/NW/SE + city), people (surname schools),
religious schools across denominations (Catholic saints, Baptist, Episcopal,
Methodist, Lutheran, nondenominational Christian), colors, places, and things,
plus academies and preps — lots of ordinary public schools among them.

**Status note**: approved and implementation already under way before a session
restart — `app/sports.py` (41-entry catalog + champ_group), `records_io` GAME +
orgs support, and `generators/jefferson/names.py` are complete; resuming at the
generator's geography/schools/season modules.

## 2. Schools, classes, conferences

- **~250–260 schools**, six classes with the spec's deliberately uneven counts
  (6A ~38 · 5A ~42 · 4A ~44 · 3A ~38 · 2A ~36 · 1A ~58; slight generation variance
  allowed). Big schools cluster in the three metros; small ones own the rural map.
- Sports offered scale with size and place: a 6A suburban school sponsors 20–30
  activities; a remote 1A school 6–10. Skiing/hockey cluster in mountain regions;
  fencing/field hockey/water polo/gymnastics concentrate in metros and private/prep
  schools; wrestling/basketball/track/XC are broad statewide.
- **~30–35 permanent conferences**, geography/travel/affinity based, mixed
  classification common, one primary conference per school **across all sports**.
- **`classification` ≠ `championship_group`** — a first-class data-model distinction.
  Schools carry a base class; each sport maps classes onto its own championship
  divisions per the spec's tables (e.g. tennis 6A/5A/4A/3A-1A; swimming 6A-5A/4A-1A;
  low-participation activities use 1–3 open divisions). Implemented as one mapping,
  `app/sports.py: champ_group(sport, classification)`, read everywhere standings and
  championships render.

## 3. The sports catalog (`app/sports.py`)

~35 sanctioned activities exactly as specified — fall (football, flag football,
soccer B/G, field hockey, volleyball G, XC B/G, tennis G, golf B, mountain biking,
water polo B/G), winter (basketball B/G, wrestling B/G, swim & dive B/G, ice hockey
B/G, alpine and nordic skiing B/G, bowling B/G, fencing B/G, gymnastics, competitive
spirit, winter track), spring (baseball, softball, lacrosse B/G, tennis B, volleyball
B, golf G, track B/G).

Each catalog entry: shape (GAME / DUAL / MEET), season, gender, mark type, and
championship grouping. All three shapes exercised heavily — GAME (football → ice
hockey → lacrosse), DUAL (tennis, wrestling duals, fencing), MEET (XC, swim, ski,
bowling, gymnastics judged POINTS, track).

## 4. The season (`generators/jefferson/`)

Full fictional **2026–27** season; **demo "today" ≈ mid-January 2027**, chosen so the
site shows all three states at once: **fall complete with championships**, **winter
mid-season** (the dense rail — skiing, hockey, fencing, swim, basketball, wrestling,
bowling all live), **spring scheduled**. Pipeline per spec:

regions → cities → schools → classifications → conferences → offered sports → teams
→ schedules → completed/upcoming contests → postseason/championships.

Realistic complications, deliberately: interstate opponents (out-of-state schools
render as plain text, not links — `resolve_school` already degrades that way),
invitationals crossing classifications, soccer/hockey ties, cancellations and
postponements (status on the record), incomplete results (meets with missing marks —
the unscored-mark machinery already handles them), and schools that don't sponsor an
activity.

Output: **records via `app/records_io`** — the records layer is the canonical write
API now. Adds `GAME_TYPE` serialization (meet + dual exist) and org records
(`records/orgs/schools.json`, `conferences.json`) which the Registry now reads
instead of inferring leagues from meet names. Wyoming contest records leave
`records/`; the specimen PDF stays as the parser fixture and upload proof.

## 5. Pages (`site/build.py`, `site/style.css`)

- **Persistent score rail** in the shell on every page: the days around the demo
  date, cells = date/status ("FT"/time/"PPD"), crest + name rows, scores or dashes,
  sport tag, each cell linking to its contest page. CSS overflow-x scroll. A
  `/scoreboard/` page carries the full week grouped by sport (the rail shows ~30
  cells; the page shows everything).
- **Contest pages**: `/games/<slug>/` (score, periods, status), `/duals/<slug>/`
  (line scoreboard), `/meets/<slug>/` (existing).
- **Sport landings** `/sports/<sport>/`: that sport's week, standings by
  championship group + conference (new `app/standings.py`, derived only: W-L and
  conference records for GAME/DUAL, meet tables for MEET), results, upcoming;
  completed fall sports show champions.
- **Front page**: rail + sport nav row + season switcher (Fall · Winter · Spring
  2026–27) + this-week scoreboard grouped by sport + fall champions module.
- **The ladder, made explicit**: conference pages become mini-fronts (their own
  standings across their sports, their week, member row) and school pages carry the
  full MHSAA-shape sports list (per sport per season: schedule/results/roster) — so
  each tier reads as a site that could stand alone inside a larger system.
- **Athlete pages** grouped by sport & season; athletes are named only where results
  name them (MEET/DUAL and individual-heavy sports), team-level GAME results carry no
  invented box scores.

## 6. Deploy mechanics (forced by scale)

~250 schools × ~35 sports ≈ tens of thousands of pages; the commit-the-tree pattern
stops being reasonable. Switch to **Vercel building from records**: `vercel.json`
with `buildCommand: python3 site/build.py`, output directory `dist/site/`. The repo
carries code + records (JSON, git-friendly); the Action becomes CI (tests +
link-check) instead of tree commits. The artifact preview keeps `dist/index.html`.

## 7. Files

| File | Change |
| --- | --- |
| `generators/jefferson/` (new pkg) | geography, schools/conferences, sports offering, scheduling, results per shape, postseason; single seed |
| `app/sports.py` (new) | catalog + `champ_group()` |
| `app/standings.py` (new) | derived standings |
| `app/records_io.py` | GAME type; orgs read/write; contest status fields |
| `site/build.py` | rail/shell, scoreboard page, game/dual pages, sport landings, season nav, front rewrite, registry on (sport, season, champ group), orgs-from-records |
| `site/style.css` | rail, sport nav, boxscore/dual blocks (both schemes) |
| `records/` | Jefferson in, Wyoming contests out |
| `.github/workflows/build.yml` | becomes CI-only |
| `vercel.json` (new) | build-from-records |
| `tests/` | generator determinism, champ-group mapping, standings math, GAME round-trip; existing 24 stay green |
| `docs/` | AAR addendum: Jefferson spec + laddered-site framing |

Order: sports catalog + GAME records → geography/schools/conferences → schedules →
results/postseason → standings → rail + scoreboard → contest pages → sport landings
→ front/ladder → deploy switch → docs.

## 8. Verification

- Two generator runs → byte-identical `records/`.
- Class counts within spec tolerance; every school's sports plausible for its size
  (asserted: no 1A with 25 activities).
- `champ_group` matches the spec's tables exactly (unit-tested per sport).
- Standings hand-check: one conference's W-L recomputed from its game records.
- Rail density: demo-date window contains contests from ≥10 sports.
- Click paths: rail → game page → school → sport section → conference mini-front →
  state front; an out-of-state opponent renders unlinked.
- Full link-check green; `python3 -m pytest -q` green; Vercel build from a clean
  checkout produces the tree.
