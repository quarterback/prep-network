# AAR — build scaling: measuring before choosing an architecture

**Date:** 2026-08-10
**Status:** Streaming and parallel rendering shipped; federation still a design question
**Why this document exists:** the brief proposed four architectural directions
for cutting the cost of a 58,000-page build. Measuring first killed three of
them and found a fifth nobody had named. The measurements are the useful part,
and they outlive the specific fix — anyone proposing to shard, defer or
federate this site should start from these numbers rather than from intuition
about what a large static build costs.

---

## The premise that was wrong

The brief framed the problem as **page count**: 58,497 pages is a lot of pages,
so cut pages — federate them into per-school repos, defer the tail to edge
rendering, prune sparse routes, distribute the deploy.

Page count was not the problem. The build's peak memory was the entire site
held as live Python strings so a link check could scan it at the end, and the
per-page cost was dominated by chrome that is identical on every page. Both are
fixed without removing a single page, and neither was on the list.

Three of the four proposed directions turn out to be aimed at the wrong thing.
The fourth — federation — survives, but for a reason the brief did not give,
and the reason only becomes visible once you measure the link graph.

## The baseline, measured

Full `python3 site/build.py` on a 16 GB Linux box, records as committed:

| | |
| --- | --- |
| wall time | 252 s |
| **peak RSS** | **7,313 MB** |
| pages | 58,497 |
| output tree | 3.37 GB across 58,553 files |
| mean page | 56 KB |
| **smallest page on the site** | **51 KB** |
| registry load alone | 9.0 s, 630 MB |

Two lines carry the whole story.

**7.3 GB peak.** Vercel's standard build container is 8 GB. This build was not
approaching a limit at some future scale; it was running at roughly 90% of the
ceiling with the state exactly as it stands today, and memory scaled linearly
with page count. Whatever the exact ceiling on a given host, a static site
generator that needs 7.3 GB to emit HTML has no headroom: the next
classification, or the next season of records, ends the build with an OOM
rather than a slow one.

**51 KB minimum.** No page on the site is smaller than 51 KB and the mean is
56 KB, which means the floor is not content — it is the chrome every page
carries. Measured on the smallest page in the tree
(`/meets/2027-05-22-jhsaa-7a-5a-choir-championships/`, 50.7 KB):

| | |
| --- | --- |
| score rail | 16.7 KB |
| masthead | 10.1 KB |
| mobile drawer | 9.7 KB |
| icon sprite | 6.7 KB |
| inline scripts | 4.1 KB |
| footer | 0.9 KB |
| **chrome total** | **48.2 KB — 95% of the page** |

The pages were not big. There were a lot of them, each carrying its own copy of
the same header.

`build()` rendered all 58,497 pages into one dict, link-checked the dict, then
wrote it. Peak memory was therefore the entire site as live Python strings —
about 3.4 GB of HTML, the bulk of it that repeated chrome, plus the 630 MB
registry and the garbage thrown off along the way.

## Finding: the site cannot be pruned by reachability

The appealing version of "build less" is to render only what the live surface
reaches — `/tour/` is the demo, so build the tour and what it links to. A
subset closed under linking cannot produce a dead link, so this would be safe
by construction.

It was tested against the built tree by BFS over every `href="/…"`:

| seed | closure | share of site |
| --- | --- | --- |
| `/tour/` alone | 57,744 | 98.7% |
| `/` alone | 57,744 | 98.7% |
| front + all nav entries | 57,744 | 98.7% |

Truncating the walk instead of running it to a fixpoint does not help, because
what it leaves behind is dead links:

| depth from nav | pages kept | links escaping the set |
| --- | --- | --- |
| 1 | 1,875 | 38,493 |
| 2 | 40,368 | 17,376 |
| 3 | 57,744 | 0 |

The site is one strongly-connected component three hops wide, and the cause is
the chrome again: **every page's masthead links `/schools/`, which links all
840 school pages, and a school page links its entire season** — 23,385
school→game edges — each of which links its athletes. Any page reaches every
page.

So reachability pruning is not a lever here. Not "expensive" — unavailable.
The only ways to cut page count are to change what links exist (a product
change) or to move the boundary so that a link leaves the origin entirely
(federation, below).

## Finding: sparse-route pruning is not where the money is

Auditing for empty and unreferenced routes was the third suggestion. Measured:
**753 pages the build writes that nothing in the tree links to** — 1.3% of the
site, every one of them an athlete.

The cause is one slice. `meet_results_tables()` prints `ev.entries[:30]`, while
`Registry.index_athletes()` gives every entrant a page. In a championship cross
country race the field runs well past 30, so an athlete who finished 31st has a
page built for them and no link to it anywhere on the site. A worked example:
`abel-abbott-pine-siding` has exactly one result, the JHSAA 2A Boys Cross
Country Championships, and it sits below the cut.

That is a correctness question, not a build-cost one — the fix is either to
link everyone the meet indexes or to index only who it links, and which of
those is right is a presentation call about how a 200-runner table should read.
Pruning it would save 1.3% of a build whose problem was 7.3 GB. Noted here
rather than fixed, because it is a product decision wearing a build-cost
costume. The empty per-sport sub-routes are the same order — a few hundred
pages at most.

## First: streaming the pages to disk

`build()` now streams. `page_routes()` returns the complete url → thunk table
without rendering anything; the build loop renders one page, harvests its
hrefs, writes it, and drops it. `link_check()` takes the harvested hrefs and
the route table instead of a dict of retained page text.

| | before | after | |
| --- | --- | --- | --- |
| peak RSS | 7,313 MB | **646 MB** | 11.3× less |
| wall time | 252 s | **214 s** | 15% faster |
| pages | 58,497 | 58,497 | — |
| output tree | `6a029c27…b81f5` | `6a029c27…b81f5` | byte-identical |

The output is the same tree: sha256 over all 58,553 files, paths included,
matches the pre-change build exactly. Nothing about the site changed.

Memory is now the registry plus one page, flat for the whole run — it does not
scale with page count at all. The build also got *faster* despite doing the
same work, because holding 3.4 GB of live strings had been making every
allocation and GC pass more expensive than the writes it deferred.

Two smaller consequences fall out of the same change:

- Pages are written to `dist/site.staging` and renamed over `dist/site` only
  after the link check passes. Previously the check ran before any writing, so
  a failed build left the old tree alone; now that pages hit disk first,
  staging is what preserves that.
- `FH_ONLY=<kinds>` renders just those page kinds. Because the route table is
  complete even when the render set is not, a partial build still link-checks
  every href it emits against all 58,497 urls the site would serve — it proves
  no link is a typo or a dead route, it just does not prove the unbuilt pages
  render. It refuses to write a sitemap, and says on stdout that the tree is
  not deployable, because a sitemap listing urls this run did not write would
  advertise 404s.

  This is the answer for iterating on the demo surface. The pages the tour and
  the front actually show are 18 of the 58,497:

  ```
  FH_ONLY=front,tour,index,news,scoreboard python3 site/build.py
  18 of 58,497 pages · links OK · 8.6 s
  ```

  8.6 s against 214 s, of which 9 s is loading the registry — so the render
  work is essentially free and the floor is the record load. Kinds are
  `front scoreboard tour index news contest sport championship school
  conference athlete`; an unknown one is rejected with the list rather than
  silently building nothing.

## Then: rendering in parallel, which the first change unlocked

Parallelism was not available before. A shared 3.4 GB dict and a link check
that needed every page at once meant there was nothing to parallelise over.
Once `page_routes()` existed, the build was a list of independent thunks, and
each worker needed only the registry plus one page.

`render_slice()` is the unit: render, harvest hrefs, write, drop. `render_all()`
forks `FH_JOBS` workers (default: one per core, capped at 4) and merges the
returned href maps for a single link check in the parent. Fork rather than
spawn, so the 630 MB registry and the route table are inherited copy-on-write
instead of pickled down a pipe.

Two details that matter more than they look:

- **Round-robin slices, not contiguous blocks.** The expensive pages cluster by
  kind — the 840 school pages each render a full season and dominate the tail.
  A block split leaves one worker grinding through all of them while the others
  sit idle. `picked[i::jobs]` interleaves the kinds.
- **Slices are merged in order**, so `link_check` names the same source page
  for a given bad href on every run. Parallelism should not make an error
  message nondeterministic.

| | original | streaming | + 4 workers |
| --- | --- | --- | --- |
| wall time | 252 s | 205 s | **63.9 s** |
| peak memory | 7,313 MB | 646 MB | **~1,840 MB** |
| output tree | `6a029c27…b81f5` | same | same |

**3.9× faster than where this started, at a quarter of the memory**, and the
tree is still byte-identical — same sha256 over all 58,553 files as the
pre-change build.

The memory figure is PSS summed across the process tree, sampled at 10 s
intervals, not `ru_maxrss`. That matters: `RUSAGE_CHILDREN.ru_maxrss` reports
the largest *single* child (657 MB here) and summing RSS across forked workers
double-counts the shared registry (3,193 MB). PSS is the honest number — 1.84 GB
of real physical memory, against an 8 GB container.

So the memory won back by streaming is partly spent again to buy the speedup,
which is the right trade at 4 workers and stops being one well before 8: the
copy-on-write share of the registry diverges as CPython touches refcounts, so
memory climbs with workers while wall time flattens once the 58,000 file
writes go I/O-bound. Hence the cap, and `FH_JOBS` to override it.

Builds under 500 pages stay serial — forking to render 18 pages costs more
than it saves.

## What is still open, in the order the numbers justify

**1. Federation is the only thing that cuts page count.** The closure analysis
is the argument *for* it: you cannot cut this graph inside one origin, but you
can cut it at an origin boundary, because a link to another deployment is not
a dead link. The natural seam is exactly where the fan-out is, and the split is
lopsided enough to be worth stating plainly: school pages, contests and
athletes are **57,965 of 58,497 pages — 99.1%**. Everything the association
itself publishes, front page and scoreboard and championships and sport hubs
and news, is **532 pages**. A state build that consumed contest records from
school repos instead of rendering them would be a build of a few hundred pages
that finishes in seconds.

Deterministic routing already supports this: `reg.url()` and
`school_url()` are the only places a cross-site link would need to learn an
origin. This is the direction worth designing properly, and the measurement
says why.

**2. Hybrid static/dynamic has a hard number attached now.** The tail worth
deferring is athlete pages (25,987, 44% of the site) and out-of-window
contests. Deferring keeps the urls alive, so nothing breaks. The blocker is
that any runtime renderer needs the registry: **9.0 s and 630 MB cold**, per
invocation, because a contest page resolves school slugs, athlete slugs and
tournament context across the whole record set. That is what a SQLite
projection rebuilt from the record stream would be *for* — and it is the
prerequisite, not an alternative. Until it exists, ISR is slower than serving
a file.

**3. The chrome floor is a deploy cost, not a reader cost — and it ranks lower
than it first appears.** 48.2 KB of identical markup on every page is 2.85 GB
of the 3.37 GB tree, which looks like the headline number until you notice it
is *identical* bytes: gzip and brotli collapse it on the wire, so no reader
pays for it. What it actually costs is deploy-side — 58,553 files to upload,
and a write phase proportional to total bytes. Worth doing eventually; not
worth doing before federation, which deletes 99% of those files outright.

An earlier draft of this document ranked it first and justified deferring it
by appeal to the README's "any device without loading a third-party site" line,
as though that were a fixed constraint. It is not — it is a design commitment
this project is free to revisit. The honest reason to rank it third is the
compression argument above, which is a measurement, not a principle.

**4. Multi-region and high-concurrency windows are not a build concern.** A
static tree on a CDN already handles Friday-night load; nothing measured here
bears on it. Revisit if and when the record store stops being git-backed.

## Method note

Every number here came from this box (4 cores, 16 GB, Linux) against the
records as committed. Two measurement traps worth naming, because both would
have produced a confident wrong answer:

- **`ru_maxrss` lies about forked builds.** `RUSAGE_CHILDREN` gives the largest
  single child, not the tree; summing per-process RSS double-counts shared
  copy-on-write pages. Only PSS answers "how much physical memory does this
  build need."
- **The link closure had to be measured on the built tree**, not reasoned about
  from the templates. The intuition — "the tour links about twenty pages, so a
  tour-only build is small" — is wrong by three orders of magnitude, and
  nothing short of walking the real hrefs would have shown it.

## Reproducing

```sh
python3 site/build.py                                   # full tree, 64 s, 4 workers
FH_JOBS=1 python3 site/build.py                         # serial, 205 s / 646 MB
FH_ONLY=front,tour,index python3 site/build.py          # partial, local only, ~9 s
python3 -m pytest -q                                    # 201 passed, 1 skipped
```
