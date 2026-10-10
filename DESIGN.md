---
name: athlete-hub
description: A personal training dashboard drawn as an orienteering map, with the season as a course.
colors:
  paper: "#FFFFFF"
  ink: "#1B1B1A"
  ink-2: "#474743"
  ink-3: "#66665F"
  hair: "#DDDDD6"
  forest: "#2C7A3A"
  forest-ink: "#1D5A28"
  forest-field: "#EAF4EA"
  forest-hair: "#C6DFC8"
  contour: "#A4521F"
  contour-ink: "#76380F"
  contour-field: "#F7ECE3"
  contour-hair: "#E5CDBB"
  water: "#1E6BB0"
  water-ink: "#144C80"
  water-field: "#E7F0F9"
  water-hair: "#C3D8EC"
  open: "#F6C343"
  open-field: "#FFF5D6"
  overprint: "#A92D86"
  overprint-field: "#F7E6F1"
  good: "#2C7A3A"
  warn: "#C77A0E"
  bad: "#C2362B"
  rest: "#9A9A92"
typography:
  display:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "88px"
    fontWeight: 800
    lineHeight: 0.92
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  display-mid:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "64px"
    fontWeight: 800
    lineHeight: 0.92
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "40px"
    fontWeight: 700
    lineHeight: 1.05
    fontFeature: "tnum"
  section-title:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "24px"
    fontWeight: 800
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "17px"
    fontWeight: 700
  body:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "tnum"
  caption:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 600
  axis:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
  status:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.05em"
  control-code:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 800
rounded:
  none: "0px"
  xs: "2px"
  sm: "3px"
  full: "50%"
spacing:
  page-x: "clamp(16px, 3vw, 40px)"
  xs: "6px"
  sm: "12px"
  md: "18px"
  lg: "24px"
  xl: "40px"
components:
  tab-health:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
  tab-run:
    backgroundColor: "{colors.contour}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
  tab-gym:
    backgroundColor: "{colors.water}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
  button-sync:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
    width: "108px"
  button-sync-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  section-band-health:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.paper}"
    typography: "{typography.section-title}"
    padding: "12px 0 11px"
  section-band-run:
    backgroundColor: "{colors.contour}"
    textColor: "{colors.paper}"
    typography: "{typography.section-title}"
    padding: "12px 0 11px"
  section-band-gym:
    backgroundColor: "{colors.water}"
    textColor: "{colors.paper}"
    typography: "{typography.section-title}"
    padding: "12px 0 11px"
  panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "20px 24px 22px"
  lead-state-field:
    backgroundColor: "{colors.forest-field}"
    textColor: "{colors.ink}"
    padding: "26px 40px 28px"
  control-code:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.overprint}"
    typography: "{typography.control-code}"
    rounded: "{rounded.full}"
    size: "30px"
  readiness-bar:
    backgroundColor: "{colors.overprint-field}"
    height: "6px"
  week-day-today:
    backgroundColor: "{colors.open-field}"
    textColor: "{colors.ink}"
    padding: "12px 14px 14px"
  info-disclosure:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.full}"
    size: "22px"
  info-disclosure-open:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  chart-tooltip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.xs}"
---

# Design System: athlete-hub

## Overview

**Creative North Star: "The Season as an Orienteering Course"**

The dashboard is printed like an orienteering map (IOF ISOM symbology). White map paper carries near-black ink; the map's own symbol colours are the data roles. The terrain is the body's state, coloured by section: Health is runnable-forest green, Run is contour brown, Gym is water blue. On top of the terrain sits the purple course overprint, the course the athlete set for themselves: races, drawn as a start triangle, control circles and a double finish circle joined by legs. Open-land yellow marks today and nothing else.

Density is high but ranked. One number per question gets hero size (Recovery, Form); everything else is set small, in tabular figures, divided by single ink rules instead of boxes. Surfaces are flat colour fields, like map areas, never cards. Nothing that was planned disappears: passed races and missed workouts are struck through, the way a map cancels a feature rather than erasing it.

The previous dark theme (Space Grotesk and IBM Plex Mono on slate with amber and blue) and the chalkboard/wallchart direction are both rejected and must not return.

**Key Characteristics:**
- Map-paper white ground, near-black ink, ISOM symbol colours as data roles.
- Section hue at full strength on tabs and section bands; pale field tints for areas; deep "ink" shades for text on those fields.
- Purple overprint is reserved for races and goals; yellow is reserved for today.
- Barlow throughout, tabular figures everywhere.
- No card chrome: one-pixel ink rules and hairlines divide the page.
- Cancel, never vanish: passed and missed items stay visible, struck through.

## Colors

A white map sheet with five ISOM symbol hues, each used for exactly one meaning.

### Primary
- **Runnable-Forest Green** (`forest`): Health. Fills the Health tab and section band, colours Health chart series (sleep score, HRV, 7-day trends). Doubles as the `good` state.
- **Forest Ink** (`forest-ink`): text, units, axis labels and sparkline strokes sitting on the pale green Health field.
- **Forest Field** (`forest-field`): the lead band's body-state area. **Forest Hair** (`forest-hair`): dividers inside that field and the empty cells of the 30-day recovery strip.

### Secondary
- **Contour Brown** (`contour`): Run. Run tab and section band, CTL line, weekly-volume bars, VO2 max line, and the week strip's planned/actual time bars.
- **Contour Ink** (`contour-ink`): Run meta text and captions, the "This week" heading. **Contour Field** / **Contour Hair** (`contour-field`, `contour-hair`): reserved pale field and divider for Run areas.

### Tertiary
- **Water Blue** (`water`): Gym. Gym tab and section band, first 1RM series. Gym chart series step through the blue family, with ink dashed lines for barbell lifts.
- **Water Ink** (`water-ink`): Gym meta text, PR values, completed split status. **Water Field** (`water-field`): a completed split day. **Water Hair** (`water-hair`): split-day dividers.

### Reserved
- **Course Overprint Purple** (`overprint`): races and goals only: the Race build heading, control circles and codes, course legs, start triangle, finish ring, days-to-go figures, readiness bar fill. The athlete-hub lockup mark is a single overprint control circle.
- **Overprint Field** (`overprint-field`): readiness bar track.
- **Open-Land Yellow** (`open`): today. Drawn as the 4px top rule on today's day in the week strip.
- **Open Field** (`open-field`): today's day background in the week strip.

### State
- **Good** (`good`, same value as forest), **Warn** (`warn`, a burnt amber, distinct from open-land yellow), **Bad** (`bad`): recovery zones (≥67 / 34–66 / <34), strain zones, trend deltas, Form scale-bar ends, done/missed status, the strike colour on a missed workout.
- **Rest Grey** (`rest`): low or no-data values in Recovery and Strain charts.

### Neutral
- **Map Paper** (`paper`): page ground, top bar, panels, sync button at rest.
- **Ink** (`ink`): primary text, structural rules (top bar, lead band, week strip, section bodies), focus ring, tooltip ground, ATL dashed line, Resting HR series.
- **Ink 2** (`ink-2`): secondary text (dates, details, meta). **Ink 3** (`ink-3`): tertiary text, chart axis labels, passed/cancelled items, upcoming and rest status.
- **Hairline** (`hair`): dividers between panels, race rows and week days.

### Named Rules
**The One Meaning Rule.** Every hue has one job. Green is Health, brown is Run, blue is Gym, purple is races, yellow is today. A colour never borrows another section's meaning, and a new surface inherits these roles rather than adding accents.

**The Overprint Rule.** Purple appears only where the athlete's own course appears: races, goals and race readiness. If it isn't a race, it isn't purple.

**The Open Land Rule.** Yellow marks today and nothing else. Warning state uses burnt amber (`warn`), never yellow.

## Typography

**Display Font:** Barlow (self-hosted, weights 400–800), with Helvetica Neue, Arial, sans-serif
**Body Font:** Barlow, same stack
**Label/Mono Font:** none; figures use Barlow with tabular numerals

**Character:** Barlow is a slightly condensed grotesque with the plain, signage-like voice of map legends and race bibs. One family carries everything; hierarchy comes from size and weight (400 to 800), not from a second face.

### Hierarchy
- **Display** (800, 88px, 0.92, -0.02em): the one hero figure, Recovery. Drops to 72px under 860px.
- **Display Mid** (800, 64px): the second hero figure, Form. 52px under 860px.
- **Headline** (700, 40px, 1.05): primary Today tiles (HRV, Resting HR, Sleep). Units follow at 15px/500 in the section's ink colour.
- **Section Title** (800, 24px, -0.01em): white on the section band.
- **Title** (700, 17px): panel and lead-block headings. Followed inline by meta at 14px/500 in the section's ink colour.
- **Body** (400, 15px, 1.4): default; workout names at 15px/700, race names at 16px/700.
- **Caption** (400, 14px, 1.5, max 75ch): disclosure text under panel heads.
- **Label** (600, 14px): tile labels, tab labels, sync button (700).
- **Axis** (400, 12px): chart ticks, strip and sparkline axes, legend keys (600).
- **Status** (700, 12px, 0.05em, uppercase): week-strip state words (Done, Missed, Today, Upcoming, Rest) with an inline check or cross.
- **Control Code** (800, 12px in the list, 13px on the course): race codes C1, A1, B1.

### Named Rules
**The Tabular Rule.** `font-variant-numeric: tabular-nums` is set on the body. Every figure on the page aligns.

**The One Hero Rule.** Only the morning's readiness answer (Recovery and Form) is set at display size. Everything else stays at 40px or below.

## Layout

The page is a vertical stack of full-bleed bands, each divided from the next by a 1px ink rule; content is capped at 1440px and padded by `page-x` (`clamp(16px, 3vw, 40px)`).

- **Top bar:** sticky, 58px min height, ink bottom rule. Lockup left, section tabs, then freshness and Sync now on the right.
- **Lead band:** two columns, `minmax(0, 1fr)` and `minmax(0, 520px)`. Left is the Health field (`forest-field`) with an ink right rule; right is white for Race build. Inside the field, Recovery and Form sit side by side (1.15fr / 1fr, 40px gap), then three primary tiles separated by forest hairlines, then a wrapped row of secondary tiles.
- **Week strip:** 190px summary column with an ink right rule, then day columns at `repeat(auto-fit, minmax(150px, 1fr))` divided by hairlines.
- **Sections:** a full-strength section band, then a 12-column grid of panels (spans 4–12). Panels are divided by hairlines (bottom, and left on a right-hand panel); edge panels drop their outer padding so content aligns with the page margin.
- **Chart heights:** 170px (small), 200px (default), 260px (large), 340px (extra large).

**Responsive.** At 1100px the lead band stacks: the Health field takes an ink bottom rule instead of a right rule. At 860px every panel spans all 12 columns, vertical panel rules drop, Recovery and Form stack, primary tiles become a single column, the week strip becomes two columns under its summary, Recent PRs go to one column, and hero figures shrink. At 520px the sync line uses a short form and the header-right row takes full width. Anchor scrolling clears the sticky bar (`scroll-padding-top: 72px`).

### Named Rules
**The No Card Chrome Rule.** Sections are colour fields divided by rules, never boxes. No panel gets a border on all four sides, a radius, or a shadow. Division is a single 1px ink rule between bands and a 1px hairline within them.

## Elevation & Depth

Flat. The map is printed on one plane; depth comes from colour fields (white paper vs. pale section fields) and rules, not from lift. `box-shadow` appears in the build only as a drawn line: the 4px yellow top rule on today (`inset 0 4px 0` open) and the outer ring of the finish control (`0 0 0 2px` paper, `0 0 0 4.5px` overprint). Neither is elevation.

### Named Rules
**The Printed Sheet Rule.** Nothing floats except the sticky top bar and the chart tooltip. No drop shadows, no blur, no layered cards.

## Shapes

Square by default. Panels, fields, bands, bars and chart bars have no radius. Small 3px corners appear only on interactive chips (section tabs, Sync now); 2px on the focus ring and chart tooltip. Circles are reserved for map symbols: control circles, the finish double ring, the lockup mark, and the (i) disclosure. The start triangle and the trend arrows are the only other drawn shapes. Strokes are 1px for rules, 1.5px for outlines (sync button, planned time bar, (i) ring) and 2.5px for course symbols.

## Components

### Section Tabs
Acetate tabs in full section hue.
- **Shape:** 3px corners, 6px 12px padding (6px 10px under 860px).
- **Colour:** forest, contour or water ground with white 14px/600 text.
- **Hover:** `filter: brightness(0.88)`, 150ms ease-out.

### Sync Now Button
- **Shape:** 3px corners, 1.5px ink outline, 7px 14px padding, 108px min width, 14px/700.
- **Hover:** inverts to ink ground with paper text, 150ms ease-out.
- **Disabled (syncing):** progress cursor, ink-2 text, ink-3 outline; a 3px ink progress bar grows along the bottom edge.

### Section Band
Full-bleed strip in the section hue with a white 24px/800 title and a 14px descriptor at 92% opacity, baseline-aligned. It opens the Health, Run and Gym sections and is the anchor target for the tabs.

### Panel and Panel Head with (i) Disclosure
Panels are unboxed regions of the 12-column grid, 20px 24px 22px padding, divided by hairlines. The head is a `details/summary`: 17px/700 title, inline meta in the section's ink colour, and a 22px circular (i) at the far right drawn as an inline SVG. The (i) ring is ink-3 at rest, ink on hover, and fills ink with paper glyph when open. The opened caption is 14px/1.5, max 75ch, in the section ink colour. Panels without explanatory text use the same head without the disclosure.

### Race Build: Control Codes and Course Overprint
The signature component. Each race gets a control code: priority letter plus a running index per priority in date order (C1, A1, B1, A2). The same code labels both the course drawing and the race list.
- **Course:** an SVG with a start triangle at today (labelled "today"), legs drawn as 2.5px overprint lines, and control circles placed along x by days to go. The last A race is the finish: a double circle. Passed races sit left of the start in ink-3, struck by a diagonal line.
- **Race list row:** 30px control circle (2.5px overprint ring, 12px/800 code; the finish adds an outer ring), race name 16px/700, date/distance/goal line in ink-2, and days to go at 26px/800 in overprint, right-aligned, with "days" beneath.
- **Readiness bar:** 6px tall, overprint fill on an overprint-field track, with a 13px ink-2 line above (current vs. peak km/wk, weeks to go).
- **Passed:** name struck through in ink-3, ring and code in ink-3, days figure at 18px with "days ago".

### Week Strip Day with Time Bars
Each day: day name and status word (Status type, with check or cross icon), workout name 15px/700, detail line 13px ink-2, then a 6px time bar. The planned duration is a 1.5px contour-brown outline; the actual duration is a solid contour-brown bar laid over it, both scaled to the week's longest session. Today gets the open-field ground and a 4px open-yellow top rule. A missed workout keeps its name, struck through in the `bad` colour; a rest day is set in ink-3 at 600.

### Today Tiles and Contour Sparklines
Primary tiles: 14px/600 label in forest ink, 40px/700 value with unit, a trend line (filled triangle up/down or arrow for flat, in good/bad/ink-3), then a 54px contour sparkline: a 1.75px forest-ink polyline over a dashed (3 3) forest mean line at 60% opacity, ending in a 2.5px dot, with a 12px axis line beneath (30-day range, average). Secondary tiles collapse to a baseline row: 18px value, 12px trend.

### Recovery Strip and Form Scale Bar
The recovery strip is 30 equal cells (2px gaps, 22px tall, max 420px) filled good/warn/bad by zone, forest-hair when empty; today's cell carries a 2px ink outline. Form is drawn as a map scale bar from −30 to +30: red zone, white neutral zone, green zone, ink frame, ticks every 10, and an ink pointer triangle at the current value.

### Charts
Chart.js, configured as a printed map legend.
- **Axes:** x axis has an ink baseline and no gridlines, max 8 ticks, no rotation; y axis has hairline gridlines and no border. Tick text 12px Barlow in ink-3.
- **Series colour:** by section role (forest for Health, contour for Run, water family for Gym). Raw daily values are a 1px line at 40% alpha over an 8% alpha fill; the 7-day trend is a 2.5px solid line in the full hue. Comparison series use ink, dashed (ATL `5 3`). Bars are square-cornered.
- **Zone-coloured series:** Recovery segments and Strain bars take good/warn/bad/rest by threshold.
- **Legend keys:** top-right, 12px/600. Line series show a 20px stroke in their own colour and dash; bar series show a filled square.
- **Tooltip:** ink ground, 2px corners, 12px Barlow (700 title).

### Gym Split and PR List
Split: three columns under an ink top rule, separated by water hairlines, 18px/700 category; a completed day takes the water-field ground and a water-ink status. PRs: two text columns (one under 860px) of hairline-divided rows, lift name left and 17px/700 water-ink value right.

## Do's and Don'ts

### Do:
- **Do** give each section its ISOM hue at full strength on its tab and band, its pale field for areas, and its ink shade for text on that field.
- **Do** keep purple (`overprint`) for races and goals, and yellow (`open`) for today.
- **Do** divide with a single 1px ink rule between bands and a 1px hairline within them.
- **Do** set every figure in Barlow with tabular numerals.
- **Do** give every race one control code and use it identically on the course and in the list.
- **Do** strike through passed races and missed workouts instead of hiding them.
- **Do** draw time and progress at exact length: time bars and readiness bars are proportional, never decorative.
- **Do** draw chart legends as map keys: line swatches for lines, filled squares for bars.

### Don't:
- **Don't** wrap panels in cards: no four-sided borders, radii or drop shadows on content regions.
- **Don't** use purple for anything that isn't a race or goal, or yellow for anything that isn't today; warnings use burnt amber.
- **Don't** add a second typeface or a monospace for figures.
- **Don't** remove passed or missed items from view.
- **Don't** set anything but Recovery and Form at display size.
- **Don't** revive the dark slate/amber theme with Space Grotesk and IBM Plex Mono, or the chalkboard/wallchart direction.
