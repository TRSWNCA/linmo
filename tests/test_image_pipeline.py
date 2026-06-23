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

    def test_splits_gray_block_by_pale_vertical_rules(self) -> None:
        image = Image.new("RGB", (260, 220), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 20, 229, 199), fill=(120, 120, 120))
        for x in [30, 229]:
            draw.line((x, 20, x, 199), fill=(165, 165, 165), width=2)
        for x in [80, 130, 180]:
            draw.line((x, 20, x + 4, 199), fill=(165, 165, 165), width=2)

        detected = detect_gray_columns(image, expected_columns=None)

        self.assertEqual(len(detected.columns), 4)

    def test_splits_gray_block_by_weak_regular_vertical_rules(self) -> None:
        image = Image.new("RGB", (360, 260), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 20, 329, 239), fill=(120, 120, 120))
        for x in [30, 80, 130, 180, 230, 280, 329]:
            for y in range(20, 239, 28):
                draw.line((x, y, x, min(239, y + 18)), fill=(150, 150, 150), width=2)

        detected = detect_gray_columns(image, expected_columns=None)

        self.assertEqual(len(detected.columns), 6)

    def test_does_not_split_gray_column_on_fragmented_bright_strokes(self) -> None:
        image = Image.new("RGB", (180, 220), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 159, 199), fill=(120, 120, 120))
        for x in [20, 90, 159]:
            draw.line((x, 20, x, 199), fill=(245, 245, 245), width=2)
        for y in range(32, 160, 24):
            draw.line((55, y, 55, y + 14), fill=(245, 245, 245), width=2)

        detected = detect_gray_columns(image, expected_columns=None)

        self.assertEqual(len(detected.columns), 2)

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

    def test_adaptive_foreground_ignores_uneven_background(self) -> None:
        image = Image.new("RGB", (40, 60))
        pixels = image.load()
        for y in range(image.height):
            for x in range(image.width):
                tone = 180 + x
                pixels[x, y] = (tone, tone, tone)
        draw = ImageDraw.Draw(image)
        draw.line((8, 6, 27, 53), fill=(25, 25, 25), width=3)
        detected = DetectedColumns([ColumnBounds(0, 39)], top=0, bottom=59)

        output = compose_column_practice_page(
            image,
            detected,
            blank_ratio=1.0,
            extract_foreground=True,
            ink_color=(0, 0, 0),
            foreground_threshold=25,
        )

        self.assertLess(output.getpixel((16, 26))[0], 80)
        self.assertEqual(output.getpixel((34, 26)), (255, 255, 255))

    def test_adaptive_foreground_uses_color_difference(self) -> None:
        image = Image.new("RGB", (30, 50), (30, 120, 30))
        draw = ImageDraw.Draw(image)
        draw.line((14, 5, 14, 44), fill=(180, 30, 30), width=3)
        detected = DetectedColumns([ColumnBounds(0, 29)], top=0, bottom=49)

        output = compose_column_practice_page(
            image,
            detected,
            blank_ratio=1.0,
            extract_foreground=True,
            ink_color=(0, 0, 0),
            foreground_threshold=30,
        )

        self.assertLess(output.getpixel((14, 25))[0], 80)
        self.assertEqual(output.getpixel((3, 25)), (255, 255, 255))

    def test_global_foreground_method_keeps_legacy_behavior(self) -> None:
        image = Image.new("RGB", (30, 60), (120, 120, 120))
        draw = ImageDraw.Draw(image)
        draw.line((10, 5, 10, 54), fill=(245, 245, 245), width=3)
        detected = DetectedColumns([ColumnBounds(0, 29)], top=0, bottom=59)

        output = compose_column_practice_page(
            image,
            detected,
            blank_ratio=1.0,
            extract_foreground=True,
            ink_color=(20, 20, 20),
            foreground_threshold=30,
            foreground_method="global",
        )

        self.assertLess(output.getpixel((10, 20))[0], 80)
        self.assertEqual(output.getpixel((25, 20)), (255, 255, 255))

    def test_rejects_unknown_foreground_method(self) -> None:
        image = Image.new("RGB", (30, 60), (255, 255, 255))
        detected = DetectedColumns([ColumnBounds(0, 29)], top=0, bottom=59)

        with self.assertRaisesRegex(ValueError, "foreground_method"):
            compose_column_practice_page(
                image,
                detected,
                blank_ratio=1.0,
                extract_foreground=True,
                foreground_method="unknown",
            )

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
