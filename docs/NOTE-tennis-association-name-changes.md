# NOTE — the tennis association has renamed schools, and this repo has not

**Status: nothing to do here yet. Do NOT start renaming records off this note.**
It exists so that somebody reading `records/orgs/schools.json` and finding a name
that does not match what Jefferson's tennis coverage calls the same school knows
why, and knows where the authoritative list lives.

## What happened

`quarterback/tennis-team-manager` builds the JHSAA — Jefferson's high-school
tennis association — from this repo's institution records
(`scripts/import_jhsaa.py`). It imports INSTITUTIONS only; no player, result or
contest ever crosses over. Over 2027-08 and 2026-08 the owner renamed **69**
schools there, and handed **9** magnet schools' tennis seats to their city
flagships.

Those renames are applied at EMIT in the tennis repo. This repo keeps the
published record under the ORIGINAL names, so the two disagree ON PURPOSE.

## Where the authoritative list is

- `tennis-team-manager/scripts/import_jhsaa.py` — `RENAMES` and `SUBSTITUTIONS`
  are the source of truth. Nothing is transcribed by hand anywhere.
- `tennis-team-manager/docs/JHSAA-name-cleanup-2027.md` — the same tables written
  out as a change list, with the reasoning. Section A is the 2027-08 pass (62
  renames), section B the 9 substitutions, section D the 2026-08 pass (7 more).

## When it is time to sync

The owner has approved bringing this repo in line, but explicitly deferred it —
**do it when asked, never on your own initiative.** It is automated:

    python3 scripts/rename_prep_network.py --dry-run    # report, change nothing
    python3 scripts/rename_prep_network.py              # apply

(That script lives in the tennis repo and rewrites THIS one.) Scope, measured on
a throwaway copy: ~59,000 occurrences across ~6,300 files, plus ~5,700 contest
FILENAME slugs — which changes public URLs. That is why it is a separate,
explicit step and not part of the import.

Two things it deliberately does not touch:

- **The 9 substituted magnets are not renamed.** They keep their identity here
  and merely stop sponsoring tennis over there — exactly as a magnet school
  would not field a team in life.
- **Sponsorship is not a rename.** Which schools play tennis is a decision the
  tennis repo makes about its own association (`EXTRA_SPONSORS` /
  `NEVER_SPONSOR`). A school joining or leaving it changes nothing in these
  records.
