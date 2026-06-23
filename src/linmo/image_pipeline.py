from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageFilter


@dataclass(frozen=True)
class ColumnBounds:
    left: int
    right: int

    @property
    def width(self) -> int:
        return self.right - self.left + 1


@dataclass(frozen=True)
class DetectedColumns:
    columns: list[ColumnBounds]
    top: int
    bottom: int

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1


@dataclass(frozen=True)
class RowBounds:
    top: int
    bottom: int

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1


@dataclass(frozen=True)
class DetectedRows:
    rows: list[RowBounds]
    left: int
    right: int

    @property
    def width(self) -> int:
        return self.right - self.left + 1


def render_pdf_page(pdf_path: Path, page_number: int, dpi: int) -> Image.Image:
    """Render a 1-based PDF page number to an RGB Pillow image."""
    if dpi <= 0:
        raise ValueError("dpi must be positive")

    with fitz.open(pdf_path) as document:
        if page_number < 1 or page_number > document.page_count:
            raise ValueError(
                f"page {page_number} is outside the PDF page range 1-{document.page_count}"
            )

        page = document.load_page(page_number - 1)
        zoom = dpi / 72.0
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def detect_gray_columns(
    image: Image.Image,
    expected_columns: int | None,
    *,
    gray_min: int = 70,
    gray_max: int = 210,
    column_coverage_ratio: float = 0.35,
    row_coverage_ratio: float = 0.35,
    min_column_width_ratio: float = 0.03,
) -> DetectedColumns:
    """Detect the main gray vertical copybook columns in a rendered page."""
    if expected_columns is not None and expected_columns < 1:
        raise ValueError("expected_columns must be >= 1")
    if not 0 <= gray_min <= gray_max <= 255:
        raise ValueError("gray_min and gray_max must satisfy 0 <= min <= max <= 255")

    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    gray_mask = (gray >= gray_min) & (gray <= gray_max)

    column_threshold = max(1, int(height * column_coverage_ratio))
    candidate_x = np.flatnonzero(gray_mask.sum(axis=0) >= column_threshold)
    min_width = max(1, int(width * min_column_width_ratio))
    columns = [
        ColumnBounds(start, end)
        for start, end in _contiguous_runs(candidate_x)
        if end - start + 1 >= min_width
    ]
    if not columns:
        raise ValueError("could not detect gray columns")

    left = min(column.left for column in columns)
    right = max(column.right for column in columns)
    span_width = right - left + 1
    row_threshold = max(1, int(span_width * row_coverage_ratio))
    candidate_y = np.flatnonzero(gray_mask[:, left : right + 1].sum(axis=1) >= row_threshold)
    row_runs = _contiguous_runs(candidate_y)
    if not row_runs:
        raise ValueError("could not detect the vertical bounds of the gray columns")

    top, bottom = max(row_runs, key=lambda run: run[1] - run[0])
    columns = _split_gray_columns_by_bright_separators(gray, columns, top, bottom, min_width)

    if expected_columns is not None and len(columns) != expected_columns:
        raise ValueError(
            "detected "
            f"{len(columns)} gray columns after separator splitting, expected {expected_columns}; "
            "try changing --columns or the gray detection thresholds"
        )

    return DetectedColumns(columns=columns, top=top, bottom=bottom)


def detect_ink_columns(
    image: Image.Image,
    expected_columns: int | None,
    *,
    ink_max: int = 170,
    column_coverage_ratio: float = 0.08,
    row_coverage_ratio: float = 0.03,
    min_column_width_ratio: float = 0.04,
    vertical_padding_ratio: float = 0.015,
) -> DetectedColumns:
    """Detect vertical text columns from dark neutral ink instead of gray panels."""
    if expected_columns is not None and expected_columns < 1:
        raise ValueError("expected_columns must be >= 1")
    if not 0 <= ink_max <= 255:
        raise ValueError("ink_max must satisfy 0 <= ink_max <= 255")

    red_grid = _detect_red_column_grid(image)
    if red_grid is not None:
        columns, top, bottom = red_grid
        if expected_columns is not None and len(columns) != expected_columns:
            raise ValueError(
                "detected "
                f"{len(columns)} red-ruled columns, expected {expected_columns}; "
                "try changing --columns or the input crop"
            )
        return DetectedColumns(columns=columns, top=top, bottom=bottom)

    mask = _dark_neutral_mask(image, ink_max)
    height, width = mask.shape

    y_start = int(height * 0.04)
    y_end = int(height * 0.96)
    working = mask[y_start:y_end, :]

    projection = working.sum(axis=0).astype(float)
    window = max(5, int(width * 0.03))
    smooth = np.convolve(projection, np.ones(window) / window, mode="same")

    column_threshold = max(1, int(working.shape[0] * column_coverage_ratio))
    candidate_x = np.flatnonzero(smooth >= column_threshold)
    min_width = max(1, int(width * min_column_width_ratio))
    ink_runs = [(start, end) for start, end in _contiguous_runs(candidate_x) if end - start + 1 >= min_width]
    columns = _ink_runs_to_column_slots(image, ink_runs)

    if expected_columns is not None and len(columns) != expected_columns:
        raise ValueError(
            "detected "
            f"{len(columns)} ink columns, expected {expected_columns}; "
            "try changing --columns, --ink-max, or the input crop"
        )

    left = min(column.left for column in columns)
    right = max(column.right for column in columns)
    span_width = right - left + 1
    row_threshold = max(1, int(span_width * row_coverage_ratio))
    candidate_y = np.flatnonzero(mask[:, left : right + 1].sum(axis=1) >= row_threshold)
    if candidate_y.size == 0:
        raise ValueError("could not detect the vertical bounds of the ink columns")

    vertical_padding = max(0, int(height * vertical_padding_ratio))
    top = max(0, int(candidate_y.min()) - vertical_padding)
    bottom = min(height - 1, int(candidate_y.max()) + vertical_padding)
    return DetectedColumns(columns=columns, top=top, bottom=bottom)


def detect_ruled_rows(
    image: Image.Image,
    expected_rows: int | None,
    *,
    line_max: int = 225,
    line_coverage_ratio: float = 0.55,
    min_gap_ratio: float = 0.025,
) -> DetectedRows:
    """Detect horizontal ruled copybook rows."""
    if expected_rows is not None and expected_rows < 1:
        raise ValueError("expected_rows must be >= 1")
    if not 0 <= line_max <= 255:
        raise ValueError("line_max must satisfy 0 <= line_max <= 255")

    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    central_left = int(width * 0.08)
    central_right = int(width * 0.92)
    line_mask = gray <= line_max

    central_width = central_right - central_left
    row_threshold = max(1, int(central_width * line_coverage_ratio))
    candidate_y = np.flatnonzero(
        line_mask[:, central_left:central_right].sum(axis=1) >= row_threshold
    )
    line_runs = _contiguous_runs(candidate_y)
    line_ys = [(start + end) // 2 for start, end in line_runs]

    min_gap = max(1, int(height * min_gap_ratio))
    bands = [
        RowBounds(top, bottom)
        for top, bottom in zip(line_ys, line_ys[1:])
        if bottom - top + 1 >= min_gap
    ]
    if not bands:
        raise ValueError("could not detect horizontal ruled rows")
    if expected_rows is not None and len(bands) < expected_rows:
        raise ValueError(
            "detected "
            f"{len(bands)} ruled rows, expected at least {expected_rows}; "
            "try changing --rows or --line-max"
        )

    selected = bands if expected_rows is None else bands[-expected_rows:]
    left, right = _detect_horizontal_rule_span(gray, line_mask, selected)
    return DetectedRows(rows=selected, left=left, right=right)


def compose_column_practice_page(
    image: Image.Image,
    detected: DetectedColumns,
    *,
    blank_ratio: float = 1.0,
    blank_color: tuple[int, int, int] = (255, 255, 255),
    background: Image.Image | None = None,
    extract_foreground: bool = False,
    ink_color: tuple[int, int, int] = (30, 30, 30),
    foreground_threshold: int = 28,
    foreground_method: str = "adaptive",
) -> Image.Image:
    """Insert a blank practice strip to the physical right of each detected column."""
    if blank_ratio <= 0:
        raise ValueError("blank_ratio must be positive")

    placements: list[tuple[Image.Image, int, int]] = []
    total_width = 0
    output_height = detected.height

    source = image.convert("RGB")
    for column in detected.columns:
        original = source.crop((column.left, detected.top, column.right + 1, detected.bottom + 1))
        blank_width = max(1, round(original.width * blank_ratio))
        placements.append((original, total_width, 0))
        total_width += blank_width + original.width

    output = _make_background((total_width, output_height), background, blank_color)
    for original, x, y in placements:
        _paste_original(
            output,
            original,
            x,
            y,
            extract_foreground,
            ink_color,
            foreground_threshold,
            foreground_method,
        )
    return output


def compose_row_practice_page(
    image: Image.Image,
    detected: DetectedRows,
    *,
    blank_ratio: float = 1.0,
    blank_color: tuple[int, int, int] = (255, 255, 255),
    background: Image.Image | None = None,
    extract_foreground: bool = False,
    ink_color: tuple[int, int, int] = (30, 30, 30),
    foreground_threshold: int = 28,
    foreground_method: str = "adaptive",
) -> Image.Image:
    """Insert a blank practice strip below each detected horizontal row."""
    if blank_ratio <= 0:
        raise ValueError("blank_ratio must be positive")

    placements: list[tuple[Image.Image, int, int]] = []
    total_height = 0
    output_width = detected.width

    source = image.convert("RGB")
    for row in detected.rows:
        original = source.crop((detected.left, row.top, detected.right + 1, row.bottom + 1))
        blank_height = max(1, round(original.height * blank_ratio))
        placements.append((original, 0, total_height))
        total_height += original.height + blank_height

    output = _make_background((output_width, total_height), background, blank_color)
    for original, x, y in placements:
        _paste_original(
            output,
            original,
            x,
            y,
            extract_foreground,
            ink_color,
            foreground_threshold,
            foreground_method,
        )
    return output


def parse_rgb_color(value: str) -> tuple[int, int, int]:
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise ValueError("color must be in #RRGGBB format")
    try:
        return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError as exc:
        raise ValueError("color must be in #RRGGBB format") from exc


def export_images(images: list[Image.Image], out_path: Path, dpi: int) -> None:
    if not images:
        raise ValueError("no images to export")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = out_path.suffix.lower()
    rgb_images = [image.convert("RGB") for image in images]

    if suffix == ".png":
        if len(rgb_images) != 1:
            raise ValueError("PNG export supports exactly one page; use PDF for multiple pages")
        rgb_images[0].save(out_path, format="PNG", dpi=(dpi, dpi))
    elif suffix == ".pdf":
        first, rest = rgb_images[0], rgb_images[1:]
        first.save(
            out_path,
            format="PDF",
            resolution=float(dpi),
            save_all=bool(rest),
            append_images=rest,
        )
    else:
        raise ValueError("output path must end with .png or .pdf")


def _contiguous_runs(values: np.ndarray) -> list[tuple[int, int]]:
    if values.size == 0:
        return []

    runs: list[tuple[int, int]] = []
    start = int(values[0])
    previous = start
    for value in values[1:]:
        current = int(value)
        if current == previous + 1:
            previous = current
            continue
        runs.append((start, previous))
        start = previous = current
    runs.append((start, previous))
    return runs


def _make_background(
    size: tuple[int, int],
    background: Image.Image | None,
    fallback_color: tuple[int, int, int],
) -> Image.Image:
    if background is None:
        return Image.new("RGB", size, fallback_color)

    pattern = background.convert("RGB")
    output = Image.new("RGB", size)
    for y in range(0, size[1], pattern.height):
        for x in range(0, size[0], pattern.width):
            output.paste(pattern, (x, y))
    return output


def _dark_neutral_mask(image: Image.Image, ink_max: int) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    gray = np.asarray(image.convert("L"), dtype=np.int16)
    red_dominant = (
        (rgb[:, :, 0] > 80)
        & (rgb[:, :, 0] > rgb[:, :, 1] + 25)
        & (rgb[:, :, 0] > rgb[:, :, 2] + 25)
    )
    return (gray <= ink_max) & ~red_dominant


def _ink_runs_to_column_slots(
    image: Image.Image,
    ink_runs: list[tuple[int, int]],
) -> list[ColumnBounds]:
    if not ink_runs:
        return []

    gray = np.asarray(image.convert("L"), dtype=np.int16)
    height, width = gray.shape
    paper_mask = gray <= 230
    paper_x = np.flatnonzero(paper_mask.sum(axis=0) > height * 0.05)
    if paper_x.size:
        paper_left = int(paper_x.min())
        paper_right = int(paper_x.max())
    else:
        paper_left = max(0, ink_runs[0][0] - int(width * 0.04))
        paper_right = min(width - 1, ink_runs[-1][1] + int(width * 0.04))

    columns: list[ColumnBounds] = []
    for index, (start, end) in enumerate(ink_runs):
        if index == 0:
            left = paper_left
        else:
            previous_end = ink_runs[index - 1][1]
            left = (previous_end + start) // 2 + 1

        if index == len(ink_runs) - 1:
            right = paper_right
        else:
            next_start = ink_runs[index + 1][0]
            right = (end + next_start) // 2

        columns.append(ColumnBounds(max(0, left), min(width - 1, right)))
    return columns


def _split_gray_columns_by_bright_separators(
    gray: np.ndarray,
    columns: list[ColumnBounds],
    top: int,
    bottom: int,
    min_width: int,
) -> list[ColumnBounds]:
    split_columns: list[ColumnBounds] = []

    for column in columns:
        crop = gray[top : bottom + 1, column.left : column.right + 1]
        if crop.shape[1] < min_width * 2:
            split_columns.append(column)
            continue

        separator_runs = _detect_bright_separator_runs(crop)
        if len(separator_runs) < 2:
            split_columns.append(column)
            continue

        local_slots = []
        for left_separator, right_separator in zip(separator_runs, separator_runs[1:]):
            left = column.left + left_separator[1] + 1
            right = column.left + right_separator[0] - 1
            if right - left + 1 >= min_width:
                local_slots.append(ColumnBounds(left, right))

        split_columns.extend(local_slots or [column])

    return split_columns


def _detect_bright_separator_runs(crop: np.ndarray) -> list[tuple[int, int]]:
    local_background = int(np.percentile(crop, 50))
    bright_threshold = min(245, local_background + 20)
    bright = crop >= bright_threshold

    width = crop.shape[1]
    tolerances = [max(2, int(width * 0.0025)), max(2, int(width * 0.006))]
    candidates: list[list[tuple[int, int]]] = []
    for tolerance in sorted(set(tolerances)):
        expanded = _horizontal_max_filter(bright, tolerance)
        for coverage in (0.55, 0.50, 0.45, 0.40):
            candidates.append(_separator_runs_for_coverage(expanded, coverage))

    regular = _best_regular_separator_runs(candidates, width)
    if regular:
        return regular

    strict_runs = candidates[0] if candidates else []
    relaxed_runs = candidates[2] if len(candidates) > 2 else strict_runs
    if _separator_runs_are_regular(relaxed_runs):
        return relaxed_runs
    return strict_runs


def _separator_runs_for_coverage(mask: np.ndarray, coverage_ratio: float) -> list[tuple[int, int]]:
    min_separator_pixels = max(1, int(mask.shape[0] * coverage_ratio))
    separator_x = np.flatnonzero(mask.sum(axis=0) >= min_separator_pixels)
    return _contiguous_runs(separator_x)


def _separator_runs_are_regular(runs: list[tuple[int, int]]) -> bool:
    if len(runs) < 4:
        return False

    centers = np.asarray([(start + end) / 2 for start, end in runs], dtype=float)
    gaps = np.diff(centers)
    median_gap = float(np.median(gaps))
    if median_gap <= 0:
        return False

    return bool(np.all(np.abs(gaps - median_gap) <= median_gap * 0.18))


def _best_regular_separator_runs(
    candidates: list[list[tuple[int, int]]],
    crop_width: int,
) -> list[tuple[int, int]]:
    best_runs: list[tuple[int, int]] = []
    best_score = float("-inf")

    for runs in candidates:
        if len(runs) < 4:
            continue
        centers = np.asarray([(start + end) / 2 for start, end in runs], dtype=float)
        for first_index in range(len(runs) - 3):
            for last_index in range(first_index + 3, len(runs)):
                span = centers[last_index] - centers[first_index]
                if span < crop_width * 0.45:
                    continue
                max_count = min(12, last_index - first_index + 1)
                for count in range(max_count, 3, -1):
                    gap = span / (count - 1)
                    if not crop_width * 0.07 <= gap <= crop_width * 0.30:
                        continue

                    matched = _match_regular_separator_sequence(
                        runs,
                        centers,
                        first_index,
                        last_index,
                        count,
                        gap,
                    )
                    if matched is None:
                        continue

                    matched_runs, average_error = matched
                    coverage = (
                        ((matched_runs[-1][0] + matched_runs[-1][1]) / 2)
                        - ((matched_runs[0][0] + matched_runs[0][1]) / 2)
                    ) / max(1, crop_width)
                    score = count * 100 + coverage * 20 - average_error / max(1, gap)
                    if score > best_score:
                        best_score = score
                        best_runs = matched_runs

    return best_runs


def _match_regular_separator_sequence(
    runs: list[tuple[int, int]],
    centers: np.ndarray,
    first_index: int,
    last_index: int,
    count: int,
    gap: float,
) -> tuple[list[tuple[int, int]], float] | None:
    tolerance = max(4.0, gap * 0.10)
    expected_start = centers[first_index]
    matched_indices: list[int] = []
    total_error = 0.0
    search_start = first_index

    for step in range(count):
        expected = expected_start + gap * step
        search_end = last_index + 1
        distances = np.abs(centers[search_start:search_end] - expected)
        if distances.size == 0:
            return None

        relative_index = int(distances.argmin())
        error = float(distances[relative_index])
        if error > tolerance:
            return None

        matched_index = search_start + relative_index
        matched_indices.append(matched_index)
        total_error += error
        search_start = matched_index + 1

    return [runs[index] for index in matched_indices], total_error / count


def _horizontal_max_filter(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask

    padded = np.pad(mask, ((0, 0), (radius, radius)), constant_values=False)
    output = np.zeros_like(mask, dtype=bool)
    for offset in range(radius * 2 + 1):
        output |= padded[:, offset : offset + mask.shape[1]]
    return output


def _detect_red_column_grid(image: Image.Image) -> tuple[list[ColumnBounds], int, int] | None:
    rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    height, width = rgb.shape[:2]
    red_mask = (
        (rgb[:, :, 0] > 150)
        & (rgb[:, :, 0] > rgb[:, :, 1] + 45)
        & (rgb[:, :, 0] > rgb[:, :, 2] + 45)
    )

    min_vertical_pixels = max(3, int(height * 0.35))
    candidate_x = np.flatnonzero(red_mask.sum(axis=0) >= min_vertical_pixels)
    vertical_runs = _contiguous_runs(candidate_x)
    if len(vertical_runs) < 3:
        return None

    centers = [(start + end) // 2 for start, end in vertical_runs]
    min_slot_width = max(8, int(width * 0.035))
    boundaries: list[int] = []
    for center in centers:
        if boundaries and center - boundaries[-1] < min_slot_width:
            boundaries[-1] = (boundaries[-1] + center) // 2
        else:
            boundaries.append(center)

    columns = [
        ColumnBounds(left + 1, right - 1)
        for left, right in zip(boundaries, boundaries[1:])
        if right - left - 1 >= min_slot_width
    ]
    if len(columns) < 2:
        return None

    grid_slice = red_mask[:, max(0, boundaries[0] - 1) : min(width, boundaries[-1] + 2)]
    grid_y = np.flatnonzero(grid_slice.any(axis=1))
    if grid_y.size == 0:
        return None

    return columns, int(grid_y.min()), int(grid_y.max())


def _paste_original(
    output: Image.Image,
    original: Image.Image,
    x: int,
    y: int,
    extract_foreground: bool,
    ink_color: tuple[int, int, int],
    foreground_threshold: int,
    foreground_method: str,
) -> None:
    if not extract_foreground:
        output.paste(original, (x, y))
        return

    alpha = _extract_foreground_alpha(original, foreground_threshold, foreground_method)
    ink = Image.new("RGB", original.size, ink_color)
    output.paste(ink, (x, y), alpha)


def _extract_foreground_alpha(
    image: Image.Image,
    threshold: int,
    method: str = "adaptive",
) -> Image.Image:
    if threshold < 0:
        raise ValueError("foreground_threshold must be >= 0")
    if method == "adaptive":
        return _extract_adaptive_foreground_alpha(image, threshold)
    if method == "global":
        return _extract_global_foreground_alpha(image, threshold)
    raise ValueError("foreground_method must be 'adaptive' or 'global'")


def _extract_global_foreground_alpha(image: Image.Image, threshold: int) -> Image.Image:
    if threshold < 0:
        raise ValueError("foreground_threshold must be >= 0")

    gray = np.asarray(image.convert("L"), dtype=np.int16)
    background = int(np.median(gray))
    dark_count = int((gray < background - threshold).sum())
    light_count = int((gray > background + threshold).sum())
    low = int(np.percentile(gray, 5))
    high = int(np.percentile(gray, 95))

    dark_score = dark_count * max(0, background - low)
    light_score = light_count * max(0, high - background)

    if light_score > dark_score:
        distance = gray - background
    else:
        distance = background - gray

    alpha = np.where(distance > threshold, 255, 0).astype(np.uint8)
    return Image.fromarray(alpha, mode="L")


def _extract_adaptive_foreground_alpha(image: Image.Image, threshold: int) -> Image.Image:
    if threshold < 0:
        raise ValueError("foreground_threshold must be >= 0")

    source = image.convert("RGB")
    width, height = source.size
    window = _foreground_background_window(width, height)

    local_rgb = source.filter(ImageFilter.MedianFilter(size=window))
    rgb = np.asarray(source, dtype=np.int16)
    background_rgb = np.asarray(local_rgb, dtype=np.int16)
    channel_distance = np.abs(rgb - background_rgb).max(axis=2)

    gray = np.asarray(source.convert("L"), dtype=np.int16)
    background_gray = np.asarray(local_rgb.convert("L"), dtype=np.int16)
    gray_distance = np.abs(gray - background_gray)
    distance = np.maximum(channel_distance, gray_distance)

    if threshold == 0:
        alpha = np.where(distance > 0, 255, 0).astype(np.uint8)
    else:
        scale = max(1, threshold)
        alpha_distance = distance.astype(np.int32) - threshold
        alpha = np.clip(alpha_distance * 255 // scale, 0, 255).astype(np.uint8)

    alpha_image = Image.fromarray(alpha, mode="L")
    return alpha_image.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))


def _foreground_background_window(width: int, height: int) -> int:
    short_side = max(1, min(width, height))
    size = max(9, min(61, int(short_side * 0.08)))
    if size % 2 == 0:
        size += 1
    return size


def _detect_horizontal_rule_span(
    gray: np.ndarray,
    line_mask: np.ndarray,
    rows: list[RowBounds],
) -> tuple[int, int]:
    height, width = gray.shape
    samples: list[np.ndarray] = []
    for row in rows:
        for y in (row.top, row.bottom):
            start = max(0, y - 1)
            end = min(height, y + 2)
            samples.append(line_mask[start:end].any(axis=0))

    if not samples:
        return 0, width - 1

    stacked = np.vstack(samples)
    threshold = max(1, int(stacked.shape[0] * 0.45))
    candidate_x = np.flatnonzero(stacked.sum(axis=0) >= threshold)
    runs = _contiguous_runs(candidate_x)
    if not runs:
        content_x = np.flatnonzero(gray < 245)
        if content_x.size == 0:
            return 0, width - 1
        return int(content_x.min()), int(content_x.max())

    return max(runs, key=lambda run: run[1] - run[0])
