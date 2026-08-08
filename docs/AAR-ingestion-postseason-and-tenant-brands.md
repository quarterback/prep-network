# AAR — the ingestion proof, the postseason layer, and whose site this is

Three pieces of work, requested together: prove the ingestion pipeline end to
end, build the state-association postseason as a real product surface, and make
school and conference pages read as those organisations' own homepages rather
than subsections of the association's.

## The premise that was wrong

The task began from a search of the repository for `hytek` and `ingest` that
returned nothing, and reasonably concluded the ingestion layer did not exist and
should be built.

It existed. `ingest/adapters/hytek_pdf.py` was already working against
`ingest/fixtures/specimens/hytek-meetmanager8-track.pdf` — a real 237-page
published printout — and pulling **7,192 results across 7 meets** out of it,
with heats, genders, classifications, rounds, relay legs and team scores, under
22 tests. The `Meet` / `Dual` / `Game` contest model and a `Provenance` record
were in `app/shapes.py`. That is the hardest single case in the whole brief and
it was done.

Worth stating plainly because it changed what the work should be. Building a
Hy-Tek track parser again would have produced a worse second copy. What was
actually missing was everything *around* the parser, which is where an ingestion
pipeline earns its keep:

| Asked for | State at the start |
| --- | --- |
| Hy-Tek track parse | **existed**, against a real specimen |
| Hy-Tek swimming | missing |
| box score input | missing — and `Game` had nowhere to put one |
| dual-match input | missing |
| school/athlete resolution | **missing entirely** |
| provenance a reviewer can audit | partial — and dropped on read for 2 of 3 shapes |
| rendered page from an import | no |
| one command to run an import | `ingest/run.py` parsed, but reported almost nothing |
| postseason / brackets | **nothing at all** |

## 1. Ingestion

### Adapters are per-format, not per-vendor

`hytek_swim` is a separate adapter from `hytek_pdf` despite the same vendor,
because the documents differ in ways that would put a conditional on every
branch of a shared parser. The PDF has no columns, only glyphs at coordinates,
so `hytek_pdf` resolves fields by x-band; a text report has real whitespace and
splits on runs of spaces. Swimming prints a **seed time beside the finals
time**, so "the last time on the line" is the wrong rule — it promotes every
scratched swimmer's seed to a result. Diving is scored rather than timed *in the
same report*, so the mark type is read off the event's column header, not its
name.

Three format-shaped bugs found while building, all of which produce
plausible-looking output rather than an error:

- **The splits row was being eaten by the relay-leg branch.** A cumulative split
  prints its interval in parentheses — `1:21.02 (28.33)` — and the `3)` inside
  one matches an unanchored `\d\)` leg marker. Ordered that way, every split in
  the meet vanishes silently. Fixed by testing splits first and anchoring leg
  markers to the start of the line.
- **The scorebook `TOTALS` row was misaligned by one column** in the fixture.
  Caught by the adapter's own checksum, not by reading it.
- **Dates were kept as Hy-Tek printed them** (`2/19/2027`). Every other record
  is ISO, so the meet sorted as a string against its neighbours and landed in
  the wrong place on every schedule — while looking like a date on its own page.

### Resolution is the half that decides whether a parse was worth anything

A meet naming `Lingle Ft. Laramie  High Schoo` — which appears **72 times in the
real specimen**, truncated at the column edge — is attached to no school. It
will not appear on that school's page, will not join its conference standings,
and will index its athletes under a name nothing links to.

`ingest/resolve.py` is a ladder — exact, normalized, alias, prefix, fuzzy — with
the rung recorded on every result. The rule that matters:

> **Ambiguity is refused, never resolved to the closest guess.** `Copper Lak`
> matches Copper Lake, Copper Lake East and Copper Lake West, so it fails and
> reports all three. Picking one would put results on the wrong school's page,
> and nothing downstream could detect it. An unresolved name is a visible gap; a
> wrongly resolved one is invisible and wrong.

Canonical output is always the bare school name — every suffix form is stripped,
including a truncated one, and `HS`, `High School` and a cut-off `High Schoo`
all fold to the same key.

### Sources are checked against themselves

Both totals-bearing adapters compare the source to its own arithmetic and drop
to `needs_review` when it disagrees. `scorebook-basketball-badtotals.csv` is
committed specifically so the review queue is demonstrated rather than asserted:
it parses cleanly, looks entirely normal, and is refused.

### What is not solid

The track PDF is a **captured** specimen. The swimming, box-score and dual
fixtures are **reconstructions** — the column semantics come from the captured
PDF and from the formats those systems produce, but the files were written for
this repository. That is weaker than the project's "no format is coded from
memory" rule wants, and it is recorded in each adapter's docstring rather than
left for someone to discover. The row shapes are right; real-world files will
carry variants these have never seen.

The track specimen's schools are Wyoming schools and resolve to nothing in
Jefferson. `--demo` says so explicitly instead of hiding it — the parse is
sound, the field is foreign.

## 2. The postseason

This did not exist. A "championship" was a `Game` whose name contained
`JHSAA 1A Championship`, which is exactly why the Championships page could only
be a season filter: there was nothing else to show.

The postseason is modelled as a **structure over contests**, not a fourth shape.
A `Tournament` holds the field, the seeds and the tree, and points at the
`Game`/`Dual`/`Meet` record for each matchup rather than restating it. Byes are
structural — a matchup with one side and no contest — because a "BYE" opponent
would enter the schools index and every page that counts opponents.

`app/postseason.py` lays the tree out on one coordinate canvas, adapted from the
NCAA bracket in `tennis-team-manager`, which had already learned the load-bearing
lesson: **cards and connector elbows must come out of the same server-side
pass.** Laid out by document flow and drawn by CSS they drift apart at some
viewport width, and every CSS fix moves the drift somewhere else.

### Three bugs, each of the "plausible wrong data" kind

**The published final drifted off its own teams.** Finals already on disk were
adopted for their score, and then `advance()` recomputed the matchup's teams
from the bracket's own feeders. The 1A football page showed the real 26–17
attached to two schools that never played it. Fixed at the source rather than
by suppressing the overwrite: when a final is already published, its two schools
take the 1 and 2 seeds — the only pair of slots that cannot meet early — so the
derived tree actually produces them, and the generator asserts the match.

**The generator read its own output as input.** Last run's quarterfinals counted
as regular-season wins, which moved the seeds, which moved the bracket. Running
it twice with nothing else changed produced a different postseason — so the run
that shipped was not the run you could reproduce. Generated rows are now owned
by their provenance adapter, excluded on read and cleared on write; three
consecutive runs are byte-identical.

**Fall soccer was "happening now" in January.** Two published finals had been
generated as draws and one as cancelled. A knockout final that ends level has no
winner, so the bracket adopted it, never resolved, and reported itself as still
being played — under *Happening now* on the front of the championships page, for
the rest of the year. Drawn finals are dropped and re-derived. A cancelled final
is now **resolved but not decided**: the tournament is over and crowns nobody,
which is what actually happened. `Tournament.status` COMPLETE therefore means
"the postseason is finished", *not* "there is a champion", and callers must
handle `champion is None`. The generator now exits non-zero if any bracket is
left unresolved in the past.

The three bracket states are the calendar, not a flag — fall finished in
November, winter runs through the demo date of 2027-01-16, spring has not
started. 112 championships: 51 complete, 26 in progress, 35 upcoming, with field
sizes 4/8/11/12/16/24/32 all occurring naturally.

## 3. Whose site is this

`shell()` grew a tenant mode. On a school or conference page the association
masthead is **replaced**, not de-emphasised: a utility strip carries `← JHSAA`
and a small network mark, and the organisation's crest, name and navigation
become the dominant header in its own colours. Championship pages deliberately
keep the association masthead — a state tournament is an association property.

Removing the duplicate mattered as much as adding the masthead. The school page
already had an identity block and its own nav from when it was a subsection;
with the masthead above it, Ashbrook's name, crest and navigation each appeared
twice on Ashbrook's own front page.

## What the screenshots caught that the markup did not

Two failures passed every string-level check and were only visible rendered:

- **The mobile bracket had tabs and no bracket.** The round radios were nested
  inside the tab strip, and `#brkr0:checked ~ .fh-brk-scroll` only reaches a
  later *sibling*, so every column stayed hidden. The markup contained all 31
  cards; none were displayed.
- **Fall soccer under "happening now"**, above.

Worth the habit: for anything visual, render it.

## Known limitations

- A combined-gender Hy-Tek meet is split into two contest records at import,
  because the association's sport keys are gendered. The split is done at the
  ingest boundary and is a judgement call, not something the source states.
- The mobile viewport reports horizontal overflow on every page including ones
  untouched here; it traces to the off-screen navigation drawer and predates
  this work.
- `Round of 16` is named by distance from the final, so a 16-team bracket's
  first round is "First Round" and a 32-team bracket's second round is "Round of
  16". That is the convention, but it means round names are not stable across
  field sizes.
- Three of the four specimens are reconstructions, as above.

## Merging main: the base was stale

This branch was cut from a `main` that has since moved a long way, and the
divergence mattered more than the diff suggested. `main` had landed **the 7A
expansion** — the state went from 256 schools to 840 across seven
classifications, not six — plus generated athletic marks (`site/marks.py`) and
a recomposed school/conference homepage.

Three consequences, none of which would have shown as a merge conflict:

- **The postseason was generated against the wrong state.** 112 championships
  built from 256 schools, with 7A missing entirely. Regenerating against the
  real state gives 129 championships over 840 schools.
- **Field-size bands went dead.** `target_field` was tuned when a division had
  a few dozen eligible schools; against a median of 88 it returned 32 for 59 of
  65 brackets, and five of the six shapes the renderer must support stopped
  occurring in real data. Rebanded against the actual spread.
- **Two more undecided finals.** The bigger state contained a championship with
  `status: final` and null scores — a second flavour of the "decides nothing"
  bug alongside the draws, and it stuck a bracket the same way. The check now
  covers both and leaves genuinely cancelled finals alone.

On the tenant masthead specifically, `main` had already recomposed the local
brand block, and its version is better than the one written here: `fh-orghead`
draws a school's *generated athletic mark* rather than a monogram square, and
already carries the Home · Teams · Schedule · Results · Championships ·
Athletics Info navigation. So the merge takes main's block wholesale and this
branch's contribution narrows to the part main was missing — replacing the state
masthead with a `← JHSAA` utility strip. Keeping both would have put the
school's identity on its own front page twice, which is the same duplication
this work removed once already.

The tests that broke on merge were the ones pinned to specific fixture data —
three named Copper Lakes, a `6A-5A` swimming division that is now `7A-5A`, a
cancelled final that no longer exists. They are now written against the shape of
the invariant instead of the fixture, so the next state regeneration does not
fail them for the wrong reason.

## Box scores across sports

Five sports, five completely different column sets, and the renderer is told
none of them:

| Sport | Tables | Columns |
| --- | --- | --- |
| Basketball | 1 | MIN FG 3PT FT OREB DREB REB AST STL BLK TO PF PTS |
| Volleyball | 1 | SP K E TA PCT AST DIG BS BA SA SE |
| Ice hockey | 2 | SKATERS G A PTS +/− PIM SOG FOW · GOALTENDING MIN SA SV GA SV% |
| Football | 4 | PASSING · RUSHING · RECEIVING · DEFENSE |
| Baseball | 2 | BATTING AB R H RBI BB SO AVG · PITCHING IP H R ER BB SO ERA |

Generating them forced two model corrections that the basketball fixture alone
had hidden:

**One column set per game is not enough.** Football prints four tables and
baseball two, with different columns and the same player appearing in more than
one. `StatLine.section` and `BoxScore.sections` carry that; a single `columns`
list could represent neither, and would have quietly dropped three quarters of
a football box score.

**Not every number in a totals row is a sum.** Volleyball's `SP` (sets played)
totals to 3, not to 24; `PCT` is an average. Both were reported as the source
contradicting itself. The rule is now sport-free: *a total that lands inside
the range of its own parts is not a sum of them* — which is true of `sp`,
`pct`, `avg`, `era` and `svpct`, and false of `pts` and `min`. Naming the
exceptions would have put a list of sports in the model.

**A final score is not always the sum of the periods.** Volleyball's linescore
is points per set (25-19, 25-22, 25-20) and its final is *sets won* (3-0).
`periods_agree` accepts either shape; checking only addition reported every
volleyball match in the state as broken.

Baseball is a **parse-only** specimen. The season has not started at the demo
date, so there is no played game to attach it to and importing it would stamp
an April result onto a January state; `ingest.run --demo` shows its columns
without writing a record.

## Commands

```sh
python3 -m ingest.run --demo                      # every specimen, parsed and resolved
python3 -m ingest.fixtures.make_boxscores         # regenerate the box-score specimens
python3 -m ingest.run <file> [--sport KEY]        # import; re-imports update in place
python3 -m generators.jefferson.postseason        # derive the championship layer
python3 site/build.py                             # 14,122 pages
python3 -m pytest -q                              # 202 tests
```
