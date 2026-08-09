# Blog draft — standard.site mention

Drop-in replacement for the existing standard.site line in the article. No
backstory, no explainer — the readers already know what standard.site and
ATProto are. Just where and how this site uses it, pulled from what's built
(`records/atproto/`, `scripts/publish_standardsite.py`).

---

This site publishes itself on standard.site: each tier — state association,
conference, school — is its own `site.standard.publication`, and every
article is a `site.standard.document`. Both are verifiable, at
`/.well-known/site.standard.publication` and via `<link>` tags on every page.
