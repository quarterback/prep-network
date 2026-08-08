"""
Seeded association newsroom for the Jefferson demo.

An association front page is a publication as much as a database — MHSAA leads
with stories and audience sections; NJSIAA leads with notices, brackets and
health/eligibility material. These are the fictional equivalents: previews,
rule changes, officiating notices, participation announcements, student
features. Written once, in the association's voice, never generated.
"""

STORIES = [
    dict(slug="port-meridian-first-fencing-title", kind="activity", kicker="Fencing",
         date="2027-01-16",
         head="Port Meridian wins first fencing team title",
         dek="The Mariners took three of six weapons finals at the Open championships "
             "in Ashbury, unseating four-time champion St. Sebastian Prep.",
         body=["Port Meridian closed out the team title on the final bout of the "
               "afternoon, taking the épée final after trailing at the break.",
               "It is the program's first team championship in any weapon since the "
               "association sanctioned fencing, and the first Open title held outside "
               "the Ashbury metro.",
               "Individual weapon results and the full team standings are posted on "
               "the fencing championship page."]),
    dict(slug="rivalry-week-ashbury", kind="activity", kicker="Basketball",
         date="2027-01-15",
         head="Ashbury schools prepare for rivalry week",
         dek="All twelve city programs meet crosstown opponents over five nights, "
             "with three games moved to larger gyms to meet ticket demand.",
         body=["Rivalry week tips off Monday with Ashbury Heights at Ashbury Central, "
               "a series that has split its last ten meetings.",
               "Athletic directors moved three games to larger venues after last "
               "season's sellouts. Remaining tickets go on sale through school "
               "offices Wednesday.",
               "All twelve games count in conference standings."]),
    dict(slug="winter-championship-sites", kind="association", kicker="Championships",
         date="2027-01-14",
         head="Winter championship sites announced",
         dek="Basketball finals return to Ashbury Coliseum; wrestling moves to the "
             "Halbrook Events Center for the first time.",
         body=["The board confirmed host sites for all winter championship events at "
               "its January meeting.",
               "Wrestling's move to Halbrook follows two years of capacity crowds at "
               "the previous site. Swimming and diving remain at the Port Meridian "
               "Aquatic Center.",
               "Session schedules and ticket information post with the brackets."]),
    dict(slug="heat-policy-revision", kind="association", kicker="Health & Safety",
         date="2027-01-13",
         head="JHSAA approves revised heat policy",
         dek="Wet-bulb thresholds replace temperature readings for practice and "
             "contest modifications, effective with the spring season.",
         body=["The revised policy sets modification and cancellation thresholds by "
               "wet-bulb globe temperature, measured on site, in place of the air "
               "temperature standard in effect since 2019.",
               "Schools receive monitoring equipment through a grant program funded "
               "with the association's sports-medicine partners.",
               "Athletic directors complete the updated training module before "
               "spring practices begin."]),
    dict(slug="flag-football-sanctioned", kind="association", kicker="Activities",
         date="2027-01-11",
         head="Girls flag football added as championship activity",
         dek="A three-division championship debuts this spring after two years of "
             "club play in the Ashbury and Halbrook metros.",
         body=["The board voted to sanction girls flag football as a championship "
               "activity beginning with the spring season.",
               "Forty-one schools have declared varsity programs for the first "
               "season, concentrated in the metro classifications.",
               "Championship divisions and the qualifying structure are posted with "
               "the spring sport pages."]),
    dict(slug="winter-championship-brackets-set", kind="activity", kicker="Championships",
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
    dict(slug="alpine-nordic-schedule-change", kind="activity", kicker="Notice",
         date="2027-01-14",
         head="Alpine and nordic events moved after Cascade Divide storm",
         dek="Three invitationals scheduled for last weekend have been rescheduled. "
             "Qualifying standards are unchanged.",
         body=["Persistent snowfall across the Cascade Divide forced postponement of "
               "three alpine and two nordic invitationals.",
               "Rescheduled dates appear on each event page. Because qualifying is "
               "based on standard rather than event count, no skier's championship "
               "eligibility is affected by the cancellations."]),
    dict(slug="officiating-shortage-winter", kind="association", kicker="Officials",
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
    dict(slug="participation-record-girls-wrestling", kind="association", kicker="Participation",
         date="2027-01-12",
         head="Girls wrestling adds programs for a fourth consecutive year",
         dek="Eleven more schools are sponsoring the sport this winter, with the "
             "largest growth outside the Ashbury metro.",
         body=["Girls wrestling has grown in every classification since sanctioning, "
               "with this year's additions concentrated in Timber Valley and the "
               "Juniper Highlands.",
               "Several small schools are competing under cooperative agreements. "
               "Co-op athletes compete for the host school in championship events."]),
    dict(slug="transfer-rule-clarification", kind="association", kicker="Eligibility",
         date="2027-01-09",
         head="Board clarifies transfer sit-out period for midyear enrollment",
         dek="The clarification affects students changing schools after the first "
             "semester without a corresponding change of residence.",
         body=["A student who transfers without a bona fide change of residence is "
               "ineligible for varsity competition for the remainder of the season "
               "in any sport played at the previous school that year.",
               "Hardship waivers continue to be reviewed case by case. Athletic "
               "directors should file requests before the student competes, not after."]),
    dict(slug="netherwood-swimmer-feature", kind="activity", kicker="Student-athlete",
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
