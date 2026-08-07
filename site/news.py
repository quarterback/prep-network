"""
Seeded association newsroom for the Jefferson demo.

An association front page is a publication as much as a database — MHSAA leads
with stories and audience sections; NJSIAA leads with notices, brackets and
health/eligibility material. These are the fictional equivalents: previews,
rule changes, officiating notices, participation announcements, student
features. Written once, in the association's voice, never generated.
"""

STORIES = [
    dict(slug="winter-championship-brackets-set", kicker="Championships",
         date="2027-01-15",
         head="Winter championship brackets released for basketball and wrestling",
         dek="Seeding meetings concluded Thursday. First-round sites are assigned to "
             "the higher seed through the quarterfinals in all six classifications.",
         body=["Basketball brackets in all six classifications are posted, along with "
               "the wrestling dual-team brackets for 6A through 2A-1A.",
               "Sites for the opening two rounds go to the higher remaining seed. "
               "Semifinals and finals will be played at neutral sites announced with "
               "the regional pairings.",
               "Coaches should confirm rosters through their athletic director before "
               "the entry deadline. Corrections after the deadline require a written "
               "request from the school's principal."]),
    dict(slug="alpine-nordic-schedule-change", kicker="Notice",
         date="2027-01-14",
         head="Alpine and nordic events moved after Cascade Divide storm",
         dek="Three invitationals scheduled for last weekend have been rescheduled. "
             "Qualifying standards are unchanged.",
         body=["Persistent snowfall across the Cascade Divide forced postponement of "
               "three alpine and two nordic invitationals.",
               "Rescheduled dates appear on each event page. Because qualifying is "
               "based on standard rather than event count, no skier's championship "
               "eligibility is affected by the cancellations."]),
    dict(slug="officiating-shortage-winter", kicker="Officials",
         date="2027-01-13",
         head="Association opens midseason officials registration for winter sports",
         dek="Basketball and wrestling assignments remain unfilled in several "
             "conferences, particularly in the high desert and North Range.",
         body=["Registration is open through the end of the month for officials in "
               "basketball, wrestling, swimming and ice hockey.",
               "New officials complete a rules clinic and a background check before "
               "receiving assignments. Mentorship pairings are available in every "
               "conference.",
               "Schools experiencing coverage gaps should contact their conference "
               "assigner directly rather than rescheduling contests."]),
    dict(slug="participation-record-girls-wrestling", kicker="Participation",
         date="2027-01-12",
         head="Girls wrestling adds programs for a fourth consecutive year",
         dek="Eleven more schools are sponsoring the sport this winter, with the "
             "largest growth outside the Ashbury metro.",
         body=["Girls wrestling has grown in every classification since sanctioning, "
               "with this year's additions concentrated in Timber Valley and the "
               "Juniper Highlands.",
               "Several small schools are competing under cooperative agreements. "
               "Co-op athletes compete for the host school in championship events."]),
    dict(slug="transfer-rule-clarification", kicker="Eligibility",
         date="2027-01-09",
         head="Board clarifies transfer sit-out period for midyear enrollment",
         dek="The clarification affects students changing schools after the first "
             "semester without a corresponding change of residence.",
         body=["A student who transfers without a bona fide change of residence is "
               "ineligible for varsity competition for the remainder of the season "
               "in any sport played at the previous school that year.",
               "Hardship waivers continue to be reviewed case by case. Athletic "
               "directors should file requests before the student competes, not after."]),
    dict(slug="netherwood-swimmer-feature", kicker="Student-athlete",
         date="2027-01-08",
         head="A Plainfield swimmer's long drive to the nearest pool",
         dek="Netherwood has no pool of its own. Practice means a bus ride, four "
             "mornings a week, before first period.",
         body=["Netherwood's swimmers train at a community pool two towns over, "
               "leaving before dawn and returning in time for class.",
               "The arrangement is common outside the metros, where aquatic programs "
               "depend on shared municipal facilities.",
               "East Plainfield and West Plainfield share the same water, and the "
               "three programs practice on a rotating schedule."]),
]

RESOURCES = [
    ("Schools & athletic directors", [
        ("Member school directory", "/schools/"),
        ("Conference assignments", "/conferences/"),
        ("Classification cycle", None),
        ("Cooperative program agreements", None),
        ("Report a result", "/report/dual.html"),
    ]),
    ("Coaches", [
        ("Rules meetings and clinics", None),
        ("Practice and contest limitations", None),
        ("Sport-by-sport manuals", None),
        ("Out-of-season contact rules", None),
    ]),
    ("Officials", [
        ("Register as an official", None),
        ("Conference assigners", None),
        ("Rules interpretations", None),
        ("Evaluation and ratings", None),
    ]),
    ("Students & families", [
        ("Eligibility standards", None),
        ("Transfer and residency", None),
        ("Championship ticketing", None),
        ("Sportsmanship expectations", None),
    ]),
]
