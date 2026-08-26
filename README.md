# athlete-hub

Centralizes your Garmin (Forerunner 255 + Circa), Hevy, and running-club (via
TrainingPeaks → Garmin) data into one local database, exposes it to Claude
through an MCP server so you can ask questions and plan ahead, and gives you
a lightweight dashboard.

## Why it's built this way

| Source | Reality | What this repo does |
|---|---|---|
| Garmin Connect | No personal API exists. Garmin only grants API access to approved companies. Every "Garmin API" you'll find (including the one this repo wraps) is unofficial and can break when Garmin changes something. | `src/garmin_sync.py` wraps [`garmin-givemydata`](https://github.com/nrvim/garmin-givemydata), the current best-maintained unofficial exporter, and normalizes its output into our schema. |
| TrainingPeaks | Personal API access isn't available — TrainingPeaks only approves commercial partners. | Not integrated directly. Your club's uploads already sync into Garmin Connect, so they arrive via the Garmin sync for free. |
| Hevy | Has a real, documented, official API (Pro subscription required). | `src/hevy_sync.py` calls it directly over HTTPS. This is the most reliable sync in the repo. |
| intervals.icu | Free account, full official REST API, and it already has a mature, reliable two-way Garmin sync — including pushing planned/structured workouts to your watch. | Used for two jobs: (1) a second read of your running data with training-load metrics (CTL/ATL/TSB) already computed, and (2) the **write path** — this repo creates workouts here, and intervals.icu's existing Garmin sync gets them onto your Forerunner. We deliberately don't try to write to Garmin directly; that path is far less reliable. |

**You'll need a free intervals.icu account** with your Garmin connected there
(Settings → Connections → tick "Upload planned workouts"). That single
integration is what makes the "create a workout, get it on my watch" loop
work without touching Garmin's unofficial write endpoints at all.

## Project layout

```
athlete-hub/
├── src/
│   ├── db.py              # SQLite schema + connection helper
│   ├── garmin_sync.py     # Garmin -> unified DB (via garmin-givemydata)
│   ├── hevy_sync.py       # Hevy -> unified DB
│   ├── intervals_sync.py  # intervals.icu -> unified DB, and DB -> intervals.icu (workout push)
│   └── races.py           # CRUD for upcoming races
├── mcp_server/
│   └── server.py          # MCP server: exposes the DB + workout creation to Claude
├── scripts/
│   └── sync_all.py        # run every sync in order
├── dashboard/
│   ├── generate_data.py   # DB -> data.json snapshot
│   ├── server.py          # serves the dashboard + POST /api/sync ("Sync now" button)
│   ├── index.html         # Chart.js dashboard reading data.json
│   └── vendor/             # self-hosted Chart.js (no CDN dependency)
├── config/
│   └── races.yaml         # example seed file for races.py
└── data/                  # athlete.db lives here (gitignored)
```

## Setup

1. **Clone this repo locally** (a machine that's on your home network with a
   stable IP is best — see the Garmin section below on why).

2. **Python deps:**
   ```bash
   uv sync
   ```
   (or, without [uv](https://docs.astral.sh/uv/): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`)

3. **Credentials** — copy `.env.example` to `.env` and fill in:
   - `HEVY_API_KEY` — from https://hevy.com/settings?developer (requires Hevy Pro)
   - `INTERVALS_ATHLETE_ID` and `INTERVALS_API_KEY` — from https://intervals.icu/settings ("Developer Settings")
   - `GARMIN_EMAIL` / `GARMIN_PASSWORD` — your Garmin Connect login (used locally only, never sent anywhere but Garmin)

4. **First sync:**
   ```bash
   uv run scripts/sync_all.py
   ```

5. **If you change the Garmin export mapping later:** `garmin-givemydata`'s
   export format can shift between versions. `GARMIN_FIELD_MAP` /
   `WELLNESS_SOURCES` near the top of `garmin_sync.py` are already verified
   against a real export (see that file's docstring for specifics), but if a
   future version of the library changes field names, re-run:
   ```bash
   uv run -m src.garmin_sync --inspect
   ```
   This prints the raw export structure without writing to the DB, so you can
   compare it against the field maps and fix anything that's drifted.

6. **View the dashboard:**
   ```bash
   uv run dashboard/server.py 8080
   # open http://localhost:8080
   ```
   This serves the static dashboard *and* a "Sync now" button in the header —
   there's no cron job (see below for why), so this is the primary way data
   gets refreshed.

7. **Add the MCP server to Claude Desktop / Claude Code** — see
   `mcp_server/README.md` for the config snippet. Once connected, you can
   also just ask Claude to sync (it calls the `sync_now` tool).

## Why there's no cron job

The original design scheduled `scripts/sync_all.py` via cron. In practice the
sync machine isn't guaranteed to be on 24/7, so a cron job would silently
miss runs. Instead, syncing is on-demand from two places that both just call
`scripts/sync_all.py`'s `main()`:

- **The dashboard's "Sync now" button** (`dashboard/server.py`'s
  `POST /api/sync`) — click it whenever you're looking at the dashboard.
- **Asking Claude to sync** (`mcp_server/server.py`'s `sync_now` tool) — works
  from any Claude session with the MCP server configured.

Both default to a 7-day lookback (`garmin-givemydata`'s export always dumps
its full accumulated local history regardless of `--days`, so `athlete.db`
still ends up complete — the short window just keeps each sync's Garmin
login/fetch step fast). Run `uv run scripts/sync_all.py --days 90` manually
for a first-time backfill or if you've gone a while between syncs.

## Phone access

Nothing here is hosted publicly by default — the DB and dashboard live on
your machine. Two good options if you want them on your phone without
exposing your health data to the internet:

- **[Tailscale](https://tailscale.com)** (free for personal use): put your
  sync machine and phone on the same private network, then open the
  dashboard or reach the MCP server over `https://your-machine.ts.net`.
  `Tailscale Funnel` can also expose a single HTTPS endpoint if you want
  Claude on the mobile app to reach the MCP server remotely.
- **GitHub Pages**, but only if the repo is public or you're on a paid GitHub
  tier that supports private Pages — don't publish `dashboard/data.json`
  from a public repo, it contains your health data.

## What's genuinely fragile here

- Garmin sync: unofficial, can break on Garmin's schedule, and running it
  from a cloud IP (e.g. GitHub Actions) is more likely to get blocked than a
  home connection — see `garmin-givemydata`'s own notes on this.
- Hevy and intervals.icu syncs: both official APIs, much more stable.

## Future work

- **A real mobile layout for the dashboard.** `index.html` has basic
  responsive CSS (the grid collapses to one column, tiles go 2-wide under
  860px), but it hasn't been designed for phone use — no touch-friendly
  sizing pass, no thought given to what matters most on a small screen.
  Reachability from a phone is already solved (see "Phone access" above);
  what's missing is the UX itself.
- **Hevy sync.** Currently skipped entirely — `sync_now`/`sync_all.py`
  always reports `hevy: FAILED: HEVY_API_KEY is not set`, and
  `strength_sessions`/`strength_sets` stay empty, since the official API
  needs a Hevy Pro subscription. Two ways to unblock it: subscribe to Pro
  and `src/hevy_sync.py` already works against the real API as written, or
  build a CSV importer against Hevy's free-tier "Export Data" feature
  instead (different shape — manual/periodic export instead of a live API
  pull, so `sync_all.py`/`sync_now` couldn't trigger it automatically).
