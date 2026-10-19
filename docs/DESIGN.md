# Interface design

## Version 1.4: story page and simulator split (scroll-craft skill)

`/` is now a one-page story built with the scroll-craft skill's method (brief,
feeling curve, grammar, signature move; see `docs/scrollcraft/`). Grammar: *live
surface*, so the page is the product running on real API data, with the app's tab
strip on top and a live status bar at the bottom. The simulator moved to
`/app.html`; the story's closing console deep-links into it
(`?facility=&reduction=&backups=&run=1`) and the simulator runs that scenario.
`/app.html#trace`, `#analytics` and `#assistant` open a view directly.

The first story build used pinned, scroll-driven sections. The owner rejected them,
so the page now scrolls normally: the capacity dial is a slider with a "Take it
offline" button, and the products that stay short are a grid. Following the skill's
taste floor, the whole UI now uses Geist (served locally) instead of a system serif,
and visible em dashes were removed. The skill's engine script was not vendored; the
page uses its own small script. Map code is shared by both pages via `geo.js` and
`geo.css`. The simulator now uses the story's night palette (same six colour roles,
mint accent) and its tab strip includes Story, so both pages read as one product.


## Version 1.3 — the world map

The owner asked for an interface that makes people say "wow" without losing the
clarity of 1.2. The signature addition is a dark, dotted world map that appears on
three screens and always answers that screen's question:

- **Disruption:** "Where the goods flow". Facilities sit at their assumed cities and
  animated dashes move along every lane. When a scenario runs, the failed facility
  pulses red and the shortfall travels outward hop by hop (amber), using the `hops`
  the API already returns, while unaffected lanes dim. The four outcome numbers sit
  on the map and count to their new values.
- **Products:** "Route on the map" highlights only the facilities and lanes that carry
  the selected product and says how many countries it crosses.
- **Analysis:** "Bridges on the map" sizes each facility by its GDS betweenness score.

The light editorial body from 1.2 stays, so the dark map is the one moment of drama
on each page. The map is decorative-plus: everything on it is also available in the
accessible network diagram, list and tables. On phones the map moves above the
controls and becomes a swipeable canvas centred on Europe. Motion is switched off
for `prefers-reduced-motion`. The impact table now shows a "Still delivered" bar per
product. The backdrop is generated from public-domain Natural Earth data by
`scripts/create_land_map.py`; see DATA_LICENSE.md.


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
