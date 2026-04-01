from pathlib import Path
import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from .mcp_toolsets import build_mcp_toolsets, include_github_mcp

load_dotenv(Path(__file__).resolve().parent / ".env")

MODEL_NAME = os.environ.get("ADK_MODEL", "gemini-3.1-pro-preview").strip()

_github_hint = ""
if include_github_mcp():
    _github_hint = (
        " You may also use tools prefixed with `github_` when they add necessary "
        "repository context; prefer pattern catalog for module discovery."
    )

root_agent = Agent(
    name="devops_builder",
    model=MODEL_NAME,
    tools=build_mcp_toolsets(),
    instruction=(
        "You are an experienced DevOps agent. Your goal is to create boilerplate "
        "Terraform using the Pattern Catalog MCP: use only tools whose names start "
        "with `pattern_catalog_` to search modules, versions, examples, validation, "
        "and related catalog metadata. Do not substitute public GitHub search or "
        "generic web browsing for catalog-backed module discovery."
        + _github_hint
        + " Produce Terraform files and a readme.md: first, how to run the "
        "configuration; then a 'Context & Background' section; cite catalog-backed "
        "sources and any URLs returned by the tools."
    ),
)
