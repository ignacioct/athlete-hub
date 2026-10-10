---
version: 1
slug: "dashboard-index-html"
primary_target: "dashboard/index.html"
related_targets: []
---

# Surface brief — dashboard/index.html

**Scope / mode:** athlete-hub dashboard, single-page Operate surface. One user, opened most days at a desk (phone over Tailscale is secondary). Redesign is visual only: every data binding, Chart.js chart, and the Sync now flow stay intact.

**Audience / job:** A runner who also lifts. They read their training state at a glance: recovery and readiness, load and fitness trends, race build, then strength. The weekly schedule is moved often and managed in TrainingPeaks, so here it is a compact reference strip, not the centrepiece.

**Order (user-confirmed):** State lead (Health) → week strip (reference) → Health detail → Run → Gym. Long explanatory captions collapse behind a per-panel (i) disclosure; every word kept.

**Must not feel:** gamified (rings, streaks, cheerleading) or dark/techy (console, neon).

## Direction contract

THESIS: The season as an orienteering course. The map shows the terrain (body state); the purple overprint shows the course the athlete set themselves (races). This refuses the category default of a flat grid of identical KPI cards on grey, where every number carries equal weight and races are a list.

OWN-WORLD: Map-paper white ground with near-black ink. ISOM symbol colours act as data roles. Health owns runnable-forest green (pale green field, deep green ink). Run owns contour brown (pale brown field, brown ink). Gym owns water blue (pale blue field, blue ink). Open-land yellow is reserved for "today". Overprint purple is used only for races and goals: control circles, start triangle, double finish circle and course legs. Barlow throughout with tabular figures. No card chrome: sections are colour fields divided by one ink rule. Missed and passed items cancel (struck through), never vanish.

STORY: In one glance the athlete sees whether their body is ready (recovery and form, hero-sized), how HRV, RHR and sleep are trending (contour-line sparklines), and where they stand on the course to the next races (purple leg bars, days to go). Then they scroll into Health, Run and Gym detail charts.

FIRST VIEWPORT: Top bar with the athlete-hub lockup (purple control-circle mark), Health/Run/Gym anchor tabs in their section colours, freshness ("Synced …") and Sync now. Lead band in two columns. Left, on the pale green Health field: Recovery 0–100 and Form, hero-sized, plus HRV, RHR and Sleep with 30-day contour sparklines. Right, on white: "Race build", a purple overprint course (start triangle = today, control circle per race with code C1/A1/B1, double circle on the last A race) and a leg list with readiness bars and days to go. Under the band sits a single-row week strip with a brown left rule per day, today marked in yellow.

FORM: Orienteering map (IOF ISOM symbology), position 5 of 7 on the ordered list; seed key 9d68725d, re-roll round 1. Signature move: purple course overprint for the race build; races carry one control code shared by the list and the course line. Raises kept: section hue at full strength (acetate tabs), length is exact (labanotation), no card chrome (metro), nothing disappears, it cancels (ticket wallet), one code links list and map (catalog).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

**Unresolved:** none blocking. Chart series colours map to the section's ISOM roles; Chart.js stays the renderer.
