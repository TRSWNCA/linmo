from __future__ import annotations

import logging
import sys
import threading
import time
import traceback
from collections import deque
from pathlib import Path
from typing import Any


_MAX_ENTRIES = 1000
_LOCK = threading.RLock()
_ENTRIES: deque[dict[str, Any]] = deque(maxlen=_MAX_ENTRIES)
_NEXT_ID = 1
_LOG_PATH: Path | None = None
_STATUS: dict[str, Any] = {
    "operation": "",
    "stage": "idle",
    "message": "",
    "page_id": None,
    "updated_at": 0.0,
}
_ROOT_HANDLER: logging.Handler | None = None


class _WarningBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            details = ""
            if record.exc_info:
                details = "".join(traceback.format_exception(*record.exc_info))
            add_runtime_log(
                record.levelname.lower(),
                f"backend.{record.name}",
                record.getMessage(),
                details,
                echo=False,
            )
        except Exception:
            pass


def configure_runtime_logging(log_path: Path) -> None:
    global _LOG_PATH, _ROOT_HANDLER
    resolved = Path(log_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        _LOG_PATH = resolved
    if _ROOT_HANDLER is None:
        handler = _WarningBufferHandler(level=logging.WARNING)
        logging.getLogger().addHandler(handler)
        _ROOT_HANDLER = handler
    add_runtime_log("info", "backend.runtime", f"运行日志已初始化：{resolved}", echo=False)


def add_runtime_log(
    level: str,
    source: str,
    message: str,
    details: str = "",
    *,
    echo: bool = True,
) -> dict[str, Any]:
    global _NEXT_ID
    normalized_level = str(level or "info").lower()
    if normalized_level not in {"debug", "info", "warning", "error"}:
        normalized_level = "info"
    entry = {
        "id": 0,
        "timestamp": time.time(),
        "level": normalized_level,
        "source": str(source or "backend"),
        "message": str(message),
        "details": str(details or ""),
    }
    with _LOCK:
        entry["id"] = _NEXT_ID
        _NEXT_ID += 1
        _ENTRIES.append(entry)
        _append_to_file(entry)
    if echo and normalized_level in {"warning", "error"}:
        text = f"[Linmo {normalized_level.upper()}] {entry['source']}: {entry['message']}"
        if entry["details"]:
            text += f"\n{entry['details'].rstrip()}"
        print(text, file=sys.stderr)
    return dict(entry)


def log_exception(source: str, message: str, exc: BaseException) -> dict[str, Any]:
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return add_runtime_log("error", source, f"{message}: {type(exc).__name__}: {exc}", details)


def set_runtime_status(
    operation: str,
    stage: str,
    message: str,
    *,
    page_id: int | None = None,
) -> dict[str, Any]:
    status = {
        "operation": str(operation),
        "stage": str(stage),
        "message": str(message),
        "page_id": int(page_id) if page_id is not None else None,
        "updated_at": time.time(),
    }
    with _LOCK:
        _STATUS.clear()
        _STATUS.update(status)
    return dict(status)


def get_runtime_diagnostics(since_id: int = 0) -> dict[str, Any]:
    with _LOCK:
        entries = [dict(entry) for entry in _ENTRIES if int(entry["id"]) > int(since_id)]
        return {
            "status": dict(_STATUS),
            "entries": entries,
            "last_id": int(_ENTRIES[-1]["id"]) if _ENTRIES else 0,
            "log_path": str(_LOG_PATH) if _LOG_PATH else "",
        }


def clear_runtime_logs() -> None:
    global _NEXT_ID
    with _LOCK:
        _ENTRIES.clear()
        _NEXT_ID = 1
        if _LOG_PATH:
            _LOG_PATH.write_text("", encoding="utf-8")


def _append_to_file(entry: dict[str, Any]) -> None:
    if _LOG_PATH is None:
        return
    try:
        if not _LOG_PATH.parent.exists():
            return
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(entry["timestamp"])))
        line = f"{timestamp} [{str(entry['level']).upper()}] {entry['source']}: {entry['message']}\n"
        if entry["details"]:
            line += f"{entry['details'].rstrip()}\n"
        with _LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass
