---
name: update-training-plan
description: Refresh data/training_plan.json from the Notion "Weekly tracker" (Season 2026–27) and regenerate the dashboard. Use when the user says the plan changed in Notion, or asks to update/sync the training plan.
---

# Update the training plan from Notion

The dashboard's "Race build" panel reads planned weekly km from
`data/training_plan.json`. That file is a hand copy of the Notion Weekly
tracker; the code never talks to Notion. This runbook refreshes the copy.

## Steps

1. Query the Weekly tracker through the Notion MCP (`notion-query-data-sources`, SQL mode):

   - Data source: `collection://2008a89f-f3fe-4aff-b5fe-18da1c534562`
   - Query:
     ```sql
     SELECT "date:Week start:start" AS ws, "Planned km", "Planned long run (km)"
     FROM "collection://2008a89f-f3fe-4aff-b5fe-18da1c534562"
     WHERE "Planned km" IS NOT NULL
     ORDER BY ws
     ```
   - If the data source is not found (new season, new database), search Notion
     for "Weekly tracker" under Training / Run, and ask the user which one to use.

2. Rewrite `data/training_plan.json`, keeping the `_source` line. Use one entry per row:
   `"<ws>": {"km": <Planned km>}`, and add `"long": <Planned long run>` only when that value is set.
   Every `ws` must be a Monday. If one is not, stop and tell the user which row is wrong.

3. Run `uv run python dashboard/generate_data.py`, then `uv run python -m tests.test_race_readiness`.

4. Report back:
   - Show the diff of `data/training_plan.json` as a short list of weeks whose planned km or long run changed, were added or were removed. If nothing changed, say so.
   - Show each upcoming race's `readiness` from `dashboard/data.json`, giving its plan peak and its compliance when present.
   - Do not commit unless the user asks.
