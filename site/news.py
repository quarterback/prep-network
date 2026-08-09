"""
Seeded association newsroom for the Jefferson demo.

An association front page is a publication as much as a database — MHSAA leads
with stories and audience sections; NJSIAA leads with notices, brackets and
health/eligibility material. These are the fictional equivalents: previews,
rule changes, officiating notices, participation announcements, student
features. Written once, in the association's voice, never generated.

Every story carries a **season** and, where it has one, a **sport**. The
season is what lets the front page change with the Fall/Winter/Spring tabs
instead of leading with the same fixture forever: the eleven stories this
file started with were all dated the same January week, so at the May demo
clock the site opened on a four-month-old fencing result and had nothing at
all to say about fall or spring. The sport supplies a photograph when a
story has no picture of its own, out of the sport library rather than a
placeholder.
""" 

STORIES = [
    # ── fall ────────────────────────────────────────────────────────────
    dict(slug="llerena-takes-7a-football", season="fall", sport="football",
         kind="activity", kicker="Football", date="2026-11-21",
         head="Llerena Civic Leadership Academy takes the 7A football title",
         dek="The Coliseum final went to the team that had lost to Serrano in "
             "September, and the rematch was not close after halftime.",
         body=["Llerena Civic Leadership Academy closed the 7A championship at "
               "Jefferson Coliseum on Friday night, beating a Serrano side it "
               "had lost to in the second week of the season.",
               "Serrano had come through the bottom half of the bracket without "
               "trailing. The 7A final was the program's first appearance in the "
               "championship game since the classification was created.",
               "Full scoring by quarter and the complete bracket are on the "
               "football championship page."]),
    dict(slug="greaves-junction-1a-football", season="fall", sport="football",
         kind="activity", kicker="Football", date="2026-11-21",
         head="Greaves Junction wins 1A on a night the smallest schools filled the house",
         dek="Sage Summit Pavilion sold out for a final between two schools whose "
             "combined enrollment is under four hundred.",
         body=["Greaves Junction beat Sablewood Union for the 1A championship at "
               "Sage Summit Pavilion, in front of the largest crowd the venue has "
               "held for a small-school final.",
               "Both programs field fewer than thirty players. Sablewood Union "
               "reached the final having played three of its four playoff games "
               "on the road.",
               "The 1A bracket, all twenty-four teams, is posted with each round's "
               "results."]),
    dict(slug="steelbridge-field-hockey", season="fall", sport="field-hockey",
         kind="activity", kicker="Field Hockey", date="2026-11-20",
         head="Steelbridge holds off Thurgood Marshall for the 7A-5A field hockey title",
         dek="A single first-half goal decided the consolidated championship at "
             "the Halbrook Events Center.",
         body=["Steelbridge won the 7A-5A field hockey championship on Friday, "
               "beating Thurgood Marshall at the Halbrook Events Center.",
               "Field hockey crowns two champions rather than one per "
               "classification — participation does not support six brackets — so "
               "the 4A-1A final followed on the same afternoon.",
               "Both brackets and every result are on the field hockey "
               "championship page."]),
    dict(slug="fall-participation-report", season="fall", kind="association",
         kicker="Participation", date="2026-11-05",
         head="Fall participation climbs for a third straight year",
         dek="Girls soccer and boys cross country accounted for most of the "
             "increase; two activities contracted.",
         body=["Member schools reported higher fall participation for the third "
               "consecutive year, with the largest gains in girls soccer and boys "
               "cross country.",
               "Two activities lost programs. The board asked staff to report in "
               "January on whether either should move to a consolidated "
               "championship format.",
               "Participation figures are collected from each member school at the "
               "close of the season and published in full."]),
    dict(slug="fall-officials-recognition", season="fall", kind="association",
         kicker="Officials", date="2026-10-28",
         head="Association recognises twelve officials for career service",
         dek="The registered officials honoured this fall have a combined 340 "
             "years across eleven sports.",
         body=["Twelve registered officials were recognised for career service at "
               "the association's fall meeting.",
               "The officials honoured have worked a combined 340 years across "
               "eleven sports, several of them in more than one season a year.",
               "Registration for winter sports officials remains open through the "
               "association's officials portal."]),

    # ── spring ──────────────────────────────────────────────────────────
    dict(slug="tennis-semifinals-preview", season="spring", sport="boys-tennis",
         kind="activity", kicker="Boys Tennis", date="2027-05-13",
         head="Four classifications reach the boys tennis semifinals this weekend",
         dek="7A has been running since April and is down to four; 4A and 5A "
             "opened last week and are already there.",
         body=["The boys tennis championships reach the semifinal round in four "
               "classifications this weekend, with all four finals set for May 22.",
               "The 7A bracket, a twenty-four team field, began on April 24 and "
               "has taken three weekends to reach this point. The 4A and 5A "
               "brackets are eight-team fields that opened on May 8.",
               "Every bracket, seed and completed line score is on the boys tennis "
               "championship page."]),
    dict(slug="ultimate-championship-field", season="spring", sport="ultimate",
         kind="activity", kicker="Ultimate", date="2027-05-12",
         head="Ultimate's 24-team field reaches the last four in its third season",
         dek="The activity was sanctioned three years ago with fourteen programs. "
             "The 7A-4A bracket now takes twenty-four.",
         body=["The 7A-4A ultimate championship is down to four teams, three years "
               "after the association sanctioned the activity with fourteen "
               "participating programs.",
               "The bracket has grown to twenty-four teams. A separate 3A-1A "
               "championship draws later this month.",
               "Results by round are posted as each is completed."]),
    dict(slug="spring-championship-sites", season="spring", kind="association",
         kicker="Championships", date="2027-05-11",
         head="Spring championship sites confirmed",
         dek="Tennis, volleyball, badminton and ultimate finals stay in Ashbury; "
             "baseball and softball move to Norview Memorial for the first time.",
         body=["The board confirmed host sites for the remaining spring "
               "championship events.",
               "The May 22 finals in tennis, boys volleyball, girls badminton and "
               "ultimate remain in Ashbury. The June 12 baseball and softball "
               "finals move to Norview Memorial Stadium for the first time.",
               "Ticketing for all championship events runs through the "
               "association, not through host schools."]),
    dict(slug="track-qualifying-standards", season="spring", sport="boys-track",
         kind="association", kicker="Track & Field", date="2027-05-06",
         head="Track qualifying standards published ahead of the June meet",
         dek="Marks must be achieved at a sanctioned meet; the association will "
             "not accept times from unsanctioned invitationals.",
         body=["Qualifying standards for the June 12 state track and field "
               "championships were published this week.",
               "Marks must be achieved at a sanctioned meet. The association "
               "reminded coaches that times and distances from unsanctioned "
               "invitationals cannot be used to qualify, whatever the timing "
               "system used.",
               "Standards are listed by event and classification for both boys and "
               "girls."]),
    dict(slug="spring-academic-honor-roll", season="spring", kind="association",
         kicker="Academics", date="2027-05-01",
         head="214 schools reach the academic honour roll",
         dek="Programs whose squad grade-point average cleared 3.25 across every "
             "sanctioned activity are recognised for the year.",
         body=["Two hundred and fourteen member schools reached the association's "
               "academic honour roll for 2026-27.",
               "The honour roll recognises programs whose squad grade-point "
               "average cleared 3.25 across every sanctioned activity, not one "
               "sport in isolation.",
               "Individual scholar-athlete recognition is announced by each school "
               "and appears on its own athletics site."]),

    # ── winter ──────────────────────────────────────────────────────────
    dict(slug="port-meridian-first-fencing-title", season="winter", sport="boys-fencing", kind="activity", kicker="Fencing",
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
    dict(slug="rivalry-week-ashbury", season="winter", sport="boys-basketball", kind="activity", kicker="Basketball",
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
    dict(slug="winter-championship-sites", season="winter", sport="boys-basketball", kind="association", kicker="Championships",
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
    dict(slug="heat-policy-revision", season="winter", kind="association", kicker="Health & Safety",
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
    dict(slug="flag-football-sanctioned", season="winter", sport="girls-flag-football", kind="association", kicker="Activities",
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
    dict(slug="winter-championship-brackets-set", season="winter", sport="boys-basketball", kind="activity", kicker="Championships",
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
    dict(slug="alpine-nordic-schedule-change", season="winter", sport="boys-alpine-skiing", kind="activity", kicker="Notice",
         date="2027-01-14",
         head="Alpine and nordic events moved after Cascade Divide storm",
         dek="Three invitationals scheduled for last weekend have been rescheduled. "
             "Qualifying standards are unchanged.",
         body=["Persistent snowfall across the Cascade Divide forced postponement of "
               "three alpine and two nordic invitationals.",
               "Rescheduled dates appear on each event page. Because qualifying is "
               "based on standard rather than event count, no skier's championship "
               "eligibility is affected by the cancellations."]),
    dict(slug="officiating-shortage-winter", season="winter", kind="association", kicker="Officials",
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
    dict(slug="participation-record-girls-wrestling", season="winter", sport="girls-wrestling", kind="association", kicker="Participation",
         date="2027-01-12",
         head="Girls wrestling adds programs for a fourth consecutive year",
         dek="Eleven more schools are sponsoring the sport this winter, with the "
             "largest growth outside the Ashbury metro.",
         body=["Girls wrestling has grown in every classification since sanctioning, "
               "with this year's additions concentrated in Timber Valley and the "
               "Juniper Highlands.",
               "Several small schools are competing under cooperative agreements. "
               "Co-op athletes compete for the host school in championship events."]),
    dict(slug="transfer-rule-clarification", season="winter", kind="association", kicker="Eligibility",
         date="2027-01-09",
         head="Board clarifies transfer sit-out period for midyear enrollment",
         dek="The clarification affects students changing schools after the first "
             "semester without a corresponding change of residence.",
         body=["A student who transfers without a bona fide change of residence is "
               "ineligible for varsity competition for the remainder of the season "
               "in any sport played at the previous school that year.",
               "Hardship waivers continue to be reviewed case by case. Athletic "
               "directors should file requests before the student competes, not after."]),
    dict(slug="carver-swimmer-feature", season="winter", sport="boys-swimming", kind="activity", kicker="Student-athlete",
         date="2027-01-08",
         head="A Plainfield swimmer's long drive to the nearest pool",
         dek="George Washington Carver has no pool of its own. Practice means a "
             "bus ride, four mornings a week, before first period.",
         body=["Carver's swimmers train at the municipal pool across town, leaving "
               "before dawn and returning in time for class.",
               "The arrangement is common outside the metros, where aquatic programs "
               "depend on shared municipal facilities.",
               "Benjamin F. Harding and Plainfield Science share the same water, and "
               "the three programs practice on a rotating schedule."]),
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
