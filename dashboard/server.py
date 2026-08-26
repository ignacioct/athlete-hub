#!/usr/bin/env python3
"""
Serves the dashboard (static files) and a POST /api/sync endpoint that runs
scripts/sync_all.py on demand. This exists instead of a cron job — the sync
machine isn't guaranteed to be on 24/7 — so syncing happens whenever you're
actually looking at the dashboard (or ask Claude, via the MCP server's
sync_now tool) rather than on a schedule.

Run:
    uv run dashboard/server.py [port]   # defaults to 8080
"""

import http.server
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent
SYNC_SCRIPT = ROOT / "scripts" / "sync_all.py"
SYNC_TIMEOUT_S = 180


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_POST(self):
        if self.path != "/api/sync":
            self.send_error(404)
            return

        try:
            proc = subprocess.run(
                [sys.executable, str(SYNC_SCRIPT), "--days", "7"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=SYNC_TIMEOUT_S,
            )
            ok = proc.returncode == 0
            output = (proc.stdout + proc.stderr)[-4000:]
        except subprocess.TimeoutExpired:
            ok = False
            output = f"sync timed out after {SYNC_TIMEOUT_S}s"

        body = json.dumps({"ok": ok, "output": output}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # SimpleHTTPRequestHandler logs every request to stderr by default;
        # keep it, just routed through print() so it's consistent if this
        # is ever run under something that captures stdout only.
        print(f"{self.address_string()} - {format % args}")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    with http.server.ThreadingHTTPServer(("", port), Handler) as httpd:
        print(f"Dashboard + sync endpoint on http://localhost:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
