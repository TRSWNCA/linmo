from __future__ import annotations

import unittest

import numpy as np
from PIL import Image, ImageDraw

from linmo.glyph_pipeline import (
    GridParams,
    _extract_glyph,
    analyze_page,
    analysis_from_ocr_payload,
    render_practice_pages,
    update_analysis,
)


class GlyphPipelineTests(unittest.TestCase):
    def test_ocr_failure_reports_reason_and_progress_before_fallback(self) -> None:
        class FailingEngine:
            model_id = "failing-test-engine"

            def analyze(self, image: Image.Image) -> dict:
                raise RuntimeError("missing paddle DLL")

        progress: list[tuple[str, str]] = []
        analysis = analyze_page(
            Image.new("RGB", (120, 80), "white"),
            engine=FailingEngine(),
            progress=lambda stage, message: progress.append((stage, message)),
        )

        self.assertEqual(analysis["engine"], "fallback")
        self.assertIn("missing paddle DLL", analysis["warning"])
        self.assertEqual(progress[0][0], "recognizing")
        self.assertEqual(progress[-1][0], "fallback")

    def test_ocr_line_is_split_into_character_boxes_and_punctuation(self) -> None:
        analysis = analysis_from_ocr_payload(
            {
                "rec_texts": ["天地，玄黄"],
                "rec_scores": [0.91],
                "rec_polys": [[[10, 20], [310, 20], [310, 80], [10, 80]]],
            },
            (400, 200),
        )

        glyphs = analysis["groups"][0]["glyphs"]
        self.assertEqual([glyph["text"] for glyph in glyphs], list("天地，玄黄"))
        self.assertEqual(glyphs[2]["kind"], "punctuation")
        self.assertEqual(glyphs[0]["bbox"], [10, 20, 70, 80])

    def test_uses_paddleocr_text_word_boxes_when_available(self) -> None:
        analysis = analysis_from_ocr_payload(
            {
                "rec_texts": ["天地"],
                "rec_scores": [0.95],
                "rec_polys": [[[10, 20], [150, 20], [150, 90], [10, 90]]],
                "text_word": [["天", "地"]],
                "text_word_boxes": [[[14, 22, 63, 88], [76, 21, 146, 89]]],
            },
            (200, 120),
        )

        self.assertEqual(
            [glyph["bbox"] for glyph in analysis["groups"][0]["glyphs"]],
            [[14, 22, 63, 88], [76, 21, 146, 89]],
        )

    def test_vertical_word_boxes_are_paired_with_canonical_text_order(self) -> None:
        analysis = analysis_from_ocr_payload(
            {
                "rec_texts": ["天地"],
                "rec_scores": [0.95],
                "rec_polys": [[[20, 10], [90, 10], [90, 210], [20, 210]]],
                # Paddle may return text_word in recognition order while sorting
                # text_word_boxes geometrically.
                "text_word": [["地", "天"]],
                "text_word_boxes": [
                    [
                        [22, 112, 88, 205],
                        [24, 15, 86, 104],
                    ]
                ],
            },
            (120, 230),
        )

        glyphs = analysis["groups"][0]["glyphs"]
        self.assertEqual([glyph["text"] for glyph in glyphs], ["天", "地"])
        self.assertEqual([glyph["bbox"] for glyph in glyphs], [[24, 15, 86, 104], [22, 112, 88, 205]])

    def test_refines_uneven_character_spacing_from_ink_projection(self) -> None:
        image = Image.new("RGB", (240, 100), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 20, 95, 82), fill="black")
        draw.rectangle((110, 30, 130, 76), fill="black")
        draw.rectangle((180, 16, 228, 88), fill="black")

        analysis = analysis_from_ocr_payload(
            {
                "rec_texts": ["甲乙丙"],
                "rec_scores": [0.96],
                "rec_polys": [[[0, 10], [239, 10], [239, 95], [0, 95]]],
            },
            image.size,
            image=image,
        )

        boxes = [glyph["bbox"] for glyph in analysis["groups"][0]["glyphs"]]
        self.assertGreaterEqual(boxes[0][2], 95)
        self.assertGreaterEqual(boxes[1][0], 108)
        self.assertLessEqual(boxes[1][2], 134)
        self.assertGreaterEqual(boxes[2][0], 178)
        self.assertGreater(boxes[0][2] - boxes[0][0], boxes[1][2] - boxes[1][0] + 40)

    def test_colored_frame_lines_are_excluded_from_character_boxes(self) -> None:
        image = Image.new("RGB", (240, 110), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((12, 22, 66, 86), fill="black")
        draw.rectangle((92, 28, 126, 80), fill="black")
        draw.rectangle((168, 18, 210, 90), fill="black")
        draw.line((0, 100, 239, 100), fill=(210, 52, 52), width=3)
        draw.line((236, 0, 236, 109), fill=(210, 52, 52), width=3)

        analysis = analysis_from_ocr_payload(
            {
                "rec_texts": ["甲乙丙"],
                "rec_scores": [0.96],
                "rec_polys": [[[0, 5], [239, 5], [239, 105], [0, 105]]],
            },
            image.size,
            image=image,
        )

        boxes = [glyph["bbox"] for glyph in analysis["groups"][0]["glyphs"]]
        self.assertLessEqual(boxes[2][2], 213)
        self.assertLessEqual(max(box[3] for box in boxes), 93)

    def test_vertical_groups_are_ordered_right_to_left(self) -> None:
        analysis = analysis_from_ocr_payload(
            {
                "rec_texts": ["甲乙", "丙丁"],
                "rec_scores": [0.9, 0.9],
                "rec_polys": [
                    [[200, 10], [240, 10], [240, 180], [200, 180]],
                    [[100, 10], [140, 10], [140, 180], [100, 180]],
                ],
            },
            (300, 220),
        )

        self.assertEqual(
            [group["glyphs"][0]["text"] for group in analysis["groups"]],
            ["甲", "丙"],
        )
        self.assertTrue(all(group["direction"] == "vertical" for group in analysis["groups"]))

    def test_refines_uneven_vertical_character_spacing(self) -> None:
        image = Image.new("RGB", (100, 240), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 8, 82, 95), fill="black")
        draw.rectangle((30, 110, 76, 130), fill="black")
        draw.rectangle((16, 180, 88, 228), fill="black")

        analysis = analysis_from_ocr_payload(
            {
                "rec_texts": ["甲乙丙"],
                "rec_scores": [0.96],
                "rec_polys": [[[10, 0], [95, 0], [95, 239], [10, 239]]],
            },
            image.size,
            image=image,
        )

        boxes = [glyph["bbox"] for glyph in analysis["groups"][0]["glyphs"]]
        self.assertGreaterEqual(boxes[0][3], 95)
        self.assertGreaterEqual(boxes[1][1], 108)
        self.assertLessEqual(boxes[1][3], 134)
        self.assertGreaterEqual(boxes[2][1], 178)

    def test_renders_a4_example_and_blank_grid_rows(self) -> None:
        source = Image.new("RGB", (500, 180), "white")
        draw = ImageDraw.Draw(source)
        for index in range(4):
            draw.rectangle((30 + index * 90, 30, 70 + index * 90, 110), fill="black")
        analysis = _analysis(4)

        pages = render_practice_pages(
            source,
            analysis,
            GridParams(grid_style="mi", cell_size_mm=15, margin_mm=15, dpi=72),
        )

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].size, (595, 842))
        # The lower cell in the pair contains grid lines but no dark glyph.
        cell = round(15 / 25.4 * 72)
        margin = round(15 / 25.4 * 72)
        inset = round(cell * 0.12)
        upper = np.asarray(
            pages[0].convert("L").crop(
                (margin + inset, margin + inset, margin + cell - inset, margin + cell - inset)
            )
        )
        lower = np.asarray(
            pages[0].convert("L").crop(
                (
                    margin + inset,
                    margin + cell + inset,
                    margin + cell - inset,
                    margin + cell * 2 - inset,
                )
            )
        )
        self.assertGreater(int((upper < 100).sum()), int((lower < 100).sum()))

    def test_large_analysis_paginates(self) -> None:
        source = Image.new("RGB", (1400, 2400), "white")
        analysis = _analysis(240)

        pages = render_practice_pages(
            source,
            analysis,
            GridParams(cell_size_mm=15, margin_mm=15, dpi=72),
        )

        self.assertGreater(len(pages), 1)

    def test_rendering_preserves_relative_glyph_sizes(self) -> None:
        source = Image.new("RGB", (180, 120), "white")
        draw = ImageDraw.Draw(source)
        draw.rectangle((20, 45, 39, 74), fill="black")
        draw.rectangle((80, 20, 129, 89), fill="black")
        analysis = {
            "version": 1,
            "model_id": "test",
            "engine": "test",
            "status": "ready",
            "image_size": [180, 120],
            "groups": [
                {
                    "id": "line-1",
                    "direction": "horizontal",
                    "included": True,
                    "glyphs": [
                        {"id": "small", "text": "小", "confidence": 1, "bbox": [20, 45, 40, 75], "included": True, "kind": "character"},
                        {"id": "large", "text": "大", "confidence": 1, "bbox": [80, 20, 130, 90], "included": True, "kind": "character"},
                    ],
                }
            ],
        }

        page = render_practice_pages(
            source,
            analysis,
            GridParams(cell_size_mm=15, margin_mm=15, dpi=72),
        )[0].convert("L")
        cell = round(15 / 25.4 * 72)
        margin = round(15 / 25.4 * 72)
        small = np.asarray(page.crop((margin, margin, margin + cell, margin + cell)))
        large = np.asarray(page.crop((margin + cell, margin, margin + cell * 2, margin + cell)))
        small_ys, small_xs = np.nonzero(small < 100)
        large_ys, large_xs = np.nonzero(large < 100)
        small_height = int(small_ys.max() - small_ys.min() + 1)
        large_height = int(large_ys.max() - large_ys.min() + 1)
        small_width = int(small_xs.max() - small_xs.min() + 1)
        large_width = int(large_xs.max() - large_xs.min() + 1)

        self.assertGreater(large_height, small_height * 1.5)
        self.assertGreater(large_width, small_width * 1.5)

    def test_manual_update_marks_analysis_reviewed(self) -> None:
        analysis = _analysis(2)
        groups = analysis["groups"]
        groups[0]["glyphs"][0]["text"] = "改"

        updated = update_analysis(analysis, groups=groups)

        self.assertEqual(updated["status"], "reviewed")
        self.assertEqual(updated["groups"][0]["glyphs"][0]["text"], "改")

    def test_ordered_stream_renders_selected_glyphs_in_saved_order(self) -> None:
        source = Image.new("RGB", (320, 180), "white")
        draw = ImageDraw.Draw(source)
        draw.rectangle((20, 30, 70, 120), fill="black")
        draw.rectangle((120, 30, 170, 120), fill="black")
        draw.rectangle((220, 30, 270, 120), fill="black")
        analysis = {
            "version": 1,
            "model_id": "test",
            "engine": "test",
            "status": "reviewed",
            "selection_mode": "ordered_stream",
            "image_size": [320, 180],
            "groups": [
                {
                    "id": "selected",
                    "direction": "horizontal",
                    "included": True,
                    "glyphs": [
                        {"id": "g3", "text": "丙", "confidence": 1, "bbox": [220, 30, 270, 120], "included": True, "kind": "character"},
                        {"id": "g1", "text": "甲", "confidence": 1, "bbox": [20, 30, 70, 120], "included": True, "kind": "character"},
                    ],
                }
            ],
        }

        pages = render_practice_pages(
            source,
            analysis,
            GridParams(grid_style="tian", cell_size_mm=15, margin_mm=15, dpi=72),
        )

        self.assertEqual(len(pages), 1)
        cell = round(15 / 25.4 * 72)
        margin = round(15 / 25.4 * 72)
        first = np.asarray(
            pages[0].convert("L").crop((margin, margin, margin + cell, margin + cell))
        )
        second = np.asarray(
            pages[0].convert("L").crop((margin + cell, margin, margin + cell * 2, margin + cell))
        )
        self.assertGreater(int((first < 140).sum()), 0)
        self.assertGreater(int((second < 140).sum()), 0)

    def test_extract_glyph_clears_light_background_haze(self) -> None:
        crop = Image.new("L", (48, 48), 236)
        draw = ImageDraw.Draw(crop)
        for x in range(48):
            draw.point((x, 0), fill=232)
            draw.point((x, 47), fill=238)
        for y in range(48):
            draw.point((0, y), fill=234)
            draw.point((47, y), fill=237)
        draw.rectangle((14, 10, 33, 37), fill=24)

        alpha, ink = _extract_glyph(crop)
        alpha_pixels = np.asarray(alpha)
        ink_pixels = np.asarray(ink)

        self.assertEqual(int(alpha_pixels[2, 2]), 0)
        self.assertEqual(int(alpha_pixels[45, 45]), 0)
        self.assertGreater(int(alpha_pixels[24, 24]), 180)
        self.assertLess(int(ink_pixels[24, 24]), 80)

    def test_extract_glyph_removes_different_colored_frame_line(self) -> None:
        crop = Image.new("RGB", (80, 64), "white")
        draw = ImageDraw.Draw(crop)
        draw.rectangle((24, 12, 58, 54), fill=(24, 24, 24))
        draw.line((5, 0, 5, 63), fill=(210, 52, 52), width=3)

        alpha, _ = _extract_glyph(crop)
        pixels = np.asarray(alpha)

        self.assertEqual(int(pixels[32, 5]), 0)
        self.assertGreater(int(pixels[32, 40]), 180)


def _analysis(count: int) -> dict:
    glyphs = []
    for index in range(count):
        column = index % 12
        row = index // 12
        left = 20 + column * 100
        top = 20 + row * 100
        glyphs.append(
            {
                "id": f"glyph-{index}",
                "text": "字",
                "confidence": 0.9,
                "bbox": [left, top, left + 60, top + 80],
                "included": True,
                "kind": "character",
            }
        )
    return {
        "version": 1,
        "model_id": "test",
        "engine": "test",
        "status": "ready",
        "image_size": [1400, 1000],
        "groups": [
            {
                "id": "line-1",
                "direction": "horizontal",
                "included": True,
                "glyphs": glyphs,
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
