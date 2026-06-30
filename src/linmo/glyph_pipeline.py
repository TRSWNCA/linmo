from __future__ import annotations

import hashlib
import math
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .runtime import add_runtime_log, log_exception


ANALYSIS_VERSION = 4
OCR_MODEL_ID = "PP-OCRv6_medium"


@dataclass(frozen=True)
class GridParams:
    grid_style: str = "tian"
    cell_size_mm: float = 15.0
    margin_mm: float = 15.0
    dpi: int = 300

    def validate(self) -> None:
        if self.grid_style not in {"tian", "mi"}:
            raise ValueError("grid_style must be 'tian' or 'mi'")
        if not 10 <= self.cell_size_mm <= 30:
            raise ValueError("cell_size_mm must be between 10 and 30")
        if not 5 <= self.margin_mm <= 30:
            raise ValueError("margin_mm must be between 5 and 30")
        if self.dpi <= 0:
            raise ValueError("dpi must be positive")


class OcrEngine(Protocol):
    model_id: str

    def analyze(self, image: Image.Image) -> dict[str, Any]: ...


_DEFAULT_OCR_ENGINE: OcrEngine | None = None


class PaddleOcrEngine:
    """Lazy local PaddleOCR adapter.

    PaddleOCR changes its result wrapper between minor releases. The parser accepts
    both mapping results and Result objects exposing ``json``/``res``.
    """

    model_id = OCR_MODEL_ID

    def __init__(self) -> None:
        default_model_dir = Path.home() / ".local" / "share" / "linmo" / "models"
        os.environ.setdefault(
            "PADDLE_PDX_CACHE_HOME",
            os.environ.get("LINMO_MODEL_DIR", str(default_model_dir)),
        )
        os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "BOS")
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "本地 OCR 尚未安装；请执行 `uv sync` 后重试"
            ) from exc
        self._ocr = PaddleOCR(
            ocr_version="PP-OCRv6",
            lang="ch",
            return_word_box=True,
            use_doc_orientation_classify=True,
            use_doc_unwarping=False,
            use_textline_orientation=True,
        )

    def analyze(self, image: Image.Image) -> dict[str, Any]:
        raw_results = list(self._ocr.predict(np.asarray(image), return_word_box=True))
        if not raw_results:
            return _empty_analysis(self.model_id)
        payload = _result_payload(raw_results[0])
        return analysis_from_ocr_payload(payload, image.size, self.model_id, image=image)


def source_fingerprint(image: Image.Image) -> str:
    thumb = image.convert("L")
    thumb.thumbnail((256, 256))
    payload = f"{image.width}x{image.height}:".encode() + thumb.tobytes()
    return hashlib.sha256(payload).hexdigest()


def analyze_page(
    image: Image.Image,
    engine: OcrEngine | None = None,
    progress: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    """Analyze a page with local OCR, using a visible low-confidence fallback.

    The fallback exists for unsupported installations and tests. It never claims
    character semantics: every detected glyph is represented by ``□``.
    """

    if os.environ.get("LINMO_DISABLE_OCR") == "1" and engine is None:
        if progress:
            progress("fallback", "OCR 已禁用，正在使用降级定位")
        analysis = _fallback_analysis(image)
    else:
        try:
            selected_engine = engine
            if selected_engine is None:
                if _DEFAULT_OCR_ENGINE is None:
                    if progress:
                        progress("initializing_model", "正在初始化模型")
                    add_runtime_log("info", "backend.ocr", f"开始初始化 PaddleOCR 模型 {OCR_MODEL_ID}")
                selected_engine = _default_ocr_engine()
            if progress:
                progress("recognizing", "正在识别")
            add_runtime_log(
                "info",
                "backend.ocr",
                f"开始识别图像，尺寸 {image.width}x{image.height}，模型 {selected_engine.model_id}",
            )
            analysis = selected_engine.analyze(image)
            glyph_count = sum(len(group.get("glyphs", [])) for group in analysis.get("groups", []))
            add_runtime_log("info", "backend.ocr", f"识别完成：{len(analysis.get('groups', []))} 行，{glyph_count} 字")
        except Exception as exc:
            log_exception("backend.ocr", "PaddleOCR 初始化或识别失败，切换到降级定位", exc)
            analysis = _fallback_analysis(image)
            analysis["warning"] = (
                f"PaddleOCR 初始化或识别失败，已使用降级定位：{type(exc).__name__}: {exc}"
            )
            if progress:
                progress("fallback", "PaddleOCR 加载失败，已使用降级定位")
    analysis["version"] = ANALYSIS_VERSION
    analysis["dpi"] = int(analysis.get("dpi", 300))
    analysis["image_size"] = [image.width, image.height]
    analysis["source_fingerprint"] = source_fingerprint(image)
    analysis.setdefault("selection_mode", "ocr_groups")
    _normalize_analysis(analysis)
    return analysis


def _default_ocr_engine() -> OcrEngine:
    global _DEFAULT_OCR_ENGINE
    if _DEFAULT_OCR_ENGINE is None:
        _DEFAULT_OCR_ENGINE = PaddleOcrEngine()
    return _DEFAULT_OCR_ENGINE


def analysis_from_ocr_payload(
    payload: dict[str, Any],
    image_size: tuple[int, int],
    model_id: str = OCR_MODEL_ID,
    *,
    image: Image.Image | None = None,
) -> dict[str, Any]:
    raw_texts = _first_present(payload, "rec_texts", "texts")
    raw_scores = _first_present(payload, "rec_scores", "scores")
    texts = list(raw_texts) if raw_texts is not None else []
    scores = list(raw_scores) if raw_scores is not None else []
    raw_line_polys = _first_present(payload, "rec_polys", "dt_polys", "polys", "rec_boxes")
    line_polys = list(raw_line_polys) if raw_line_polys is not None else []
    word_boxes = _first_present(
        payload,
        "text_word_boxes",
        "rec_word_boxes",
        "word_boxes",
        "word_boxes_list",
    )
    if word_boxes is None:
        word_boxes = []
    groups: list[dict[str, Any]] = []
    for line_index, text in enumerate(texts):
        line_poly = _as_polygon(line_polys[line_index]) if line_index < len(line_polys) else None
        if line_poly is None:
            continue
        score = float(scores[line_index]) if line_index < len(scores) else 0.0
        direction = _direction_for_polygon(line_poly, str(text))
        boxes_for_line = word_boxes[line_index] if line_index < len(word_boxes) else None
        # PaddleOCR sorts word boxes geometrically without applying the same
        # permutation to text_word. The recognized line text is therefore the
        # canonical character order; boxes are sorted independently below.
        tokens = list(str(text))
        char_boxes = _character_boxes(tokens, line_poly, boxes_for_line, direction, image=image)
        glyphs = []
        for char_index, (char, box) in enumerate(zip(tokens, char_boxes)):
            glyphs.append(
                {
                    "id": f"g{line_index + 1}-{char_index + 1}",
                    "text": char,
                    "confidence": score,
                    "bbox": _polygon_bbox(box, image_size),
                    "polygon": box,
                    "included": True,
                    "kind": "punctuation" if _is_punctuation(char) else "character",
                }
            )
        if glyphs:
            groups.append(
                {
                    "id": f"line-{line_index + 1}",
                    "direction": direction,
                    "included": True,
                    "glyphs": glyphs,
                }
            )
    analysis = {
        "version": ANALYSIS_VERSION,
        "model_id": model_id,
        "engine": "paddleocr",
        "status": "ready",
        "selection_mode": "ocr_groups",
        "image_size": [image_size[0], image_size[1]],
        "groups": groups,
    }
    _select_main_body(analysis)
    _sort_groups(analysis)
    return analysis


def render_practice_pages(
    source: Image.Image,
    analysis: dict[str, Any],
    params: GridParams,
) -> list[Image.Image]:
    params.validate()
    page_width = round(210 / 25.4 * params.dpi)
    page_height = round(297 / 25.4 * params.dpi)
    margin = round(params.margin_mm / 25.4 * params.dpi)
    cell = round(params.cell_size_mm / 25.4 * params.dpi)
    columns = max(1, (page_width - margin * 2) // cell)
    pair_gap = max(2, round(1.5 / 25.4 * params.dpi))
    pair_height = cell * 2 + pair_gap

    logical_lines = _renderable_lines(analysis)
    if not logical_lines:
        raise ValueError("没有可排版的正文字符；请先检查识别与正文选择")
    glyph_scale = _common_glyph_scale(logical_lines, cell)

    pages: list[Image.Image] = []
    page = Image.new("RGB", (page_width, page_height), "white")
    y = margin
    for logical_line in logical_lines:
        for start in range(0, len(logical_line), columns):
            chunk = logical_line[start : start + columns]
            if y + pair_height > page_height - margin:
                pages.append(page)
                page = Image.new("RGB", (page_width, page_height), "white")
                y = margin
            for index, glyph in enumerate(chunk):
                x = margin + index * cell
                _draw_grid(page, (x, y), cell, params.grid_style)
                _draw_grid(page, (x, y + cell), cell, params.grid_style)
                _paste_glyph(page, source, glyph["bbox"], (x, y), cell, glyph_scale)
            y += pair_height
    pages.append(page)
    return pages


def update_analysis(
    analysis: dict[str, Any],
    *,
    groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    updated = dict(analysis)
    if groups is not None:
        updated["groups"] = groups
    updated.setdefault("selection_mode", "ocr_groups")
    _normalize_analysis(updated)
    updated["status"] = "reviewed"
    return updated


def _result_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        payload = result
    elif hasattr(result, "json"):
        payload = result.json
        if callable(payload):
            payload = payload()
    elif hasattr(result, "res"):
        payload = result.res
    else:
        raise ValueError("无法解析 PaddleOCR 返回结果")
    if isinstance(payload, dict) and isinstance(payload.get("res"), dict):
        payload = payload["res"]
    if not isinstance(payload, dict):
        raise ValueError("PaddleOCR 返回结果不是对象")
    return payload


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _empty_analysis(model_id: str) -> dict[str, Any]:
    return {
        "version": ANALYSIS_VERSION,
        "model_id": model_id,
        "engine": "paddleocr",
        "status": "ready",
        "groups": [],
    }


def _fallback_analysis(image: Image.Image) -> dict[str, Any]:
    gray = np.asarray(image.convert("L"), dtype=np.int16)
    background = np.asarray(
        image.convert("L").filter(ImageFilter.MedianFilter(size=31)), dtype=np.int16
    )
    ink = np.abs(gray - background) > 28
    row_projection = ink.sum(axis=1)
    active_rows = np.flatnonzero(row_projection > max(2, image.width * 0.008))
    row_runs = _runs(active_rows, max_gap=max(2, image.height // 300))
    groups = []
    glyph_index = 0
    for line_index, (top, bottom) in enumerate(row_runs):
        if bottom - top < max(3, image.height * 0.008):
            continue
        projection = ink[top : bottom + 1].sum(axis=0)
        active_cols = np.flatnonzero(projection > max(1, (bottom - top + 1) * 0.03))
        col_runs = _runs(active_cols, max_gap=max(2, (bottom - top + 1) // 5))
        glyphs = []
        for left, right in col_runs:
            if right - left < 2:
                continue
            glyph_index += 1
            glyphs.append(
                {
                    "id": f"fallback-{glyph_index}",
                    "text": "□",
                    "confidence": 0.0,
                    "bbox": [left, top, right + 1, bottom + 1],
                    "polygon": [[left, top], [right, top], [right, bottom], [left, bottom]],
                    "included": True,
                    "kind": "character",
                }
            )
        if glyphs:
            groups.append(
                {
                    "id": f"line-{line_index + 1}",
                    "direction": "horizontal",
                    "included": True,
                    "glyphs": glyphs,
                }
            )
    return {
        "version": ANALYSIS_VERSION,
        "model_id": "fallback-layout-only",
        "engine": "fallback",
        "status": "needs_ocr",
        "selection_mode": "ocr_groups",
        "warning": "未加载 PaddleOCR，当前仅提供低置信度字形定位",
        "groups": groups,
    }


def _select_main_body(analysis: dict[str, Any]) -> None:
    groups = analysis.get("groups", [])
    samples = []
    for group in groups:
        sizes = [
            min(glyph["bbox"][2] - glyph["bbox"][0], glyph["bbox"][3] - glyph["bbox"][1])
            for glyph in group["glyphs"]
            if glyph.get("kind") != "punctuation"
        ]
        if sizes:
            samples.append((group, float(np.median(sizes)), len(sizes)))
    if not samples:
        return
    buckets: dict[int, int] = {}
    for _, size, count in samples:
        bucket = max(1, round(math.log(max(1.0, size), 1.22)))
        buckets[bucket] = buckets.get(bucket, 0) + count
    dominant = max(buckets, key=buckets.get)
    dominant_sizes = [size for _, size, _ in samples if abs(round(math.log(max(1.0, size), 1.22)) - dominant) <= 1]
    target = float(np.median(dominant_sizes))
    for group, size, count in samples:
        group["included"] = count >= 2 and target * 0.62 <= size <= target * 1.55

    horizontal = [
        (group, size, count)
        for group, size, count in samples
        if group.get("included") and group.get("direction") != "vertical"
    ]
    vertical = [
        item
        for item in samples
        if item[0].get("included") and item[0].get("direction") == "vertical"
    ]
    if len(vertical) > len(horizontal):
        spans = [
            (
                group,
                max(glyph["bbox"][3] for glyph in group["glyphs"])
                - min(glyph["bbox"][1] for glyph in group["glyphs"]),
            )
            for group, _, _ in vertical
        ]
        if spans:
            maximum_span = max(span for _, span in spans)
            for group, span in spans:
                group["included"] = span >= maximum_span * 0.68
        return
    if len(horizontal) < 4:
        return

    counts = np.asarray([count for _, _, count in horizontal], dtype=float)
    minimum_body_length = max(3, int(math.floor(float(np.percentile(counts, 60)) * 0.55)))
    anchors = [item for item in horizontal if item[2] >= minimum_body_length]
    if len(anchors) < 3:
        return
    anchor_left = float(
        np.median(
            [
                min(glyph["bbox"][0] for glyph in group["glyphs"])
                for group, _, _ in anchors
            ]
        )
    )
    anchor_top = min(_group_center(group)[1] for group, _, _ in anchors)
    anchor_bottom = max(_group_center(group)[1] for group, _, _ in anchors)
    for group, size, count in horizontal:
        left = min(glyph["bbox"][0] for glyph in group["glyphs"])
        center_y = _group_center(group)[1]
        aligned_short_line = (
            anchor_top <= center_y <= anchor_bottom
            and abs(left - anchor_left) <= target * 1.8
        )
        group["included"] = count >= minimum_body_length or aligned_short_line


def _sort_groups(analysis: dict[str, Any]) -> None:
    groups = analysis.get("groups", [])
    horizontal = [group for group in groups if group.get("direction") != "vertical"]
    vertical = [group for group in groups if group.get("direction") == "vertical"]
    if len(vertical) > len(horizontal):
        groups.sort(key=lambda group: -_group_center(group)[0])
        for group in groups:
            group["glyphs"].sort(key=lambda glyph: (glyph["bbox"][1], glyph["bbox"][0]))
    else:
        groups.sort(key=lambda group: (_group_center(group)[1], _group_center(group)[0]))
        for group in groups:
            group["glyphs"].sort(key=lambda glyph: (glyph["bbox"][0], glyph["bbox"][1]))


def _normalize_analysis(analysis: dict[str, Any]) -> None:
    analysis.setdefault("selection_mode", "ocr_groups")
    for group_index, group in enumerate(analysis.get("groups", [])):
        group.setdefault("id", f"line-{group_index + 1}")
        group.setdefault("direction", "horizontal")
        group.setdefault("included", True)
        for glyph_index, glyph in enumerate(group.get("glyphs", [])):
            glyph.setdefault("id", f"{group['id']}-{glyph_index + 1}")
            glyph.setdefault("text", "□")
            glyph.setdefault("confidence", 0.0)
            glyph.setdefault("included", True)
            glyph["bbox"] = [int(round(value)) for value in glyph["bbox"]]
            glyph["kind"] = (
                "punctuation" if _is_punctuation(str(glyph.get("text", ""))) else "character"
            )
    _sort_groups(analysis)


def _renderable_lines(analysis: dict[str, Any]) -> list[list[dict[str, Any]]]:
    if analysis.get("selection_mode") == "ordered_stream":
        ordered_glyphs: list[dict[str, Any]] = []
        for group in analysis.get("groups", []):
            if not group.get("included", True):
                continue
            ordered_glyphs.extend(
                glyph for glyph in group.get("glyphs", [])
                if glyph.get("included", True)
            )
        line = _renderable_line(ordered_glyphs)
        return [line] if line else []

    lines = []
    for group in analysis.get("groups", []):
        if not group.get("included", True):
            continue
        glyphs = [glyph for glyph in group.get("glyphs", []) if glyph.get("included", True)]
        output = _renderable_line(glyphs)
        if output:
            lines.append(output)
    return lines


def _renderable_line(glyphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    pending_prefix: list[int] | None = None
    for glyph in glyphs:
        bbox = list(glyph["bbox"])
        if glyph.get("kind") == "punctuation":
            if _is_opening_punctuation(str(glyph.get("text", ""))):
                pending_prefix = _union_bbox(pending_prefix, bbox)
            elif output:
                output[-1]["bbox"] = _union_bbox(output[-1]["bbox"], bbox)
            continue
        if pending_prefix is not None:
            bbox = _union_bbox(pending_prefix, bbox)
            pending_prefix = None
        output.append({"text": glyph.get("text", "□"), "bbox": bbox})
    return output


def _paste_glyph(
    output: Image.Image,
    source: Image.Image,
    bbox: list[int],
    origin: tuple[int, int],
    cell: int,
    common_scale: float,
) -> None:
    left, top, right, bottom = bbox
    width, height = right - left, bottom - top
    padding = max(1, round(max(width, height) * 0.03))
    crop_box = (
        max(0, left - padding),
        max(0, top - padding),
        min(source.width, right + padding),
        min(source.height, bottom + padding),
    )
    crop = source.crop(crop_box).convert("RGB")
    alpha, ink = _extract_glyph(crop)
    max_size = round(cell * 0.92)
    scale = min(
        common_scale,
        max_size / max(1, crop.width),
        max_size / max(1, crop.height),
    )
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    alpha = alpha.resize(size, Image.Resampling.LANCZOS)
    ink = ink.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    x = origin[0] + (cell - size[0]) // 2
    y = origin[1] + (cell - size[1]) // 2
    output.paste(ink, (x, y), alpha)


def _common_glyph_scale(logical_lines: list[list[dict[str, Any]]], cell: int) -> float:
    extents = []
    for line in logical_lines:
        for glyph in line:
            left, top, right, bottom = glyph["bbox"]
            extent = max(right - left, bottom - top)
            if extent > 0:
                extents.append(extent)
    if not extents:
        return 1.0
    reference = float(np.percentile(extents, 90))
    return max(0.01, cell * 0.80 / max(1.0, reference))


def _extract_glyph(crop: Image.Image) -> tuple[Image.Image, Image.Image]:
    color_mask = _color_aware_ink_mask(crop)
    crop = crop.convert("L")
    short = max(1, min(crop.size))
    gray = np.asarray(crop, dtype=np.int16)
    corner_width = max(1, round(short * 0.025))
    background_samples = np.concatenate(
        (
            gray[:corner_width, :corner_width].ravel(),
            gray[:corner_width, -corner_width:].ravel(),
            gray[-corner_width:, :corner_width].ravel(),
            gray[-corner_width:, -corner_width:].ravel(),
        )
    )
    border_background = int(np.median(background_samples))
    global_distance = np.abs(gray - border_background)
    if float(np.std(background_samples)) <= 18:
        distance = global_distance
    else:
        radius = max(3.0, short * 0.18)
        local_background = np.asarray(crop.filter(ImageFilter.GaussianBlur(radius)), dtype=np.int16)
        distance = np.maximum(np.abs(gray - local_background), global_distance // 2)
    nonzero = distance[distance > 0]
    high = int(np.percentile(nonzero, 95)) if nonzero.size else 0
    threshold = (
        min(max(8, int(np.percentile(nonzero, 62))), max(8, round(high * 0.45)))
        if nonzero.size
        else 255
    )
    scale = max(10, high - threshold) if nonzero.size else 10
    alpha = np.clip(
        (distance.astype(np.int32) - threshold) * 255 / scale, 0, 255
    ).astype(np.uint8)
    # Drop weak near-background pixels aggressively; residual paper tint is worse than
    # a slightly thinner stroke for practice sheets.
    low_alpha_cutoff = max(28, min(72, threshold * 2))
    alpha = np.where(alpha >= low_alpha_cutoff, alpha, 0).astype(np.uint8)
    alpha = np.where(color_mask, alpha, 0).astype(np.uint8)
    alpha_image = (
        Image.fromarray(alpha, "L")
        .filter(ImageFilter.MaxFilter(3))
        .filter(ImageFilter.MinFilter(3))
    )
    texture = np.clip(gray - np.maximum(distance // 3, 0), 0, 235).astype(np.uint8)
    return alpha_image, Image.fromarray(texture, "L")


def _draw_grid(
    image: Image.Image,
    origin: tuple[int, int],
    cell: int,
    style: str,
) -> None:
    draw = ImageDraw.Draw(image)
    x, y = origin
    color = (204, 112, 112)
    helper = (224, 164, 164)
    outer_width = max(1, round(cell * 0.008))
    helper_width = max(1, round(cell * 0.004))
    draw.rectangle((x, y, x + cell, y + cell), outline=color, width=outer_width)
    _draw_dashed(draw, (x + cell // 2, y, x + cell // 2, y + cell), helper, helper_width, cell)
    _draw_dashed(draw, (x, y + cell // 2, x + cell, y + cell // 2), helper, helper_width, cell)
    if style == "mi":
        _draw_dashed(draw, (x, y, x + cell, y + cell), helper, helper_width, cell)
        _draw_dashed(draw, (x + cell, y, x, y + cell), helper, helper_width, cell)


def _draw_dashed(
    draw: ImageDraw.ImageDraw,
    line: tuple[int, int, int, int],
    color: tuple[int, int, int],
    width: int,
    cell: int,
) -> None:
    x1, y1, x2, y2 = line
    length = math.hypot(x2 - x1, y2 - y1)
    dash = max(3, round(cell * 0.045))
    for start in range(0, round(length), dash * 2):
        end = min(round(length), start + dash)
        a = start / max(1, length)
        b = end / max(1, length)
        draw.line(
            (
                round(x1 + (x2 - x1) * a),
                round(y1 + (y2 - y1) * a),
                round(x1 + (x2 - x1) * b),
                round(y1 + (y2 - y1) * b),
            ),
            fill=color,
            width=width,
        )


def _character_boxes(
    tokens: list[str],
    line_poly: list[list[int]],
    raw_boxes: Any,
    direction: str,
    *,
    image: Image.Image | None = None,
) -> list[list[list[int]]]:
    parsed = []
    if isinstance(raw_boxes, (list, tuple)):
        for raw in raw_boxes:
            polygon = _as_polygon(raw)
            if polygon is not None:
                parsed.append(polygon)
    parsed.sort(
        key=lambda polygon: (
            _polygon_center(polygon)[1],
            _polygon_center(polygon)[0],
        )
        if direction == "vertical"
        else (
            _polygon_center(polygon)[0],
            _polygon_center(polygon)[1],
        )
    )
    initial = parsed if len(parsed) == len(tokens) else _equal_character_boxes(tokens, line_poly, direction)
    if image is None or len(tokens) <= 1:
        return initial
    try:
        return _refine_character_boxes_from_ink(
            tokens,
            line_poly,
            initial,
            direction,
            image,
        )
    except Exception as exc:
        add_runtime_log(
            "warning",
            "backend.segmentation",
            f"笔墨边界细化失败，保留 OCR 字框：{type(exc).__name__}: {exc}",
            echo=False,
        )
        return initial


def _equal_character_boxes(
    tokens: list[str],
    line_poly: list[list[int]],
    direction: str,
) -> list[list[list[int]]]:
    left, top, right, bottom = _polygon_bbox(line_poly, None)
    count = max(1, len(tokens))
    if direction == "vertical":
        return [
            [[left, round(top + i * (bottom - top) / count)],
             [right, round(top + i * (bottom - top) / count)],
             [right, round(top + (i + 1) * (bottom - top) / count)],
             [left, round(top + (i + 1) * (bottom - top) / count)]]
            for i in range(count)
        ]
    return [
        [[round(left + i * (right - left) / count), top],
         [round(left + (i + 1) * (right - left) / count), top],
         [round(left + (i + 1) * (right - left) / count), bottom],
         [round(left + i * (right - left) / count), bottom]]
        for i in range(count)
    ]


def _refine_character_boxes_from_ink(
    tokens: list[str],
    line_poly: list[list[int]],
    initial_boxes: list[list[list[int]]],
    direction: str,
    image: Image.Image,
) -> list[list[list[int]]]:
    left, top, right, bottom = _polygon_bbox(line_poly, image.size)
    if right - left < 2 or bottom - top < 2:
        return initial_boxes
    crop = image.crop((left, top, right, bottom)).convert("RGB")
    ink = _line_ink_mask(crop)
    vertical = direction == "vertical"
    projection = ink.sum(axis=1 if vertical else 0).astype(np.float64)
    if not projection.size or not np.any(projection):
        return initial_boxes
    projection = np.convolve(projection, np.array([1, 2, 3, 2, 1], dtype=np.float64) / 9, mode="same")
    axis_start = top if vertical else left
    axis_end = bottom if vertical else right
    raw_anchors = []
    for previous, following in zip(initial_boxes, initial_boxes[1:]):
        previous_box = _polygon_bbox(previous, None)
        following_box = _polygon_bbox(following, None)
        previous_end = previous_box[3] if vertical else previous_box[2]
        following_start = following_box[1] if vertical else following_box[0]
        raw_anchors.append((previous_end + following_start) / 2 - axis_start)
    boundaries = _projection_boundaries(
        projection,
        len(tokens),
        raw_anchors,
        cross_size=(right - left) if vertical else (bottom - top),
    )
    axis_boundaries = [0, *boundaries, axis_end - axis_start]
    refined = []
    nominal = (axis_end - axis_start) / max(1, len(tokens))
    padding = max(1, round(nominal * 0.025))
    for index in range(len(tokens)):
        segment_start = int(axis_boundaries[index])
        segment_end = int(axis_boundaries[index + 1])
        if segment_end <= segment_start:
            refined.append(initial_boxes[index])
            continue
        segment = ink[segment_start:segment_end, :] if vertical else ink[:, segment_start:segment_end]
        ys, xs = np.nonzero(segment)
        if not len(xs):
            refined.append(initial_boxes[index])
            continue
        if vertical:
            box_left = max(left, left + int(xs.min()) - padding)
            box_right = min(right, left + int(xs.max()) + 1 + padding)
            box_top = max(top + segment_start, top + segment_start + int(ys.min()) - padding)
            box_bottom = min(top + segment_end, top + segment_start + int(ys.max()) + 1 + padding)
        else:
            box_left = max(left + segment_start, left + segment_start + int(xs.min()) - padding)
            box_right = min(left + segment_end, left + segment_start + int(xs.max()) + 1 + padding)
            box_top = max(top, top + int(ys.min()) - padding)
            box_bottom = min(bottom, top + int(ys.max()) + 1 + padding)
        if box_right <= box_left or box_bottom <= box_top:
            refined.append(initial_boxes[index])
            continue
        refined.append(
            [
                [box_left, box_top],
                [box_right, box_top],
                [box_right, box_bottom],
                [box_left, box_bottom],
            ]
        )
    return refined


def _color_aware_ink_mask(crop: Image.Image) -> np.ndarray:
    rgb = np.asarray(crop.convert("RGB"), dtype=np.float64)
    height, width = rgb.shape[:2]
    if not height or not width:
        return np.zeros((height, width), dtype=bool)
    border = max(1, round(min(width, height) * 0.04))
    border_samples = np.concatenate(
        (
            rgb[:border, :, :].reshape(-1, 3),
            rgb[-border:, :, :].reshape(-1, 3),
            rgb[:, :border, :].reshape(-1, 3),
            rgb[:, -border:, :].reshape(-1, 3),
        ),
        axis=0,
    )
    background = np.median(border_samples, axis=0)
    delta = background.reshape(1, 1, 3) - rgb
    distance = np.linalg.norm(delta, axis=2)
    normalized_distance = np.clip(distance / math.sqrt(3), 0, 255).astype(np.uint8)
    threshold = max(8, _otsu_threshold(normalized_distance))
    foreground = normalized_distance >= threshold
    if int(foreground.sum()) < 12:
        return foreground

    vectors = delta[foreground]
    norms = np.linalg.norm(vectors, axis=1)
    valid = norms > 1e-6
    if int(valid.sum()) < 12:
        return foreground
    directions = vectors[valid] / norms[valid, None]
    centers = _cluster_color_directions(directions)
    if len(centers) <= 1:
        return foreground
    separation = max(
        1.0 - float(np.dot(first, second))
        for index, first in enumerate(centers)
        for second in centers[index + 1 :]
    )
    if separation < 0.06:
        return foreground

    foreground_positions = np.argwhere(foreground)
    valid_positions = foreground_positions[valid]
    labels = np.argmax(directions @ centers.T, axis=1)
    edge_x = max(1, round(width * 0.07))
    edge_y = max(1, round(height * 0.07))
    central_left, central_right = width * 0.14, width * 0.86
    central_top, central_bottom = height * 0.14, height * 0.86
    scores = []
    for label in range(len(centers)):
        positions = valid_positions[labels == label]
        if not len(positions):
            scores.append(float("-inf"))
            continue
        ys = positions[:, 0]
        xs = positions[:, 1]
        central_count = int(
            (
                (xs >= central_left)
                & (xs <= central_right)
                & (ys >= central_top)
                & (ys <= central_bottom)
            ).sum()
        )
        edge_count = int(
            (
                (xs < edge_x)
                | (xs >= width - edge_x)
                | (ys < edge_y)
                | (ys >= height - edge_y)
            ).sum()
        )
        active_columns = len(np.unique(xs))
        active_rows = len(np.unique(ys))
        line_like = (
            (active_columns >= width * 0.78 and active_rows <= height * 0.20)
            or (active_rows >= height * 0.78 and active_columns <= width * 0.20)
        )
        score = central_count * 2.0 + len(positions) * 0.32 - edge_count * 1.35
        if line_like:
            score -= len(positions) * 1.5
        scores.append(score)
    selected_label = int(np.argmax(scores))
    selected_center = centers[selected_label]
    compatible_labels = {
        index
        for index, center in enumerate(centers)
        if float(np.dot(center, selected_center)) >= 0.94
    }
    selected = np.zeros((height, width), dtype=bool)
    selected_positions = valid_positions[
        np.isin(labels, list(compatible_labels))
    ]
    selected[selected_positions[:, 0], selected_positions[:, 1]] = True
    if int(selected.sum()) < max(8, round(int(foreground.sum()) * 0.05)):
        return foreground
    return selected


def _cluster_color_directions(directions: np.ndarray) -> np.ndarray:
    if len(directions) > 6000:
        step = max(1, len(directions) // 6000)
        samples = directions[::step][:6000]
    else:
        samples = directions
    center = samples.mean(axis=0)
    norm = float(np.linalg.norm(center))
    if norm <= 1e-6:
        center = samples[0]
    else:
        center = center / norm
    centers = [center]
    target_count = min(3, max(1, len(samples) // 12))
    while len(centers) < target_count:
        similarities = samples @ np.asarray(centers).T
        candidate = samples[int(np.argmin(np.max(similarities, axis=1)))]
        if max(float(np.dot(candidate, existing)) for existing in centers) > 0.995:
            break
        centers.append(candidate)
    centers_array = np.asarray(centers, dtype=np.float64)
    for _ in range(10):
        labels = np.argmax(samples @ centers_array.T, axis=1)
        updated = []
        for index, current in enumerate(centers_array):
            members = samples[labels == index]
            if not len(members):
                updated.append(current)
                continue
            member_center = members.mean(axis=0)
            member_norm = float(np.linalg.norm(member_center))
            updated.append(member_center / member_norm if member_norm > 1e-6 else current)
        next_centers = np.asarray(updated)
        if np.max(np.abs(next_centers - centers_array)) < 1e-4:
            centers_array = next_centers
            break
        centers_array = next_centers
    return centers_array


def _line_ink_mask(crop: Image.Image) -> np.ndarray:
    return _color_aware_ink_mask(crop)


def _otsu_threshold(values: np.ndarray) -> int:
    histogram = np.bincount(values.ravel(), minlength=256).astype(np.float64)
    total = histogram.sum()
    if total <= 0:
        return 255
    weighted_total = float(np.dot(np.arange(256), histogram))
    background_weight = 0.0
    background_sum = 0.0
    best_variance = -1.0
    best_threshold = 0
    for threshold in range(256):
        background_weight += histogram[threshold]
        if background_weight <= 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight <= 0:
            break
        background_sum += threshold * histogram[threshold]
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_total - background_sum) / foreground_weight
        variance = background_weight * foreground_weight * (background_mean - foreground_mean) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return best_threshold


def _projection_boundaries(
    projection: np.ndarray,
    count: int,
    raw_anchors: list[float],
    *,
    cross_size: int,
) -> list[int]:
    if count <= 1:
        return []
    length = len(projection)
    nominal = length / count
    min_width = max(1, round(nominal * 0.18))
    max_width = max(min_width + 1, round(nominal * 2.25))
    boundary_cost = np.zeros(length + 1, dtype=np.float64)
    for position in range(1, length):
        boundary_cost[position] = (
            projection[max(0, position - 1)] + projection[min(length - 1, position)]
        ) / max(1, cross_size * 2)

    candidate_sets: list[list[int]] = []
    for index in range(1, count):
        anchor = raw_anchors[index - 1] if index - 1 < len(raw_anchors) else nominal * index
        expected = nominal * index
        center = anchor if 0 < anchor < length else expected
        radius = nominal * 0.78
        lower = max(min_width * index, round(center - radius))
        upper = min(length - min_width * (count - index), round(center + radius))
        if upper < lower:
            lower = max(min_width * index, round(expected - radius))
            upper = min(length - min_width * (count - index), round(expected + radius))
        ranked = sorted(
            range(lower, upper + 1),
            key=lambda position: (
                boundary_cost[position] + 0.025 * ((position - center) / max(1.0, nominal)) ** 2,
                abs(position - center),
            ),
        )
        candidates = sorted(set(ranked[:48] + [max(lower, min(upper, round(center)))]))
        candidate_sets.append(candidates)

    states: dict[int, tuple[float, list[int]]] = {0: (0.0, [])}
    for candidates in candidate_sets:
        next_states: dict[int, tuple[float, list[int]]] = {}
        for position in candidates:
            best: tuple[float, list[int]] | None = None
            for previous, (cost, path) in states.items():
                width = position - previous
                if width < min_width or width > max_width:
                    continue
                width_cost = 0.045 * ((width - nominal) / max(1.0, nominal)) ** 2
                candidate = (cost + boundary_cost[position] * 2.4 + width_cost, [*path, position])
                if best is None or candidate[0] < best[0]:
                    best = candidate
            if best is not None:
                next_states[position] = best
        if not next_states:
            return [round(length * index / count) for index in range(1, count)]
        states = next_states

    best_final: tuple[float, list[int]] | None = None
    for previous, (cost, path) in states.items():
        width = length - previous
        if width < min_width or width > max_width:
            continue
        final_cost = cost + 0.045 * ((width - nominal) / max(1.0, nominal)) ** 2
        if best_final is None or final_cost < best_final[0]:
            best_final = (final_cost, path)
    if best_final is None:
        return [round(length * index / count) for index in range(1, count)]
    return best_final[1]


def _as_polygon(value: Any) -> list[list[int]] | None:
    array = np.asarray(value)
    if array.size == 4 and array.ndim == 1:
        left, top, right, bottom = [int(round(float(item))) for item in array]
        return [[left, top], [right, top], [right, bottom], [left, bottom]]
    if array.ndim == 2 and array.shape[0] >= 4 and array.shape[1] >= 2:
        return [[int(round(float(x))), int(round(float(y)))] for x, y in array[:4, :2]]
    return None


def _polygon_bbox(
    polygon: list[list[int]],
    image_size: tuple[int, int] | None,
) -> list[int]:
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    if image_size is not None:
        left = max(0, min(image_size[0] - 1, left))
        top = max(0, min(image_size[1] - 1, top))
        right = max(left + 1, min(image_size[0], right))
        bottom = max(top + 1, min(image_size[1], bottom))
    return [left, top, right, bottom]


def _polygon_center(polygon: list[list[int]]) -> tuple[float, float]:
    left, top, right, bottom = _polygon_bbox(polygon, None)
    return (left + right) / 2, (top + bottom) / 2


def _direction_for_polygon(polygon: list[list[int]], text: str) -> str:
    left, top, right, bottom = _polygon_bbox(polygon, None)
    return "vertical" if bottom - top > (right - left) * 1.35 and len(text) > 1 else "horizontal"


def _group_center(group: dict[str, Any]) -> tuple[float, float]:
    boxes = [glyph["bbox"] for glyph in group.get("glyphs", [])]
    if not boxes:
        return 0.0, 0.0
    return (
        sum((box[0] + box[2]) / 2 for box in boxes) / len(boxes),
        sum((box[1] + box[3]) / 2 for box in boxes) / len(boxes),
    )


def _is_punctuation(text: str) -> bool:
    return bool(text) and all(unicodedata.category(char).startswith("P") for char in text)


def _is_opening_punctuation(text: str) -> bool:
    return text in {"（", "(", "【", "[", "《", "〈", "“", "‘", "「", "『"}


def _union_bbox(first: list[int] | None, second: list[int]) -> list[int]:
    if first is None:
        return list(second)
    return [
        min(first[0], second[0]),
        min(first[1], second[1]),
        max(first[2], second[2]),
        max(first[3], second[3]),
    ]


def _runs(values: np.ndarray, max_gap: int = 0) -> list[tuple[int, int]]:
    if values.size == 0:
        return []
    output = []
    start = previous = int(values[0])
    for raw in values[1:]:
        value = int(raw)
        if value <= previous + max_gap + 1:
            previous = value
            continue
        output.append((start, previous))
        start = previous = value
    output.append((start, previous))
    return output
