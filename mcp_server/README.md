# Connecting the MCP server to Claude

## Claude Desktop / Claude Code (local, works today)

Add to your MCP config (`claude_desktop_config.json`, or `.mcp.json` for
Claude Code):

```json
{
  "mcpServers": {
    "athlete-hub": {
      "command": "/absolute/path/to/athlete-hub/.venv/bin/python",
      "args": ["/absolute/path/to/athlete-hub/mcp_server/server.py"]
    }
  }
}
```

No `env` block needed — `.env` is found automatically (python-dotenv walks up from
`src/intervals_sync.py`'s own location to the project root), regardless of what
working directory the MCP host launches the server from.

Restart Claude Desktop / Claude Code after editing. You should then be able
to ask things like "how has my resting HR trended over the last month?" or
"add the Valencia Marathon on Dec 6 as an A race, goal 3:30" directly in
chat, and Claude will call these tools.

## Phone / Claude mobile app

The mobile app needs an HTTPS URL, not a local stdio process. The
lower-effort path here is **Tailscale Funnel**: run the MCP server as an
HTTP server (FastMCP supports `mcp.run(transport="streamable-http")`) on
your always-on sync machine, expose it with `tailscale funnel`, and add that
URL as a custom connector in Claude's settings. This keeps the data off the
public internet — only devices on your tailnet (or explicitly funneled) can
reach it.

This is a reasonable "phase 2" once the local setup is working — start
local, add remote access once you trust the sync pipeline.
