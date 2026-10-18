# Interface design

## Version 1.2 — editorial redesign

The owner found the 1.1 interface hard to follow and said it looked like a generic
AI dashboard: a dark navy sidebar, a fake workspace switcher, an "AI" badge, arrow
icons on every button and marketing slogans ("Your network. Every possibility.",
"Connected insight. Confident decisions."). Version 1.2 removes all of that and
reorganises each screen around the question it answers.

**Staging.** Each view opens with a plain question as its title and one paragraph
saying what the screen does:

| Tab | Title | Purpose |
|---|---|---|
| Disruption | What happens when a facility fails? | Scenario set-up, outcome, network, product impact, recovery |
| Products | Where does a product come from? | Lanes for one SKU; recorded vs modeled delivery time |
| Analysis | Which facilities hold the network together? | GDS betweenness, WCC, single-source products |
| Ask the graph | Ask a question in plain language. | Local NL-to-Cypher with visible evidence |

**Cause beside effect.** On desktop the scenario controls sit in a sticky column on
the left, laid out as three numbered steps (facility, capacity lost, backups), with
exposure depth tucked under *Advanced*. Everything they change — the four-number
readout, the network map, product impact and the recovery comparison — is on the
right, so a run and its result are visible together. Below 1080 px the controls move
above the results; below 760 px the network defaults to a list.

**Visual language.** Warm paper background, white panels with hairline borders,
no shadows or gradients. One accent (deep teal) marks actions and selection; red
means disrupted, amber means downstream, green means recovered. Page titles use the
system serif (Iowan Old Style / Charter / Georgia); everything else uses the system
sans with tabular figures. The CSP allows no external fonts, so nothing is
downloaded. Observed and assumed data keep their own colours (blue and purple)
everywhere they appear.

**Network map.** Four labelled stages, left to right. Cards carry a thin stage-colour
bar instead of icons; a disrupted card turns red and says by how much, downstream
cards turn amber and say so in text, and unaffected lanes fade. The legend explains
the lane and state styles. The map scrolls within its panel on narrow screens.

**Copy.** Labels say what a value is ("Recoverable with backups", "Before / After /
Lost", "Recorded shipping time" vs "Fastest modeled route"). Buttons say what they
do ("Run simulation", "Re-run with backups", "Download result as JSON").

UI-only work: the simulation, database, dataset, GDS and LLM boundary are unchanged,
and every element ID used by the script is preserved. Responsive checks for 1.2 are
recorded in `reports/browser-qa.json` under `editorial_redesign`; screenshots in
`docs/screenshots/` were captured from the running application.
