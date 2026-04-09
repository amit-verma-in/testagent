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
