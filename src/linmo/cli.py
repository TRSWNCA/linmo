from __future__ import annotations

import argparse
from pathlib import Path

from .image_pipeline import export_images
from .pages import parse_pages
from .processing import ProcessingParams, process_input_glyph_pages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linmo",
        description="Create calligraphy practice pages from copybook PDFs.",
    )
    parser.add_argument("input", type=Path, help="Input PDF path.")
    parser.add_argument("--pages", required=True, help="1-based pages, e.g. 41, 1-3, 1,3,5.")
    parser.add_argument(
        "--grid-style",
        choices=["tian", "mi"],
        default="tian",
        help="Practice grid style: tian (田字格) or mi (米字格).",
    )
    parser.add_argument("--cell-size-mm", type=float, default=15.0, help="Grid cell size in millimetres.")
    parser.add_argument("--margin-mm", type=float, default=15.0, help="A4 page margin in millimetres.")
    parser.add_argument("--dpi", type=int, default=300, help="PDF rendering DPI.")
    parser.add_argument("--out", type=Path, required=True, help="Output .png or .pdf path.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        pages = parse_pages(args.pages)
        outputs = []
        params = ProcessingParams(
            grid_style=args.grid_style,
            cell_size_mm=args.cell_size_mm,
            margin_mm=args.margin_mm,
            dpi=args.dpi,
        )

        for page_number in pages:
            _, rendered = process_input_glyph_pages(args.input, page_number, params)
            outputs.extend(rendered)
        if args.out.suffix.lower() == ".png" and len(outputs) > 1:
            for index, output in enumerate(outputs, start=1):
                path = args.out.with_name(f"{args.out.stem}-{index:03d}.png")
                export_images([output], path, args.dpi)
        else:
            export_images(outputs, args.out, args.dpi)
    except Exception as exc:
        parser.exit(2, f"linmo: error: {exc}\n")


if __name__ == "__main__":
    main()
