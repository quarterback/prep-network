# Blog draft — standard.site section

This is the section that was missing from the draft post about VarsityApex,
Oregontennis, and the ATProto piece. The earlier pass at this article was
written without the repo in front of it, so "standard.site" landed as a bare
link with no explanation of what it is or why it's the load-bearing decision
in the protocol layer. This fixes that, pulled from what's actually built
(`docs/AAR-atproto-standard-site.md`, `docs/PLAN-standard-site.md`,
`records/atproto/`, `scripts/publish_standardsite.py`).

Two edits below: a rewrite of the existing standard.site mention (drop-in
replacement for the paragraph in "Why is it like this?"), and a new section to
insert before "### What I'd already built."

---

## 1. Replace the existing paragraph

Original:

> Rather than just solve the problem of what a demo would look like for a new
> state high school activities association website, or athletic conference
> site or high school sports site, I wondered what an integrated model would
> look like. Using [standard.site](https://standard.site) and conventional
> integration, trying to design a model where if only a school was using
> \[this platform I'm building] that it would work fine for them, but as more
> schools in their state/district/region started adding themselves, that it
> would be able to be connected int some kind of network without needing to
> be inside the same CMS or even using the same tools.

Replacement:

> Rather than just solve the problem of what a demo would look like for a new
> state high school activities association website, or athletic conference
> site or high school sports site, I wondered what an integrated model would
> look like. I wanted a school running this to work fine on its own, but as
> more schools in a state or district started adding themselves, for it to
> connect into a real network — without needing to share a CMS, a vendor, or
> even a codebase with each other.
>
> The piece that makes that not just a hope is [standard.site](https://standard.site),
> and it's worth explaining what that actually is, because I didn't invent it
> and that's the point.

## 2. New section — insert before "### What I'd already built"

### standard.site, and the part I didn't invent

standard.site exists because three different AT Protocol publishing apps —
Leaflet, pckt.blog and Offprint — each independently built a schema for "this
is a publication, these are its posts," discovered their schemas didn't talk
to each other, and did the boring, correct thing: they agreed on one shared
one instead of each defending their own. That agreement is standard.site.
Bluesky already renders enhanced preview cards for it. WordPress ships a
plugin for it. EmDash bakes it into their CMS. Sequoia publishes it straight
out of a static site generator. None of those tools know VarsityApex exists,
and none of them need to.

That's a different claim than building my own schema and asking people to
trust it. Adopting an existing standard means the newsroom is legible to
everything already reading those records, today, with zero coordination —
not "legible once someone builds an integration."

So there's a split, and it's a split I'd recommend to anyone doing something
similar:

| Layer | Records | Why |
| --- | --- | --- |
| The site and its articles | `site.standard.*` | A live community standard already fits this exactly. Portable, discoverable, subscribable, for free. |
| The actual results — meets, duals, games | project-specific records | Nothing else models a wrestling dual or a judged gymnastics meet. This is the part actually worth building. |

I was tempted to design my own lexicon for everything, publication included.
That would've been a mistake. A `site.standard.document` record has a title,
a publish date and a path — there's no field in it for *Alder Creek 36,
Salmonberry Prairie 61*, and that's correct. Bending a publication schema
into holding a score would produce a private dialect wearing a standard's
name, which is the exact problem standard.site was invented to end. Scores
don't need a lexicon to reach the network anyway — an account just posts
them.

The part I like best is what this does to the "ladder" the whole project is
built around: state association, conference, school. In standard.site terms,
every tier just *is* a publication. The state association is one. A
conference is one. A school is one. That's not a stretch of the schema, it's
exactly what it's for — and it turns "schools can stand alone or connect into
something bigger" from a claim about page layout into something other
software can actually see. A parent could subscribe to just their kid's
school and get its articles in a Bluesky timeline, with the state association
having agreed to precisely nothing.

None of this is exposed to the people it's for. A publication record claims
itself twice — once at `/.well-known/site.standard.publication`, once as a
`<link>` tag on every page — so anything reading the site can verify it
without asking. And there's a rule I ended up leaning on more than expected:
until that record actually exists for a given site, the build emits neither
tag. No placeholder AT-URI, nothing that resolves to a lie. A consumer that
fetches a fake link fails; a consumer that finds no link correctly concludes
the site doesn't participate yet, which is just true and better to say
plainly. Publishing the record itself is also kept separate from building the
site — the build is a pure function of what's in the repo and touches no
network; a small standalone script does the actual write once there's a real
handle and app password behind it. That way a deploy can't half-succeed with
pages live and records missing, or the reverse.

Which gets back to the vendor-lock-in argument from earlier, made concrete
instead of asserted: in a real deployment, each tier holds its own records
under its own identity, the state association aggregates upward, and a school
that decides to leave walks away whole — every hand-typed green-notebook
result still attached to a record it controls, not an export nobody built.
The site itself stays a boring, normal thing a parent or an athletic director
uses without ever learning what a DID is. That inversion — adoption that
requires no adoption from the people the site is actually for — is the whole
pitch, and it's a better one than anything I could've made up myself.
