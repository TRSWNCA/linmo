from __future__ import annotations

import webview
from pathlib import Path
from typing import Any

from .paths import AppPaths, default_app_paths
from .services import LinmoServices, file_to_data_url


class LinmoApi:
    def __init__(self, paths: AppPaths | None = None):
        self.paths = paths or default_app_paths()
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

    def get_page_thumbnail(self, page_id: int) -> str:
        return file_to_data_url(self.services.create_thumbnail(page_id))

    def get_page_preview(self, page_id: int) -> str:
        return file_to_data_url(self.services.create_page_preview(page_id))

    def get_copybook_cover(self, copybook_id: int) -> str:
        path = self.services.copybook_cover(copybook_id)
        return file_to_data_url(path) if path else ""

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

    def export_queue_to_pdf(
        self,
        queue_item_ids: list[int],
        preset_id: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        path = self.services.export_queue_to_pdf(queue_item_ids, preset_id, output_path)
        return {"output_path": str(path), "page_count": len(queue_item_ids)}

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
