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

`style` picks the type treatment. Six of them, so eight logos don't look like
eight settings of the same font. None uses PP Valve — the display italic is the
site's own identity, and a sponsor wearing it directly above the footer
wordmark reads as a house brand:

    anchor  Montreal 800 mixed case, largest — the lead sponsor
    heavy   Montreal 800 uppercase, tight
    wide    Montreal 500 uppercase, wide tracking
    mark    Montreal 600 mixed case behind a geometric glyph
    rule    Montreal 800 mixed case over a hairline
    light   Montreal 400 mixed case, quiet
"""

SPONSORS = [
    dict(name="Cascade Divide Orthopedics", style="anchor"),
    dict(name="Timber Valley Credit Union", style="mark"),
    dict(name="Growers Mutual", style="heavy"),
    dict(name="Cloverbank Dairy", style="rule"),
    dict(name="Harborline Electric Co-op", style="wide"),
    dict(name="Sagebrush Orthodontics", style="light"),
    dict(name="Granite Basin College", style="mark"),
    dict(name="Meridian Outfitters", style="heavy"),
]
