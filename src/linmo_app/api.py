from __future__ import annotations

import functools
import platform
import sys
from pathlib import Path
from typing import Any

import fitz
import webview

from linmo.runtime import (
    add_runtime_log,
    clear_runtime_logs,
    configure_runtime_logging,
    get_runtime_diagnostics,
    log_exception,
)

from .paths import AppPaths, default_app_paths
from .services import LinmoServices, file_to_data_url


def _log_public_api_errors(cls):
    excluded = {"append_runtime_log", "get_runtime_diagnostics", "clear_runtime_logs"}
    for name, method in list(vars(cls).items()):
        if name.startswith("_") or name in excluded or not callable(method):
            continue

        @functools.wraps(method)
        def wrapped(self, *args, __method=method, __name=name, **kwargs):
            try:
                return __method(self, *args, **kwargs)
            except Exception as exc:
                log_exception("backend.api", f"API {__name} 执行失败", exc)
                raise

        setattr(cls, name, wrapped)
    return cls


@_log_public_api_errors
class LinmoApi:
    def __init__(self, paths: AppPaths | None = None):
        self.paths = paths or default_app_paths()
        configure_runtime_logging(self.paths.logs_dir / "linmo.log")
        add_runtime_log(
            "info",
            "backend.startup",
            f"Linmo 启动：{platform.platform()}，Python {platform.python_version()}，可执行文件 {sys.executable}",
        )
        self.services = LinmoServices(self.paths)
        self.services.repo.clear_queue_items()

    # -- window chrome helpers --
    def window_move_by(self, delta_x: int, delta_y: int) -> None:
        try:
            window = _current_window()
            if window is None:
                return
            window.move(int(window.x or 0) + int(delta_x), int(window.y or 0) + int(delta_y))
        except Exception:
            pass

    def window_minimize(self) -> None:
        _call_window("minimize")

    def window_toggle_maximize(self) -> None:
        _call_window("toggle_fullscreen")

    def window_close(self) -> None:
        _call_window("destroy")

    def get_home_stats(self) -> dict[str, int]:
        return self.services.repo.stats()

    def list_copybooks(self) -> list[dict[str, Any]]:
        return self.services.repo.list_copybooks()

    def import_copybooks(self, paths: list[str]) -> list[dict[str, Any]]:
        return self.services.import_copybooks(paths)

    def update_copybook_metadata(self, copybook_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
        return self.services.update_copybook_metadata(copybook_id, metadata)

    def list_pages(self, copybook_id: int) -> list[dict[str, Any]]:
        return self.services.repo.list_pages(copybook_id)

    def get_page_detail(self, page_id: int) -> dict[str, Any]:
        return self.services.get_page_detail(int(page_id))

    def update_page_crop(self, page_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
        return self.services.update_page_crop(int(page_id), metadata)

    def get_page_thumbnail(self, page_id: int) -> str:
        return file_to_data_url(self.services.create_thumbnail(page_id))

    def get_page_preview(self, page_id: int) -> str:
        return file_to_data_url(self.services.create_page_preview(page_id))

    def get_copybook_cover(self, copybook_id: int) -> str:
        path = self.services.copybook_cover(copybook_id)
        return file_to_data_url(path) if path else ""

    def render_page_previews(self, page_id: int, params: dict[str, Any]) -> list[str]:
        return [
            file_to_data_url(path)
            for path in self.services.render_page_previews(int(page_id), params)
        ]

    def analyze_page(self, page_id: int, force: bool = False) -> dict[str, Any]:
        return self.services.analyze_page(int(page_id), bool(force))

    def update_page_analysis(
        self,
        page_id: int,
        groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self.services.update_page_analysis(int(page_id), groups)

    def export_page_to_generated_post(
        self,
        page_id: int,
        params: dict[str, Any],
        name: str,
        output_format: str = "pdf",
    ) -> dict[str, Any]:
        return self.services.export_page_to_generated_post(int(page_id), params, name, output_format)

    def add_pages_to_queue(self, page_ids: list[int]) -> list[dict[str, Any]]:
        items = []
        queued_page_ids = set()
        for page_id in page_ids:
            page_id = int(page_id)
            if page_id in queued_page_ids:
                continue
            queued_page_ids.add(page_id)
            items.append(
                self.services.repo.add_queue_item(
                    page_id,
                    self.services.default_params_for_page(page_id),
                )
            )
        return items

    def list_queue_items(self) -> list[dict[str, Any]]:
        return self.services.repo.list_queue_items()

    def update_queue_item(self, item_id: int, params: dict[str, Any]) -> dict[str, Any]:
        return self.services.repo.update_queue_item(item_id, params)

    def render_queue_preview(self, item_id: int) -> str:
        return file_to_data_url(self.services.render_queue_preview(item_id))

    def render_queue_previews(self, item_id: int) -> list[str]:
        return [
            file_to_data_url(path)
            for path in self.services.render_queue_previews(int(item_id))
        ]

    def analyze_queue_item(self, item_id: int, force: bool = False) -> dict[str, Any]:
        return self.services.analyze_queue_item(int(item_id), bool(force))

    def update_queue_analysis(
        self,
        item_id: int,
        groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self.services.update_queue_analysis(int(item_id), groups)

    def export_queue_to_pdf(
        self,
        queue_item_ids: list[int],
        preset_id: int | None = None,
        output_path: str | None = None,
        name: str | None = None,
        output_format: str = "pdf",
    ) -> dict[str, Any]:
        if name is not None:
            post = self.services.export_queue_to_generated_post(queue_item_ids, name, preset_id, output_format)
            return {"output_path": post["original_pdf_path"], "page_count": post["page_count"], "generated_post": post}
        path = self.services.export_queue_to_pdf(queue_item_ids, preset_id, output_path)
        with fitz.open(path) as document:
            page_count = document.page_count
        return {"output_path": str(path), "page_count": page_count}

    def get_next_generated_post_name(self) -> str:
        return self.services.next_generated_post_name()

    def list_generated_posts(self) -> list[dict[str, Any]]:
        return self.services.list_generated_posts()

    def get_generated_post_thumbnail(self, post_id: int) -> str:
        path = self.services.generated_post_thumbnail(int(post_id))
        return file_to_data_url(path) if path else ""

    def list_generated_post_files(self, post_id: int) -> list[dict[str, Any]]:
        return self.services.list_generated_post_files(int(post_id))

    def sync_generated_post(self, post_id: int) -> dict[str, Any]:
        return self.services.sync_generated_post(int(post_id))

    def list_presets(self) -> list[dict[str, Any]]:
        return self.services.repo.list_presets()

    def create_preset(self, data: dict[str, Any]) -> dict[str, Any]:
        return self.services.repo.create_preset(data)

    def update_preset(self, preset_id: int, data: dict[str, Any]) -> dict[str, Any]:
        return self.services.repo.update_preset(preset_id, data)

    def delete_preset(self, preset_id: int) -> dict[str, bool]:
        self.services.repo.delete_preset(preset_id)
        return {"ok": True}

    def get_settings(self) -> dict[str, str]:
        return self.services.repo.get_settings()

    def update_settings(self, settings: dict[str, Any]) -> dict[str, str]:
        return self.services.repo.update_settings(settings)

    def get_runtime_diagnostics(self, since_id: int = 0) -> dict[str, Any]:
        return get_runtime_diagnostics(int(since_id))

    def append_runtime_log(
        self,
        level: str,
        source: str,
        message: str,
        details: str = "",
    ) -> dict[str, Any]:
        normalized_source = str(source or "app")
        if not normalized_source.startswith("frontend"):
            normalized_source = f"frontend.{normalized_source}"
        return add_runtime_log(level, normalized_source, message, details, echo=False)

    def clear_runtime_logs(self) -> dict[str, bool]:
        clear_runtime_logs()
        return {"ok": True}

    def choose_import_files(self) -> list[str]:
        return _open_file_dialog(allow_multiple=True)

    def choose_background_image(self) -> str:
        files = _open_file_dialog(allow_multiple=False, images_only=True)
        return files[0] if files else ""

    def choose_cover_image(self) -> str:
        files = _open_file_dialog(allow_multiple=False, images_only=True)
        return files[0] if files else ""


def _call_window(action: str) -> None:
    try:
        window = _current_window()
        if window is None:
            return
        getattr(window, action)()
    except Exception:
        pass


def _current_window():
    import webview

    return webview.windows[0] if webview.windows else None


def _open_file_dialog(allow_multiple: bool, images_only: bool = False) -> list[str]:
    try:
        import webview

        window = webview.windows[0] if webview.windows else None
        if window is None:
            return []
        file_types = ("Images (*.jpg;*.jpeg;*.png;*.webp;*.bmp)", "All files (*.*)") if images_only else (
            "PDF and images (*.pdf;*.jpg;*.jpeg;*.png;*.webp;*.bmp)",
            "All files (*.*)",
        )
        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=allow_multiple,
            file_types=file_types,
        )
        return [str(Path(path)) for path in (result or [])]
    except Exception:
        return []
