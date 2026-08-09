# prep-network

Open infrastructure for high school sports results.

One data model and one renderer serving a state association site, a conference
site, and a school site from the same records — with the records living in each
program's own repository rather than a vendor's silo.

The bar for the reader is deliberately modest: **see results on any device
without loading a third-party site.**

---

## The problem, in one file

State associations run their meets in software — Hy-Tek MEET MANAGER,
DirectAthletics MeetPro, TrackWrestling — that holds every place, mark, grade,
school, heat assignment and qualifying flag as structured data. Then it prints a
PDF, and the structure is gone. The PDF is what gets published.

`ingest/fixtures/specimens/hytek-meetmanager8-track.pdf` is a real published
example: 237 pages, real embedded text, zero image streams. Reading it back:

```
7 meets · 7,192 results · 73 relay events · 71 schools
```

from a document that a computer previously could not answer a single question
about. That is the whole argument.

The file is kept as a **format specimen**, not a corpus. This project is
day-one-forward; it does not backfill history. The specimen exists so the parser
is written against real structure instead of an invented one.

## Status

| Piece | State |
| --- | --- |
| `ingest/pdftext.py` — positioned PDF text, stdlib only | working |
| `ingest/adapters/hytek_pdf.py` — Hy-Tek printout → `Meet` | working, real specimen |
| `ingest/adapters/hytek_swim.py` — MM text results → `Meet` | working |
| `ingest/adapters/scorebook_csv.py` — scorebook → `Game` + box score | working |
| `ingest/adapters/dual_card.py` — match card → `Dual` | working |
| `ingest/resolve.py` — source names → member schools | working |
| `app/shapes.py` — MEET / DUAL / GAME + postseason | working |
| `app/postseason.py` — bracket geometry | working |
| `generators/` — the fictional state, incl. 165 championships | working |
| `site/build.py` — 54,005 pages, three tenant tiers | working |
| `atproto/` — lexicons, local repo store, relay, AppView | not started |

```sh
python3 -m pytest -q                              # 202 tests
python3 -m generators.jefferson.gen               # the state, at the demo clock
python3 -m generators.jefferson.mascots --check   # the mascot distribution
python3 -m generators.jefferson.boxscores         # periods, box scores, track cards
python3 -m ingest.run --demo                      # every specimen, parsed and resolved
python3 -m generators.jefferson.postseason        # derive the championship layer
python3 site/build.py                             # writes dist/site/ (54,005 pages)
```

## Ingestion, end to end

`python3 -m ingest.run --demo` parses every committed specimen and prints what
it produced — contests, resolution report, and anything the source's own
checksums flagged:

```
hytek-mm-swimming-results.txt      → hytek_swim
  meet  2027 JHSAA 7A-5A Swimming & Diving …   7 events · 31 results · 10 schools
scorebook-basketball-boxscore.csv  → scorebook_csv
  game  Copper Lake East at Ansotegui Siding   65–53 · 4 periods · box 15 players
scorebook-basketball-badtotals.csv → scorebook_csv
  game  Sage Summit at Norview                 [needs review: totals disagree]
dual-tennis-match-card.txt         → dual_card
  dual  Academy of Arts … at Vista Terrace     9 lines · 5.0–4.0
hytek-meetmanager8-track.pdf       → hytek_pdf
  meet  WHSAA State Track & Field Championships  141 events · 2,427 results
```

The flow is `file → parser → normalization → resolution → contest record →
page`, and the source stays attached: every imported record carries its
filename, format family, content hash, the source's own ids, and the adapter
version that read it, shown on the page itself.

Two rules that are load-bearing rather than decorative. **Ambiguity is refused**
— `Copper Lak` matches three schools, so it fails and reports all three instead
of guessing, because a wrongly resolved school is invisible and wrong where an
unresolved one is a visible gap. And **a source is checked against itself** — a
scorebook whose TOTALS row disagrees with its player rows lands as
`needs_review`, which `scorebook-basketball-badtotals.csv` exists to prove.

## The postseason

Championships are first-class records, not text on a game. A `Tournament` holds
the field, the seeds and the tree and *points at* the contest record for each
matchup; byes are structural rather than a fake opponent. Brackets are laid out
server-side in `app/postseason.py` so cards and their connector elbows share one
coordinate system — horizontally scrolling on desktop, one round at a time below
900px. Titles decided by a meet rather than a bracket (cross country, golf,
swimming, marching band) route to the meet renderer under the same navigation.

The demo clock is **2027-05-13**, set in `generators/jefferson/gen.py`. It is
late in the year on purpose: every season has results (fall 14,136 · winter
12,749 · spring 3,324, and all 45 sports), and staggered championship weekends
mean complete, in-progress and upcoming brackets all exist at that one date.
Scoring happens inline with scheduling, so moving the clock produces a
*different* season rather than the same one further along — everything derived
from it has to be rebuilt.

**[`/tour/`](dist/site/tour/) is the fastest way in.** One live link to every
page type the site produces — a box score, each of the three bracket states, a
bye, a meet-decided title, an imported record, a school site. Links are
resolved from the records at build time, so the page cannot rot into a list of
404s when the state is regenerated; a category with no example says so rather
than linking nowhere.

See [`docs/AAR-ingestion-postseason-and-tenant-brands.md`](docs/AAR-ingestion-postseason-and-tenant-brands.md).

## The model

Every activity a state association sanctions is a configuration over one of
three shapes. Nothing downstream knows what sport it is looking at.

| Shape | Structure |
| --- | --- |
| **MEET** | N teams, M events; each entry has a mark and a place; team score **derived** |
| **DUAL** | 2 teams, N ordered lines, one team point per line, clinch rules |
| **GAME** | 2 teams, one score each, optional periods and box score |

MEET is built first on purpose. It is the shape that carries olympic sports and
the one nobody models well; GAME is a MEET with two entrants and no events.
Building GAME first yields a schema that cannot express a track meet.

Marks are wider than "a number", because an association sanctions **activities**,
not just sports — a survey of a sport-rich association (CHSAA, ~30 activities)
turns up judged scores (gymnastics, spirit), adjudicated ratings (music),
ordinal-only placings (speech, debate), and tallies (golf, bowling) alongside
measured times and distances.

## What made the parsing hard

Three things, each of which fails silently and plausibly:

1. **Kerning splits cells across show operators with no position of their own.**
   `Salway, Taelynn` is emitted as `Salwa` + `y, Taelynn` at one anchor. Sorting
   fragments by x yields `y, TaelynnSalwa`. The fix is to concatenate in
   emission order — exact, and needs no font metrics.
2. **A published "results PDF" is often a bundle, not a contest.** The specimen
   is six regionals plus the state championships. Parsed as one meet, every
   classification's 100m stacks into event 1 and three athletes tie for first.
3. **Event numbers are reused across rounds**, and relays print the school where
   the athlete name goes. Both drop or duplicate data while the output still
   looks complete.

## Design commitments

- **Extraction only.** Nothing rendered is model-generated. The model's entire
  job is messy input → structured record, which makes provenance and a review
  queue mandatory: every record carries `source_uri`, `adapter`, `extracted_at`,
  `confidence`, `review_state`. An unreviewed extraction is not a result.
- **Protocol-native.** The canonical store is the record repository; SQLite is a
  projection that can be dropped and rebuilt from the record stream. The test
  that decides whether that is real: drop the database, replay, compare.
- **Team scores are always derived.** A printed team-score table is a checksum
  for the extraction, never an input to it.
- **No format is coded from memory.** Every adapter is written against a real
  captured specimen.

See [`docs/AAR-project-genesis-and-source-research.md`](docs/AAR-project-genesis-and-source-research.md)
for the source research and the reasoning behind the scope.
