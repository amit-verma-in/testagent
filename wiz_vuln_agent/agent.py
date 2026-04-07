"""ADK agent: Wiz MCP + Pattern Catalogue MCP + local Wiz CLI."""

from __future__ import annotations

import json
import os
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import override

from dotenv import load_dotenv

# Repo root (parent of wiz_vuln_agent/). ADK web often uses another cwd, so load .env by path.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv()
from google.adk.agents import LlmAgent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

_OPENAI_TOOL_BUDGET = 128
_FUNCTION_TOOLS = 2
_MCP_TOOL_BUDGET = _OPENAI_TOOL_BUDGET - _FUNCTION_TOOLS

# Native Gemini via Google AI Studio / ADK (same pattern as main branch devops_builder).
_DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"


def _wiz_child_env() -> dict[str, str]:
    """Full environment for MCP child processes (PATH, auth env vars)."""
    return dict(os.environ)


def _mcp_session_timeout_seconds() -> float:
    """Long timeout for mcp-remote OAuth / init (ADK default 5s is too low)."""
    for key in ("MCP_SESSION_TIMEOUT", "WIZ_MCP_SESSION_TIMEOUT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return max(5.0, float(raw))
    return 600.0


def _mcp_remote_stdio_for_url(remote_url: str, env_prefix: str) -> StdioConnectionParams:
    """stdio bridge: npx mcp-remote <url> (OAuth in browser; tokens under ~/.mcp-auth)."""
    args: list[str] = ["-y", "mcp-remote", remote_url]
    oauth_port = (os.environ.get(f"{env_prefix}REMOTE_OAUTH_PORT") or "").strip()
    if oauth_port.isdigit():
        args.append(oauth_port)
    resource = (os.environ.get(f"{env_prefix}REMOTE_RESOURCE") or "").strip()
    if resource:
        args.extend(["--resource", resource])
    extra = (os.environ.get(f"{env_prefix}REMOTE_EXTRA_ARGS") or "").strip()
    if extra:
        args.extend(shlex.split(extra))
    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=(os.environ.get("WIZ_MCP_NPX") or "npx").strip(),
            args=args,
            env=_wiz_child_env(),
        ),
        timeout=_mcp_session_timeout_seconds(),
    )


def _wiz_connection_params() -> StdioConnectionParams | StreamableHTTPConnectionParams:
    if (os.environ.get("WIZ_MCP_REMOTE_URL") or "").strip():
        return _mcp_remote_stdio_for_url(
            (os.environ.get("WIZ_MCP_REMOTE_URL") or "").strip(),
            "WIZ_MCP_",
        )
    url = (os.environ.get("WIZ_MCP_URL") or "").strip()
    if url:
        headers: dict | None = None
        raw_headers = (os.environ.get("WIZ_MCP_HEADERS_JSON") or "").strip()
        if raw_headers:
            headers = json.loads(raw_headers)
        return StreamableHTTPConnectionParams(
            url=url,
            headers=headers,
            timeout=_mcp_session_timeout_seconds(),
        )
    command = (os.environ.get("WIZ_MCP_COMMAND") or "npx").strip()
    args_line = (os.environ.get("WIZ_MCP_ARGS") or "").strip()
    if not args_line:
        raise ValueError(
            "Configure Wiz MCP in your project .env (loaded from "
            f"{_PROJECT_ROOT / '.env'}). Set WIZ_MCP_REMOTE_URL (mcp-remote), or "
            "WIZ_MCP_URL + WIZ_MCP_HEADERS_JSON, or WIZ_MCP_ARGS + optional WIZ_MCP_COMMAND. "
            "See env.example. Docs: https://docs.wiz.io/docs/set-up-wiz-mcp-server"
        )
    args = shlex.split(args_line)
    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=command,
            args=args,
            env=_wiz_child_env(),
        ),
        timeout=_mcp_session_timeout_seconds(),
    )


def _patcat_mcp_configured() -> bool:
    return bool(
        (os.environ.get("PATCAT_MCP_REMOTE_URL") or "").strip()
        or (os.environ.get("PATCAT_MCP_URL") or "").strip()
    )


def _patcat_connection_params() -> StdioConnectionParams | StreamableHTTPConnectionParams:
    if not _patcat_mcp_configured():
        raise ValueError("Pattern Catalogue MCP is not configured (set PATCAT_MCP_REMOTE_URL or PATCAT_MCP_URL).")
    if (os.environ.get("PATCAT_MCP_REMOTE_URL") or "").strip():
        return _mcp_remote_stdio_for_url(
            (os.environ.get("PATCAT_MCP_REMOTE_URL") or "").strip(),
            "PATCAT_MCP_",
        )
    url = (os.environ.get("PATCAT_MCP_URL") or "").strip()
    if not url:
        raise ValueError(
            "Set PATCAT_MCP_REMOTE_URL (recommended, same as Wiz: mcp-remote + OAuth) "
            "or PATCAT_MCP_URL for direct HTTP MCP."
        )
    headers: dict | None = None
    raw_headers = (os.environ.get("PATCAT_MCP_HEADERS_JSON") or "").strip()
    if raw_headers:
        headers = json.loads(raw_headers)
    return StreamableHTTPConnectionParams(
        url=url,
        headers=headers,
        timeout=_mcp_session_timeout_seconds(),
    )


_AGENT_INSTRUCTION = """You are an assistant for cloud security and Terraform delivery using:
1) **Wiz** (MCP + optional Wiz CLI) for vulnerabilities, posture, and IaC scanning,
2) **Pattern Catalogue** (internal MCP) for Terraform using approved AVM / internal modules,
3) **Local Wiz CLI tools** for scanning directories and cloned Git repos.

**Greetings (hi, hello, good morning, what can you do):**
Reply briefly and list these **capabilities** (you may phrase naturally):
- Write or extend **Terraform for AWS and Azure** using **Pattern Catalogue MCP tools** (internal modules, conventions from the server).
- Query **Wiz via MCP** for cloud security issues, vulnerabilities, and posture (use the Wiz MCP tool names/schemas you receive).
- **Scan local Terraform/IaC** with `scan_local_terraform_code` or **clone and scan a public HTTPS Git repo** with `scan_github_terraform_repository` (Wiz CLI on the host).

**Terraform authoring (create / build / scaffold AWS or Azure infra):**
- Prefer **Pattern Catalogue MCP tools** first: discover modules and parameters from the tools the PatCat server exposes, then generate Terraform that matches those patterns.
- Do not invent module sources or APIs that the tools do not support; if something is missing, say so and suggest what to ask in Pattern Catalogue or your platform docs.
- When the user wants **security validation**, offer or run **Wiz CLI scan** on the path they specify (or after they save files under an allowed root).

**Wiz MCP (cloud / platform data):**
- For vulnerabilities, issues, exposure, compliance: call the relevant **Wiz MCP** tools; ground answers in tool output only.

**Local / GitHub scans (Wiz CLI):**
- Use `scan_local_terraform_code` / `scan_github_terraform_repository` as documented in your tools; then summarize with severity, affected resources, and remediation from scan output.

Stay concise unless the user asks for depth."""


def _use_openai_backend() -> bool:
    """Use LiteLLM only when targeting an OpenAI-compatible gateway.

    Set ``LLM_PROVIDER=gemini`` and ``GOOGLE_API_KEY`` (and optionally ``ADK_MODEL``)
    to use Gemini Pro via Google ADK + AI Studio, matching main branch ``devops_builder``.
    """
    p = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if p == "gemini":
        return False
    if p in ("openai", "oai", "litellm"):
        return True
    has_google = bool((os.environ.get("GOOGLE_API_KEY") or "").strip())
    has_openai_key = bool((os.environ.get("OPENAI_API_KEY") or "").strip())
    if has_google and not has_openai_key:
        return False
    if has_openai_key:
        return True
    if (os.environ.get("OPENAI_BASE_URL") or "").strip():
        return True
    return False


def _openai_mcp_unlimited() -> bool:
    return (os.environ.get("OPENAI_MAX_MCP_TOOLS") or "").strip().lower() in (
        "0",
        "none",
        "off",
        "unlimited",
    )


def _resolve_llm_model():
    """Gemini model id for ADK, or LiteLlm for OpenAI-compatible gateways."""
    if not _use_openai_backend():
        return (os.environ.get("ADK_MODEL") or _DEFAULT_GEMINI_MODEL).strip()

    from google.adk.models.lite_llm import LiteLlm

    raw = (
        os.environ.get("OPENAI_MODEL")
        or os.environ.get("LITELLM_MODEL")
        or "gpt-4o-mini"
    ).strip()
    if "/" in raw:
        model_name = raw
    else:
        model_name = f"openai/{raw}"

    kwargs: dict = {}
    base = (os.environ.get("OPENAI_BASE_URL") or "").strip()
    if base:
        kwargs["api_base"] = base
    return LiteLlm(model=model_name, **kwargs)


def _wiz_tool_filter_from_env() -> list[str] | None:
    raw = (os.environ.get("WIZ_MCP_TOOL_FILTER") or "").strip()
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


def _patcat_tool_filter_from_env() -> list[str] | None:
    raw = (os.environ.get("PATCAT_MCP_TOOL_FILTER") or "").strip()
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


def _openai_patcat_mcp_cap() -> int | None:
    if not _use_openai_backend() or not _patcat_mcp_configured():
        return None
    if _openai_mcp_unlimited():
        return None
    raw = (os.environ.get("OPENAI_MAX_PATCAT_MCP_TOOLS") or "").strip().lower()
    if raw in ("none", "unlimited", "0"):
        return None
    ex = (os.environ.get("OPENAI_MAX_PATCAT_MCP_TOOLS") or "").strip()
    if ex:
        return max(1, min(int(ex), _MCP_TOOL_BUDGET))
    return min(48, _MCP_TOOL_BUDGET)


def _openai_wiz_mcp_cap() -> int | None:
    if not _use_openai_backend():
        return None
    if _openai_mcp_unlimited():
        return None
    ex = (os.environ.get("OPENAI_MAX_WIZ_MCP_TOOLS") or "").strip()
    if ex:
        return max(1, min(int(ex), _MCP_TOOL_BUDGET))
    pat = _openai_patcat_mcp_cap()
    if pat is not None:
        return max(1, _MCP_TOOL_BUDGET - pat)
    legacy = (os.environ.get("OPENAI_MAX_MCP_TOOLS") or "").strip()
    if legacy and legacy.lower() not in ("128", "none", "unlimited", "0", "off"):
        try:
            return max(1, min(int(legacy) - _FUNCTION_TOOLS, _MCP_TOOL_BUDGET))
        except ValueError:
            pass
    return _MCP_TOOL_BUDGET


def _mcp_tool_sort_key_wiz(tool: BaseTool) -> tuple:
    name = (tool.name or "").lower()
    keywords = (
        "vuln",
        "cve",
        "issue",
        "threat",
        "finding",
        "security",
        "compliance",
        "resource",
        "inventory",
        "posture",
        "misconfig",
        "exposure",
        "attack",
        "graph",
        "query",
    )
    for i, kw in enumerate(keywords):
        if kw in name:
            return (0, i, name)
    return (1, 0, name)


def _mcp_tool_sort_key_patcat(tool: BaseTool) -> tuple:
    name = (tool.name or "").lower()
    keywords = (
        "terraform",
        "module",
        "avm",
        "pattern",
        "catalog",
        "aws",
        "azure",
        "azurerm",
        "ec2",
        "s3",
        "vpc",
        "aks",
        "storage",
    )
    for i, kw in enumerate(keywords):
        if kw in name:
            return (0, i, name)
    return (1, 0, name)


class _SortedCappedMcpToolset(McpToolset):
    """Caps tool count for OpenAI; keeps highest-priority tools first."""

    def __init__(
        self,
        *,
        max_tools: int,
        tool_sort_key: Callable[[BaseTool], tuple],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._max_tools_cap = max_tools
        self._tool_sort_key = tool_sort_key

    @override
    async def get_tools(self, readonly_context=None):
        tools = await super().get_tools(readonly_context)
        if len(tools) <= self._max_tools_cap:
            return tools
        tools = sorted(tools, key=self._tool_sort_key)
        return tools[: self._max_tools_cap]


def _wizcli_function_tools() -> list[FunctionTool]:
    from .wizcli_tools import (
        scan_github_terraform_repository,
        scan_local_terraform_code,
    )

    return [
        FunctionTool(scan_local_terraform_code),
        FunctionTool(scan_github_terraform_repository),
    ]


def _build_wiz_mcp_toolset() -> McpToolset:
    params = _wiz_connection_params()
    tf = _wiz_tool_filter_from_env()
    kwargs: dict = {"connection_params": params}
    if tf is not None:
        kwargs["tool_filter"] = tf
    cap = _openai_wiz_mcp_cap()
    if cap is not None:
        return _SortedCappedMcpToolset(
            max_tools=cap,
            tool_sort_key=_mcp_tool_sort_key_wiz,
            **kwargs,
        )
    return McpToolset(**kwargs)


def _build_patcat_mcp_toolset() -> McpToolset | None:
    if not _patcat_mcp_configured():
        return None
    params = _patcat_connection_params()
    tf = _patcat_tool_filter_from_env()
    kwargs: dict = {"connection_params": params}
    if tf is not None:
        kwargs["tool_filter"] = tf
    cap = _openai_patcat_mcp_cap()
    if cap is not None:
        return _SortedCappedMcpToolset(
            max_tools=cap,
            tool_sort_key=_mcp_tool_sort_key_patcat,
            **kwargs,
        )
    return McpToolset(**kwargs)


def _all_agent_tools() -> list:
    tools: list = [*_wizcli_function_tools(), _build_wiz_mcp_toolset()]
    pat = _build_patcat_mcp_toolset()
    if pat is not None:
        tools.append(pat)
    return tools


root_agent = LlmAgent(
    model=_resolve_llm_model(),
    name="wiz_patcat_assistant",
    instruction=_AGENT_INSTRUCTION,
    tools=_all_agent_tools(),
)
