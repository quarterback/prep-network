# AAR — ingestion, the postseason, tenant brands, the demo clock, and mascots

Started as three pieces of work and grew to six across the session. The three
that were asked for up front: prove the ingestion pipeline end to
end, build the state-association postseason as a real product surface, and make
school and conference pages read as those organisations' own homepages rather
than subsections of the association's. Three more arrived as the work was
reviewed: box scores across five sports, moving the demo clock so every season
has results, and rebuilding the mascot system.

The most useful thing in this document is probably the section on **the
workaround habit** near the end. Twice I shipped a caveat where a fix was
available, and both times the reviewer had to point it out.

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
- Eight of the nine specimens are reconstructions; only the track PDF is a
  captured file.
- The generated box-score numbers are internally consistent but not always
  *plausible* — a running back can end up with 22 carries for 11 yards, because
  attempts and yards are drawn independently. The totals add up; the football
  does not always make sense.
- `generators.jefferson.gen` and `.postseason` each carry their own copy of the
  demo date. They agree today; nothing enforces it.

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

### And then PR #7 landed on top

A second branch shipped the same tenant-masthead feature a different way — a
`compact` variant of the state masthead behind `shell(..., org=True)` — and
merged first. That is a genuine conflict of approach, not of text: two
implementations of one requirement, and only one can exist.

The resolution was to **take main's wholesale and keep only the part it was
missing**. Reverting a merged decision to reinstate a parallel one is the wrong
kind of conflict resolution even when you prefer your own; what this branch had
that main's did not was the explicit `← JHSAA` link-back, which is the thing
that makes a shrunken bar read as a *network* bar rather than just a smaller
state bar. That is now one added line, not a competing masthead.

Also carried over from that branch: three places where 7A existed everywhere
except the navigation — the Schools menu, two classification facet bars, and a
class-span sort using `'654321'.find()` that ranked 7A correctly only by
accident. Those were defects in this branch too, so duplicating the fix the
same way was better than waiting to see which PR merged first.

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

### The demo clock was the actual problem

Baseball first shipped as a *parse-only* specimen: the season had not started at
the demo date of 2027-01-16, so there was no played game to attach it to. That
was a workaround for a fixable problem, and the fix was the obvious one —
**move the clock**. It should have been the first move rather than the last.

Two thirds of the calendar had no results at January: every game after
2027-01-16 was scheduled and scoreless, so no spring sport could demonstrate
anything. The clock is one constant in `generators.jefferson.gen`, but moving it
is not "the same season further along" — scoring happens inline with
scheduling, so a later date consumes different RNG draws and produces a
*different* season. Everything derived from it has to be rebuilt, and anything
pinned to a specific result stops being true.

At **2027-05-13** all three seasons have results (fall 14,136 · winter 12,749 ·
spring 3,324) and all 45 sports have at least one. Baseball imports like any
other sport.

Two things had to move with it. Championship weekends are now **staggered** —
fall in November, winter in February, spring split between 05-22 and 06-12 —
because a single spring date would put every spring bracket in the same state
and the postseason pages would only ever demonstrate one of the three. And the
tests that named specific schools had to stop: the 1A football champion is
Greaves Junction now, not Mabryville, and an assertion naming Mabryville still
passed because they remain in the 32-team field. Those are written against the
invariant now — *the champion is the winner of the contest the final links to* —
which is true at any clock.

## Mascots

The state had **36 names dealt uniformly to 840 schools**. The commonest
appeared 28 times, nothing appeared once, and every mining town and fishing
port drew from the same small bag. Massey's national database shows three
separate things wrong with that.

**The curve is steep and long-tailed.** Eagles is 1,229 high schools, Tigers
879, Panthers 827 — then thousands of names used exactly once. Roughly a fifth
of American high schools share the top dozen names and roughly a third have a
name almost nobody else has; a uniform draw over a short list produces neither
end. The core list now carries Massey's own counts as weights, so the shape
comes from the real data instead of a guess. Result: **407 distinct names, 72%
used once, the commonest at 3.7%** (Massey's real Eagles share is about 5%).

**The common names are national; the odd ones are local.** Nobody invents
"Eagles" — it arrives from everywhere. But Hoopeston's Cornjerkers, Jordan's
Beetdiggers, Cairo's Syrupmakers and Tillamook's Cheesemakers are each a town
describing its own work, and each exists in one place. So the tail is generated
per area and **consumed rather than sampled**: Gold Valley gets Orediggers,
Highgraders and Assayers; Harborline gets Dorymen, Bar Pilots and Netmenders;
Cascade Divide gets Lava Bears and Alpenglow. Zero landed in the wrong area.

**Fauna from elsewhere.** Condors, servals, markhor, kookaburras, pangolins,
leafcutters — steered toward metro and private schools, where they land at
**1.6× their base rate** rather than sprinkled evenly over ranch country. A
real 1A school is not the Pangolins; this is a deliberate stretch for variety
and is documented as one.

### The Indigenous-names question, and getting it wrong first

I initially excluded Native American mascots wholesale and wrote that up as a
principled decision. The reviewer's response — that imaginative Indigenous
names exist which aren't racist — was right, and the blanket rule was the lazy
read rather than the careful one.

The line that actually matters is **a people used as a mascot** versus **a word
from the region's languages for a thing**. Out: Indians, Braves, Chiefs,
Redskins, Redmen, Savages, and every tribal name — Indians alone is 418 high
schools on Massey, and the few programmes that keep one do it under an explicit
agreement with the nation whose name it is, which a fictional state cannot
claim. In: *chinook* (a wind and a salmon), *skookum* (strong), *hyak* (swift),
*kokanee* (landlocked sockeye), *wapiti* (elk), *sasquatch* (from Halkomelem
*sásq'ets*). Those name a thing, several are already ordinary English, and
Hyaks, Chinooks, Nanooks and Wapiti are real current uncontroversial mascots.
It is also the layer Jefferson's own map is already built from — Klamath,
Owyhee, Shasta, Siskiyou.

They weight only into the areas whose landscape the words describe, which is
where the real ones are. One candidate got cut on review: *klahowya* is a
greeting, so "Klahowyas" would have meant "Hellos".

Assignment is a post-pass keyed on each school's name, costing the state
generator no RNG draws. The now-redundant `rng.choice` in `gen.py` stays for
exactly that reason — deleting it would shift the RNG stream and silently
regenerate the season.

## Depth, and a route to find it

The reviewer opened a championship game page and saw a bare final score. The
numbers were worse than that suggested: **23,149 played games, 5 with a box
score, 84% with no period scoring at all.** Basketball had 1 of 3,817 — my own
imported fixture. Track meets carried exactly one event each, when a real one
runs eighteen and MEET is the shape this whole model was designed around.

So the ingestion work had proved a capability on five files and stopped. A
capability demonstrated on five records out of thirty thousand is one nobody
browsing will ever meet, which makes it indistinguishable from not having it.

`generators/jefferson/boxscores.py` is a post-pass, on the same terms as the
mascots — keyed on each record's identity, no RNG contact with the state
generator:

- **Period scoring on everything that has it**: 97% of played games, up from
  16% (and that 16% was volleyball alone, because the generator returns sets
  for volleyball and `None` for everything else).
- **Box scores on a slice**: every postseason game, plus a deterministic 22% of
  the regular season. 5,875 in all. Not everything — these are fictional games
  and boxing all of them adds ~60MB of invented statistics for no extra proof.
- **Full 18-event cards for track meets**, with entries drawn from each
  school's roster.

Rosters are per (school, sport) and stable across games, so a player who scores
18 in December is the same player in February and athlete pages accumulate a
season instead of showing one disconnected line.

Two bugs while building it, both already-seen shapes:

- **Not idempotent.** The box-score selection RNG was the same stream the
  period generation drew from, so on a second run — where periods already
  existed and consumed nothing — a different set of games was selected and the
  count grew from 5,792 to 8,731. Exactly the postseason generator's bug, and
  the same fix: independent streams per decision.
- **A stat that did not add up.** Offensive plus defensive rebounds did not
  equal total rebounds, because all three were drawn separately. Any reader who
  checks a box score checks that.

### The tour page

Depth alone does not solve the actual complaint, which was *"I need a route
where I can at least show how the various page types work, so I'm not hunting
for all of this."* A 54,000-page build hides its own range: a bye only appears
in brackets with an odd field, a needs-review import is one record in thirty
thousand.

`/tour/` is one live link per page type, grouped — results, ingestion, the
three bracket states, organisations. Every link is **resolved from the records
at build time** rather than hard-coded, so it cannot rot into a list of 404s
the next time the state regenerates, and a category with no example says so
instead of linking nowhere.

That last property immediately earned itself. The first build reported "no
example" for Meet, which is how I found the one-event track meets. The second
reported it for "imported dual" — because the plain "Dual match" row above it
had taken the imported record, since row selection deduplicates. Both were the
index telling me something true about the state rather than rendering a
plausible page over a gap.

## The workaround habit

The most repeatable lesson from this session is not technical. Twice I shipped
a caveat where a fix was available, and both times the reviewer had to say so.

**Baseball as a "parse-only" specimen.** The spring season had not started at
the demo date, so there was no game to attach a box score to. I documented that
as a known limitation and moved on. The fix was to move the clock — one
constant — and the reviewer's "it was always silly that you didn't do that from
the outset" was correct. Moving it turned out to have real consequences (a
different season, restaggered championships, tests that had to stop naming
schools), but *none of those were reasons not to do it*; they were the work.

**The blanket mascot exclusion**, above: a rule that avoided the question
instead of answering it.

**Box scores proved on five files.** The capability was real and the rendering
was right, and I stopped at the point where it was demonstrable to me rather
than the point where it was discoverable by a reader. 5 records out of 23,149
is a feature you have to be told about to find.

The shared pattern is choosing the option that is easiest to write up honestly
over the option that is best for the product. A caveat in a docstring feels
like diligence and reads like one, which is exactly what makes it a
comfortable place to stop. The check that would have caught both: *is the thing
I am about to document as a limitation actually fixable with the tools already
in the repo?* For the clock it was one constant, and for the mascots it was a
distinction that the retirement campaigns themselves already draw.

A third, smaller instance of the same shape: several tests were written pinned
to specific fixture data — three named Copper Lakes, a `6A-5A` division, a
cancelled final, Mabryville as champion. Every one of them broke or, worse,
**kept passing while asserting something no longer true**: after the clock
moved, the assertion naming Mabryville still passed because Mabryville remained
in the 32-team field long after it stopped winning it. A green test asserting a
stale fact is worse than a red one. They are now written against invariants —
*the champion is the winner of the contest the final links to* — which hold at
any clock.

## Commands

```sh
python3 -m ingest.run --demo                      # every specimen, parsed and resolved
python3 -m ingest.fixtures.make_boxscores         # regenerate the box-score specimens
python3 -m generators.jefferson.mascots --check   # the mascot distribution
python3 -m ingest.run <file> [--sport KEY]        # import; re-imports update in place
python3 -m generators.jefferson.postseason        # derive the championship layer
python3 site/build.py                             # 14,122 pages
python3 -m pytest -q                              # 202 tests
```
