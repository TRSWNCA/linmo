from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import posixpath
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageDraw, ImageFont

from linmo.glyph_pipeline import (
    ANALYSIS_VERSION,
    analyze_page,
    _extract_glyph,
    render_practice_pages,
    source_fingerprint,
    update_analysis,
)
from linmo.processing import ProcessingParams, load_input_page
from linmo.runtime import add_runtime_log, log_exception, set_runtime_status

from .paths import AppPaths
from .repository import Repository

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
GENERATED_FILE_SUFFIXES = {".pdf", ".png"}
QUEUE_PREVIEW_CACHE_VERSION = "glyph-grid-v1"
MAX_COPYBOOK_CROP_RATIO = 0.45
MAX_TOTAL_COPYBOOK_CROP_RATIO = 0.8


class LinmoServices:
    def __init__(self, paths: AppPaths):
        self.paths = paths
        self.paths.ensure()
        self.repo = Repository(paths.db_path)
        defaults = {
            "data_dir": str(paths.root),
            "default_dpi": "300",
            "default_export_dir": str(paths.exports_dir),
            "webdav_url": "",
            "webdav_username": "",
            "webdav_password": "",
            "webdav_remote_root": "Linmo",
        }
        current_settings = self.repo.get_settings()
        missing_defaults = {key: value for key, value in defaults.items() if key not in current_settings}
        if missing_defaults:
            self.repo.update_settings(missing_defaults)

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

    def create_page_transform_preview(self, page_id: int) -> Path:
        page = self.repo.get_page_with_copybook(page_id)
        preview_path = self.paths.previews_dir / f"transform-{page_id}.jpg"
        if preview_path.exists():
            return preview_path

        image = self.load_page_transformed_image(page, dpi=180)
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
        current = self.repo.get_copybook(copybook_id)
        data = dict(metadata)
        cover_source = data.pop("cover_source_path", "")
        if cover_source:
            data["cover_path"] = str(self._copy_cover_image(copybook_id, Path(str(cover_source)).expanduser()))
        if "crop_left_ratio" in data:
            data["crop_left_ratio"] = _copybook_crop_ratio(data["crop_left_ratio"])
        if "crop_right_ratio" in data:
            data["crop_right_ratio"] = _copybook_crop_ratio(data["crop_right_ratio"])
        if "crop_top_ratio" in data:
            data["crop_top_ratio"] = _copybook_crop_ratio(data["crop_top_ratio"])
        if "crop_bottom_ratio" in data:
            data["crop_bottom_ratio"] = _copybook_crop_ratio(data["crop_bottom_ratio"])
        left_ratio = float(data.get("crop_left_ratio", current.get("crop_left_ratio", 0)) or 0)
        right_ratio = float(data.get("crop_right_ratio", current.get("crop_right_ratio", 0)) or 0)
        top_ratio = float(data.get("crop_top_ratio", current.get("crop_top_ratio", 0)) or 0)
        bottom_ratio = float(data.get("crop_bottom_ratio", current.get("crop_bottom_ratio", 0)) or 0)
        self._validate_crop_ratios(left_ratio, right_ratio, top_ratio, bottom_ratio)

        updated = self.repo.update_copybook(copybook_id, data)
        if (
            float(current.get("crop_left_ratio") or 0) != float(updated.get("crop_left_ratio") or 0)
            or float(current.get("crop_right_ratio") or 0) != float(updated.get("crop_right_ratio") or 0)
            or float(current.get("crop_top_ratio") or 0) != float(updated.get("crop_top_ratio") or 0)
            or float(current.get("crop_bottom_ratio") or 0) != float(updated.get("crop_bottom_ratio") or 0)
        ):
            self._invalidate_copybook_page_caches(copybook_id)
        return updated

    def get_page_detail(self, page_id: int) -> dict[str, Any]:
        return self.repo.get_page_with_copybook(page_id)

    def update_page_crop(self, page_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
        current = self.repo.get_page_with_copybook(page_id)
        left_ratio = _copybook_crop_ratio(metadata.get("crop_left_ratio", current.get("crop_left_ratio", 0)))
        right_ratio = _copybook_crop_ratio(metadata.get("crop_right_ratio", current.get("crop_right_ratio", 0)))
        top_ratio = _copybook_crop_ratio(metadata.get("crop_top_ratio", current.get("crop_top_ratio", 0)))
        bottom_ratio = _copybook_crop_ratio(metadata.get("crop_bottom_ratio", current.get("crop_bottom_ratio", 0)))
        rotation_degrees = _page_rotation_degrees(
            metadata.get("rotation_degrees", current.get("rotation_degrees", 0))
        )
        self._validate_crop_ratios(left_ratio, right_ratio, top_ratio, bottom_ratio)

        updated = self.repo.update_page(
            page_id,
            {
                "crop_left_ratio": left_ratio,
                "crop_right_ratio": right_ratio,
                "crop_top_ratio": top_ratio,
                "crop_bottom_ratio": bottom_ratio,
                "rotation_degrees": rotation_degrees,
                "crop_override": 1,
            },
        )
        if (
            float(current.get("crop_left_ratio") or 0) != left_ratio
            or float(current.get("crop_right_ratio") or 0) != right_ratio
            or float(current.get("crop_top_ratio") or 0) != top_ratio
            or float(current.get("crop_bottom_ratio") or 0) != bottom_ratio
            or float(current.get("rotation_degrees") or 0) != rotation_degrees
            or int(current.get("page_crop_override") or 0) != 1
        ):
            self._invalidate_page_caches(page_id)
        return self.repo.get_page_with_copybook(page_id)

    def load_page_image(self, page: dict[str, Any], dpi: int) -> Image.Image:
        image = self.load_page_transformed_image(page, dpi)
        return self._apply_page_crop(image, page)

    def load_page_transformed_image(self, page: dict[str, Any], dpi: int) -> Image.Image:
        if page["copybook_source_type"] == "pdf":
            image = load_input_page(Path(page["copybook_source_path"]), int(page["page_no"]), dpi)
        else:
            image = load_input_page(Path(page["source_path"]), 1, dpi)
        return self._apply_page_rotation(image, float(page.get("rotation_degrees", 0) or 0))

    def analyze_page(self, page_id: int, force: bool = False, dpi: int | None = None) -> dict[str, Any]:
        set_runtime_status("ocr", "loading_page", "正在读取页面", page_id=page_id)
        try:
            page = self.repo.get_page_with_copybook(page_id)
            resolved_dpi = int(dpi or self.default_params_for_page(page_id)["dpi"])
            source = self.load_page_image(page, dpi=resolved_dpi)
            fingerprint = source_fingerprint(source)
            cached = self.repo.get_page_analysis(page_id)
            if (
                not force
                and cached is not None
                and cached["source_fingerprint"] == fingerprint
                and int(cached["analysis"].get("version", 0)) == ANALYSIS_VERSION
            ):
                add_runtime_log("info", "backend.ocr", f"页面 {page_id} 使用识别缓存")
                set_runtime_status("ocr", "cache_hit", "正在读取识别缓存", page_id=page_id)
                return cached["analysis"]
            if os.environ.get("LINMO_DISABLE_OCR") != "1":
                os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(self.paths.models_dir))

            def report_progress(stage: str, message: str) -> None:
                set_runtime_status("ocr", stage, message, page_id=page_id)

            analysis = analyze_page(source, progress=report_progress)
            analysis["dpi"] = resolved_dpi
            saved = self.repo.save_page_analysis(page_id, analysis)["analysis"]
            if analysis.get("warning"):
                add_runtime_log("warning", "backend.ocr", str(analysis["warning"]), echo=False)
                set_runtime_status("ocr", "warning", str(analysis["warning"]), page_id=page_id)
            else:
                set_runtime_status("ocr", "complete", "识别完成", page_id=page_id)
            return saved
        except Exception as exc:
            set_runtime_status("ocr", "error", f"识别失败：{exc}", page_id=page_id)
            log_exception("backend.services", f"页面 {page_id} 识别失败", exc)
            raise

    def update_page_analysis(
        self,
        page_id: int,
        groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        analysis = self.analyze_page(page_id)
        updated = update_analysis(analysis, groups=groups)
        if any(str(group.get("id", "")).startswith("selected-stream") for group in groups):
            updated["selection_mode"] = "ordered_stream"
            updated["ocr_groups"] = analysis.get("ocr_groups") or analysis.get("groups", [])
        elif analysis.get("ocr_groups") is not None:
            updated["ocr_groups"] = analysis.get("ocr_groups")
        return self.repo.save_page_analysis(page_id, updated)["analysis"]

    def update_page_ocr_groups(
        self,
        page_id: int,
        groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        analysis = self.analyze_page(page_id)
        source_groups = copy.deepcopy(groups)
        if analysis.get("selection_mode") == "ordered_stream":
            updated = copy.deepcopy(analysis)
            updated["ocr_groups"] = source_groups
            source_glyphs = {
                str(glyph.get("id")): glyph
                for group in source_groups
                for glyph in group.get("glyphs", [])
            }
            for group in updated.get("groups", []):
                for glyph in group.get("glyphs", []):
                    source = source_glyphs.get(str(glyph.get("id")))
                    if source is None:
                        continue
                    glyph["text"] = source.get("text", glyph.get("text", ""))
                    glyph["bbox"] = copy.deepcopy(source.get("bbox", glyph.get("bbox")))
                    glyph["polygon"] = copy.deepcopy(source.get("polygon", glyph.get("polygon")))
                    glyph["kind"] = source.get("kind", glyph.get("kind", "character"))
            updated["status"] = "reviewed"
        else:
            updated = update_analysis(analysis, groups=source_groups)
            updated["selection_mode"] = "ocr_groups"
        return self.repo.save_page_analysis(page_id, updated)["analysis"]

    def search_glyphs(
        self,
        text: str,
        copybook_id: int | None = None,
        author: str = "",
        limit: int = 60,
        offset: int = 0,
    ) -> dict[str, Any]:
        query = str(text).strip()
        if len(query) != 1 or not _is_han_character(query):
            raise ValueError("请输入一个汉字")
        return self.repo.search_glyphs(
            query,
            copybook_id=int(copybook_id) if copybook_id is not None else None,
            author=str(author),
            limit=limit,
            offset=offset,
        )

    def list_glyph_filters(self, text: str = "") -> dict[str, Any]:
        query = str(text).strip()
        if query and (len(query) != 1 or not _is_han_character(query)):
            raise ValueError("请输入一个汉字")
        return self.repo.list_glyph_filters(query)

    def glyph_image(self, occurrence_id: int) -> Path:
        glyph = self.repo.get_glyph_occurrence(int(occurrence_id))
        cache_key = hashlib.sha1(
            json.dumps(
                {
                    "fingerprint": glyph["source_fingerprint"],
                    "bbox": glyph["bbox"],
                    "updated_at": glyph["updated_at"],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:12]
        path = self.paths.glyphs_dir / f"{int(occurrence_id)}-{cache_key}.png"
        if path.exists():
            return path

        page = self.repo.get_page_with_copybook(int(glyph["page_id"]))
        cached_analysis = self.repo.get_page_analysis(int(glyph["page_id"]))
        if cached_analysis is None:
            raise ValueError("单字来源页的识别结果已失效")
        dpi = int(cached_analysis["analysis"].get("dpi", self.default_params_for_page(int(glyph["page_id"]))["dpi"]))
        source = self.load_page_image(page, dpi=dpi)
        left, top, right, bottom = [int(value) for value in glyph["bbox"]]
        width = max(1, right - left)
        height = max(1, bottom - top)
        padding = max(2, round(max(width, height) * 0.04))
        box = (
            max(0, left - padding),
            max(0, top - padding),
            min(source.width, right + padding),
            min(source.height, bottom + padding),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("单字标注范围无效")
        crop = source.crop(box).convert("RGB")
        alpha, ink = _extract_glyph(crop)
        rgba = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        rgba.paste(ink.convert("RGB"), (0, 0), alpha)
        path.parent.mkdir(parents=True, exist_ok=True)
        for stale_path in self.paths.glyphs_dir.glob(f"{int(occurrence_id)}-*.png"):
            if stale_path != path:
                stale_path.unlink()
        rgba.save(path, "PNG")
        return path

    def list_collections(self) -> list[dict[str, Any]]:
        return self.repo.list_collections()

    def create_collection(self, name: str) -> dict[str, Any]:
        return self.repo.create_collection(name)

    def get_collection(self, collection_id: int) -> dict[str, Any]:
        collection = self.repo.get_collection(int(collection_id))
        for item in collection.get("items", []):
            character = str(item.get("character", ""))
            if item.get("occurrence_id") is not None and item.get("text") != character:
                return self.update_collection(int(collection_id), {})
            if item.get("occurrence_id") is None and _is_han_character(character):
                if self.repo.search_glyphs(character, limit=1)["items"]:
                    return self.update_collection(int(collection_id), {})
        return collection

    def update_collection(self, collection_id: int, data: dict[str, Any]) -> dict[str, Any]:
        current = self.repo.get_collection(int(collection_id))
        old_text = str(current.get("input_text", ""))
        new_text = str(data.get("input_text", old_text))
        if len(new_text) > 500:
            raise ValueError("集字内容最多 500 个字符")

        old_selections = {
            int(item["position"]): item.get("occurrence_id")
            for item in current.get("items", [])
        }
        if new_text == old_text:
            selections = dict(old_selections)
        else:
            selections = {}
            for old_position, new_position in _matching_text_positions(old_text, new_text):
                if old_position in old_selections:
                    selections[new_position] = old_selections[old_position]

        for item in data.get("selections", []) or []:
            position = int(item["position"])
            if 0 <= position < len(new_text):
                selections[position] = item.get("occurrence_id")

        collection_items = []
        for position, character in enumerate(new_text):
            if not _is_han_character(character):
                continue
            occurrence_id = selections.get(position)
            if occurrence_id is not None:
                try:
                    occurrence = self.repo.get_glyph_occurrence(int(occurrence_id))
                    if occurrence["text"] != character:
                        occurrence_id = None
                except ValueError:
                    occurrence_id = None
            if occurrence_id is None:
                result = self.repo.search_glyphs(character, limit=1)
                if result["items"]:
                    occurrence_id = int(result["items"][0]["id"])
            collection_items.append(
                {
                    "position": position,
                    "character": character,
                    "occurrence_id": occurrence_id,
                }
            )

        payload = {
            key: data[key]
            for key in ("name", "input_text", "direction", "line_capacity", "background")
            if key in data
        }
        payload["input_text"] = new_text
        updated = self.repo.update_collection(int(collection_id), payload, collection_items)
        preview = self.paths.collection_previews_dir / f"{int(collection_id)}.png"
        if preview.exists():
            preview.unlink()
        return updated

    def delete_collection(self, collection_id: int) -> None:
        self.repo.delete_collection(int(collection_id))
        preview = self.paths.collection_previews_dir / f"{int(collection_id)}.png"
        if preview.exists():
            preview.unlink()

    def render_collection_preview(self, collection_id: int) -> Path:
        path = self.paths.collection_previews_dir / f"{int(collection_id)}.png"
        if path.exists():
            return path
        image = self._render_collection(int(collection_id))
        image.thumbnail((1400, 1000), Image.Resampling.LANCZOS)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, "PNG")
        return path

    def export_collection_png(self, collection_id: int) -> Path:
        collection = self.repo.get_collection(int(collection_id))
        image = self._render_collection(int(collection_id))
        export_dir = Path(
            self.repo.get_settings().get("default_export_dir", str(self.paths.exports_dir))
        ).expanduser()
        export_dir.mkdir(parents=True, exist_ok=True)
        base_name = _safe_file_name(str(collection["name"])) or "集字"
        path = export_dir / f"{base_name}.png"
        suffix = 2
        while path.exists():
            path = export_dir / f"{base_name}-{suffix}.png"
            suffix += 1
        image.save(path, "PNG")
        return path

    def _render_collection(self, collection_id: int) -> Image.Image:
        collection = self.get_collection(collection_id)
        text = str(collection["input_text"])
        capacity = max(1, int(collection["line_capacity"]))
        direction = str(collection["direction"])
        positions = _collection_layout(text, direction, capacity)
        cell = 256
        margin = 24
        max_column = max((column for _, _, column, _ in positions), default=0)
        max_row = max((row for _, _, _, row in positions), default=0)
        width = max(cell, (max_column + 1) * cell) + margin * 2
        height = max(cell, (max_row + 1) * cell) + margin * 2
        background = (255, 255, 255, 255) if collection["background"] == "white" else (0, 0, 0, 0)
        output = Image.new("RGBA", (width, height), background)
        draw = ImageDraw.Draw(output)
        font = _collection_font(round(cell * 0.58))
        item_map = {int(item["position"]): item for item in collection["items"]}

        for position, character, column, row in positions:
            x = margin + column * cell
            y = margin + row * cell
            if _is_han_character(character):
                item = item_map.get(position)
                occurrence_id = item.get("occurrence_id") if item else None
                if occurrence_id is None:
                    draw.rectangle(
                        (x + 18, y + 18, x + cell - 18, y + cell - 18),
                        outline=(150, 150, 150, 220),
                        width=3,
                    )
                    _draw_centered_text(draw, (x, y, x + cell, y + cell), character, font, (140, 140, 140, 230))
                    continue
                with Image.open(self.glyph_image(int(occurrence_id))) as glyph_source:
                    glyph = glyph_source.convert("RGBA")
                glyph.thumbnail((round(cell * 0.88), round(cell * 0.88)), Image.Resampling.LANCZOS)
                output.alpha_composite(
                    glyph,
                    (x + (cell - glyph.width) // 2, y + (cell - glyph.height) // 2),
                )
            elif not character.isspace():
                _draw_centered_text(draw, (x, y, x + cell, y + cell), character, font, (32, 32, 32, 255))
        return output

    def render_page_previews(
        self,
        page_id: int,
        params_dict: dict[str, Any],
    ) -> list[Path]:
        params = self._params_from_dict(params_dict)
        page = self.repo.get_page_with_copybook(page_id)
        source = self.load_page_image(page, dpi=params.dpi)
        analysis = self.analyze_page(page_id, dpi=params.dpi)
        outputs = render_practice_pages(source, analysis, params.grid)
        cache_key = _page_preview_cache_key(page_id, params_dict, analysis)
        paths = []
        for index, output in enumerate(outputs, start=1):
            output.thumbnail((1200, 1200))
            out_path = self.paths.previews_dir / f"page-{page_id}-{cache_key}-{index}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            output.convert("RGB").save(out_path, "JPEG", quality=88)
            paths.append(out_path)
        return paths

    def render_page_preview(self, page_id: int, params_dict: dict[str, Any]) -> Path:
        return self.render_page_previews(page_id, params_dict)[0]

    def export_page_to_generated_post(
        self,
        page_id: int,
        params_dict: dict[str, Any],
        name: str,
        output_format: str = "pdf",
    ) -> dict[str, Any]:
        clean_name = name.strip()
        clean_format = output_format.strip().lower()
        if not clean_name:
            raise ValueError("generated post name cannot be empty")
        if clean_format not in {"pdf", "png"}:
            raise ValueError("output_format must be pdf or png")

        post = self.repo.create_generated_post(clean_name, 0)
        post_dir = self._generated_post_dir(int(post["id"]))
        post_dir.mkdir(parents=True, exist_ok=True)
        results_dir = post_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        images = self._render_page_images(page_id, params_dict)

        if clean_format == "pdf":
            original_path = post_dir / "original.pdf"
            first, rest = [image.convert("RGB") for image in images][0], [image.convert("RGB") for image in images][1:]
            first.save(original_path, "PDF", resolution=float(self._params_from_dict({}).dpi), save_all=bool(rest), append_images=rest)
            self.repo.record_export(original_path, len(images))
            with fitz.open(original_path) as document:
                generated_page_count = document.page_count
        else:
            original_dir = post_dir / "original"
            original_dir.mkdir(parents=True, exist_ok=True)
            saved_paths = self._save_png_pages(images, original_dir)
            original_path = saved_paths[0]
            self.repo.record_export(original_path, len(saved_paths))
            generated_page_count = len(saved_paths)

        thumb = self._create_generated_post_thumbnail(int(post["id"]), original_path)
        return self.repo.update_generated_post(
            int(post["id"]),
            {
                "original_pdf_path": str(original_path),
                "output_format": clean_format,
                "thumb_path": str(thumb),
                "page_count": generated_page_count,
                "result_count": self._count_generated_results(results_dir),
                "sync_status": "local",
            },
        )

    def analyze_queue_item(self, item_id: int, force: bool = False) -> dict[str, Any]:
        item = self.repo.get_queue_item(item_id)
        params = self._params_from_dict(item["params"])
        return self.analyze_page(int(item["page_id"]), force=force, dpi=params.dpi)

    def update_queue_analysis(
        self,
        item_id: int,
        groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        item = self.repo.get_queue_item(item_id)
        return self.update_page_analysis(int(item["page_id"]), groups)

    def render_queue_previews(self, item_id: int) -> list[Path]:
        item = self.repo.get_queue_item(item_id)
        page_id = int(item["page_id"])
        params_dict = dict(item["params"])
        page = self.repo.get_page_with_copybook(page_id)
        params = self._params_from_dict(params_dict)
        outputs = self._render_page_images(page_id, params_dict)
        cache_key = _queue_preview_cache_key(item, page)
        paths = []
        for index, output in enumerate(outputs, start=1):
            output.thumbnail((1200, 1200))
            out_path = self.paths.previews_dir / f"queue-{item_id}-{cache_key}-{index}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            output.convert("RGB").save(out_path, "JPEG", quality=88)
            paths.append(out_path)
        return paths

    def render_queue_preview(self, item_id: int) -> Path:
        return self.render_queue_previews(item_id)[0]

    def export_queue_to_pdf(
        self,
        queue_item_ids: list[int],
        preset_id: int | None = None,
        output_path: str | None = None,
    ) -> Path:
        images = self._render_queue_images(queue_item_ids, preset_id)

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

    def next_generated_post_name(self) -> str:
        return f"卷{_chinese_number(self.repo.count_generated_posts() + 1)}"

    def export_queue_to_generated_post(
        self,
        queue_item_ids: list[int],
        name: str,
        preset_id: int | None = None,
        output_format: str = "pdf",
    ) -> dict[str, Any]:
        clean_name = name.strip()
        clean_format = output_format.strip().lower()
        if not clean_name:
            raise ValueError("generated post name cannot be empty")
        if not queue_item_ids:
            raise ValueError("queue_item_ids cannot be empty")
        if clean_format not in {"pdf", "png"}:
            raise ValueError("output_format must be pdf or png")

        post = self.repo.create_generated_post(clean_name, 0)
        post_dir = self._generated_post_dir(int(post["id"]))
        post_dir.mkdir(parents=True, exist_ok=True)
        results_dir = post_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        if clean_format == "pdf":
            original_path = post_dir / "original.pdf"
            self.export_queue_to_pdf(queue_item_ids, preset_id, str(original_path))
            with fitz.open(original_path) as document:
                generated_page_count = document.page_count
        else:
            original_dir = post_dir / "original"
            original_dir.mkdir(parents=True, exist_ok=True)
            images = self._render_queue_images(queue_item_ids, preset_id)
            saved_paths = self._save_png_pages(images, original_dir)
            original_path = saved_paths[0]
            self.repo.record_export(original_path, len(saved_paths))
            generated_page_count = len(saved_paths)

        thumb = self._create_generated_post_thumbnail(int(post["id"]), original_path)
        return self.repo.update_generated_post(
            int(post["id"]),
            {
                "original_pdf_path": str(original_path),
                "output_format": clean_format,
                "thumb_path": str(thumb),
                "page_count": generated_page_count,
                "result_count": self._count_generated_results(results_dir),
                "sync_status": "local",
            },
        )

    def list_generated_posts(self) -> list[dict[str, Any]]:
        posts = []
        for post in self.repo.list_generated_posts():
            posts.append(self._refresh_generated_post_file_counts(post))
        return posts

    def generated_post_thumbnail(self, post_id: int) -> Path | None:
        post = self.repo.get_generated_post(post_id)
        thumb_path = Path(post["thumb_path"]) if post.get("thumb_path") else None
        if thumb_path and thumb_path.exists():
            return thumb_path
        originals = self._generated_original_files(post)
        if not originals:
            return None
        thumb = self._create_generated_post_thumbnail(post_id, originals[0])
        self.repo.update_generated_post(post_id, {"thumb_path": str(thumb)})
        return thumb

    def list_generated_post_files(self, post_id: int) -> list[dict[str, Any]]:
        post = self.repo.get_generated_post(post_id)
        files = []
        for original in self._generated_original_files(post):
            files.append({"kind": "original", "name": original.name, "path": str(original), "size": original.stat().st_size})
        results_dir = self._generated_post_dir(post_id) / "results"
        for path in self._generated_files_in_dir(results_dir):
            files.append({"kind": "result", "name": path.name, "path": str(path), "size": path.stat().st_size})
        return files

    def sync_generated_post(self, post_id: int) -> dict[str, Any]:
        post = self.repo.get_generated_post(post_id)
        settings = self.repo.get_settings()
        client = _WebDavClient.from_settings(settings)
        remote_root = settings.get("webdav_remote_root", "Linmo").strip("/") or "Linmo"
        remote_post_dir = posixpath.join(remote_root, _safe_remote_name(str(post["name"])))
        remote_results_dir = posixpath.join(remote_post_dir, "results")

        self.repo.update_generated_post(post_id, {"sync_status": "syncing"})
        try:
            client.ensure_dir(remote_root)
            client.ensure_dir(remote_post_dir)
            client.ensure_dir(remote_results_dir)

            local_originals = self._generated_original_files(post)
            if not local_originals:
                raise ValueError("generated output does not exist")
            if str(post.get("output_format", "pdf")) == "png":
                remote_original_dir = posixpath.join(remote_post_dir, "original")
                client.ensure_dir(remote_original_dir)
                for local_original in local_originals:
                    remote_original = posixpath.join(remote_original_dir, local_original.name)
                    if client.exists(remote_original):
                        client.download(remote_original, local_original)
                    else:
                        client.upload(local_original, remote_original)
            else:
                local_original = local_originals[0]
                remote_original = posixpath.join(remote_post_dir, "original.pdf")
                if client.exists(remote_original):
                    client.download(remote_original, local_original)
                else:
                    client.upload(local_original, remote_original)

            results_dir = self._generated_post_dir(post_id) / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            for name in client.list_generated_files(remote_results_dir):
                client.download(posixpath.join(remote_results_dir, name), results_dir / name)

            thumb = self._create_generated_post_thumbnail(post_id, local_originals[0])
            return self.repo.update_generated_post(
                post_id,
                {
                    "thumb_path": str(thumb),
                    "result_count": self._count_generated_results(results_dir),
                    "sync_status": "synced",
                    "remote_path": remote_post_dir,
                    "last_synced_at": int(time.time()),
                },
            )
        except Exception:
            self.repo.update_generated_post(post_id, {"sync_status": "error"})
            raise

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

    def _apply_page_crop(self, image: Image.Image, page: dict[str, Any]) -> Image.Image:
        left_ratio = _copybook_crop_ratio(page.get("crop_left_ratio", 0))
        right_ratio = _copybook_crop_ratio(page.get("crop_right_ratio", 0))
        top_ratio = _copybook_crop_ratio(page.get("crop_top_ratio", 0))
        bottom_ratio = _copybook_crop_ratio(page.get("crop_bottom_ratio", 0))
        if left_ratio <= 0 and right_ratio <= 0 and top_ratio <= 0 and bottom_ratio <= 0:
            return image

        left = int(round(image.width * left_ratio))
        right = image.width - int(round(image.width * right_ratio))
        top = int(round(image.height * top_ratio))
        bottom = image.height - int(round(image.height * bottom_ratio))
        min_width = max(16, int(round(image.width * 0.1)))
        min_height = max(16, int(round(image.height * 0.1)))
        if right - left < min_width or bottom - top < min_height:
            image.close()
            raise ValueError("copybook crop margins leave too little page content")
        cropped = image.crop((left, top, right, bottom))
        image.close()
        return cropped

    def _apply_page_rotation(self, image: Image.Image, rotation_degrees: float) -> Image.Image:
        angle = _page_rotation_degrees(rotation_degrees)
        if abs(angle) < 0.001:
            return image
        normalized = angle % 360
        if abs(normalized - 90) < 0.001:
            rotated = image.transpose(Image.Transpose.ROTATE_90)
        elif abs(normalized - 180) < 0.001:
            rotated = image.transpose(Image.Transpose.ROTATE_180)
        elif abs(normalized - 270) < 0.001:
            rotated = image.transpose(Image.Transpose.ROTATE_270)
        else:
            rgb = image.convert("RGB")
            corners = [
                rgb.getpixel((0, 0)),
                rgb.getpixel((max(0, rgb.width - 1), 0)),
                rgb.getpixel((0, max(0, rgb.height - 1))),
                rgb.getpixel((max(0, rgb.width - 1), max(0, rgb.height - 1))),
            ]
            fill = tuple(sorted(color[channel] for color in corners)[len(corners) // 2] for channel in range(3))
            rotated = rgb.rotate(
                angle,
                resample=Image.Resampling.BICUBIC,
                expand=True,
                fillcolor=fill,
            )
            if rgb is not image:
                rgb.close()
        image.close()
        return rotated

    def _validate_crop_ratios(self, left_ratio: float, right_ratio: float, top_ratio: float, bottom_ratio: float) -> None:
        if left_ratio + right_ratio >= MAX_TOTAL_COPYBOOK_CROP_RATIO:
            raise ValueError("left and right crop margins are too large")
        if top_ratio + bottom_ratio >= MAX_TOTAL_COPYBOOK_CROP_RATIO:
            raise ValueError("top and bottom crop margins are too large")

    def _invalidate_copybook_page_caches(self, copybook_id: int) -> None:
        for page in self.repo.list_pages(copybook_id):
            page_id = int(page["id"])
            self._invalidate_page_caches(page_id)

    def _invalidate_page_caches(self, page_id: int) -> None:
        occurrence_ids = self.repo.list_page_glyph_occurrence_ids(page_id)
        for path in (
            self.paths.thumbs_dir / f"{page_id}.jpg",
            self.paths.previews_dir / f"source-{page_id}.jpg",
            self.paths.previews_dir / f"transform-{page_id}.jpg",
        ):
            if path.exists():
                path.unlink()
        for path in self.paths.previews_dir.glob(f"page-{page_id}-*.jpg"):
            path.unlink()
        for occurrence_id in occurrence_ids:
            for path in self.paths.glyphs_dir.glob(f"{occurrence_id}-*.png"):
                path.unlink()
        self.repo.delete_page_analysis(page_id)

    def _new_copybook_dir(self) -> Path:
        stamp = f"{int(time.time() * 1000)}"
        path = self.paths.library_dir / stamp
        path.mkdir(parents=True, exist_ok=False)
        return path

    def _generated_post_dir(self, post_id: int) -> Path:
        return self.paths.generated_dir / str(post_id)

    def _render_queue_images(
        self,
        queue_item_ids: list[int],
        preset_id: int | None = None,
    ) -> list[Image.Image]:
        if not queue_item_ids:
            raise ValueError("queue_item_ids cannot be empty")
        preset = self.repo.get_preset(preset_id) if preset_id else None
        images = []
        for item_id in queue_item_ids:
            item = self.repo.get_queue_item(int(item_id))
            params_dict = dict(item["params"])
            if preset:
                params_dict = self._apply_preset(params_dict, preset)
            images.extend(self._render_page_images(int(item["page_id"]), params_dict))
        return images

    def _render_page_images(
        self,
        page_id: int,
        params_dict: dict[str, Any],
    ) -> list[Image.Image]:
        params = self._params_from_dict(params_dict)
        page = self.repo.get_page_with_copybook(page_id)
        source = self.load_page_image(page, dpi=params.dpi)
        analysis = self.analyze_page(page_id, dpi=params.dpi)
        return render_practice_pages(source, analysis, params.grid)

    def _save_png_pages(self, images: list[Image.Image], output_dir: Path) -> list[Path]:
        saved_paths = []
        for index, image in enumerate(images, start=1):
            out_path = output_dir / f"{index:03d}.png"
            image.convert("RGB").save(out_path, "PNG")
            saved_paths.append(out_path)
        return saved_paths

    def _generated_original_files(self, post: dict[str, Any]) -> list[Path]:
        original = Path(post["original_pdf_path"]) if post.get("original_pdf_path") else None
        if str(post.get("output_format", "pdf")) == "png":
            original_dir = self._generated_post_dir(int(post["id"])) / "original"
            return self._generated_files_in_dir(original_dir)
        if original and original.exists():
            return [original]
        return []

    def _generated_files_in_dir(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in GENERATED_FILE_SUFFIXES)

    def _create_generated_post_thumbnail(self, post_id: int, source_path: Path) -> Path:
        thumb_path = self.paths.generated_thumbs_dir / f"{post_id}.jpg"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.suffix.lower() == ".pdf":
            with fitz.open(source_path) as document:
                if document.page_count == 0:
                    raise ValueError(f"generated PDF has no pages: {source_path}")
                page = document.load_page(0)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(120 / 72, 120 / 72), alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        else:
            image = Image.open(source_path).convert("RGB")
        image.thumbnail((260, 360))
        image.convert("RGB").save(thumb_path, "JPEG", quality=85)
        image.close()
        return thumb_path

    def _count_generated_results(self, results_dir: Path) -> int:
        return len(self._generated_files_in_dir(results_dir))

    def _refresh_generated_post_file_counts(self, post: dict[str, Any]) -> dict[str, Any]:
        results_dir = self._generated_post_dir(int(post["id"])) / "results"
        count = self._count_generated_results(results_dir)
        if int(post.get("result_count") or 0) != count:
            post = self.repo.update_generated_post(int(post["id"]), {"result_count": count})
        return post

    def _params_from_dict(self, data: dict[str, Any]) -> ProcessingParams:
        return ProcessingParams(
            grid_style=str(data.get("grid_style", "tian")),
            cell_size_mm=float(data.get("cell_size_mm", 15.0)),
            margin_mm=float(data.get("margin_mm", 15.0)),
            dpi=int(data.get("dpi", 300)),
        )

    def default_params_for_page(self, page_id: int) -> dict[str, Any]:
        return {
            "grid_style": "tian",
            "cell_size_mm": 15.0,
            "margin_mm": 15.0,
            "dpi": int(self.repo.get_settings().get("default_dpi", "300")),
        }

    def _apply_preset(self, params: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
        merged = dict(params)
        merged.update(preset.get("params", {}))
        return merged


def file_to_data_url(path: Path) -> str:
    mime = "image/jpeg"
    if path.suffix.lower() == ".png":
        mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _is_han_character(value: str) -> bool:
    if len(value) != 1:
        return False
    codepoint = ord(value)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x323AF
    )


def _matching_text_positions(old: str, new: str) -> list[tuple[int, int]]:
    old_length = len(old)
    new_length = len(new)
    table = [[0] * (new_length + 1) for _ in range(old_length + 1)]
    for old_index in range(old_length - 1, -1, -1):
        for new_index in range(new_length - 1, -1, -1):
            if old[old_index] == new[new_index]:
                table[old_index][new_index] = table[old_index + 1][new_index + 1] + 1
            else:
                table[old_index][new_index] = max(
                    table[old_index + 1][new_index],
                    table[old_index][new_index + 1],
                )
    matches = []
    old_index = 0
    new_index = 0
    while old_index < old_length and new_index < new_length:
        if old[old_index] == new[new_index]:
            matches.append((old_index, new_index))
            old_index += 1
            new_index += 1
        elif table[old_index + 1][new_index] >= table[old_index][new_index + 1]:
            old_index += 1
        else:
            new_index += 1
    return matches


def _collection_layout(
    text: str,
    direction: str,
    capacity: int,
) -> list[tuple[int, str, int, int]]:
    positions: list[tuple[int, str, int, int]] = []
    major = 0
    minor = 0
    for position, character in enumerate(text):
        if character == "\n":
            major += 1
            minor = 0
            continue
        if minor >= capacity:
            major += 1
            minor = 0
        if direction == "vertical":
            column, row = major, minor
        else:
            column, row = minor, major
        positions.append((position, character, column, row))
        minor += 1
    return positions


def _collection_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    bounds = draw.textbbox((0, 0), text, font=font)
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    x = box[0] + (box[2] - box[0] - text_width) // 2 - bounds[0]
    y = box[1] + (box[3] - box[1] - text_height) // 2 - bounds[1]
    draw.text((x, y), text, font=font, fill=fill)


def _safe_file_name(value: str) -> str:
    cleaned = "".join("_" if char in '<>:"/\\|?*' else char for char in value.strip())
    return cleaned.rstrip(". ")


def _queue_preview_cache_key(item: dict[str, Any], page: dict[str, Any]) -> str:
    payload = {
        "version": QUEUE_PREVIEW_CACHE_VERSION,
        "page_id": int(item["page_id"]),
        "page_no": int(page["page_no"]),
        "params": item["params"],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()[:12]


def _page_preview_cache_key(page_id: int, params: dict[str, Any], analysis: dict[str, Any]) -> str:
    payload = {
        "version": "page-glyph-v1",
        "page_id": int(page_id),
        "params": params,
        "analysis": analysis,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()[:12]


def _chinese_number(value: int) -> str:
    digits = "零一二三四五六七八九"
    if value <= 0:
        return str(value)
    if value < 10:
        return digits[value]
    if value < 20:
        return "十" + (digits[value % 10] if value % 10 else "")
    if value < 100:
        tens, ones = divmod(value, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        suffix = "" if rest == 0 else ("零" + _chinese_number(rest) if rest < 10 else _chinese_number(rest))
        return digits[hundreds] + "百" + suffix
    return str(value)


def _safe_remote_name(value: str) -> str:
    return value.replace("/", "／").replace("\\", "＼").strip() or "未命名"


def _page_rotation_degrees(value: Any) -> float:
    try:
        angle = float(value or 0)
    except (TypeError, ValueError):
        angle = 0.0
    if not math.isfinite(angle):
        angle = 0.0
    normalized = (angle + 180.0) % 360.0 - 180.0
    if abs(normalized) < 0.001:
        return 0.0
    return round(normalized, 3)


def _copybook_crop_ratio(value: Any) -> float:
    try:
        ratio = float(value or 0)
    except (TypeError, ValueError):
        ratio = 0.0
    if ratio < 0:
        return 0.0
    if ratio > MAX_COPYBOOK_CROP_RATIO:
        return MAX_COPYBOOK_CROP_RATIO
    return ratio


class _WebDavClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/") + "/"
        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, self.base_url, username, password)
        opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(password_manager))
        self._opener = opener

    @classmethod
    def from_settings(cls, settings: dict[str, str]) -> "_WebDavClient":
        url = settings.get("webdav_url", "").strip()
        username = settings.get("webdav_username", "").strip()
        password = settings.get("webdav_password", "")
        if not url or not username or not password:
            raise ValueError("请先在设置中填写 WebDAV 地址、用户名和应用密码")
        return cls(url, username, password)

    def exists(self, path: str, collection: bool = False) -> bool:
        try:
            self._request("PROPFIND", path, headers={"Depth": "0"}, collection=collection)
            return True
        except urllib.error.HTTPError as error:
            if error.code in {404, 410}:
                return False
            raise

    def ensure_dir(self, path: str) -> None:
        if self.exists(path, collection=True):
            return
        try:
            self._request("MKCOL", path, collection=True)
        except urllib.error.HTTPError as error:
            if error.code in {405, 409} and self.exists(path, collection=True):
                return
            raise

    def upload(self, local_path: Path, remote_path: str) -> None:
        content_type = "image/png" if local_path.suffix.lower() == ".png" else "application/pdf"
        self._request("PUT", remote_path, data=local_path.read_bytes(), headers={"Content-Type": content_type})

    def download(self, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with self._request("GET", remote_path) as response:
            local_path.write_bytes(response.read())

    def list_generated_files(self, path: str) -> list[str]:
        try:
            with self._request("PROPFIND", path, headers={"Depth": "1"}, collection=True) as response:
                data = response.read()
        except urllib.error.HTTPError as error:
            if error.code in {404, 410}:
                return []
            raise
        names: list[str] = []
        root = ET.fromstring(data)
        for response in root.findall("{DAV:}response"):
            href = response.findtext("{DAV:}href")
            if not href:
                continue
            name = urllib.parse.unquote(href.rstrip("/").split("/")[-1])
            if Path(name).suffix.lower() in GENERATED_FILE_SUFFIXES:
                names.append(name)
        return sorted(set(names))

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        collection: bool = False,
    ):
        quoted = "/".join(urllib.parse.quote(part) for part in path.strip("/").split("/") if part)
        if collection and quoted and not quoted.endswith("/"):
            quoted += "/"
        url = urllib.parse.urljoin(self.base_url, quoted)
        request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        return self._opener.open(request, timeout=30)
