# standard.site — the site and its articles on AT Protocol

## Why this and not our own lexicons

Three AT Protocol publishing apps — Leaflet, pckt.blog and Offprint — each
invented a schema for "this is a publication, these are its posts," discovered
the schemas were incompatible, and agreed on one instead. That's
[standard.site](https://standard.site). Bluesky renders enhanced previews for
it; WordPress ships a plugin, EmDash bakes it into their CMS, Sequoia publishes
it from static site generators.

Adopting an existing standard is a different claim than inventing one. It says
the newsroom is legible to everything already reading those records, today,
without anyone at an association knowing the protocol exists.

## Scope: the publication layer only

`site.standard.document` has `title`, `publishedAt` and `path`. There is no
field in it that could hold *Alder Creek 36, Salmonberry Prairie 61* — and
that's correct, it isn't a results schema and shouldn't be bent into one.

So the split is:

| Layer | Records | Why |
| --- | --- | --- |
| Publication — the site, its articles | `site.standard.*` | An existing standard fits exactly. Portable, discoverable, subscribable. |
| Contests — meets, duals, games | `org.prepnet.*` | Nothing else models them. This is the part the project is actually proving. |

Scores don't need a lexicon to reach the network. An account posts them.

## The two records

```jsonc
// records/atproto/publication.json — one, rkey "self"
{ "$type": "site.standard.publication",
  "name": "Fieldhouse",
  "url": "https://…",
  "description": "…",
  "basicTheme": { "$type": "site.standard.theme.basic",
                  "background": {…}, "foreground": {…},
                  "accent": {…}, "accentForeground": {…} },
  "preferences": { "showInDiscover": true } }

// records/atproto/documents/<slug>.json — one per story, rkey = slug
{ "$type": "site.standard.document",
  "site": "at://<did>/site.standard.publication/self",
  "title": "…", "description": "…",
  "publishedAt": "2027-01-15T00:00:00Z",
  "path": "/news/winter-championship-brackets-set/" }
```

Record keys are story slugs, so republishing an edited story updates its
document rather than adding a second copy.

## Verification

Claimed twice, so a consumer can check either:

- `/.well-known/site.standard.publication` returns the publication's AT-URI
- every page carries `<link rel="site.standard.publication">`; article pages
  add `<link rel="site.standard.document">`

## Publish is not build

`site/build.py` is a pure function of the records in this repo — it writes
files and touches no network. Folding a PDS write into it would let a deploy
half-succeed: pages published, records not, or the reverse.

`scripts/publish_standardsite.py` does the writes, and needs an identity this
project doesn't have yet:

```
FH_HANDLE=… FH_APP_PASSWORD=… python3 scripts/publish_standardsite.py
```

It prints the resulting `FH_PUB_URI`. Set that in the build environment and the
site starts emitting its `<link>` tags and `.well-known` file.

**Until then the build omits both rather than emitting a placeholder.** An
unresolvable AT-URI in a rel tag is worse than an absent one — a consumer
fetches it and fails, instead of correctly concluding the site doesn't
participate yet. A test pins this in both directions.

The DID isn't knowable until login, which is why documents carry `"site": ""`
in the repo and the publisher rebuilds them fresh with the real URI injected.

## What it buys downstream

The site is a normal public-facing thing that regular people use without ever
learning what a DID is. The portability sits underneath: an institution that
later wants an official microblog account already has its publication and its
articles as records in a repo it controls, and can walk away from this tool
with them intact. That's the vendor-lock-in argument made concrete rather than
asserted — which is the whole reason the protocol is in this project at all.
