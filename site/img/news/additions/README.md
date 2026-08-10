# Photo drop folder

Anything here overrides the stock library, with no code change. Name the file
after what it should replace:

| Name it | And it becomes |
| --- | --- |
| a **sport key** — `cricket.jpg`, `boys-rugby.jpg`, `chess.jpg` | that sport's photo everywhere: sport hub, share card, story fallback |
| a **photo family** — `track.jpg`, `aquatic.jpg`, `gym-generic.jpg` | every sport the stock library maps to that family |
| a **news slug** — `tennis-semifinals-preview.jpg` | that story's lead image (slugs are in `site/news.py`) |

`.jpg`, `.jpeg`, `.png` and `.webp` all work. Landscape, 1200px wide or more:
these are used as share-card images too, and the card is 1.91:1.

## Credits

Every photo prints its credit — the licences require it and a newsroom would
anyway. Add them to `credits.json` beside the files, keyed on the same name:

```json
{
  "cricket":   {"credit": "Photographer Name", "license": "Unsplash"},
  "boys-rugby":{"credit": "Photographer Name", "license": "CC BY 2.0"}
}
```

A file with no entry renders without a credit line rather than failing.

## Sport keys with no picture of their own

These currently borrow from a family, so a photo named for them is the
biggest single improvement available: `cricket`, `boys-rugby`, `girls-rugby`,
`badminton`, `boys-squash`, `girls-squash`, `chess`, `ultimate`,
`girls-flag-football`, `competitive-spirit`, `mountain-biking`.
