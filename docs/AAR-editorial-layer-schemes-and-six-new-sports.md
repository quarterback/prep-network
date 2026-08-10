# AAR — the editorial layer, the scheme system, and six new sports

Follows `AAR-ingestion-postseason-and-tenant-brands.md`. That one ended with a
site that could parse a Hy-Tek PDF and draw a bracket. This one is about the
run after it, which was mostly about the things a results system needs that
are not results — and, at the end, about six sports added specifically to
find out where the model breaks.

---

## 1. The complaint that turned out to be a build failure

The user reported the same thing four separate times across the session, in
four different words: *the red/blue theme isn't there*, *the tour copy isn't
gone*, *I still don't see it*. Each time the code was correct and pushed, and
each time I checked the branch, confirmed the fix, and said so.

That was the wrong answer three times running. The right answer was found only
when I stopped verifying the branch and measured the build:

```
peak RSS  7.14 GB      elapsed 322s
```

Vercel's build container has 8 GB. `build()` rendered all 58,497 pages into a
dict, link-checked the dict, then wrote it — roughly 3 GB of HTML strings on
top of the records already resident. The build was dying at the ceiling, and
Vercel does the correct thing with a failed build: it keeps serving the last
one that succeeded. **Every commit for most of the session had been a coin
flip on whether it shipped**, and the user had been looking at a site several
commits behind while being told the work was done.

Fixed by planning pages as `(url, thunk)` pairs — which still yields the URL
set that link checking and the sitemap need in full — then rendering, checking
and writing one at a time:

```
peak RSS  0.63 GB      elapsed 186s
```

**The lesson is not "watch memory".** It is that when a user reports the same
invisible problem repeatedly and the code keeps looking right, the code is
probably not the system. I checked `git`, the branch, the merge and the diff —
four artifacts, all of which agreed with me — and never once checked the thing
that stood between them and the user. The user eventually diagnosed it
themselves ("production isn't getting the deploys, they sit in staging"),
which is the part that should sting.

---

## 2. An athletics site is not a scoreboard

The school and conference pages had been given their own mastheads in the
previous run and were still sparse, because a brand on a dashboard is still a
dashboard. The user's brief was precise about why: a real department has
several simultaneous jobs — what just happened, what is next, who was
recognised, what the standings say — and a page carrying one result and a
schedule rail is empty on every day nobody played, which is most days.

The fix was not layout first. It was that **there was nothing to lay out**.

`generators/jefferson/honors.py` derives 12,291 typed editorial items across
all 840 schools, median 11 each, from the state that already exists:

| Anchored in real data | Anchored only in a stable hash |
| --- | --- |
| athlete of the week — the best line in a real box score | scholar-athlete |
| coach milestones — real wins against a real career total | academic team |
| all-conference, coach of the year — off the standings | signings |
| record performances — real marks from real meets | hall of fame, staff hires |

The right-hand column still names real people from real rosters at real
schools and is selected by `crc32`, not a die, so nothing moves between runs.
Every item carries a **scope**, so one record renders as a school headline, a
league honour-roll entry and a statewide award — which is the first time the
tenant model did work rather than describing itself.

Then the layout: feature 48% / news+honours 27% / schedule 25%, above the
fold, then the season ribbon, then a four-module band. Event rows are three
lines where cards were six, so seven fixtures fit where four did.

The single change that mattered most is one line of selection logic. A school
now leads with a story that is **usually not a score** — a title, a milestone,
a record, a signing — and falls back to the last final only when nothing
bigger happened. Before, every school front in the state led with its most
recent result, which is why they all read identically.

### What went wrong here

`athlete-of-week` initially reached 86 of 840 schools, because box scores
exist on a quarter of games and I keyed the honour on box scores alone. A
module that is blank on 90% of pages is worse than no module. Widened to fall
back to a meet win or a winning dual flight — every school has one of the
three — and it reached 316 directly with the rest covered by other kinds.

Two headlines shipped naming the school in the dek but not the headline
("*Victor Nakamura named Breakwater League coach of the year / Lev Volkov
finished 8-0*" — reader meets two names and no connection). Caught by reading
the generated output rather than the generating code, which is the only way
these are ever caught.

---

## 3. Colour schemes, and a palette being filtered rather than applied

The user sent five palettes over the session and repeatedly said the red/white/
blue ones "didn't look red/white/blue". I twice replied, accurately, that every
hex was present in the CSS. Accurate and useless.

The actual cause: `--surface-mast` was hard-wired to `--linen`, and the type on
it to `--ink`. **The masthead — the largest coloured surface on every page —
could only ever be a pale tint.** In a red/white/blue palette that left red and
blue nowhere to go but a 20px chip in the corner, and the page came out beige.
That is a palette being filtered, not applied.

Fixed by making the masthead themeable (`--surface-mast`, `--on-mast`,
`--on-mast-dim`, `--mast-rule` — the band under the bar, where athletics sites
traditionally put their second colour). Nine schemes now each own their bar.

Every palette got a contrast pass before use, and the table decided the role
assignments rather than taste:

| Scheme | Note |
| --- | --- |
| **Ensign** (default) | the only palette needing *no* adjustment — twilight 18.7:1, oxblood 9.1:1, cobalt 8.6:1 as link text at the hex given, pure red 4.6:1 |
| Banner, Apex | bright accents demoted to fill-only; links darkened to clear AA |
| Rally | all five colours too bright for text (lemon is 1.3:1), so all five take surfaces |

Two related failures worth recording:

* **I invented two schemes** (pennant, chalk) to pad the picker to eight when
  the user asked for more. They hadn't asked for *mine*. Removed the same
  session, correctly.
* **The picker was seven unlabelled 20px squares**, living in `.fh-mast-nav`,
  which is `display:none` below 860px — so on a phone no scheme was reachable
  at all, and on school and conference pages (compact masthead) none was
  reachable at any width. The user asked for a dropdown; they were right.

And one that was not mine: the whole site rendered muddy grey on Brave mobile
because nothing declared `color-scheme`, so Chromium's Auto Dark Theme
re-inverted a page that never asked for it — flipping the white burger bars to
dark on a navy bar. `color-scheme: only light` is the opt-out (plain `light`
is not enough).

---

## 4. Six new sports, added to find the edges

Chess first, then badminton, squash, cricket and rugby sevens. The point was
not coverage. It was to see which of them the model absorbs as pure
configuration and which force a change — because "nothing downstream knows
what sport it is looking at" is the claim this catalog makes, and a claim
only means something where it could fail.

**Absorbed with no change at all:** squash (a five-line singles ladder) and
rugby sevens (a GAME with a two-table box score). Configuration only. That is
the result the catalog wants.

**Forced a change:**

* **Chess** needed a *drawn line*. Five boards, a point a board, and a drawn
  board is a half — 2.5–2.5 is an ordinary score. `Line.winner` had exactly two
  legal values. Now `"draw"` splits the point, `None` still means unplayed, and
  the renderer bolds neither side.
* **Chess** also needed a format where *nobody is eliminated*.
  `TournamentFormat.SWISS` — five rounds over two days, pairing on running
  score, no repeat meetings, a full-point bye for an odd field. Rounds and
  matchups carried it unchanged; what differs is that the champion is the top
  of a standings table, so `champion` and `runner_up` branch on format.
* **Badminton** needed a squad handed out *by gender within a co-ed sport*.
  A Line already held a list of competitors, but nothing had asked for one boy
  and one girl on the same side of one.
* **Cricket** needed a **result sentence**. Its box score — two innings, each
  with a batting card and a bowling card belonging to opposite teams — the
  section mechanism carried without complaint, which was a genuinely good sign.
  What it could not carry is that *"104 to 92" is not a result*. The same two
  totals are "won by 12 runs" if the side batting first defended, and "won by
  4 wickets with 7 balls remaining" if the chase got home. `Game.result` holds
  the sport's own sentence; every other sport leaves it `None`.

The cricket cards reconcile — each bowling card's runs conceded sum to the
total the other side made, its wickets to the wickets that fell. That
discipline then caught rugby, where conversions were being drawn at random and
the SCORING column did not add to the scoreline; solved back into tries,
conversions and a penalty, and verified across all 480 sides.

**A bug the sports found in existing code:** every playoff score outside
football and soccer came from one 38–72 basketball draw. A tennis quarter-final
shipped as 52–48; a volleyball playoff carried a 60-point score. Only the
finals looked right, because those were adopted from the state generator, which
has always known the difference. The first screenful was fine and every
interior round was nonsense — which is exactly where a reader clicks next.

---

## 5. Realism work, and what "doesn't make sense" turned out to mean

The user said golf, tennis, cross country and track "don't make any sense".
Investigating found the shared cause: **twelve of twenty MEET activities
carried a single event, and the team score under all of them was the same
derivation — add up the places of everything the school entered.** That put a
golf team on 36, a bowling team on 45 and a gymnastics team on 11: numbers in
no unit anyone scores those sports in.

Event cards now match the sport, and the team result is derived per event and
summed by a rule the *catalog* owns (`app.sports.MEET_SCORING`), so the
renderer can label the column in the units the generator computed — Strokes,
Pinfall, Points, Score, Rating. Ties share a place, which golf and bowling need
because their marks are whole numbers and a three-way tie on 79 was printing as
first, second and third.

Three flat bugs surfaced in the same pass, all of which had been live for the
whole project:

1. **Girls badminton was contested at foil, épée and sabre.** Everything that
   was not tennis or wrestling fell through to the fencing card.
2. **Every tennis, fencing and badminton line printed a score contradicting its
   own winner** — the scoreline was generated home-first and the winner drawn
   separately.
3. **Rosters were drawn from one unisex name list**, so Vera and Imogen
   wrestled at 106 and Rafael played girls tennis.

None of the three would have been found by reading code. All three were found
by printing the generated records and looking at them.

---

## 6. The photographs, and four bugs that had been eating them

The previous section of this file listed photography as a known gap and said
so honestly: nineteen stock images, several of them crowds and coaches. The
owner then did the obvious thing and dropped twenty-five photographs into
`site/img/news/additions/`.

They did not appear. Or rather, they appeared in some places and not others,
which is worse, and the reason turned out to be **four separate defects, none
of which would raise anything**:

| | |
| --- | --- |
| `ADDITION_CREDITS = _json.load(...)` ran three lines *before* `import json as _json` | `NameError`, swallowed by a bare `except`, so every credit in the folder resolved to the empty string. Silently. Which is the one failure mode a photo licence actually cares about. |
| `story_img` looked only in `img/news/` | a story whose picture arrived in the drop folder ran its own article page with no image while that same photograph led the front page |
| `image_size` joined `/img/additions/x.jpg` onto `site/` | the folder is a level deeper, so every share card fed by a dropped photo shipped with no width or height — the exact jumping-card problem that function exists to prevent |
| `SPORT_PHOTO` had no entry for `baseball` or `softball`, and still listed `girls-badminton` | `baseball.jpg` had been sitting in the library since the first build with nothing pointing at it; both diamond sports were resolving to a Fortepan archive interior. `girls-badminton` stopped being a key when badminton went co-ed. |

All four are the same shape as §5's: a fallback doing its job so well that the
thing it was covering for never got noticed. The bare `except` is the worst of
them — it is *load a file, or don't, either is fine*, applied to a legal
obligation. Both sidecar reads now go through one loader that catches
`FileNotFoundError` and nothing else.

Two things that were work rather than bugs. The files arrived at camera
resolution — 50 MB for twenty, one 4.3 MB frame for a single hero — so they
are resized to a 1600px long edge at quality 82, which is 5.7 MB for all
twenty-five, and the README now carries the one-liner that does it. And I had
to *look* at them: reading the filenames would have filed a girls lacrosse
huddle as rugby and a baseball tag play as softball, because that is what I
had them down as from a first pass over a contact sheet. A second look at full
size caught both. Same lesson as §5, in a different medium.

The folder now supports **variants** — `baseball.jpg`, `baseball-2.jpg`, up to
`-5` — because the owner supplied five baseball frames and the honest reading
of that is *use all five*. Which one a page gets is a stable hash of its school
or conference, so 840 school fronts leading on baseball no longer lead on the
same picture.

Sixteen of fifty-one sports now lead on a real photograph. The README lists the
thirty-five that do not, worst fit first, so the next drop has somewhere to go.

---

## 6b. The merge that was always going to happen

Two branches fixed the same 7 GB out-of-memory failure independently — §1 here,
and PR #15 — so the entire tail of `build.py` conflicted, both sides having
rewritten it for the same reason.

Resolved wholly in favour of #15, which is the better fix and not close:

* it stages into `dist.staging` and renames only after the link check passes,
  so a failed build leaves the previous tree standing rather than a
  half-written one — directly addressing §1, where a failed build was invisible
* it link-checks against the **route table** rather than against what was
  rendered, so a partial build can still prove its links
* it forks up to four workers: **389 s → 113 s**, 0.68 GB peak

The only thing grafted on from this side was the drop-folder copy. Worth
recording that the right move on a conflict this size was to read both and
concede, not to reconcile line by line — the two implementations agreed on the
diagnosis and differed on ambition, and merging them would have produced
something worse than either.

---

## 7. Things I would do differently

**Check the delivery path, not just the artifact.** Four rounds of "it is
fixed" against a user who could see it wasn't. The branch, the merge and the
diff all agreed with me and all three were the wrong evidence.

**Read generated output, not generating code.** Every substantive bug this
session — the sabres in badminton, the contradicting scorelines, the unisex
names, the phantom track team scores, the misaligned result language — was
found by dumping records and reading them, and none by re-reading the
functions that made them.

**Don't answer a design complaint with a correctness argument.** "Every hex is
in the CSS" was true and unhelpful twice. The user was describing what the page
*looked like*; I kept answering about what the file *contained*.

**Don't invent scope inside someone else's brief.** Two colour schemes I made
up to reach a round number, and a caveat shipped in place of a fix more than
once (that habit is documented in the previous AAR and recurred here).

**A bare `except` around a file read is a decision, not a convenience.** The
credits loader silently turned a `NameError` into "no photographer is credited
on anything", and would have gone on doing it. Catch the thing you mean —
`FileNotFoundError` — and let the rest raise.

**Look at the picture.** Two of twenty photographs were filed as the wrong
sport off a small contact sheet, and both were caught only by opening them at
full size. The medium changed; the §5 lesson did not.

---

## 7. Where it stands

```
59,096 pages · 840 schools · 25,795 athletes · links OK
51 sanctioned activities · 174 state championships
12,291 editorial items · 9 colour schemes · 25 photographs, 16 sports
201 tests passing, 1 skipped
build: 113s, 0.68 GB peak, 4 workers
```

```sh
python3 -m generators.jefferson.gen          # the state, at the demo clock
python3 -m ingest.run --demo --write         # every specimen, imported
python3 -m generators.jefferson.postseason   # brackets, meets, the Swiss
python3 -m generators.jefferson.boxscores    # periods, box scores, innings
python3 -m generators.jefferson.honors       # the editorial layer
python3 site/build.py                        # dist/site
python3 -m social.bsky --post                # the account, from the records
```

Known gaps, stated rather than hidden:

* **Photography, thirty-five sports of it.** Sixteen sports lead on a real
  photograph now; the rest are on the stock library. Most read correctly —
  they are the right sport, just not as good — but `chess` shows a general
  gym interior, squash shows tennis courts, and flag football shows tackle
  football. `site/img/news/additions/README.md` ranks them worst-fit first.
  I still cannot search Unsplash from the build environment (it wants an API
  key and returns `Authorization required`), so choosing them stays a job for
  a human with a browser.
* **Box-score players have no athlete pages.** Only meet and dual competitors
  are indexed, so honours naming a basketball player link to the sport page.
  Fixing it adds roughly 40,000 pages.
* **The chess championship is the only Swiss.** Nothing else uses the format,
  so its rendering has one consumer and one test path.
