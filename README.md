# athlete-hub

Centralizes your Garmin (Forerunner 255 + Circa), Hevy, and running-club (via
TrainingPeaks → Garmin) data into one local database, exposes it to Claude
through an MCP server so you can ask questions and plan ahead, and gives you
a lightweight dashboard.

## Why it's built this way

| Source | Reality | What this repo does |
|---|---|---|
| Garmin Connect | No personal API exists. Garmin only grants API access to approved companies. Every "Garmin API" you'll find (including the one this repo wraps) is unofficial and can break when Garmin changes something. | `src/garmin_sync.py` wraps [`garmin-givemydata`](https://github.com/nrvim/garmin-givemydata), the current best-maintained unofficial exporter, and normalizes its output into our schema. |
| TrainingPeaks | Personal API access isn't available — TrainingPeaks only approves commercial partners. | Not integrated directly. Your club's uploads already sync into Garmin Connect, so completed workouts arrive via the regular Garmin sync for free. *Planned* future workouts from the club's plan are a separate story — see `fetch_future_workout_schedule()` in "What's genuinely fragile here" below. |
| Hevy | Has a real, documented, official API — but it's Pro-only, and this account isn't Pro. | `src/hevy_sync.py` uses [`hevy-unofficial`](https://pypi.org/project/hevy-unofficial/) instead, a reverse-engineered client for the same private API the mobile app uses, authenticated via a session token instead of an API key. See "What's genuinely fragile here" — this is a much less proven dependency than the others. |
| intervals.icu | Free account, full official REST API, and it already has a mature, reliable two-way Garmin sync — including pushing planned/structured workouts to your watch. | Used for two jobs: (1) a second read of your running data with training-load metrics (CTL/ATL/TSB) already computed, and (2) the **write path** — this repo creates workouts here, and intervals.icu's existing Garmin sync gets them onto your Forerunner. We deliberately don't try to write to Garmin directly; that path is far less reliable. |

**You'll need a free intervals.icu account** with your Garmin connected there
(Settings → Connections → tick "Upload planned workouts"). That single
integration is what makes the "create a workout, get it on my watch" loop
work without touching Garmin's unofficial write endpoints at all.

## Project layout

```
athlete-hub/
├── src/
│   ├── db.py                # SQLite schema + connection helper
│   ├── garmin_sync.py       # Garmin -> unified DB (via garmin-givemydata)
│   ├── hevy_sync.py         # Hevy -> unified DB (via hevy-unofficial)
│   ├── intervals_sync.py    # intervals.icu -> unified DB, and DB -> intervals.icu (workout push)
│   ├── races.py             # CRUD for upcoming races
│   ├── weekly_workouts.py   # planned-vs-actual view of the current week (shared: dashboard + MCP)
│   └── strength_progress.py # PPL split status, estimated 1RM history, recent PRs (shared: dashboard + MCP)
├── mcp_server/
│   ├── server.py           # MCP server: exposes the DB + workout creation to Claude
│   └── README.md           # how to connect it to Claude Desktop / Claude Code
├── scripts/
│   ├── sync_all.py         # run every sync in order
│   ├── seed_races.py       # one-time bulk import from config/races.yaml
│   └── hevy_login.py       # one-time manual token capture for Hevy (see its docstring)
├── dashboard/
│   ├── generate_data.py    # DB -> data.json snapshot
│   ├── server.py           # serves the dashboard + POST /api/sync ("Sync now" button)
│   ├── index.html          # Chart.js dashboard reading data.json
│   └── vendor/              # self-hosted Chart.js (no CDN dependency)
├── config/
│   └── races.yaml          # example seed file for races.py
└── data/                   # athlete.db lives here (gitignored)
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
   - `HEVY_EMAIL` — your Hevy account email. Also run `python scripts/hevy_login.py`
     once (see that file's docstring) — Hevy isn't Pro-gated here, but does need a
     one-time manual token capture; see "What's genuinely fragile here".
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

**Status:** Tailscale is set up and works for reaching the dashboard from a
phone browser — the sync machine and phone are on the same tailnet, and
`dashboard/server.py` already binds to all interfaces, so no code changes
were needed for that part.

Claude's mobile/web app is a separate problem, though: custom connectors are
called from Anthropic's cloud infrastructure, not from your phone, so
Tailscale-only access doesn't work for the MCP server — it needs to be
reachable from the public internet (`Tailscale Funnel`), which also means it
needs real authentication first, since `mcp_server/server.py` currently has
none. That work (a bearer-token `TokenVerifier` + `AuthSettings`, switching
to `transport="streamable-http"`, then funneling it) was started and paused
on the `feature/mobile-mcp-access` branch.

## What's genuinely fragile here

- Garmin sync: unofficial, can break on Garmin's schedule, and running it
  from a cloud IP (e.g. GitHub Actions) is more likely to get blocked than a
  home connection — see `garmin-givemydata`'s own notes on this.
- `garmin_sync.fetch_future_workout_schedule()` (powers the "this week's
  workouts" panel's view into your club's TrainingPeaks -> Garmin plan): the
  most fragile thing in this repo. `garmin-givemydata`'s own CLI can't fetch
  future-dated anything (every fetch mode hardcodes `end_date=today`), so
  this reaches into `garmin_client.GarminClient`'s *private*
  `_fetch_batch()` method — underscore-prefixed, not a public API — to run
  one extra GraphQL query with a future end date. It's wrapped so a failure
  here never breaks the rest of the sync, but if `garmin_client`'s internals
  change, this specific feature silently stops working until someone
  updates it.
- `src/hevy_sync.py`: uses `hevy-unofficial`, a reverse-engineered client
  with **0 GitHub stars/forks, 6 commits, alpha version, one maintainer** —
  no track record at all compared to `garmin-givemydata`. If Hevy changes
  their private API, there's no community to notice or patch it; that falls
  on us. Also: its automated Playwright browser login doesn't work for a
  Google-linked Hevy account — Google detects and blocks OAuth sign-ins
  from automated browsers. `scripts/hevy_login.py` works around this with a
  fully manual flow (log in normally in your own browser, copy one cookie
  value) that Google has no reason to block. `/user_workouts_paged` also
  silently 400s if `limit` is set above 5 — undocumented, found by testing;
  `PAGE_SIZE = 5` in `hevy_sync.py` is not arbitrary. If this dependency
  ever breaks and doesn't get fixed upstream, the fallback is a CSV
  importer against Hevy's free-tier "Export Data" feature instead —
  different shape (manual/periodic export instead of a live API pull, so
  `sync_all.py`/`sync_now` couldn't trigger it automatically), but zero
  reverse-engineering risk.
- intervals.icu sync: official API, stable.

## Future work

- **A real mobile layout for the dashboard.** `index.html` has basic
  responsive CSS (the grid collapses to one column, tiles go 2-wide under
  860px), but it hasn't been designed for phone use — no touch-friendly
  sizing pass, no thought given to what matters most on a small screen.
  Reachability from a phone is already solved (see "Phone access" above);
  what's missing is the UX itself.
