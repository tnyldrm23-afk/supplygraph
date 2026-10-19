# SupplyGraph scroll surface: brief

**Self-authored under explicit creative delegation.** The owner asked for the UI to
be redesigned with the scroll-craft skill and, earlier in the same project, said:
"Final haline gelene kadar bana hicbir sey sorma her seye erisimine izin veriyorum"
(do not ask me anything until it is final; full access granted). No interview was
held. Evidence and assumptions are separated below.

## The eight topics

1. **Vibe.** Authored: "a control room at night, quiet until it isn't." References:
   airport departure boards, weather radar loops, the opening of a disaster film
   before anything goes wrong.
2. **Journey, in order.** Authored: see the network running; understand its four
   stages; break one facility with your own hand; watch backups recover part of it;
   see which products still lose; take the controls yourself.
3. **Energy curve.** Calm, calm, then the single intense stretch, then easing, then
   sober, then still and attentive.
4. **Feeling and the one moment.** See the feeling curve and peak below.
5. **What no other site does.** Authored: the scroll wheel is the capacity dial of a
   real facility, and every number on screen comes from the real max-flow solver.
6. **Distance from premium-minimal.** Authored: *dense* (information-forward, data
   product) rather than premium-minimal. Small type, many real figures, one accent.
7. **One unbroken world or distinct scenes?** Distinct states of one surface. Not a
   worldflight: no generated footage exists and the honest asset is the live map.
8. **Assets.** Evidence: no photography or footage. Available: the live API
   (13 facilities, 962 lanes, 118 products, solver), the dotted Natural Earth map,
   real DataCo demand. No assets are generated; no kie.ai spend.

## Grammar

**Live surface** (uniqueness.md §2.3). SupplyGraph is a tool and the honest pitch is
"watch what it does". Every panel is real markup computing from real API responses.
Why the other seven lost: filmic one-shot and continuous world need footage that does
not exist and would be invented; chaptered editorial and typographic poster would
describe the tool instead of running it; gallery has no product range to walk; split
stage has no two-sided argument; rhythmic cutlist fights the one long held moment the
story needs. Also hero-depth.md: "Working surfaces such as dashboards do not need an
invented marketing hero."

Bans honoured: no scrub, no kinetic headlines, no spotlight, no drift past two
stops, no marketing bar, no display type at hero scale, no scrims over photography.

## Feeling curve (written before the acts)

| # | Feeling | What on screen causes it |
|---|---|---|
| 1 | Calm | The network already running: goods flowing on every lane, 100% delivered |
| 2 | Understanding | The four stages laid out with every real facility named |
| 3 | Dread, then shock (**peak**) | The visitor's scroll drains Atlas Textiles to zero and the shortfall spreads city by city |
| 4 | Relief | Reserve contracts switch on and 60.3 units/day count back |
| 5 | Sobriety | The products that still lose supply, one at a time, with real numbers |
| 6 | Agency | The controls are handed over: any facility, any capacity, run it for real |

**Authored silence.** The first 14% of act 3 changes nothing except the selection
ring and the status line. It is intentional, not dead scroll.

## The peak

"I scrolled and a textile supplier in Porto went offline, and I watched the
shortage reach London and New York." Lives in act 3, which has the largest span.

**Tell-someone sentence.** It's the site where your scroll wheel shuts down a
factory in Porto and you watch the shortage reach New York.

## Signature move

**Scroll as capacity dial.** Act 3 maps scroll progress to Atlas Textiles' lost
capacity in 10% steps. Each step shows the solver's real answer for that reduction
(prefetched from `POST /api/scenarios`), so the map, the counters and the lost
product list are true at every stop of the wheel.

## Score

| Beat | Device | Why |
|---|---|---|
| Calm | `pin` (surface holds, flow animates) | The hero is the surface already in a state |
| Understanding | `flow` + `in` | Plain structure reads best as a document moment |
| Peak | `pin`, longest span, page-local progress | The signature move needs a held frame |
| Relief | `count` on entry | Real figures, ticking once |
| Sobriety | `pan` | A range of products reads as breadth |
| Agency | `pin` close holding an actual input | A tool ends with a cursor in a control |

Four families or more: pin, flow/in, count, pan. No family twice in a row.
Total about 10 viewport-heights across 6 acts.

## Owner verdict and revision (2026-10-19)

The first build pinned four acts, drove Atlas Textiles' capacity from scroll progress
and moved the "still short" products on a horizontal pinned rail. The owner rejected
both mechanisms: they made the page harder to use and added nothing ("Eger siteye bir
sey katmiyorsa scroll ekleme bosuna"). Desktop is the target; phone is secondary.

Revision, per the skill's rule that the brief wins over a device:

- **No pinned acts, no scroll-driven state, no rail.** The page scrolls normally
  (5.7 viewport-heights instead of 12). Sections fade in once.
- **Signature move kept, input changed.** The capacity dial is now a real slider plus a
  "Take it offline" button that steps 100% to 0% at 650 ms per step. Every step still
  shows the solver's real answer, and the ripple still plays the first time the network
  goes short.
- **"Still short" is a grid** of eight product labels, readable at a glance.
- Close unchanged: an actual input that opens the simulator with the scenario run.

Felt curve after the change (cold pass on desktop): calm, understanding, tension when
pressing the button then shock at 20% (40 products short at once), relief, sobriety,
agency. Matches the intended curve; the peak is now triggered by the visitor's click
instead of their scroll wheel.
