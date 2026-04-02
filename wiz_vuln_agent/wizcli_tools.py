"""Local Wiz CLI invocation for Terraform / IaC scans (MCP cannot read the filesystem)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

# Resolved relative to this file's package parent (project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_WORK_DIR = _PROJECT_ROOT / ".wiz_scan_work"


def _wizcli_bin() -> str:
    return (os.environ.get("WIZCLI_BIN") or "wizcli").strip()


def _scan_timeout_seconds() -> float:
    raw = (os.environ.get("WIZCLI_SCAN_TIMEOUT") or "600").strip()
    return max(30.0, float(raw))


def _max_stdout_chars() -> int:
    raw = (os.environ.get("WIZCLI_MAX_OUTPUT_CHARS") or "400000").strip()
    return max(10_000, int(raw))


def _allowed_roots() -> list[Path]:
    raw = (os.environ.get("WIZCLI_ALLOWED_SCAN_ROOTS") or "").strip()
    roots: list[Path] = []
    if raw:
        for part in raw.split(","):
            p = part.strip()
            if p:
                roots.append(Path(p).expanduser().resolve())
    else:
        roots.append(_PROJECT_ROOT.resolve())
    _WORK_DIR.mkdir(parents=True, exist_ok=True)
    roots.append(_WORK_DIR.resolve())
    return roots


def _is_under_allowed_root(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _terraform_scan_args(target_dir: Path, policy_hits: str | None) -> list[str]:
    """Build wizcli argv; override with WIZCLI_SCAN_ARGS_EXTRA (shlex split appended)."""
    import shlex

    cmd = [
        _wizcli_bin(),
        "scan",
        "dir",
        str(target_dir),
        "--types=Terraform",
        "--stdout=json",
    ]
    extra = (os.environ.get("WIZCLI_SCAN_ARGS_EXTRA") or "").strip()
    if extra:
        cmd.extend(shlex.split(extra))
    if policy_hits:
        cmd.append(f"--by-policy-hits={policy_hits}")
    return cmd


def _validate_https_git_url(url: str) -> str:
    u = url.strip().rstrip("/")
    if not u.startswith("https://"):
        raise ValueError("Only https:// Git repository URLs are allowed.")
    if "@" in u.split("://", 1)[-1]:
        raise ValueError("Embedded credentials in URLs are not allowed.")
    if len(u) > 500 or " " in u or "\n" in u:
        raise ValueError("Invalid repository URL.")
    return u


async def _run_wizcli(args: list[str]) -> tuple[int, str, str]:
    timeout = _scan_timeout_seconds()

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ,
        )

    proc = await asyncio.to_thread(_run)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _truncate(text: str) -> tuple[str, bool]:
    cap = _max_stdout_chars()
    if len(text) <= cap:
        return text, False
    return text[:cap] + "\n\n[truncated: set WIZCLI_MAX_OUTPUT_CHARS to raise limit]", True


def _parse_json_loose(blob: str) -> Any | None:
    blob = blob.strip()
    if not blob:
        return None
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


async def scan_local_terraform_code(
    directory_path: str,
    policy_hits: str | None = None,
) -> dict[str, Any]:
    """Scan a local directory for Terraform with Wiz CLI (wizcli). Requires wizcli installed and authenticated.

    Use when the user asks to scan local Terraform/IaC on disk. The path must be under an allowed root
    (project root and .wiz_scan_work by default, or WIZCLI_ALLOWED_SCAN_ROOTS).

    Args:
        directory_path: Absolute path to the folder to scan (e.g. /Users/me/proj/terraform).
        policy_hits: Optional Wiz policy filter, e.g. \"BLOCK\" for --by-policy-hits=BLOCK.

    Returns:
        exit_code, stderr, parsed JSON (if stdout was valid JSON), raw stdout (maybe truncated), and notes.
    """
    roots = _allowed_roots()
    target = Path(directory_path).expanduser()
    if not _is_under_allowed_root(target, roots):
        return {
            "ok": False,
            "error": (
                "Path is not under allowed scan roots. Set WIZCLI_ALLOWED_SCAN_ROOTS to a "
                "comma-separated list of absolute paths, or use a path under the project / .wiz_scan_work."
            ),
            "allowed_roots_hint": [str(r) for r in roots],
            "requested": directory_path,
        }
    if not target.is_dir():
        return {"ok": False, "error": f"Not a directory: {target}"}

    args = _terraform_scan_args(target, policy_hits)
    code, out, err = await _run_wizcli(args)
    out, truncated = _truncate(out)
    parsed = _parse_json_loose(out)
    return {
        "ok": code == 0,
        "exit_code": code,
        "wizcli_command": args,
        "stderr": err.strip(),
        "stdout_truncated": truncated,
        "stdout_json": parsed,
        "stdout_raw": out if parsed is None else None,
    }


async def scan_github_terraform_repository(
    repo_https_url: str,
    branch: str | None = None,
    policy_hits: str | None = None,
) -> dict[str, Any]:
    """Clone a public (or credential-accessible) Git repo via HTTPS and run Wiz Terraform scan on it.

    Requires git on PATH and wizcli installed. Clone depth is 1.

    Args:
        repo_https_url: HTTPS clone URL, e.g. https://github.com/org/repo.git
        branch: Optional branch or tag; default is remote default branch.
        policy_hits: Optional, e.g. \"BLOCK\" for --by-policy-hits=BLOCK.

    Returns:
        Same shape as scan_local_terraform_code plus clone_path used.
    """
    if (os.environ.get("WIZCLI_DISABLE_GITHUB_CLONE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return {
            "ok": False,
            "error": "GitHub clone scans are disabled (WIZCLI_DISABLE_GITHUB_CLONE).",
        }

    try:
        url = _validate_https_git_url(repo_https_url)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    _WORK_DIR.mkdir(parents=True, exist_ok=True)
    clone_name = f"repo_{uuid.uuid4().hex}"
    clone_path = _WORK_DIR / clone_name

    git_cmd = ["git", "clone", "--depth", "1"]
    if branch:
        git_cmd.extend(["--branch", branch])
    git_cmd.extend([url, str(clone_path)])

    def _git_clone() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            git_cmd,
            capture_output=True,
            text=True,
            timeout=_scan_timeout_seconds(),
            env=os.environ,
        )

    try:
        g = await asyncio.to_thread(_git_clone)
        if g.returncode != 0:
            return {
                "ok": False,
                "error": "git clone failed",
                "git_stderr": g.stderr.strip(),
                "git_stdout": g.stdout.strip(),
                "git_command": git_cmd,
            }

        args = _terraform_scan_args(clone_path, policy_hits)
        code, out, err = await _run_wizcli(args)
        out, truncated = _truncate(out)
        parsed = _parse_json_loose(out)
        return {
            "ok": code == 0,
            "exit_code": code,
            "clone_path": str(clone_path),
            "git_command": git_cmd,
            "wizcli_command": args,
            "stderr": err.strip(),
            "stdout_truncated": truncated,
            "stdout_json": parsed,
            "stdout_raw": out if parsed is None else None,
        }
    finally:
        try:
            shutil.rmtree(clone_path, ignore_errors=True)
        except OSError:
            pass
