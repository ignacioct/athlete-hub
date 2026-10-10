# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One user: a runner who also lifts, and who is this repo's developer. Running is the primary sport. It follows a running club's plan (TrainingPeaks → Garmin Connect, Forerunner 255) and builds toward races. Strength training (logged in Hevy, push/pull/legs split) supports the running. The user plans their own training; no coach uses this tool. Nobody else uses the dashboard.

They open it most days, usually at a desk, to read their training state: recovery and readiness, load and fitness trends, progress toward upcoming races, and strength progression. The weekly schedule is moved often and managed in TrainingPeaks itself. The dashboard shows it as a compact supporting reference, not the centrepiece.

## Product Purpose

athlete-hub pulls Garmin, Hevy, the running club's TrainingPeaks plan (via Garmin), and intervals.icu into one local SQLite database. It exposes that database to Claude through an MCP server, so Claude can answer training questions and push structured workouts to the watch via intervals.icu. The dashboard is the daily read-only view of that data. Success means the user trusts it and opens it instead of Garmin Connect, Hevy and intervals.icu separately.

## Positioning

Garmin and TrainingPeaks offer no personal API, and Hevy's official API needs a Pro subscription. athlete-hub is the only tool the user has that merges all three into one schema, puts the club's planned week next to what was actually done, and writes planned workouts back to the watch through intervals.icu's official API.

## Operating Context

- Mostly viewed on a desktop or laptop browser. Phone viewing over Tailscale happens occasionally and should hold up, but it is secondary.
- Runs entirely locally. `data/athlete.db` and `dashboard/data.json` hold personal health data and must never be exposed publicly.
- Data refreshes on demand only, through the dashboard's "Sync now" button (`dashboard/server.py`, `POST /api/sync`) or the MCP `sync_now` tool. There is no cron job, so data can be days old. `generated_at` is the honest freshness signal.

## Capabilities and Constraints

- The dashboard is a single static page: `dashboard/index.html`, vanilla HTML/CSS/JS, no framework. It renders `dashboard/data.json`, which `dashboard/generate_data.py` produces, using self-hosted Chart.js (`dashboard/vendor/chart.umd.min.js`).
- data.json keys: `generated_at`, `activities`, `daily_metrics` (resting HR, HRV, sleep, body battery, stress, VO2max, CTL/ATL/form), `races` (with priority A/B/C, goal time and a `readiness` block), `weekly_workouts` (the club plan per day, matched to an `actual` activity), `vo2max_history`, `weekly_split` (push/pull/legs done this week), `core_lifts` (est. 1RM series per lift), `recent_prs`.
- The current redesign is visual only. Every data binding, the Chart.js usage and the Sync now behaviour must keep working.
- Fragile upstream data, a reason panels may show stale or missing data: the Garmin export is unofficial; the weekly club plan relies on a private Garmin endpoint; Hevy uses a reverse-engineered client. Empty and missing states are normal, not edge cases.

## Brand Commitments

Only the plain "athlete-hub" name. There is no logo and no identity to keep. The current dark theme (Space Grotesk + IBM Plex Mono, slate/amber/blue) is an anti-reference. A previously explored chalkboard/wallchart direction was rejected and must not be revived.

## Evidence on Hand

Real personal data in `dashboard/data.json` (about 106 activities, about 103 days of metrics, 5 races, 7-day club plan, 1RM history from 2025-09 onward, 8 recent PRs). Design against this real data. Never fabricate content. No marketing claims or testimonials apply.

## Product Principles

1. State over schedule. Recovery, load and race-build trends lead; the weekly plan is a compact reference, because the schedule lives and changes in TrainingPeaks.
2. Running leads, strength supports. Order and weight follow the user's actual priorities.
3. Numbers must be trustworthy at a glance. Show data freshness, units and missing data honestly, and choose clarity over flourish.
4. Private by default. The page is built for local or Tailscale use and never for public hosting.
5. Functionality never regresses. Visual work keeps every binding, chart and the sync flow intact.
