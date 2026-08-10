# Photo drop folder

Anything here overrides the stock library, with no code change. Name the file
after what it should replace:

| Name it | And it becomes |
| --- | --- |
| a **sport key** — `cricket.jpg`, `boys-rugby.jpg`, `chess.jpg` | that sport's photo everywhere: sport hub, share card, story fallback |
| a **photo family** — `track.jpg`, `aquatic.jpg`, `gym-generic.jpg` | every sport the stock library maps to that family |
| a **news slug** — `tennis-semifinals-preview.jpg` | that story's lead image (slugs are in `site/news.py`) |

`.jpg`, `.jpeg`, `.png` and `.webp` all work. Landscape, 1200px wide or more.
These are used as share-card images too, and the card is 1.91:1, so a portrait
frame gets cropped hard by whoever renders the card.

**Resize before committing.** Long edge 1600, quality 82 — about 250 KB a
photo. Straight-off-the-camera files run 2–4 MB each, and the build copies the
whole folder into `dist/`.

```sh
python3 -c "
from PIL import Image, ImageOps; import sys, pathlib
for p in sys.argv[1:]:
    im = ImageOps.exif_transpose(Image.open(p)).convert('RGB')
    im.thumbnail((1600, 1600), Image.LANCZOS)
    im.save(p, 'JPEG', quality=82, optimize=True, progressive=True)
" *.jpg
```

## Variants

A name can carry more than one photograph — `baseball.jpg`, `baseball-2.jpg`,
`baseball-3.jpg`. All three are baseball; which one a page gets is a stable
hash of that page's school or conference, so the 840 school fronts leading on
baseball do not all lead on the same frame. Numbering must be unbroken: the
search stops at the first gap.

## Credits

Every photo prints its credit — the licences require it and a newsroom would
anyway. Add them to `credits.json` beside the files, keyed on the file's name
**including the variant number**:

```json
{
  "cricket":    {"credit": "Photographer Name", "license": "Unsplash"},
  "cricket-2":  {"credit": "Someone Else",      "license": "Unsplash"},
  "boys-rugby": {"credit": "Photographer Name", "license": "CC BY 2.0"}
}
```

A variant with no entry of its own falls back to the base name's credit, and a
file with no entry at all renders without a credit line rather than failing.

## Sport keys still on a borrowed picture

Sixteen sports now lead on a photograph from this folder. Thirty-five are still
on the stock library, and a file named for any of them is the biggest single
improvement available. The ones where the borrowed picture is furthest off:

| Key | Currently showing |
| --- | --- |
| `chess` | a general-purpose gym interior, shared with `debate` |
| `boys-squash`, `girls-squash` | an aerial of tennis courts |
| `girls-flag-football` | tackle football |
| `competitive-spirit` | gymnastics |
| `mountain-biking` | a cross-country trail |
| `boys-lacrosse`, `field-hockey` | one generic field-sports frame |
| `winter-track` | outdoor track |
| `choir` | a marching band |

The rest — basketball, soccer, wrestling, swimming, hockey, skiing, volleyball,
bowling, fencing, gymnastics, track, cross country, water polo — are on stock
photographs of the right sport, so they read correctly; they are just not as
good as these.
