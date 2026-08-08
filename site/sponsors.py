"""
Association sponsors — the footer rail every state site carries.

Set as type, not sourced as art. A generated or borrowed logo lands in the one
failure mode that matters here: a mark that half-resembles a real company's.
Wordmarks in the site's own faces avoid that entirely, stay vector-crisp at any
size, and follow the palette into dark mode without a second asset.

Which categories appear is the realistic part. State associations are funded by
sports medicine groups, credit unions, mutual insurers, dairy boards, rural
electric co-ops, orthodontists and regional grocers — the local-institution
economy, not national brands. Names are invented from Jefferson's own
geography (`names.STEMS` supplies the same stems the towns draw from) so the
rail reads as one state's business community.

`style` picks the typeface — eight sponsors, eight faces, all drawn from the
owner's own library across the other repos. None uses PP Valve: the display
italic is the site's identity, and a sponsor wearing it directly above the
footer wordmark reads as a house brand.

    slant       Object Sans Heavy Slanted — sports-medicine energy
    poster      Formula Extended Bold caps — the mutual insurer
    mono        Azeret Mono caps, tracked — the rural utility
    soft        Fuji Bold behind a circle — the credit union
    serif       Author Bold Italic on a rule — the dairy
    collegiate  Author Semibold behind a diamond — the college
    neutral     Switzer Semibold — the clinic
    tall        Pangram Compressed Extrabold caps — the outfitter
"""

SPONSORS = [
    dict(name="Cascade Divide Orthopedics", style="slant"),
    dict(name="Timber Valley Credit Union", style="soft"),
    dict(name="Growers Mutual", style="poster"),
    dict(name="Cloverbank Dairy", style="serif"),
    dict(name="Harborline Electric Co-op", style="mono"),
    dict(name="Sagebrush Orthodontics", style="neutral"),
    dict(name="Granite Basin College", style="collegiate"),
    dict(name="Meridian Outfitters", style="tall"),
]
