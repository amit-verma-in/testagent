#!/usr/bin/env python3
"""Run ADK Web with McKinsey-blue themed UI assets.

The stock ADK Dev UI uses Material primary colors that read as red/pink. This
launcher copies the bundled Angular app to `.adk_web_branded/`, injects a small
CSS override, and temporarily redirects `google.adk.cli.fast_api`'s browser
path to that folder (see google-adk upgrades — if `adk web` breaks, compare
`get_fast_api_app` in `google.adk.cli.fast_api`).
"""

from __future__ import annotations

import importlib.util
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BRAND_CSS = ROOT / "adk_web_branding" / "mckinsey-adk-theme.css"
BRANDED_DIR = ROOT / ".adk_web_branded"
INJECT_MARK = "mckinsey-adk-theme.css"

_branded_ready: pathlib.Path | None = None


def _cli_package_dir() -> pathlib.Path:
    spec = importlib.util.find_spec("google.adk.cli.fast_api")
    if not spec or not spec.origin:
        raise RuntimeError("google.adk.cli.fast_api not found; install google-adk in this venv.")
    return pathlib.Path(spec.origin).parent.resolve()


def _prepare_branded_assets(source_browser: pathlib.Path) -> pathlib.Path:
    global _branded_ready
    if _branded_ready is not None:
        return _branded_ready

    if BRANDED_DIR.is_dir():
        shutil.rmtree(BRANDED_DIR)
    shutil.copytree(source_browser, BRANDED_DIR)

    index = BRANDED_DIR / "index.html"
    text = index.read_text(encoding="utf-8")
    inject = f'  <link rel="stylesheet" href="./{INJECT_MARK}">\n'
    if INJECT_MARK not in text:
        text = text.replace("</head>", inject + "</head>", 1)
        index.write_text(text, encoding="utf-8")

    shutil.copy2(BRAND_CSS, BRANDED_DIR / INJECT_MARK)
    _branded_ready = BRANDED_DIR
    return _branded_ready


def _install_browser_path_shim() -> None:
    cli_dir = _cli_package_dir()
    _orig = pathlib.Path.__truediv__

    def _truediv(self: pathlib.Path, key: pathlib.PurePath | str) -> pathlib.Path:
        if key == "browser":
            try:
                if self.resolve() == cli_dir:
                    return _prepare_branded_assets(cli_dir / "browser")
            except (OSError, ValueError):
                pass
        return _orig(self, key)

    pathlib.Path.__truediv__ = _truediv  # type: ignore[method-assign]
    pathlib.PosixPath.__truediv__ = _truediv  # type: ignore[method-assign]
    if hasattr(pathlib, "WindowsPath"):
        pathlib.WindowsPath.__truediv__ = _truediv  # type: ignore[method-assign]


def main() -> None:
    _install_browser_path_shim()
    from google.adk.cli.cli_tools_click import main as adk_cli_main

    sys.argv = ["adk", "web", *sys.argv[1:]]
    adk_cli_main()


if __name__ == "__main__":
    main()
