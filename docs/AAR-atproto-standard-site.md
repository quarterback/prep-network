# AAR — the AT Protocol layer: adopting standard.site instead of inventing

**Date:** 2026-08-08
**Status:** Built and verifiable offline; publishing gated on an identity
**Why this document exists:** the protocol work is the part of this project meant
to carry conversations with people who live in the atmosphere, and the decisions
in it are more interesting than the code. Written to be shareable on its own,
like the genesis AAR. The worldbuilding is deliberately not the subject here.

---

## 1. Why a protocol is in a high-school sports site at all

Not data ownership. Every record on this site is public — a box score is a
public act, and "own your data" is an empty pitch for content anyone may copy.

The real argument is **portability against vendor lock-in, including lock-in to
this tool**. The vendor category this project exists to replace holds its
position not because its software is good but because leaving it means losing
your archive. A results platform whose canonical layer is records in a
repository the institution controls cannot hold anyone hostage — including us.
That is a *structural* claim about the product, and AT Protocol is how the claim
is made checkable instead of promised.

The second argument is audience-shaped. Nearly everything built on the protocol
today is a tool for people who already know what a DID is. This is the
opposite: a site regular people would use — parents, athletic directors, a
sports editor at a weekly — who will never know the protocol is present, and
whose experience gets quietly better because of it. For talking to protocol
people, that inversion *is* the pitch: adoption that requires no adoption.

## 2. The load-bearing decision: adopt where a standard exists, invent only where none does

The obvious move was to design `org.prepnet.*` lexicons for everything —
publication, articles, contests, orgs. The better move, and the one taken:

| Layer | Records | Why |
| --- | --- | --- |
| The site and its articles | `site.standard.*` (standard.site) | A live community standard fits exactly. Everything already reading these records can see us. |
| Contests — meets, duals, games | `org.prepnet.temp.*` | Nothing else models a wrestling dual or a judged gymnastics meet. This is the part the project actually proves. |

standard.site exists because three AT Protocol publishing apps — Leaflet,
pckt.blog, Offprint — each invented a schema for "this is a publication, these
are its posts," discovered the schemas were incompatible, and agreed on one.
Bluesky renders enhanced previews for it; WordPress ships a plugin, EmDash
bakes it into their CMS, Sequoia publishes it from static site generators.
Adopting it says something inventing never can: *the newsroom is legible to an
ecosystem today, with zero coordination.*

The boundary between the layers is principled, not lazy. A
`site.standard.document` carries `title`, `publishedAt`, `path`. There is no
field that could hold "Alder Creek 36, Salmonberry Prairie 61," and bending one
in would produce a private dialect wearing a standard's name — the exact
failure standard.site was created to end. Scores don't need a lexicon to reach
the network anyway: **an account posts them.** Records are for structure;
posts are for the feed. Keeping those straight is most of the design.

## 3. What was built

Two record types, written by the site build into `records/atproto/` so they are
reviewable in a pull request like every other record in this repo:

```jsonc
// publication.json — one, rkey "self"
{ "$type": "site.standard.publication",
  "name": "VarsityApex", "url": "https://…", "description": "…",
  "basicTheme": { "$type": "site.standard.theme.basic",
                  "background": …, "foreground": …, "accent": … },
  "preferences": { "showInDiscover": true } }

// documents/<slug>.json — one per article, rkey = the story slug
{ "$type": "site.standard.document",
  "site": "at://<did>/site.standard.publication/self",
  "title": "…", "description": "…",
  "publishedAt": "2027-01-15T00:00:00Z",
  "path": "/news/winter-championship-brackets-set/" }
```

Details that turned out to matter:

- **Record keys are story slugs.** Republishing an edited story updates its
  record in place instead of accreting copies. When a story was renamed
  (`netherwood-…` → `carver-…`), the rkey moved with it and the stale record
  was deleted — rkeys are identity, and identity changes are real deletions.
- **`publishedAt` is midnight UTC** of the story's date. The association posts
  by day, not by minute; a fabricated clock time would have been the only
  invented field in the record.
- **The theme record carries the actual palette** a reader sees, so a consumer
  rendering a preview can tint it like the site.

## 4. Verification, and the placeholder rule

Ownership is claimed twice, and a consumer can check either:

- `/.well-known/site.standard.publication` on the domain returns the
  publication's AT-URI
- every page carries `<link rel="site.standard.publication">`; article pages
  add `<link rel="site.standard.document">` pointing at their own record

The rule that fell out of building this: **until the publication record
actually exists, emit neither.** The build omits the link tags and the
`.well-known` file entirely when `FH_PUB_URI` is unset, rather than emitting a
placeholder. An unresolvable AT-URI in a rel tag is worse than an absent one —
a consumer fetches it and *fails*, instead of correctly concluding the site
doesn't participate yet. Tests pin both directions (no tags when unset; tags
that resolve to the same repo when set). This generalizes: in a protocol where
claims are checkable, a fake claim is strictly worse than no claim.

## 5. Publish is not build

`site/build.py` is a pure function of the records in this repository — it
writes files and touches no network. Folding a PDS write into it would let a
deploy half-succeed: pages published, records not, or the reverse.

`scripts/publish_standardsite.py` does the writes (stdlib only, app password,
`com.atproto.repo.putRecord`), and it exists separately for a second reason:
**the DID is unknowable until login.** Every document's `site` field points at
the publication's AT-URI, which contains the DID — so the records on disk carry
`"site": ""` and the publisher rebuilds them with the real URI injected at the
moment it finally knows it. It prints the resulting `FH_PUB_URI`; set that in
the build environment and the site starts emitting its tags and `.well-known`
file. Same-rkey re-runs are idempotent.

## 6. What the protocol buys the thesis

The project's structural claim is the ladder: state → conference → school, each
tier able to stand alone inside a larger system. In standard.site terms,
**every tier is a publication.** The association is one. A conference is one. A
school is one. That isn't a stretch of the lexicon — it's exactly what the
lexicon is for — and it converts the ladder from a claim about page structure
into something *other software can see*. A parent subscribes to their kid's
school and gets its articles in a Bluesky timeline, with the association having
agreed to nothing. That is the no-buy-in argument, demonstrated rather than
asserted.

And the portability argument becomes concrete: in a real deployment each tier
holds its records in a repo under its own identity, the association aggregates,
and a school that leaves walks away whole. Downstream, an institutional
presence on the network — an official microblog account posting scores — starts
from records the institution already holds, not from an export nobody built.

## 7. Honest limits, and the order of next steps

- **No identity yet.** Everything is verifiable offline (records on disk,
  tests, dry-run publisher); nothing is in a live repo until there's a handle
  on a domain and an app password. That is one decision and ten minutes.
- **`org.prepnet.temp.*` NSIDs are provisional.** The contest lexicons are the
  project's real contribution to the atmosphere and eventually deserve the
  standard.site treatment themselves: published schemas, a `.well-known`
  claim, and ideally a second implementer — the lesson of standard.site is
  that a standard is born the day the *second* app agrees.
- **One publication today.** The per-tier publications (conference, school)
  are wiring, not design — the records plane already knows every org.
- **Scores-as-posts is unbuilt.** The account that posts results is the last
  piece of the "records for structure, posts for the feed" split.

The order: identity → publish the association publication → per-tier
publications → the scores account → formalize the contest lexicons.

## 8. The one-paragraph version, for saying out loud

The association site publishes itself as a standard.site publication and each
article as a document, so anything in the atmosphere already reading those
records — Bluesky link previews included — picks it up without being told about
us. We adopted the community lexicon for the layer where one exists and
invented only where none does (nothing models a wrestling dual), and the
interesting part isn't the code: it's that this is a boring public-records site
normal people use, whose users will never know the protocol is there, and whose
host institution can walk away with its records intact — which is the entire
argument for building on the protocol in the first place.
