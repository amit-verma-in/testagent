# testagent — Wiz & Pattern Catalogue ADK agent

This repository hosts a **Google ADK** (`adk web`) agent that combines **Wiz** (cloud security), an internal **Pattern Catalogue** MCP server (Terraform patterns and modules), **local Wiz CLI** scans, and **on-disk file tools** for generated artifacts.

The agent package lives in `wiz_vuln_agent/` and exposes `root_agent` as `wiz_vuln_agent.agent:root_agent`.

## What it can do

- **Wiz MCP** — Query Wiz for vulnerabilities, posture, inventory, and related security data (tool names depend on your Wiz MCP server).
- **Pattern Catalogue MCP** — Discover and apply approved Terraform patterns and modules (configure your internal MCP endpoint).
- **Wiz CLI** — Scan local Terraform/IaC directories or clone a public HTTPS Git repo and scan it (`scan_local_terraform_code`, `scan_github_terraform_repository`). Requires the `wizcli` binary on `PATH` and Wiz authentication (see below).
- **Local workspace** — Write, read, and list files under a configurable output directory (default: `agent_output/` at the repo root).

## Prerequisites

- **Python 3.10+** recommended.
- **Node.js** with `npx` if you use `mcp-remote` for Wiz or Pattern Catalogue (OAuth in the browser; tokens are stored under `~/.mcp-auth` by the remote helper).
- **Wiz CLI** (optional, for local/Git scans): install from vendor docs, e.g. macOS `brew install --cask wizcli`. Do not `pip install wizcli` — the PyPI name is unrelated.

## Setup

1. Clone or copy this repo and open a terminal at the **repository root** (the directory that contains `wiz_vuln_agent/`).

2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure environment variables. Copy `env.example` to `.env` at the **repo root** and edit:

   ```bash
   cp env.example .env
   ```

4. Add MCP and model settings to `.env`. At minimum you typically set:

   - **Gemini (recommended for this project):** `GOOGLE_API_KEY`, optionally `ADK_MODEL` (default in code is `gemini-2.5-pro`). Set `LLM_PROVIDER=gemini` if you also have `OPENAI_API_KEY` set but want Gemini.
   - **OpenAI-compatible API:** `OPENAI_API_KEY` and optionally `OPENAI_BASE_URL`, `OPENAI_MODEL` / `LITELLM_MODEL`.

5. **Wiz MCP** — Set one of the following (see comments in `wiz_vuln_agent/agent.py` for full options):

   - `WIZ_MCP_REMOTE_URL` — e.g. Wiz’s remote MCP URL; uses `npx mcp-remote` and OAuth.
   - Or `WIZ_MCP_URL` + optional `WIZ_MCP_HEADERS_JSON` for streamable HTTP.
   - Or `WIZ_MCP_COMMAND` / `WIZ_MCP_ARGS` for a custom stdio MCP command.

6. **Pattern Catalogue MCP** — Set `PATCAT_MCP_REMOTE_URL` (same `mcp-remote` pattern as Wiz) or `PATCAT_MCP_URL` with optional `PATCAT_MCP_HEADERS_JSON`.

## Run the ADK web UI

Run **`adk web` from the parent of the agent package folder** so ADK discovers the agent module:

```bash
cd /path/to/testagent    # repo root
source .venv/bin/activate
adk web
```

Or use the helper script (creates/uses `.venv`, sets `SSL_CERT_FILE` via `certifi`, then runs `adk web`):

```bash
./run_adk_web.sh
```

Pass extra `adk web` arguments through the script: `./run_adk_web.sh --port 8000`.

In the ADK UI, select the app/module that maps to **`wiz_vuln_agent.agent`** (agent name in code: `wiz_patcat_assistant`).

## Wiz CLI authentication

`wizcli` is invoked on the host; it does **not** read MCP OAuth tokens from `~/.mcp-auth` as bearer credentials. For scans, authenticate the CLI the way Wiz documents, for example:

- **Device code:** `wizcli auth --use-device-code` (or follow current `wizcli auth --help`), or  
- **Service account:** set `WIZ_CLIENT_ID` and `WIZ_CLIENT_SECRET` where your shell runs the agent / `adk web`.
- `wizcli scan dir --use-device-code --no-publish`

Scan paths must stay under allowed roots (project root and `.wiz_scan_work` by default, or paths listed in `WIZCLI_ALLOWED_SCAN_ROOTS`). See `wiz_vuln_agent/wizcli_tools.py` for timeouts and other `WIZCLI_*` options.

## Local output directory

By default, `write_local_workspace_file` and related tools write under **`agent_output/`** at the repo root. Override with `AGENT_LOCAL_OUTPUT_DIR` in `.env`. Optional: `AGENT_LOCAL_FILE_MAX_BYTES`.

## Repository layout (high level)

| Path | Purpose |
|------|---------|
| `wiz_vuln_agent/agent.py` | ADK `LlmAgent`, MCP toolsets, instruction text |
| `wiz_vuln_agent/wizcli_tools.py` | Wiz CLI scan helpers |
| `wiz_vuln_agent/local_workspace_tools.py` | Read/write/list under the local output dir |
| `requirements.txt` | Python dependencies |
| `env.example` | Example `.env` keys for LLM + local tools |
| `run_adk_web.sh` | Convenience launcher for `adk web` |
| `agent_output/` | Default on-disk output for generated Terraform/docs (gitignored if configured) |

## Documentation links

- [Wiz CLI](https://docs.wiz.io/wiz-cli/)
- [Set up Wiz MCP server](https://docs.wiz.io/docs/set-up-wiz-mcp-server) (Wiz)

## Security note

Do not commit `.env`, API keys, or real tenant secrets. Sample Terraform under `agent_output/terraform/` may include **intentionally vulnerable** examples for scanner testing only; review before any real deployment.
