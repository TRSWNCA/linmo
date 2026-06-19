from __future__ import annotations

import os
import sys
from pathlib import Path

from .api import LinmoApi


def main() -> None:
    _configure_linux_webengine()
    try:
        import webview
    except ImportError as exc:
        raise SystemExit("pywebview is not installed. Run `uv sync` first.") from exc

    _ensure_display_available()
    api = LinmoApi()
    frontend = _frontend_entry()
    webview.create_window(
        "Linmo",
        url=str(frontend),
        js_api=api,
        width=1480,
        height=960,
        min_size=(980, 640),
    )
    webview.start(debug=_debug_enabled(), gui=_preferred_gui())


def _debug_enabled() -> bool:
    return os.environ.get("LINMO_WEBVIEW_DEBUG") == "1"


def _preferred_gui() -> str | None:
    gui = os.environ.get("LINMO_WEBVIEW_GUI")
    if gui:
        return gui
    if sys.platform.startswith("linux"):
        return "qt"
    return None


def _configure_linux_webengine() -> None:
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("LINMO_WEBVIEW_ACCELERATION") == "1":
        return

    _append_env_flags(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        [
            "--disable-gpu",
            "--disable-gpu-compositing",
            "--disable-zero-copy",
            "--disable-features=VaapiVideoDecoder",
        ],
    )
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")


def _append_env_flags(name: str, flags: list[str]) -> None:
    existing = os.environ.get(name, "")
    existing_parts = existing.split()
    merged = existing_parts[:]
    for flag in flags:
        if flag not in existing_parts:
            merged.append(flag)
    os.environ[name] = " ".join(merged)


def _ensure_display_available() -> None:
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return
    raise SystemExit(
        "No Linux display server was detected. Start Linmo from a desktop "
        "session with DISPLAY or WAYLAND_DISPLAY set."
    )


def _frontend_entry() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    built = repo_root / "frontend" / "dist" / "index.html"
    if built.exists():
        return built
    dev = repo_root / "frontend" / "index.html"
    if dev.exists():
        return dev
    raise FileNotFoundError("frontend/index.html not found")


if __name__ == "__main__":
    main()
