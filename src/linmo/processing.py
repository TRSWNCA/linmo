from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .glyph_pipeline import GridParams, analyze_page, render_practice_pages
from .image_pipeline import (
    compose_column_practice_page,
    compose_row_practice_page,
    detect_gray_columns,
    detect_ink_columns,
    detect_ruled_rows,
    export_images,
    parse_rgb_color,
    render_pdf_page,
)


@dataclass(frozen=True)
class ProcessingParams:
    grid_style: str = "tian"
    cell_size_mm: float = 15.0
    margin_mm: float = 15.0
    mode: str = "row"
    column_detection: str = "gray"
    columns: int | None = None
    rows: int | None = None
    blank_ratio: float = 1.0
    dpi: int = 300
    gray_min: int = 70
    gray_max: int = 210
    ink_max: int = 170
    line_max: int = 225
    background_image: Path | None = None
    extract_foreground: bool = False
    ink_color: str = "#000000"
    foreground_threshold: int = 18
    foreground_method: str = "adaptive"

    @property
    def grid(self) -> GridParams:
        return GridParams(
            grid_style=self.grid_style,
            cell_size_mm=self.cell_size_mm,
            margin_mm=self.margin_mm,
            dpi=self.dpi,
        )


def load_input_page(input_path: Path, page_number: int, dpi: int) -> Image.Image:
    if input_path.suffix.lower() == ".pdf":
        return render_pdf_page(input_path, page_number, dpi)
    if page_number != 1:
        raise ValueError("image inputs only support page_number=1")
    with Image.open(input_path) as image:
        return image.convert("RGB").copy()


def process_image(image: Image.Image, params: ProcessingParams) -> Image.Image:
    background = Image.open(params.background_image) if params.background_image else None
    extract_foreground = params.extract_foreground or background is not None
    ink_color = parse_rgb_color(params.ink_color)

    try:
        if params.mode == "col":
            if params.column_detection == "gray":
                detected = detect_gray_columns(
                    image,
                    params.columns,
                    gray_min=params.gray_min,
                    gray_max=params.gray_max,
                )
            elif params.column_detection == "ink":
                detected = detect_ink_columns(image, params.columns, ink_max=params.ink_max)
            else:
                raise ValueError(f"unsupported column_detection: {params.column_detection}")

            return compose_column_practice_page(
                image,
                detected,
                blank_ratio=params.blank_ratio,
                blank_color=(255, 255, 255),
                background=background,
                extract_foreground=extract_foreground,
                ink_color=ink_color,
                foreground_threshold=params.foreground_threshold,
                foreground_method=params.foreground_method,
            )

        if params.mode == "row":
            detected = detect_ruled_rows(image, params.rows, line_max=params.line_max)
            return compose_row_practice_page(
                image,
                detected,
                blank_ratio=params.blank_ratio,
                blank_color=(255, 255, 255),
                background=background,
                extract_foreground=extract_foreground,
                ink_color=ink_color,
                foreground_threshold=params.foreground_threshold,
                foreground_method=params.foreground_method,
            )
    finally:
        if background is not None:
            background.close()

    raise ValueError(f"unsupported mode: {params.mode}")


def process_input_page(input_path: Path, page_number: int, params: ProcessingParams) -> Image.Image:
    return process_image(load_input_page(input_path, page_number, params.dpi), params)


def process_glyph_pages(
    image: Image.Image,
    params: ProcessingParams,
    analysis: dict | None = None,
) -> tuple[dict, list[Image.Image]]:
    page_analysis = analysis or analyze_page(image)
    return page_analysis, render_practice_pages(image, page_analysis, params.grid)


def process_input_glyph_pages(
    input_path: Path,
    page_number: int,
    params: ProcessingParams,
    analysis: dict | None = None,
) -> tuple[dict, list[Image.Image]]:
    image = load_input_page(input_path, page_number, params.dpi)
    return process_glyph_pages(image, params, analysis)


def export_processed_pages(
    pages: list[tuple[Path, int, ProcessingParams]],
    out_path: Path,
) -> None:
    images = [process_input_page(path, page_number, params) for path, page_number, params in pages]
    dpi = pages[0][2].dpi if pages else 300
    export_images(images, out_path, dpi)
