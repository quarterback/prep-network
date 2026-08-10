"""
Sport icons — Tabler Icons (MIT), inlined.

Icons compress the fifty-activity nav into something scannable: a glyph with
the sport's name beside it, instead of a wall of text links. Paths are
embedded rather than linked because the site is static and the artifact CSP
blocks external hosts.

Most glyphs are Tabler's. Six at the foot of `ICONS` are drawn for this
catalog, because Tabler has no shuttlecock, squash racquet, cricket bat, rugby
ball, crosse or hockey stick, and the fallbacks they replaced were wrong
enough to misread — field hockey was showing a golf club.

Tabler Icons · MIT License · https://github.com/tabler/tabler-icons
"""

ICONS = {
 "ball-american-football": "<path d=\"M15 9l-6 6\" /> <path d=\"M10 12l2 2\" /> <path d=\"M12 10l2 2\" /> <path d=\"M8 21a5 5 0 0 0 -5 -5\" /> <path d=\"M16 3c-7.18 0 -13 5.82 -13 13a5 5 0 0 0 5 5c7.18 0 13 -5.82 13 -13a5 5 0 0 0 -5 -5\" /> <path d=\"M16 3a5 5 0 0 0 5 5\" />",
 "ball-baseball": "<path d=\"M5.636 18.364a9 9 0 1 0 12.728 -12.728a9 9 0 0 0 -12.728 12.728z\" /> <path d=\"M12.495 3.02a9 9 0 0 1 -9.475 9.475\" /> <path d=\"M20.98 11.505a9 9 0 0 0 -9.475 9.475\" /> <path d=\"M9 9l2 2\" /> <path d=\"M13 13l2 2\" /> <path d=\"M11 7l2 1\" /> <path d=\"M7 11l1 2\" /> <path d=\"M16 11l1 2\" /> <path d=\"M11 16l2 1\" />",
 "ball-basketball": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\" /> <path d=\"M5.65 5.65l12.7 12.7\" /> <path d=\"M5.65 18.35l12.7 -12.7\" /> <path d=\"M12 3a9 9 0 0 0 9 9\" /> <path d=\"M3 12a9 9 0 0 1 9 9\" />",
 "ball-football": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\" /> <path d=\"M12 7l4.76 3.45l-1.76 5.55h-6l-1.76 -5.55z\" /> <path d=\"M12 7v-4m3 13l2.5 3m-.74 -8.55l3.74 -1.45m-11.44 7.05l-2.56 2.95m.74 -8.55l-3.74 -1.45\" />",
 "ball-tennis": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\" /> <path d=\"M6 5.3a9 9 0 0 1 0 13.4\" /> <path d=\"M18 5.3a9 9 0 0 0 0 13.4\" />",
 "ball-volleyball": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\" /> <path d=\"M12 12a8 8 0 0 0 8 4\" /> <path d=\"M7.5 13.5a12 12 0 0 0 8.5 6.5\" /> <path d=\"M12 12a8 8 0 0 0 -7.464 4.928\" /> <path d=\"M12.951 7.353a12 12 0 0 0 -9.88 4.111\" /> <path d=\"M12 12a8 8 0 0 0 -.536 -8.928\" /> <path d=\"M15.549 15.147a12 12 0 0 0 1.38 -10.611\" />",
 "bike": "<path d=\"M5 18m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0\" /> <path d=\"M19 18m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0\" /> <path d=\"M12 19l0 -4l-3 -3l5 -4l2 3l3 0\" /> <path d=\"M17 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" />",
 "bowling": "<path d=\"M7 11v.01\" /> <path d=\"M11 10v.01\" /> <path d=\"M10 14v.01\" /> <path d=\"M11.059 6.07a8 8 0 1 0 .32 15.81\" /> <path d=\"M15.969 9h4\" /> <path d=\"M14.969 5c0 1.5 1 2 1 4c0 2.5 -2 4.5 -2 7c0 2.6 1.9 6 1.9 6h4.1s2 -3.4 2 -6c0 -2.5 -2 -4.5 -2 -7c0 -2 1 -2.5 1 -4a3 3 0 1 0 -6 0\" />",
 "golf": "<path d=\"M12 18v-15l7 4l-7 4\" /> <path d=\"M9 17.67c-.62 .36 -1 .82 -1 1.33c0 1.1 1.8 2 4 2s4 -.9 4 -2c0 -.5 -.38 -.97 -1 -1.33\" />",
 "ice-skating": "<path d=\"M5.905 5h3.418a1 1 0 0 1 .928 .629l1.143 2.856a3 3 0 0 0 2.207 1.83l4.717 .926a2.084 2.084 0 0 1 1.682 2.045v.714a1 1 0 0 1 -1 1h-13.895a1 1 0 0 1 -1 -1.1l.8 -8a1 1 0 0 1 1 -.9z\" /> <path d=\"M3 19h17a1 1 0 0 0 1 -1\" /> <path d=\"M9 15v4\" /> <path d=\"M15 15v4\" />",
 "karate": "<path d=\"M18 4m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" /> <path d=\"M3 9l4.5 1l3 2.5\" /> <path d=\"M13 21v-8l3 -5.5\" /> <path d=\"M8 4.5l4 2l4 1l4 3.5l-2 3.5\" />",
 "mountain": "<path d=\"M3 20h18l-6.921 -14.612a2.3 2.3 0 0 0 -4.158 0l-6.921 14.612z\" /> <path d=\"M7.5 11l2 2.5l2.5 -2.5l2 3l2.5 -2\" />",
 "play-football": "<path d=\"M11 4a1 1 0 1 0 2 0a1 1 0 0 0 -2 0\" /> <path d=\"M3 17l5 1l.75 -1.5\" /> <path d=\"M14 21v-4l-4 -3l1 -6\" /> <path d=\"M6 12v-3l5 -1l3 3l3 1\" /> <path d=\"M19.5 20a.5 .5 0 1 0 0 -1a.5 .5 0 0 0 0 1z\" fill=\"currentColor\" />",
 "run": "<path d=\"M13 4m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" /> <path d=\"M4 17l5 1l.75 -1.5\" /> <path d=\"M15 21l0 -4l-4 -3l1 -6\" /> <path d=\"M7 12l0 -3l5 -1l3 3l3 1\" />",
 "snowflake": "<path d=\"M10 4l2 1l2 -1\" /> <path d=\"M12 2v6.5l3 1.72\" /> <path d=\"M17.928 6.268l.134 2.232l1.866 1.232\" /> <path d=\"M20.66 7l-5.629 3.25l.01 3.458\" /> <path d=\"M19.928 14.268l-1.866 1.232l-.134 2.232\" /> <path d=\"M20.66 17l-5.629 -3.25l-2.99 1.738\" /> <path d=\"M14 20l-2 -1l-2 1\" /> <path d=\"M12 22v-6.5l-3 -1.72\" /> <path d=\"M6.072 17.732l-.134 -2.232l-1.866 -1.232\" /> <path d=\"M3.34 17l5.629 -3.25l-.01 -3.458\" /> <path d=\"M4.072 9.732l1.866 -1.232l.134 -2.232\" /> <path d=\"M3.34 7l5.629 3.25l2.99 -1.738\" />",
 "stretching": "<path d=\"M16 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" /> <path d=\"M5 20l5 -.5l1 -2\" /> <path d=\"M18 20v-5h-5.5l2.5 -6.5l-5.5 1l1.5 2\" />",
 "swimming": "<path d=\"M16 9m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" /> <path d=\"M6 11l4 -2l3.5 3l-1.5 2\" /> <path d=\"M3 16.75a2.4 2.4 0 0 0 1 .25a2.4 2.4 0 0 0 2 -1a2.4 2.4 0 0 1 2 -1a2.4 2.4 0 0 1 2 1a2.4 2.4 0 0 0 2 1a2.4 2.4 0 0 0 2 -1a2.4 2.4 0 0 1 2 -1a2.4 2.4 0 0 1 2 1a2.4 2.4 0 0 0 2 1a2.4 2.4 0 0 0 1 -.25\" />",
 "sword": "<path d=\"M20 4v5l-9 7l-4 4l-3 -3l4 -4l7 -9z\" /> <path d=\"M6.5 11.5l6 6\" />",
 "target-arrow": "<path d=\"M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" /> <path d=\"M12 7a5 5 0 1 0 5 5\" /> <path d=\"M13 3.055a9 9 0 1 0 7.941 7.945\" /> <path d=\"M15 6v3h3l3 -3h-3v-3z\" /> <path d=\"M15 9l-3 3\" />",
 "music": "<path d=\"M3 17a3 3 0 1 0 6 0a3 3 0 0 0 -6 0\" /> <path d=\"M13 17a3 3 0 1 0 6 0a3 3 0 0 0 -6 0\" /> <path d=\"M9 17v-13h10v13\" /> <path d=\"M9 8h10\" />",
 "microphone": "<path d=\"M15 12.9a5 5 0 1 0 -3.902 -3.9\" /> <path d=\"M15 12.9l-3.902 -3.899l-7.513 8.584a2 2 0 1 0 2.827 2.83l8.588 -7.515z\" />",
 "messages": "<path d=\"M21 14l-3 -3h-7a1 1 0 0 1 -1 -1v-6a1 1 0 0 1 1 -1h9a1 1 0 0 1 1 1v10\" /> <path d=\"M14 15v2a1 1 0 0 1 -1 1h-7l-3 3v-10a1 1 0 0 1 1 -1h2\" />",
 "disc": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\" /> <path d=\"M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" /> <path d=\"M7 12a5 5 0 0 1 5 -5\" /> <path d=\"M12 17a5 5 0 0 0 5 -5\" />",
 "chess": "<path d=\"M8 16l1.5 -8h5l1.5 8\" /> <path d=\"M6 20h12v-2a1 1 0 0 0 -1 -1h-10a1 1 0 0 0 -1 1v2z\" /> <path d=\"M12 4v2\" /> <path d=\"M11 5h2\" /> <path d=\"M9.5 8h5\" />",
 "yoga": "<path d=\"M12 4m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\" /> <path d=\"M4 20h4l1.5 -3\" /> <path d=\"M17 20l-1 -5h-5l1 -7\" /> <path d=\"M4 10l4 -1l4 -1l4 1.5l4 1.5\" />",

 # ---- drawn for this catalog, in Tabler's grammar (24x24, 2px round stroke).
 # Tabler has no glyph for any of these six, and the fallbacks they replace
 # were wrong enough to misread: field hockey was showing a GOLF CLUB, and
 # lacrosse a target-and-arrow. Squash, badminton, cricket and rugby were each
 # borrowing the nearest ball, which put three different racquet sports and
 # two different bat-and-ball sports on one icon apiece.
 "shuttlecock": "<path d=\"M12 18.6m-2.9 0a2.9 2.9 0 1 0 5.8 0a2.9 2.9 0 1 0 -5.8 0\" /> <path d=\"M9.7 16.8l-3.7 -8.8\" /> <path d=\"M14.3 16.8l3.7 -8.8\" /> <path d=\"M6 8a9 9 0 0 1 12 0\" /> <path d=\"M12 15.7v-9.5\" />",
 "racquet": "<path d=\"M10 14a6.4 4.9 -45 1 1 9 -9a6.4 4.9 -45 1 1 -9 9z\" /> <path d=\"M10.7 13.3l7.6 -7.6\" /> <path d=\"M11.7 7.2l5.6 5.6\" /> <path d=\"M9.6 14.4l-4.2 4.2\" /> <path d=\"M4 17.4l2.6 2.6\" />",
 "cricket": "<path d=\"M19.8 4.2l1.6 1.6\" /> <path d=\"M18.6 5.4l-2.9 2.9\" /> <path d=\"M15.7 8.3l-7.4 7.4a2.4 2.4 0 0 0 0 3.4a2.4 2.4 0 0 0 3.4 0l7.4 -7.4z\" /> <path d=\"M5 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0\" />",
 "ball-rugby": "<path d=\"M4.6 19.4c-2.4 -2.4 -1.4 -8.4 2.2 -12s9.6 -4.6 12 -2.2s1.4 8.4 -2.2 12s-9.6 4.6 -12 2.2z\" /> <path d=\"M8.5 15.5l7 -7\" /> <path d=\"M10.6 14.1l1.7 1.7\" /> <path d=\"M13.1 11.6l1.7 1.7\" /> <path d=\"M15.6 9.1l1.7 1.7\" />",
 "lacrosse": "<path d=\"M12.8 11.2l3.2 -6.6a5 5 0 0 1 4.6 4.6l-6.6 3.2z\" /> <path d=\"M14.9 7.3l3.4 3.4\" /> <path d=\"M12.6 11.6l-6.8 6.8\" /> <path d=\"M4.4 17l2.6 2.6\" />",
 "hockey-stick": "<path d=\"M6.5 3.5l3.5 11.2a4.5 4.5 0 0 0 4.3 3.1h4.2\" /> <path d=\"M18.5 17.8a2 2 0 0 1 0 4h-4.4\" /> <path d=\"M6 20m-1.8 0a1.8 1.8 0 1 0 3.6 0a1.8 1.8 0 1 0 -3.6 0\" />",
}

SPORT_ICON = {
 "football": "ball-american-football",
 "girls-flag-football": "play-football",
 "boys-soccer": "ball-football",
 "girls-soccer": "ball-football",
 "field-hockey": "hockey-stick",
 "girls-volleyball": "ball-volleyball",
 "boys-cross-country": "run",
 "girls-cross-country": "run",
 "girls-tennis": "ball-tennis",
 "boys-golf": "golf",
 "mountain-biking": "bike",
 "boys-water-polo": "swimming",
 "girls-water-polo": "swimming",
 "boys-basketball": "ball-basketball",
 "girls-basketball": "ball-basketball",
 "boys-wrestling": "karate",
 "girls-wrestling": "karate",
 "boys-swimming": "swimming",
 "girls-swimming": "swimming",
 "boys-ice-hockey": "ice-skating",
 "girls-ice-hockey": "ice-skating",
 "boys-alpine-skiing": "mountain",
 "girls-alpine-skiing": "mountain",
 "boys-nordic-skiing": "snowflake",
 "girls-nordic-skiing": "snowflake",
 "bowling": "bowling",
 "boys-fencing": "sword",
 "girls-fencing": "sword",
 "gymnastics": "yoga",
 "competitive-spirit": "stretching",
 "winter-track": "run",
 "baseball": "ball-baseball",
 "softball": "ball-baseball",
 "boys-lacrosse": "lacrosse",
 "girls-lacrosse": "lacrosse",
 "boys-tennis": "ball-tennis",
 "boys-volleyball": "ball-volleyball",
 "girls-golf": "golf",
 "boys-track": "run",
 "girls-track": "run",
 "badminton": "shuttlecock",
 "squash": "racquet",
 "cricket": "cricket",
 "boys-rugby": "ball-rugby",
 "girls-rugby": "ball-rugby",
 "ultimate": "disc",
 "marching-band": "music",
 "choir": "microphone",
 "debate": "messages",
 "chess": "chess"
}


#: The Bluesky butterfly (official brand mark) — a FILLED logo where every
#: other glyph is a Tabler stroke, so it ships as its own symbol with its own
#: viewBox and is referenced with `.fh-bf` (fill) rather than `.fh-ic` (stroke).
BSKY_PATH = (
    "M135.72 44.03C202.216 93.951 273.74 195.17 300 249.49c26.262-54.316 "
    "97.782-155.54 164.28-205.46C512.26 8.009 590-19.862 590 68.825c0 17.712"
    "-10.155 148.79-16.111 170.07-20.703 73.984-96.144 92.854-163.25 81.433 "
    "117.3 19.964 147.14 86.092 82.697 152.22-122.39 125.59-175.91-31.511-189.63"
    "-71.766-2.514-7.38-3.69-10.832-3.708-7.896-.017-2.936-1.193.516-3.707 "
    "7.896-13.714 40.255-67.233 197.36-189.63 71.766-64.444-66.128-34.605"
    "-132.26 82.697-152.22-67.108 11.421-142.55-7.449-163.25-81.433C20.155 "
    "217.613 10 86.535 10 68.825c0-88.687 77.742-60.816 125.72-24.795z"
)


def sprite() -> str:
    """Every glyph as a <symbol>, emitted once per page.

    Inlining the paths at each call site cost ~450 bytes a glyph, and the nav
    carries the sports list twice (desktop dropdown + mobile drawer) — 82 icons,
    ~37KB, on all 10,900 pages. Defined once and referenced, the same nav costs
    the sprite (~9KB) plus ~55 bytes a reference. Stroke presentation moved to
    CSS (`.fh-ic`) so a reference is just the class and the <use>.
    """
    syms = "".join(f'<symbol id="i-{name}" viewBox="0 0 24 24">{paths}</symbol>'
                   for name, paths in ICONS.items())
    syms += (f'<symbol id="i-bsky" viewBox="0 0 600 530">'
             f'<path d="{BSKY_PATH}"/></symbol>')
    return f'<svg class="fh-sprite" aria-hidden="true"><defs>{syms}</defs></svg>'


def bsky(cls: str = "fh-bf") -> str:
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-bsky"/></svg>'


def icon(sport_key: str, cls: str = "fh-ic") -> str:
    name = SPORT_ICON.get(sport_key, "run")
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{name}"/></svg>'
