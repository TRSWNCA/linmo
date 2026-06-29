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
