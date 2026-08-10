# Build scaling — where the cost actually is

## Why this exists

The brief asked how to cut the cost of rebuilding a 58,000-page site: federate
it into per-school repos, defer the tail to edge rendering, prune sparse
routes, or distribute the deploy. Four plausible directions, none of them
measured.

So they were measured first. Three of the four turn out to be aimed at the
wrong thing, and the one number nobody had is the one that matters.

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

## What changed

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

## What is still open, in the order the numbers justify

**1. The chrome floor (2.85 GB of the 3.37 GB tree).** The score rail is
identical on all 58,497 pages and changes on every rebuild. Deduplicating it —
client-side include, or an edge transform — cuts the deployed tree by roughly
an order of magnitude and shrinks every future rebuild's write phase. The cost
is that the rail stops working without JS, which is a product decision, not a
technical one, and it runs against the stated bar of "see results on any device
without loading a third-party site."

**2. Federation is the only thing that cuts page count.** The closure analysis
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

**3. Hybrid static/dynamic has a hard number attached now.** The tail worth
deferring is athlete pages (25,987, 44% of the site) and out-of-window
contests. Deferring keeps the urls alive, so nothing breaks. The blocker is
that any runtime renderer needs the registry: **9.0 s and 630 MB cold**, per
invocation, because a contest page resolves school slugs, athlete slugs and
tournament context across the whole record set. That is what a SQLite
projection rebuilt from the record stream would be *for* — and it is the
prerequisite, not an alternative. Until it exists, ISR is slower than serving
a file.

**4. Multi-region and high-concurrency windows are not a build concern.** A
static tree on a CDN already handles Friday-night load; nothing measured here
bears on it. Revisit if and when the record store stops being git-backed.

## Reproducing

```sh
python3 site/build.py                                   # full tree, 214 s / 646 MB
FH_ONLY=front,tour,index python3 site/build.py          # partial, local only, ~9 s
python3 -m pytest -q                                    # 201 passed, 1 skipped
```
