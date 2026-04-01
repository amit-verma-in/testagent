# Devops Builder (Google ADK)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure SSL Cert Path

```bash
export SSL_CERT_FILE=$(python -m certifi)
```

## Model availability fallback

If you hit `503 UNAVAILABLE` for `gemini-3.1-pro-preview` during demand spikes, set a temporary fallback in `devops_builder/.env`:

```bash
ADK_MODEL=gemini-2.5-pro
```

## MCP: Pattern Catalog (primary)

By default this agent uses **only** the Pattern Catalog MCP (`pattern_catalog_*` tools). **GitHub MCP is off** unless you set `INCLUDE_GITHUB_MCP=true`.

ADK uses **`McpToolset`** (Streamable HTTP). `devops_builder/mcp_toolsets.py` reads **`~/.cursor/mcp.json`** for `mcpServers["pattern-catalog"]` (**`url`** and **`headers`**), with env overrides.

**You must supply Pattern Catalog auth** (the server returns **401** without it): either `headers.Authorization` on `pattern-catalog` in `mcp.json`, or `PATTERN_CATALOG_ACCESS_TOKEN` / `PATTERN_CATALOG_AUTHORIZATION` in `devops_builder/.env`. Cursor OAuth alone does not inject tokens into ADK.

| Variable | Purpose |
|----------|---------|
| `INCLUDE_GITHUB_MCP` | Set to `true` only if you also want `github_*` MCP tools (default: off) |
| `CURSOR_MCP_JSON` | Alternate MCP JSON path |
| `PATTERN_CATALOG_MCP_URL` | Override Patcat URL |
| `PATTERN_CATALOG_ACCESS_TOKEN` / `PATTERN_CATALOG_AUTHORIZATION` | Catalog auth |
| `GITHUB_*` | Only used when `INCLUDE_GITHUB_MCP=true` |

If tool discovery fails, the server may need **SSE** instead of Streamable HTTP; switch to `SseConnectionParams` in `mcp_toolsets.py` using the same URL and headers.

## Run the Agent in Web UI

ADK discovers agents as **Python packages in subfolders** of the directory you run the command from (not a single `agent.py` at the project root). This repo’s agent package is `devops_builder/`.

From **`testagent/`** (this project’s root—the parent of `devops_builder/`):

```bash
adk web
```

Optional explicit agents directory:

```bash
adk web .
```
