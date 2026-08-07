# AAR — project genesis, source research, and scope

**Date:** 2026-08-07
**Status:** Scoping complete, build started
**Why this document exists:** the research below is the load-bearing part of this
project's rationale, and it was produced by fetching real artifacts rather than
reasoning from memory. It is written to be shareable on its own.

---

## 1. The idea

High school sports data is a diffuse, low-margin market the major vendors have largely
abandoned to inertia. MaxPreps and a handful of others sit on top; underneath, every
state association and school runs a patchwork. Results are produced by third-party
software — Hy-Tek, DirectAthletics, TrackWrestling, GolfGenius — which emits structured
data that is then **printed to PDF and discarded**. Nothing downstream ingests it.

The consequence is that local media cannot follow olympic sports — the non-football,
non-basketball half of the calendar — because there is no machine-readable path from
"the meet happened" to "the story exists."

The proposal: **one data model and one renderer serving a state association site, a
conference site, and a school site from the same records**, with the records living in
each program's own repository rather than a vendor's silo. Opt-in network; results flow
upward from school to conference to state, and outward to anyone building on the schema.

Two properties make this unusual:

- **The data is public record by nature.** Scores, marks, and rosters are already
  published. The usual privacy objection to federating a dataset does not apply, which
  makes this an unusually clean fit for AT Protocol.
- **It does not require anyone to change behavior.** The data already exists in Hy-Tek
  files and on local media sites. The ingestion layer meets it where it is.

The bar for the reader is deliberately modest: **see results on any device without
loading a third-party site.**

### What this is not

Not a venture-scale SaaS play. Not an attempt to out-scale MaxPreps, which is
unwinnable. This is a demonstration that a category of vendor software can be replaced
by an open schema and a parser — cheaply, by a very small team. If a state association
wants to pay for a bespoke build on top of it, good; that is not the motive.

---

## 2. Source research — what was actually observed

Every finding below came from fetching the live artifact.

### 2.1 A state association that publishes nothing

`whsaa.org` (Wyoming High School Activities Association) publishes **no competitive
results at all**. It is an administrative shell — officials' registration, board
minutes, rules clinics. Everything else links out to `dragonflymax.com` and
`nfhslearn.com`. No scoreboard, no standings, no live bracket.

This is the floor case, and it is not unusual.

### 2.2 Results published as a wall of PDFs

`whsaa.org/archives/track/trarchives.html` lists `TR-1973.pdf` through `TR-2026.pdf`
(2004 and earlier as `.htm`), plus `class.pdf` and `overallstate.pdf` record books.
Fifty-four years. No database, no API, no search, no structure.

### 2.3 The specimen: `TR-2026.pdf`

**A 237-page Hy-Tek MEET MANAGER 8 printout containing real embedded text** — not a
scan. Verified: zero image streams (`/Image`, `/DCTDecode`, `/CCITTFaxDecode`,
`/JBIG2Decode` all absent), 244 content streams carrying text operators.

Decompressing the content streams and reading the text-positioning operators recovers
the layout exactly. Its column structure is stable and machine-readable:

```
x=18.0    Event 1  Girls 100 Meter Dash 1A
x=47.2    1A2A East:  12.56  @ 2006   Maggie Ochsner, Lingle-Ft. Laramie      <- standing record
x=47.2    Name          x=199.8 Yr   x=222.0 School     x=403.3 Prelims  x=492.8 H#
x=34.7:1  x=48.0:Davis, Alaina    x=203.8:12  x=220.9:Kaycee  High School    x=410.5:13.08  x=437.8:Q  x=498.4:2
x=34.7:4  x=48.0:Mehling, Bailey  x=204.1:11  x=220.9:Southeast High School  x=410.5:13.49  x=438.8:q  x=498.4:3
```

The page header carries meet name, date range, venue, and the generating application:
`Hy-Tek's MEET MANAGER  8:27 AM  5/26/2026`.

**This single file is the whole argument.** The data was fully structured inside Hy-Tek
— places, marks, grades, school affiliations, heat assignments, qualifying flags,
standing records — and every bit of that structure was destroyed at print time. What
remains is a PDF. Recovering it is a parsing problem, not a data-availability problem.

**The specimen is checked in at `ingest/fixtures/specimens/hytek-meetmanager8-track.pdf`.**
It is kept as a *format specimen*, not as a data source — see §4.

#### The parsing detail that shapes the adapter

PDF kerning splits strings across text-showing operators. `Salway, Taelynn` is emitted
as `Salwa` + `y, Taelynn`, with both fragments anchored at the same x-position. Columns
must therefore be recovered by **x-position clustering with fragment joining at a shared
anchor** — never by whitespace splitting. A naïve `split()` corrupts roughly every name
containing a kerning pair, silently and plausibly.

### 2.4 Where the results actually live

Since the association publishes nothing, coverage falls to local media. `wyopreps.com`
(Townsquare radio) publishes the same results **two different ways on one site**:

- Article pages, hand-typed prose:
  `**Final Score:** #1 Sheridan 38 Laramie 14 - 52 straight for the Broncs.`
- A scoreboard page, native HTML tables:
  `10/25 - 7pm | #1 Gillette | 41 | #2 Cheyenne East | 6 | FINAL`

Both are real inputs the system must absorb. Neither is machine-readable today.

### 2.5 The aggregators block automated access

`athletic.net` returns **HTTP 403** to automated fetches. `osaa.org` likewise returned
**403**.

This is worth stating plainly rather than discovering in week three: a paste-a-link
ingestion surface will work against association sites, local media, and school sites,
and will **not** reliably work against the large aggregators. Any plan that assumes
otherwise is wrong.

---

## 3. Prior art in the author's own work

Much of this architecture already exists in pieces across earlier projects. The value of
this repo is partly consolidation.

- **`oregontennis.org` / cheesybook** — a live Oregon HS tennis tool with report-a-dual,
  scoreboard, teams, lineups, and seeding packets, filtered by Season / Gender / Class.
  This is the DUAL contest shape and scope-filtering already working, with real coach
  input. The hardest interaction in the whole system — getting a coach to report a
  result — is already solved here.
- **`tennis-team-manager`** — models dual formats precisely: per-line results, clinch
  rules, and formats that vary by division (`app/ncaa.py` `DUAL_FORMATS`,
  `engine/dual.py`). Directly transferable to the DUAL shape.
- **`dev-site`** — already publishes `site.standard.publication` / `site.standard.document`
  records to AT Protocol via a dependency-free Node client
  (`scripts/sync-standard.mjs`: `createSession` → resolve DID → resolve PDS →
  `putRecord`, with a mapping file for idempotency). That flow is the proven basis for
  the record publisher here, and `site.standard.*` is reused for articles rather than
  inventing an article lexicon.

---

## 4. Scope decisions, and one correction

| Decision | Choice |
| --- | --- |
| Time horizon | **Day 1 forward.** No historical backfill. |
| Data | Fictional state, emitted in the **real** observed formats |
| Inputs | File upload · paste a link · native CMS entry |
| AI role | **Extraction only** — nothing displayed is model-generated |
| AT Proto | **Protocol-native from the start** — records are the source of truth |
| Breadth | One season (fall), all three tenant tiers, end to end |

### The correction worth recording

Mid-scoping, the agent proposed pivoting to ingest the real 54-year WHSAA archive,
reasoning that real data is more convincing than synthetic. **This was wrong**, and the
owner rejected it:

> "why are you so insistent on capturing past data — I have NO INTEREST in parsing old
> data, this is all going to be DAY 1 FORWARD content not PAST CONTENT at all."

The reasoning that makes the fictional state correct:

1. **The system is forward-looking.** Its job is to capture results as they are produced,
   not to reconstruct history. Backfill is a different product.
2. **Real data carries complexity with no upside here** — minors' names, correction and
   takedown handling, association relationships — none of which the demo needs to prove
   anything.
3. **It forks cleanly.** Once a real association wants to see themselves in it, swapping
   the fictional state's data for theirs is a data change, not an architecture change.
   Building on the fictional state first *is* the portable path.

The Hy-Tek specimen therefore stays in the repo as a **format specimen** — evidence of
what real associations emit, and the fixture the adapter is tested against — not as a
corpus to import. The generator emits *new* content in that same real format.

### A related, separate finding

The recruiting/college-exposure angle (parents wanting kids' stats visible) is the most
crowded corner of this market — Hudl, NCSA, SportsRecruits, athletic.net profiles all
compete there. The uncrowded gap is a school or program **owning its athletics presence
without maintenance overhead**, in sports nobody covers. That is the defensible framing.

---

## 5. Architecture

```
   sources                adapters              records              projection        surfaces
┌──────────────┐      ┌──────────────┐     ┌──────────────┐     ┌────────────┐    ┌──────────────┐
│ Hy-Tek PDF   │      │ hytek_pdf    │     │ school repo  │     │            │    │ state site   │
│ semicolon    │─────▶│ hytek_delim  │────▶│ (per DID)    │────▶│  AppView   │───▶│ conf site    │
│ pasted URL   │      │ html_table   │     │ org.prepnet.*│     │  (SQLite)  │    │ school site  │
│ CMS form     │      │ prose        │     └──────┬───────┘     └────────────┘    │ results feed │
└──────────────┘      └──────────────┘            │                    ▲          └──────────────┘
                             │                    ▼                    │
                      review queue          local relay ───────────────┘
                      (confidence)          (Jetstream-shaped)
```

### The core model: three contest shapes

Every sport is a configuration over one of three shapes. Nothing downstream knows what
sport it is looking at.

| Shape | Structure | Sports |
| --- | --- | --- |
| **MEET** | N teams, M events; each entry has a **mark** (time/distance/height/points) and a place; team score derived from a placing table | cross country, track, swimming, wrestling tournaments, stroke-play golf |
| **DUAL** | 2 teams, N ordered lines, each its own result, team point per line, clinch rules | tennis, wrestling duals, match-play golf |
| **GAME** | 2 teams, 1 score each, optional period splits, optional box score | football, volleyball (sets), soccer, basketball, baseball |

**MEET is built first, and that ordering is not arbitrary.** The real specimen *is* a
MEET — heats, qualifying flags, relays, standing records, and a derived team score. It
is the shape nobody models well and the one that carries olympic sports. GAME is a MEET
with two entrants and no events. Building GAME first yields a schema that cannot express
a track meet, which is precisely the mistake the incumbents made.

### What "extraction only" implies

Everything rendered is deterministic from extracted records. No generated recaps, no
summaries, no narrative. The model's entire job is messy input → structured record.

That makes **provenance and review mandatory**, because there is no prose layer to hide
behind. Every record carries `source_uri`, `adapter`, `extracted_at`, `confidence`, and
`review_state`. Anything below threshold lands in a review queue and does not publish.
An unreviewed extraction is not a result.

### What "protocol-native" implies

The canonical store is the record repository, not the database. SQLite is a
**projection** that can be dropped and rebuilt from the record stream. This is what makes
portability provable rather than claimed, and it is the single test that decides whether
the protocol layer is real or decorative.

### Lexicons (`org.prepnet.*`)

Named for shapes, not sports. A namespace per sport per state (`com.<state>.<sport>.*`)
was considered and rejected — it defeats the interoperability claim outright.

`org.prepnet.org.school` · `org.prepnet.org.conference` · `org.prepnet.contest.meet` ·
`.contest.dual` · `.contest.game` · `org.prepnet.roster` · `org.prepnet.athlete` ·
`org.prepnet.standing` · `org.prepnet.bracket`

Development uses `.temp.` variant NSIDs per the AT Proto style guide until stable.

---

## 6. Technical notes worth keeping

**On AT Proto aggregation.** A common misconception is that aggregating N schools means
subscribing to N PDSes, and that this scales badly. It does not work that way. Relays
aggregate every PDS into a single stream; Jetstream converts that CBOR firehose to JSON
with a `wantedCollections` filter. Cost is independent of PDS count — 20 schools and
20,000 are the same subscription. Jetstream caps at 100 wanted collections/prefixes,
which one `org.prepnet.*` prefix satisfies permanently. The real throughput question is
AppView write rate on a peak night: a few hundred contests, which SQLite handles without
comment.

**Tooling.** `@atproto/lex` for validation and codegen, the `goat` CLI (`goat lex pull`),
and the Python `atproto` SDK, whose generator accepts custom schemas. What must be custom
is the AppView — no library does domain aggregation, and none should.

**Hosting.** The firehose consumer wants a long-lived websocket, which is awkward on
serverless. A single always-on machine is simpler; `tennis-team-manager` already runs
this shape on fly.io (`gunicorn --workers 1 --threads 32`, volume-backed SQLite), so
there is no new operational surface.

**PDF extraction needs no library.** Content streams are `zlib`-compressed; text
positions come from `Tm`/`Td` operators and text from `Tj`/`TJ`. Stdlib `zlib` + `re` is
sufficient, and was used to produce §2.3 above.

---

## 7. Verification that matters

- **Adapter fidelity against the specimen** — parse the Hy-Tek PDF and assert against a
  hand-checked expected extraction covering a kerning-split name, a relay, a `Q`/`q`
  qualifier, and a standing-record line.
- **Relay round-trip (the decisive test)** — drop the AppView database, replay the record
  stream, assert the rebuilt projection is identical. This proves records are the source
  of truth and the site is a projection. If it does not pass, "protocol-native" is
  decoration.
- **Scope isolation** — a school tenant must never render another school's data.
- **Standings math** — derived MEET team scores match hand-computed values.
- **Lexicon validation in CI** so records cannot drift from their schemas.

---

## 8. Open items

- GitHub repo creation is blocked for the current integration (403 on
  `POST /user/repos`); the repo must be created manually before anything can be pushed.
- Live-PDS demo schools need a handle and app password, same setup as the existing
  standard.site workflow. Not needed until the local record store works.
- Project naming is unsettled; `prep-network` is a placeholder.
