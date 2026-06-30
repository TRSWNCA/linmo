from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from linmo.glyph_pipeline import PaddleOcrEngine


RESOURCE_DIR = Path(__file__).parent / "resources"


class OcrResourceIntegrationTests(unittest.TestCase):
    """Run the real local OCR model against every checked-in resource image."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = PaddleOcrEngine()

    def test_recognizes_every_resource_image(self) -> None:
        resource_paths = sorted(RESOURCE_DIR.glob("*.png"))
        self.assertTrue(resource_paths, "tests/resources 下没有 PNG 测试图片")

        for resource_path in resource_paths:
            with self.subTest(resource=resource_path.name):
                with Image.open(resource_path) as source:
                    analysis = self.engine.analyze(source.convert("RGB"))

                groups = analysis["groups"]
                body_groups = [group for group in groups if group.get("included", True)]
                all_texts = [_group_text(group) for group in groups]
                body_texts = [_group_text(group) for group in body_groups]
                character_count = sum(
                    len(str(glyph.get("text", "")))
                    for group in groups
                    for glyph in group.get("glyphs", [])
                )
                body_character_count = sum(
                    len(str(glyph.get("text", "")))
                    for group in body_groups
                    for glyph in group.get("glyphs", [])
                )

                print(
                    f"\n[{resource_path.name}] "
                    f"OCR {len(groups)} 行 / {character_count} 字；"
                    f"正文 {len(body_groups)} 行 / {body_character_count} 字"
                )
                for index, (group, text) in enumerate(zip(groups, all_texts), start=1):
                    scope = "正文" if group.get("included", True) else "排除"
                    direction = "竖排" if group.get("direction") == "vertical" else "横排"
                    print(f"  {index:02d}. [{scope}][{direction}] {text}")
                print("  正文汇总：" + " / ".join(body_texts))

                self.assertGreater(len(groups), 0, f"{resource_path.name} 未识别出任何行")
                self.assertGreater(
                    character_count,
                    0,
                    f"{resource_path.name} 未识别出任何字符",
                )
                self.assertGreater(
                    len(body_groups),
                    0,
                    f"{resource_path.name} 未识别出正文行",
                )


def _group_text(group: dict) -> str:
    return "".join(str(glyph.get("text", "")) for glyph in group.get("glyphs", []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
