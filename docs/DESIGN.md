# Interface design — visual refinement

The owner requested a more professional application with easier visual reading.
The first interface compressed important labels to 7–9 px on narrow screens and
hid mobile navigation labels. The revised interface uses a 15 px body, 13–15 px
controls and table data, readable captions, and a dark navy / blue visual system.

The layout follows a decision: overview metrics, scenario inputs, network, product
impact, then recovery comparison. Scenario results show affected products and
unmet daily units instead of exposing an internal identifier. Exports retain the
full scenario record. The service-level bar reflects actual solver output.

The network occupies the full content width. Desktop uses stage columns and clear
facility cards with keyboard selection. Below 760 px, the default becomes a readable
facility list; Map and Facilities controls let the user choose either. The map can
scroll within its own panel. Data tables also scroll within their own panels.
Recovery information remains available on mobile. Navigation always has text.

Product, analytics, assistant and methodology screens share typography, cards,
colors and spacing. Observed and assumed evidence remain visibly distinct. Cypher
is placed behind an expandable section with a high-contrast code surface. No
external fonts, images, icon CDN or UI framework are needed.

UI-only work does not change the simulation, database, dataset, GDS or LLM boundary.
Verification is recorded in reports/browser-qa.json with actual viewport checks and
real interactions; screenshots are captured from the working application.
