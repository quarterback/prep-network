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
| `ingest/adapters/hytek_pdf.py` — Hy-Tek printout → `Meet` | working, 22 tests |
| `app/shapes.py` — MEET / DUAL / GAME contest model | working |
| `atproto/` — lexicons, local repo store, relay, AppView | not started |
| `app/web/` — the three tenant tiers | not started |
| `generators/` — the fictional state | not started |

```sh
python3 -m pytest -q
```

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
