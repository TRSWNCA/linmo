from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from linmo.image_pipeline import (
    ColumnBounds,
    DetectedColumns,
    compose_column_practice_page,
    compose_row_practice_page,
    detect_gray_columns,
    detect_ink_columns,
    detect_ruled_rows,
    parse_rgb_color,
)


class ImagePipelineTests(unittest.TestCase):
    def test_detects_seven_columns_in_synthetic_page(self) -> None:
        image = _synthetic_copybook_page()

        detected = detect_gray_columns(image, expected_columns=7)

        self.assertEqual(len(detected.columns), 7)
        self.assertEqual(detected.top, 30)
        self.assertEqual(detected.bottom, 229)
        self.assertEqual([column.width for column in detected.columns], [20] * 7)

    def test_auto_detects_gray_columns(self) -> None:
        image = _synthetic_copybook_page()

        detected = detect_gray_columns(image, expected_columns=None)

        self.assertEqual(len(detected.columns), 7)

    def test_composes_blank_strip_to_right_of_each_column(self) -> None:
        image = _synthetic_copybook_page()
        detected = detect_gray_columns(image, expected_columns=7)

        output = compose_column_practice_page(image, detected, blank_ratio=1.0)

        self.assertEqual(output.size, (280, 200))
        self.assertEqual(output.getpixel((10, 10)), (128, 128, 128))
        self.assertEqual(output.getpixel((30, 10)), (255, 255, 255))
        self.assertEqual(output.getpixel((50, 10)), (128, 128, 128))
        self.assertEqual(output.getpixel((70, 10)), (255, 255, 255))

    def test_extracts_light_foreground_from_dark_column_onto_background(self) -> None:
        image = Image.new("RGB", (30, 60), (120, 120, 120))
        draw = ImageDraw.Draw(image)
        draw.line((10, 5, 10, 54), fill=(245, 245, 245), width=3)
        detected = DetectedColumns([ColumnBounds(0, 29)], top=0, bottom=59)
        background = Image.new("RGB", (8, 8), (230, 220, 200))

        output = compose_column_practice_page(
            image,
            detected,
            blank_ratio=1.0,
            background=background,
            extract_foreground=True,
            ink_color=(20, 20, 20),
            foreground_threshold=30,
        )

        self.assertEqual(output.size, (60, 60))
        self.assertEqual(output.getpixel((1, 1)), (230, 220, 200))
        self.assertLess(output.getpixel((10, 20))[0], 80)
        self.assertEqual(output.getpixel((40, 20)), (230, 220, 200))

    def test_detects_ink_columns_in_synthetic_page(self) -> None:
        image = Image.new("RGB", (180, 220), (230, 210, 170))
        draw = ImageDraw.Draw(image)
        for x in [25, 75, 125]:
            draw.rectangle((x, 30, x + 18, 190), fill=(20, 20, 20))
        draw.text((120, 205), "red", fill=(180, 0, 0))

        detected = detect_ink_columns(image, expected_columns=3, ink_max=80)

        self.assertEqual(len(detected.columns), 3)
        self.assertLessEqual(detected.top, 35)
        self.assertGreaterEqual(detected.bottom, 185)

    def test_auto_detects_ink_columns(self) -> None:
        image = Image.new("RGB", (180, 220), (230, 210, 170))
        draw = ImageDraw.Draw(image)
        for x in [25, 75, 125]:
            draw.rectangle((x, 30, x + 18, 190), fill=(20, 20, 20))

        detected = detect_ink_columns(image, expected_columns=None, ink_max=80)

        self.assertEqual(len(detected.columns), 3)

    def test_detects_last_three_ruled_rows_in_synthetic_page(self) -> None:
        image = _synthetic_ruled_page()

        detected = detect_ruled_rows(image, expected_rows=3)

        self.assertEqual([(row.top, row.bottom) for row in detected.rows], [(60, 100), (100, 140), (140, 180)])
        self.assertEqual((detected.left, detected.right), (20, 219))

    def test_auto_detects_all_ruled_rows(self) -> None:
        image = _synthetic_ruled_page()

        detected = detect_ruled_rows(image, expected_rows=None)

        self.assertEqual(
            [(row.top, row.bottom) for row in detected.rows],
            [(20, 60), (60, 100), (100, 140), (140, 180)],
        )

    def test_composes_blank_strip_below_each_row(self) -> None:
        image = _synthetic_ruled_page()
        detected = detect_ruled_rows(image, expected_rows=3)

        output = compose_row_practice_page(image, detected, blank_ratio=1.0)

        self.assertEqual(output.size, (200, 246))
        self.assertEqual(output.getpixel((10, 0)), (180, 180, 180))
        self.assertEqual(output.getpixel((10, 40)), (180, 180, 180))
        self.assertEqual(output.getpixel((10, 50)), (255, 255, 255))
        self.assertEqual(output.getpixel((10, 82)), (180, 180, 180))

    def test_parse_rgb_color(self) -> None:
        self.assertEqual(parse_rgb_color("#1e2f3a"), (30, 47, 58))
        self.assertEqual(parse_rgb_color("ffffff"), (255, 255, 255))


def _synthetic_copybook_page() -> Image.Image:
    image = Image.new("RGB", (240, 260), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    x = 20
    for _ in range(7):
        draw.rectangle((x, 30, x + 19, 229), fill=(128, 128, 128))
        x += 30
    return image


def _synthetic_ruled_page() -> Image.Image:
    image = Image.new("RGB", (240, 220), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for y in [20, 60, 100, 140, 180]:
        draw.line((20, y, 219, y), fill=(180, 180, 180), width=1)
    return image


if __name__ == "__main__":
    unittest.main()
