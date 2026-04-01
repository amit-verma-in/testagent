"""MCP toolsets: read URLs/headers from ~/.cursor/mcp.json, with optional .env overrides."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

logger = logging.getLogger(__name__)

DEFAULT_PATTERN_CATALOG_MCP_URL = "https://patcat.avm.mckinsey.com/"
DEFAULT_GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


def _cursor_mcp_json_path() -> Path:
    override = os.environ.get("CURSOR_MCP_JSON", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cursor" / "mcp.json"


def _load_cursor_mcp_servers() -> dict[str, dict[str, Any]]:
    path = _cursor_mcp_json_path()
    if not path.is_file():
        logger.info("Cursor MCP config not found at %s", path)
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.warning("Could not parse %s, using env/defaults only: %s", path, e)
        return {}
    servers = raw.get("mcpServers")
    if not isinstance(servers, dict):
        return {}
    return {str(k): v for k, v in servers.items() if isinstance(v, dict)}


def _normalize_headers(value: Any) -> dict[str, str]:
    if not value or not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in value.items():
        if v is None:
            continue
        out[str(k)] = str(v)
    return out


def _server_cfg(
    servers: dict[str, dict[str, Any]], *names: str
) -> dict[str, Any] | None:
    for name in names:
        entry = servers.get(name)
        if isinstance(entry, dict):
            return entry
    return None


def _http_url_from_entry(entry: dict[str, Any] | None) -> str | None:
    if not entry:
        return None
    url = entry.get("url")
    return url.strip() if isinstance(url, str) else None


def _pattern_catalog_has_auth(entry: dict[str, Any] | None) -> bool:
    headers = _normalize_headers(entry.get("headers") if entry else None)
    if headers.get("Authorization", "").strip():
        return True
    if os.environ.get("PATTERN_CATALOG_AUTHORIZATION", "").strip():
        return True
    if os.environ.get("PATTERN_CATALOG_ACCESS_TOKEN", "").strip():
        return True
    return False


def _env_flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def include_github_mcp() -> bool:
    return _env_flag("INCLUDE_GITHUB_MCP", default=False)


def build_pattern_catalog_toolset(
    servers: dict[str, dict[str, Any]] | None = None,
) -> McpToolset:
    if servers is None:
        servers = _load_cursor_mcp_servers()
    entry = _server_cfg(servers, "pattern-catalog", "pattern_catalog")
    url = (
        os.environ.get("PATTERN_CATALOG_MCP_URL", "").strip()
        or _http_url_from_entry(entry)
        or DEFAULT_PATTERN_CATALOG_MCP_URL
    )
    headers = _normalize_headers(entry.get("headers") if entry else None)

    if os.environ.get("PATTERN_CATALOG_AUTHORIZATION", "").strip():
        headers["Authorization"] = os.environ["PATTERN_CATALOG_AUTHORIZATION"].strip()
    elif os.environ.get("PATTERN_CATALOG_ACCESS_TOKEN", "").strip():
        headers["Authorization"] = (
            f"Bearer {os.environ['PATTERN_CATALOG_ACCESS_TOKEN'].strip()}"
        )

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url,
            headers=headers if headers else None,
            timeout=60.0,
            sse_read_timeout=600.0,
        ),
        tool_name_prefix="pattern_catalog_",
    )


def build_github_mcp_toolset(
    servers: dict[str, dict[str, Any]] | None = None,
) -> McpToolset:
    if servers is None:
        servers = _load_cursor_mcp_servers()
    entry = _server_cfg(servers, "github")
    url = (
        os.environ.get("GITHUB_MCP_URL", "").strip()
        or _http_url_from_entry(entry)
        or DEFAULT_GITHUB_MCP_URL
    )
    headers = _normalize_headers(entry.get("headers") if entry else None)

    if os.environ.get("GITHUB_MCP_AUTHORIZATION", "").strip():
        headers["Authorization"] = os.environ["GITHUB_MCP_AUTHORIZATION"].strip()
    elif os.environ.get("GITHUB_MCP_TOKEN", "").strip():
        headers["Authorization"] = (
            f"Bearer {os.environ['GITHUB_MCP_TOKEN'].strip()}"
        )

    if not headers.get("Authorization", "").strip():
        raise RuntimeError(
            "GitHub MCP: no Authorization header. Add `github` → `headers` in "
            "~/.cursor/mcp.json, or set GITHUB_MCP_TOKEN / GITHUB_MCP_AUTHORIZATION "
            "in the environment."
        )

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url,
            headers=headers,
            timeout=60.0,
            sse_read_timeout=600.0,
        ),
        tool_name_prefix="github_",
    )


def build_mcp_toolsets() -> list[McpToolset]:
    servers = _load_cursor_mcp_servers()
    toolsets: list[McpToolset] = []

    pattern_entry = _server_cfg(servers, "pattern-catalog", "pattern_catalog")
    if not _pattern_catalog_has_auth(pattern_entry):
        raise RuntimeError(
            "Pattern Catalog MCP requires credentials (the server returns 401 without them). "
            "Set PATTERN_CATALOG_ACCESS_TOKEN or PATTERN_CATALOG_AUTHORIZATION in "
            "devops_builder/.env, or add headers.Authorization under "
            'mcpServers["pattern-catalog"] in ~/.cursor/mcp.json. '
            "Cursor OAuth alone does not expose a token to ADK."
        )

    toolsets.append(build_pattern_catalog_toolset(servers))

    if include_github_mcp():
        toolsets.append(build_github_mcp_toolset(servers))
    else:
        logger.info(
            "GitHub MCP disabled (set INCLUDE_GITHUB_MCP=true to enable). "
            "Using Pattern Catalog MCP only."
        )

    return toolsets
