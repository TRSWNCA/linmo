from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageStat

from linmo.cli import main as cli_main
from linmo.image_pipeline import detect_gray_columns, detect_ink_columns, detect_ruled_rows


RESOURCE_DIR = Path(__file__).parent / "resources"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "test_cli_resources"


class CliResourcesTests(unittest.TestCase):
    def test_cli_generates_practice_pages_for_resource_directory(self) -> None:
        resource_paths = sorted(RESOURCE_DIR.glob("*.png"))
        self.assertGreater(resource_paths, [], "expected at least one PNG resource")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for resource_path in resource_paths:
            with self.subTest(resource=resource_path.name):
                with Image.open(resource_path) as source_image:
                    source = source_image.convert("RGB")
                    mode_args = _mode_args_for(source)
                    detected_parts = _detected_part_count(source, mode_args)
                    source_size = source.size

                self.assertGreater(detected_parts, 1)
                output_path = OUTPUT_DIR / f"{resource_path.stem}-practice.png"
                cli_main(
                    [
                        str(resource_path),
                        "--pages",
                        "1",
                        "--blank-ratio",
                        "1.0",
                        "--dpi",
                        "72",
                        *mode_args,
                        "--out",
                        str(output_path),
                    ]
                )

                self.assertTrue(output_path.is_file())
                with Image.open(output_path) as output_image:
                    output = output_image.convert("RGB")

                self.assertGreater(output.width, 0)
                self.assertGreater(output.height, 0)
                self.assertGreater(_grayscale_range(output), 20)

                if _arg_value(mode_args, "--mode") == "row":
                    self.assertGreater(output.height, source_size[1])
                else:
                    self.assertGreater(output.width, source_size[0])


def _mode_args_for(image: Image.Image) -> list[str]:
    if _detected_ruled_row_count(image) >= 4:
        return ["--mode", "row"]
    if _dark_neutral_midtone_coverage(image) >= 0.2:
        return ["--mode", "col", "--column-detection", "gray"]
    return [
        "--mode",
        "col",
        "--column-detection",
        "ink",
        "--foreground-threshold",
        "35",
    ]


def _detected_ruled_row_count(image: Image.Image) -> int:
    try:
        return len(detect_ruled_rows(image, expected_rows=None).rows)
    except ValueError:
        return 0


def _detected_part_count(image: Image.Image, mode_args: list[str]) -> int:
    mode = _arg_value(mode_args, "--mode")
    if mode == "row":
        return len(detect_ruled_rows(image, expected_rows=None).rows)
    if _arg_value(mode_args, "--column-detection") == "gray":
        return len(detect_gray_columns(image, expected_columns=None).columns)
    return len(detect_ink_columns(image, expected_columns=None).columns)


def _dark_neutral_midtone_coverage(image: Image.Image) -> float:
    rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    gray = np.asarray(image.convert("L"), dtype=np.int16)
    channel_range = rgb.max(axis=2) - rgb.min(axis=2)
    dark_neutral_midtone = (channel_range <= 15) & (gray >= 70) & (gray <= 180)
    return float(dark_neutral_midtone.mean())


def _grayscale_range(image: Image.Image) -> int:
    minimum, maximum = ImageStat.Stat(image.convert("L")).extrema[0]
    return int(maximum - minimum)


def _arg_value(args: list[str], name: str) -> str:
    return args[args.index(name) + 1]


if __name__ == "__main__":
    unittest.main()
