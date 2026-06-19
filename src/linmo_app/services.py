from __future__ import annotations

import base64
import shutil
import time
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from linmo.processing import ProcessingParams, load_input_page, process_image

from .paths import AppPaths
from .repository import Repository

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


class LinmoServices:
    def __init__(self, paths: AppPaths):
        self.paths = paths
        self.paths.ensure()
        self.repo = Repository(paths.db_path)
        self.repo.update_settings(
            {
                "data_dir": str(paths.root),
                "default_dpi": "300",
                "default_export_dir": str(paths.exports_dir),
            }
        )

    def import_copybooks(self, paths: list[str]) -> list[dict[str, Any]]:
        imported = []
        for raw in paths:
            path = Path(raw).expanduser()
            if not path.exists():
                raise ValueError(f"file does not exist: {path}")
            if path.is_dir():
                imported.append(self._import_image_dir(path))
            elif path.suffix.lower() == ".pdf":
                imported.append(self._import_pdf(path))
            elif path.suffix.lower() in IMAGE_SUFFIXES:
                imported.append(self._import_image_file(path))
            else:
                raise ValueError(f"unsupported input: {path}")
        return imported

    def create_thumbnail(self, page_id: int) -> Path:
        page = self.repo.get_page_with_copybook(page_id)
        thumb_path = self.paths.thumbs_dir / f"{page_id}.jpg"
        if thumb_path.exists():
            return thumb_path

        image = self.load_page_image(page, dpi=120)
        image.thumbnail((260, 360))
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(thumb_path, "JPEG", quality=85)
        self.repo.update_page_thumb(page_id, thumb_path)
        return thumb_path

    def create_page_preview(self, page_id: int) -> Path:
        page = self.repo.get_page_with_copybook(page_id)
        preview_path = self.paths.previews_dir / f"source-{page_id}.jpg"
        if preview_path.exists():
            return preview_path

        image = self.load_page_image(page, dpi=180)
        image.thumbnail((1200, 1200))
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(preview_path, "JPEG", quality=88)
        return preview_path

    def copybook_cover(self, copybook_id: int) -> Path | None:
        copybook = self.repo.get_copybook(copybook_id)
        cover_path = Path(copybook["cover_path"]) if copybook.get("cover_path") else None
        if cover_path and cover_path.exists():
            return cover_path

        pages = self.repo.list_pages(copybook_id)
        if not pages:
            return None
        return self.create_thumbnail(int(pages[0]["id"]))

    def update_copybook_metadata(self, copybook_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
        data = dict(metadata)
        cover_source = data.pop("cover_source_path", "")
        if cover_source:
            data["cover_path"] = str(self._copy_cover_image(copybook_id, Path(str(cover_source)).expanduser()))
        return self.repo.update_copybook(copybook_id, data)

    def load_page_image(self, page: dict[str, Any], dpi: int) -> Image.Image:
        if page["copybook_source_type"] == "pdf":
            return load_input_page(Path(page["copybook_source_path"]), int(page["page_no"]), dpi)
        return load_input_page(Path(page["source_path"]), 1, dpi)

    def render_queue_preview(self, item_id: int) -> Path:
        item = self.repo.get_queue_item(item_id)
        page = self.repo.get_page_with_copybook(int(item["page_id"]))
        params = self._params_from_dict(item["params"])
        source = self.load_page_image(page, dpi=params.dpi)
        output = process_image(source, params)
        output.thumbnail((1200, 1200))
        out_path = self.paths.previews_dir / f"queue-{item_id}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        output.convert("RGB").save(out_path, "JPEG", quality=88)
        return out_path

    def export_queue_to_pdf(
        self,
        queue_item_ids: list[int],
        preset_id: int | None = None,
        output_path: str | None = None,
    ) -> Path:
        if not queue_item_ids:
            raise ValueError("queue_item_ids cannot be empty")
        preset = self.repo.get_preset(preset_id) if preset_id else None
        images = []
        for item_id in queue_item_ids:
            item = self.repo.get_queue_item(int(item_id))
            page = self.repo.get_page_with_copybook(int(item["page_id"]))
            params_dict = dict(item["params"])
            if preset:
                params_dict = self._apply_preset(params_dict, preset)
            params = self._params_from_dict(params_dict)
            images.append(process_image(self.load_page_image(page, dpi=params.dpi), params))

        if output_path:
            out_path = Path(output_path).expanduser()
        else:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            out_path = self.paths.exports_dir / f"{stamp}-linmo.pdf"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        first, rest = [image.convert("RGB") for image in images][0], [image.convert("RGB") for image in images][1:]
        first.save(out_path, "PDF", resolution=float(self._params_from_dict({}).dpi), save_all=bool(rest), append_images=rest)
        self.repo.record_export(out_path, len(images))
        return out_path

    def _import_pdf(self, source: Path) -> dict[str, Any]:
        copybook_dir = self._new_copybook_dir()
        target = copybook_dir / "source.pdf"
        shutil.copy2(source, target)
        copybook = self.repo.create_copybook(
            {
                "title": source.stem,
                "source_type": "pdf",
                "source_path": str(target),
            }
        )
        with fitz.open(target) as document:
            for index, page in enumerate(document, start=1):
                rect = page.rect
                self.repo.create_page(
                    {
                        "copybook_id": copybook["id"],
                        "page_no": index,
                        "source_path": str(target),
                        "width": int(rect.width),
                        "height": int(rect.height),
                    }
                )
        return self.repo.get_copybook(copybook["id"])

    def _import_image_file(self, source: Path) -> dict[str, Any]:
        copybook_dir = self._new_copybook_dir()
        pages_dir = copybook_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        target = pages_dir / f"1{source.suffix.lower()}"
        shutil.copy2(source, target)
        copybook = self.repo.create_copybook(
            {
                "title": source.stem,
                "source_type": "images",
                "source_path": str(pages_dir),
            }
        )
        self._create_image_page(copybook["id"], 1, target)
        return self.repo.get_copybook(copybook["id"])

    def _import_image_dir(self, source: Path) -> dict[str, Any]:
        files = [path for path in sorted(source.iterdir()) if path.suffix.lower() in IMAGE_SUFFIXES]
        if not files:
            raise ValueError(f"no supported images in: {source}")
        copybook_dir = self._new_copybook_dir()
        pages_dir = copybook_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        copybook = self.repo.create_copybook(
            {
                "title": source.name,
                "source_type": "images",
                "source_path": str(pages_dir),
            }
        )
        for index, file_path in enumerate(files, start=1):
            target = pages_dir / f"{index}{file_path.suffix.lower()}"
            shutil.copy2(file_path, target)
            self._create_image_page(copybook["id"], index, target)
        return self.repo.get_copybook(copybook["id"])

    def _create_image_page(self, copybook_id: int, page_no: int, source: Path) -> None:
        with Image.open(source) as image:
            width, height = image.size
        self.repo.create_page(
            {
                "copybook_id": copybook_id,
                "page_no": page_no,
                "source_path": str(source),
                "width": width,
                "height": height,
            }
        )

    def _copy_cover_image(self, copybook_id: int, source: Path) -> Path:
        if not source.exists():
            raise ValueError(f"cover image does not exist: {source}")
        if source.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"unsupported cover image: {source}")
        target_dir = self._copybook_storage_dir(copybook_id)
        target = target_dir / f"cover{source.suffix.lower()}"
        shutil.copy2(source, target)
        return target

    def _copybook_storage_dir(self, copybook_id: int) -> Path:
        copybook = self.repo.get_copybook(copybook_id)
        source_path = Path(copybook["source_path"])
        if copybook["source_type"] == "pdf":
            return source_path.parent
        return source_path.parent if source_path.name != "pages" else source_path.parent

    def _new_copybook_dir(self) -> Path:
        stamp = f"{int(time.time() * 1000)}"
        path = self.paths.library_dir / stamp
        path.mkdir(parents=True, exist_ok=False)
        return path

    def _params_from_dict(self, data: dict[str, Any]) -> ProcessingParams:
        return ProcessingParams(
            mode=data.get("mode", "row"),
            column_detection=data.get("column_detection", "gray"),
            columns=_optional_int(data.get("columns")),
            rows=_optional_int(data.get("rows")),
            blank_ratio=float(data.get("blank_ratio", 1.0)),
            dpi=int(data.get("dpi", 300)),
            gray_min=int(data.get("gray_min", 70)),
            gray_max=int(data.get("gray_max", 210)),
            ink_max=int(data.get("ink_max", 170)),
            line_max=int(data.get("line_max", 225)),
            background_image=_optional_path(data.get("background_image")),
            extract_foreground=bool(data.get("extract_foreground", False)),
            ink_color=data.get("ink_color", "#000000"),
            foreground_threshold=int(data.get("foreground_threshold", 18)),
        )

    def default_params_for_page(self, page_id: int) -> dict[str, Any]:
        page = self.repo.get_page_with_copybook(page_id)
        if page["copybook_source_type"] == "images":
            return {
                "mode": "col",
                "column_detection": "ink",
                "blank_ratio": 1.0,
                "ink_color": "#000000",
                "foreground_threshold": 35,
            }
        title = str(page.get("copybook_title", ""))
        if "红楼梦" in title:
            return {"mode": "col", "column_detection": "gray", "blank_ratio": 1.0, "ink_color": "#000000"}
        return {"mode": "row", "column_detection": "gray", "blank_ratio": 1.0, "ink_color": "#000000"}

    def _apply_preset(self, params: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
        merged = dict(params)
        for key in ["background_image", "ink_color", "foreground_threshold", "mode", "column_detection"]:
            if preset.get(key) not in (None, ""):
                merged[key] = preset[key]
        merged.update(preset.get("params", {}))
        return merged


def file_to_data_url(path: Path) -> str:
    mime = "image/jpeg"
    if path.suffix.lower() == ".png":
        mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value)).expanduser()
