from __future__ import annotations

import os
import unittest
from pathlib import Path

import fitz

from linmo.cli import build_parser, main as cli_main

os.environ["LINMO_DISABLE_OCR"] = "1"


RESOURCE_DIR = Path(__file__).parent / "resources"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "test_cli_resources"


class CliResourcesTests(unittest.TestCase):
    def test_cli_accepts_grid_parameters(self) -> None:
        args = build_parser().parse_args(
            [
                "input.png",
                "--pages",
                "1",
                "--grid-style",
                "mi",
                "--cell-size-mm",
                "15",
                "--out",
                "output.png",
            ]
        )

        self.assertEqual(args.grid_style, "mi")
        self.assertEqual(args.cell_size_mm, 15)

    def test_cli_generates_practice_pages_for_resource_directory(self) -> None:
        resource_paths = sorted(RESOURCE_DIR.glob("*.png"))
        self.assertGreater(resource_paths, [], "expected at least one PNG resource")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for resource_path in resource_paths:
            with self.subTest(resource=resource_path.name):
                output_path = OUTPUT_DIR / f"{resource_path.stem}-practice.pdf"
                cli_main(
                    [
                        str(resource_path),
                        "--pages",
                        "1",
                        "--grid-style",
                        "mi",
                        "--cell-size-mm",
                        "15",
                        "--dpi",
                        "72",
                        "--out",
                        str(output_path),
                    ]
                )

                self.assertTrue(output_path.is_file())
                with fitz.open(output_path) as document:
                    self.assertGreater(document.page_count, 0)
                    rect = document[0].rect
                    self.assertAlmostEqual(rect.width, 595, delta=2)
                    self.assertAlmostEqual(rect.height, 842, delta=2)


if __name__ == "__main__":
    unittest.main()
