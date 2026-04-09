"""Write and read files under a single agent output directory on the local machine."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _output_root() -> Path:
    raw = (os.environ.get("AGENT_LOCAL_OUTPUT_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (_PROJECT_ROOT / "agent_output").resolve()


def _max_file_bytes() -> int:
    raw = (os.environ.get("AGENT_LOCAL_FILE_MAX_BYTES") or "2097152").strip()
    try:
        return max(1024, int(raw))
    except ValueError:
        return 2097152


def _safe_relative(relative_path: str) -> Path:
    p = Path(relative_path.strip())
    if p.is_absolute():
        raise ValueError("relative_path must be relative, not absolute.")
    parts = p.parts
    if ".." in parts or p.parts[:1] == ("..",):
        raise ValueError("relative_path must not contain '..'.")
    if not parts or parts == (".",):
        raise ValueError("relative_path must include a file or folder name.")
    return Path(*parts)


def _full_path(relative_path: str) -> Path:
    rel = _safe_relative(relative_path)
    return _output_root() / rel


async def write_local_workspace_file(
    relative_path: str,
    content: str,
    create_directories: bool = True,
) -> dict[str, Any]:
    """Write text to a file under the agent output directory (local disk).

    Default root is ``<project>/agent_output/``. Override with ``AGENT_LOCAL_OUTPUT_DIR``.

    Args:
        relative_path: Path relative to that root, e.g. ``terraform/main.tf`` or ``README.md``.
        content: Full file contents (UTF-8).
        create_directories: If True, create parent directories as needed.

    Returns:
        Status dict with absolute path written, or error message.
    """
    root = _output_root()
    max_b = _max_file_bytes()
    if len(content.encode("utf-8")) > max_b:
        return {
            "ok": False,
            "error": f"Content exceeds AGENT_LOCAL_FILE_MAX_BYTES ({max_b}).",
        }

    try:
        target = _full_path(relative_path)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    try:
        target.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "Resolved path escapes output root."}

    def _write() -> None:
        if create_directories:
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    try:
        await asyncio.to_thread(_write)
    except OSError as e:
        return {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "path": str(target),
        "bytes_written": len(content.encode("utf-8")),
        "output_root": str(root),
    }


def _default_pattern_catalog_md(relative_directory: str) -> str:
    rel = relative_directory.strip().rstrip("/")
    return f"""# Pattern Catalogue alignment

Terraform in this folder was produced with **Pattern Catalogue** conventions in mind.
Use internal modules and sources returned by the Pattern Catalogue MCP tools for your organization.

## Next steps (agent workflow)

1. Use **Pattern Catalogue** MCP tools in this agent to confirm module sources, versions, and parameters.
2. Replace or refine raw resources with `module` blocks per catalog guidance where applicable.
3. Run `terraform fmt` and `terraform validate` locally.
4. Optionally run `scan_local_terraform_code` on this folder after Wiz CLI authentication.

Output folder (relative to agent output root): `{rel}/`
"""


async def write_terraform_stack(
    output_relative_directory: str,
    main_tf: str,
    variables_tf: str,
    outputs_tf: str,
    readme_md: str,
    pattern_catalog_md: str | None = None,
) -> dict[str, Any]:
    """Write a complete Terraform stack under one folder in the agent output directory.

    Use this when authoring Terraform from **Pattern Catalogue** (or firm module) workflows so
    outputs match the standard layout: one directory containing ``main.tf``, ``variables.tf``,
    ``outputs.tf``, ``README.md``, and ``PATTERN_CATALOG.md`` (see ``agent_output/terraform/ecs-converted-alb``).

    Args:
        output_relative_directory: Directory **relative to the agent output root**, e.g.
            ``terraform/my-ecs-service``. No trailing slash; must not escape the output root.
        main_tf: Contents of ``main.tf``.
        variables_tf: Contents of ``variables.tf``.
        outputs_tf: Contents of ``outputs.tf``.
        readme_md: Contents of ``README.md`` (describe the stack, inputs, and how to use it).
        pattern_catalog_md: Optional contents of ``PATTERN_CATALOG.md``. If omitted, a default
            Pattern Catalogue workflow stub is written.

    Returns:
        Status dict with ``ok``, ``files_written`` (absolute paths), ``output_directory_relative``,
        or ``error`` / ``step`` on first failure.
    """
    base = output_relative_directory.strip().rstrip("/")
    if not base or base.endswith((".tf", ".md")):
        return {
            "ok": False,
            "error": "output_relative_directory must be a directory path (e.g. terraform/my-stack), not a file.",
        }

    pat = pattern_catalog_md if pattern_catalog_md is not None else _default_pattern_catalog_md(base)

    files: list[tuple[str, str]] = [
        ("main.tf", main_tf),
        ("variables.tf", variables_tf),
        ("outputs.tf", outputs_tf),
        ("README.md", readme_md),
        ("PATTERN_CATALOG.md", pat),
    ]

    written: list[str] = []
    for name, content in files:
        rel = f"{base}/{name}"
        r = await write_local_workspace_file(rel, content, create_directories=True)
        if not r.get("ok"):
            return {
                "ok": False,
                "error": r.get("error"),
                "step": name,
                "files_written_so_far": written,
            }
        written.append(r["path"])

    return {
        "ok": True,
        "output_directory_relative": base,
        "files_written": written,
        "output_root": str(_output_root()),
    }


async def read_local_workspace_file(relative_path: str) -> dict[str, Any]:
    """Read a UTF-8 text file from under the agent output directory."""
    try:
        target = _full_path(relative_path)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    root = _output_root()
    try:
        target.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "Path escapes output root."}

    if not target.is_file():
        return {"ok": False, "error": f"Not a file or missing: {target}"}

    max_b = _max_file_bytes()

    def _read() -> str:
        data = target.read_bytes()
        if len(data) > max_b:
            raise ValueError(f"File larger than {max_b} bytes.")
        return data.decode("utf-8")

    try:
        text = await asyncio.to_thread(_read)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except OSError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "path": str(target), "content": text}


async def list_local_workspace_files(
    relative_directory: str = "",
) -> dict[str, Any]:
    """List files and subdirectories under a path inside the agent output directory."""
    root = _output_root()
    if not relative_directory.strip():
        base = root
    else:
        try:
            base = _full_path(relative_directory)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        try:
            base.relative_to(root)
        except ValueError:
            return {"ok": False, "error": "Path escapes output root."}

    if not base.exists():
        return {"ok": False, "error": f"Does not exist: {base}"}
    if not base.is_dir():
        return {"ok": False, "error": f"Not a directory: {base}"}

    def _list() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for child in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            rel = child.relative_to(root)
            out.append(
                {
                    "name": child.name,
                    "relative_path": str(rel).replace("\\", "/"),
                    "is_dir": child.is_dir(),
                }
            )
        return out

    try:
        entries = await asyncio.to_thread(_list)
    except OSError as e:
        return {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "output_root": str(root),
        "directory": str(base),
        "entries": entries,
    }
