from __future__ import annotations

import argparse
from pathlib import Path

from .image_pipeline import export_images
from .pages import parse_pages
from .processing import ProcessingParams, process_input_page


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linmo",
        description="Create calligraphy practice pages from copybook PDFs.",
    )
    parser.add_argument("input", type=Path, help="Input PDF path.")
    parser.add_argument("--pages", required=True, help="1-based pages, e.g. 41, 1-3, 1,3,5.")
    parser.add_argument("--mode", choices=["col", "row"], default="col", help="Split mode.")
    parser.add_argument("--columns", type=int, help="Expected number of vertical columns. Auto-detected when omitted.")
    parser.add_argument("--rows", type=int, help="Expected number of horizontal ruled rows. Auto-detected when omitted.")
    parser.add_argument(
        "--column-detection",
        choices=["gray", "ink"],
        default="gray",
        help="Column detection strategy for col mode.",
    )
    parser.add_argument("--blank-style", choices=["white"], default="white", help="Blank practice area style.")
    parser.add_argument("--blank-ratio", type=float, default=1.0, help="Blank width relative to each source column.")
    parser.add_argument("--dpi", type=int, default=300, help="PDF rendering DPI.")
    parser.add_argument("--out", type=Path, required=True, help="Output .png or .pdf path.")
    parser.add_argument("--gray-min", type=int, default=70, help="Minimum gray value for column background detection.")
    parser.add_argument("--gray-max", type=int, default=210, help="Maximum gray value for column background detection.")
    parser.add_argument("--ink-max", type=int, default=170, help="Maximum gray value for dark ink column detection.")
    parser.add_argument("--line-max", type=int, default=225, help="Maximum gray value for horizontal rule detection.")
    parser.add_argument(
        "--background-image",
        type=Path,
        help="Optional texture/background image. When set, source foreground is extracted and redrawn on this background.",
    )
    parser.add_argument(
        "--extract-foreground",
        action="store_true",
        help="Extract text/line foreground and redraw it on the output background.",
    )
    parser.add_argument("--ink-color", default="#1e1e1e", help="Foreground ink color in #RRGGBB format.")
    parser.add_argument(
        "--foreground-threshold",
        type=int,
        default=18,
        help="Minimum grayscale distance from the estimated background for foreground extraction.",
    )
    parser.add_argument(
        "--foreground-method",
        choices=["adaptive", "global"],
        default="adaptive",
        help="Foreground extraction strategy. adaptive uses local contrast; global keeps the legacy median threshold.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        pages = parse_pages(args.pages)
        outputs = []
        params = ProcessingParams(
            mode=args.mode,
            column_detection=args.column_detection,
            columns=args.columns,
            rows=args.rows,
            blank_ratio=args.blank_ratio,
            dpi=args.dpi,
            gray_min=args.gray_min,
            gray_max=args.gray_max,
            ink_max=args.ink_max,
            line_max=args.line_max,
            background_image=args.background_image,
            extract_foreground=args.extract_foreground,
            ink_color=args.ink_color,
            foreground_threshold=args.foreground_threshold,
            foreground_method=args.foreground_method,
        )

        for page_number in pages:
            outputs.append(process_input_page(args.input, page_number, params))
        export_images(outputs, args.out, args.dpi)
    except Exception as exc:
        parser.exit(2, f"linmo: error: {exc}\n")


if __name__ == "__main__":
    main()
