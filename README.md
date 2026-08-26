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
│   └── index.html         # static Chart.js dashboard reading data.json
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
   python scripts/sync_all.py
   ```

5. **Verify the Garmin adapter against your real data.** `garmin-givemydata`'s
   export format can shift between versions, and I built the column mapping
   in `garmin_sync.py` from its documentation rather than a live export (I
   don't have network access in this environment to test against your
   account). The first time you run it:
   ```bash
   python -m src.garmin_sync --inspect
   ```
   This prints the raw export structure without writing to the DB, so you can
   confirm (or fix) the field mapping in `GARMIN_FIELD_MAP` near the top of
   the file before the real sync runs.

6. **View the dashboard.** Browsers block `fetch()` on files opened directly
   (`file://`), so serve it:
   ```bash
   python dashboard/generate_data.py   # writes dashboard/data.json
   cd dashboard && python -m http.server 8080
   # open http://localhost:8080
   ```
   `scripts/sync_all.py` already regenerates `data.json` after every sync.

7. **Add the MCP server to Claude Desktop / Claude Code** — see
   `mcp_server/README.md` for the config snippet.

8. **Schedule it.** A cron job (or launchd/systemd timer) calling
   `scripts/sync_all.py` once or twice a day keeps everything current:
   ```
   0 6,20 * * * cd /path/to/athlete-hub && .venv/bin/python scripts/sync_all.py >> sync.log 2>&1
   ```

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
