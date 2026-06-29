from __future__ import annotations

import os
import tempfile
import unittest
import urllib.error
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from linmo_app.api import LinmoApi
from linmo_app.paths import AppPaths
from linmo_app.services import LinmoServices, _WebDavClient

os.environ["LINMO_DISABLE_OCR"] = "1"


class AppServicesTests(unittest.TestCase):
    def test_repository_import_thumbnail_queue_preview_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            _make_ruled_image(source)
            services = LinmoServices(AppPaths(root / "data"))

            imported = services.import_copybooks([str(source)])
            self.assertEqual(len(imported), 1)
            self.assertEqual(services.repo.stats()["copybooks"], 1)

            pages = services.repo.list_pages(imported[0]["id"])
            self.assertEqual(len(pages), 1)
            self.assertNotEqual(Path(pages[0]["source_path"]).resolve(), source.resolve())

            thumb = services.create_thumbnail(pages[0]["id"])
            self.assertTrue(thumb.exists())
            self.assertEqual(thumb, services.create_thumbnail(pages[0]["id"]))

            params = {
                "grid_style": "tian",
                "cell_size_mm": 15,
                "margin_mm": 15,
                "dpi": 72,
            }
            queue_item = services.repo.add_queue_item(pages[0]["id"], params)
            preview = services.render_queue_preview(queue_item["id"])
            self.assertTrue(preview.exists())
            self.assertIn(f"queue-{queue_item['id']}-", preview.name)

            updated = services.repo.update_queue_item(queue_item["id"], {"grid_style": "mi"})
            updated_preview = services.render_queue_preview(updated["id"])
            self.assertTrue(updated_preview.exists())
            self.assertNotEqual(preview, updated_preview)

            output = services.export_queue_to_pdf([queue_item["id"]])
            self.assertTrue(output.exists())
            self.assertEqual(services.repo.stats()["exported_pages"], 1)

    def test_generated_post_export_default_name_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            _make_ruled_image(source)
            services = LinmoServices(AppPaths(root / "data"))

            imported = services.import_copybooks([str(source)])
            page = services.repo.list_pages(imported[0]["id"])[0]
            queue_item = services.repo.add_queue_item(
                page["id"],
                {"grid_style": "tian", "cell_size_mm": 15, "dpi": 72},
            )

            self.assertEqual(services.next_generated_post_name(), "卷一")
            post = services.export_queue_to_generated_post([queue_item["id"]], "卷一")
            self.assertEqual(post["name"], "卷一")
            self.assertEqual(post["page_count"], 1)
            self.assertEqual(post["result_count"], 0)
            self.assertTrue(Path(post["original_pdf_path"]).exists())
            self.assertTrue(Path(post["thumb_path"]).exists())
            self.assertEqual(services.next_generated_post_name(), "卷二")
            self.assertEqual(len(services.list_generated_posts()), 1)

            files = services.list_generated_post_files(post["id"])
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["kind"], "original")
            self.assertEqual(files[0]["name"], "original.pdf")
            self.assertEqual(services.repo.stats()["exported_pages"], 1)

    def test_generated_post_can_export_png_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "pages"
            image_dir.mkdir()
            _make_ruled_image(image_dir / "1.png")
            _make_ruled_image(image_dir / "2.png")
            services = LinmoServices(AppPaths(root / "data"))

            imported = services.import_copybooks([str(image_dir)])
            pages = services.repo.list_pages(imported[0]["id"])
            queue_items = [
                services.repo.add_queue_item(page["id"], {"grid_style": "tian", "cell_size_mm": 15, "dpi": 72})
                for page in pages
            ]

            post = services.export_queue_to_generated_post([item["id"] for item in queue_items], "卷一", output_format="png")

            self.assertEqual(post["output_format"], "png")
            self.assertEqual(post["page_count"], 2)
            self.assertTrue(Path(post["original_pdf_path"]).exists())
            self.assertEqual(Path(post["original_pdf_path"]).suffix, ".png")
            files = services.list_generated_post_files(post["id"])
            self.assertEqual([file["name"] for file in files], ["001.png", "002.png"])
            self.assertTrue(Path(post["thumb_path"]).exists())
            self.assertEqual(services.repo.stats()["exported_pages"], 2)

    def test_page_analysis_is_cached_and_can_be_reviewed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            _make_ruled_image(source)
            services = LinmoServices(AppPaths(root / "data"))
            imported = services.import_copybooks([str(source)])
            page = services.repo.list_pages(imported[0]["id"])[0]
            item = services.repo.add_queue_item(
                page["id"], {"grid_style": "tian", "cell_size_mm": 15, "dpi": 72}
            )

            first = services.analyze_queue_item(item["id"])
            second = services.analyze_queue_item(item["id"])
            self.assertEqual(first, second)
            self.assertTrue(first["groups"])

            groups = first["groups"]
            groups[0]["glyphs"][0]["text"] = "改"
            reviewed = services.update_queue_analysis(item["id"], groups)
            self.assertEqual(reviewed["status"], "reviewed")
            self.assertEqual(
                services.analyze_queue_item(item["id"])["groups"][0]["glyphs"][0]["text"],
                "改",
            )

    def test_copybook_crop_margins_are_applied_before_page_loading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "margin.png"
            _make_margin_image(source)
            services = LinmoServices(AppPaths(root / "data"))

            imported = services.import_copybooks([str(source)])
            page = services.repo.list_pages(imported[0]["id"])[0]
            uncropped = services.load_page_image(services.repo.get_page_with_copybook(page["id"]), dpi=72)
            self.assertEqual(uncropped.size, (120, 100))

            updated = services.update_copybook_metadata(
                imported[0]["id"],
                {
                    "crop_left_ratio": 0.1,
                    "crop_right_ratio": 0.1,
                    "crop_top_ratio": 0.2,
                    "crop_bottom_ratio": 0.3,
                },
            )
            self.assertAlmostEqual(updated["crop_left_ratio"], 0.1)
            self.assertAlmostEqual(updated["crop_right_ratio"], 0.1)
            self.assertAlmostEqual(updated["crop_top_ratio"], 0.2)
            self.assertAlmostEqual(updated["crop_bottom_ratio"], 0.3)

            cropped = services.load_page_image(services.repo.get_page_with_copybook(page["id"]), dpi=72)
            self.assertEqual(cropped.size, (96, 50))
            self.assertEqual(cropped.getpixel((0, 0)), (255, 255, 255))
            self.assertEqual(cropped.getpixel((95, 49)), (255, 255, 255))

    def test_page_crop_overrides_copybook_default_and_single_page_flow_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "page.png"
            _make_margin_image(source)
            services = LinmoServices(AppPaths(root / "data"))

            imported = services.import_copybooks([str(source)])
            updated_copybook = services.update_copybook_metadata(
                imported[0]["id"],
                {
                    "crop_left_ratio": 0.05,
                    "crop_right_ratio": 0.05,
                    "crop_top_ratio": 0.1,
                    "crop_bottom_ratio": 0.1,
                },
            )
            self.assertAlmostEqual(updated_copybook["crop_left_ratio"], 0.05)
            self.assertAlmostEqual(updated_copybook["crop_right_ratio"], 0.05)
            self.assertAlmostEqual(updated_copybook["crop_top_ratio"], 0.1)

            page = services.repo.list_pages(imported[0]["id"])[0]
            detail = services.get_page_detail(page["id"])
            self.assertAlmostEqual(detail["crop_left_ratio"], 0.05)
            self.assertAlmostEqual(detail["crop_right_ratio"], 0.05)
            self.assertAlmostEqual(detail["crop_top_ratio"], 0.1)
            self.assertAlmostEqual(detail["crop_bottom_ratio"], 0.1)
            self.assertEqual(int(detail["page_crop_override"]), 0)

            page_detail = services.update_page_crop(
                page["id"],
                {"crop_left_ratio": 0.1, "crop_right_ratio": 0.0, "crop_top_ratio": 0.2, "crop_bottom_ratio": 0.0},
            )
            self.assertAlmostEqual(page_detail["crop_left_ratio"], 0.1)
            self.assertAlmostEqual(page_detail["crop_right_ratio"], 0.0)
            self.assertAlmostEqual(page_detail["crop_top_ratio"], 0.2)
            self.assertAlmostEqual(page_detail["crop_bottom_ratio"], 0.0)
            self.assertEqual(int(page_detail["page_crop_override"]), 1)

            image = services.load_page_image(services.repo.get_page_with_copybook(page["id"]), dpi=72)
            self.assertEqual(image.size, (108, 80))

            analysis = services.analyze_page(page["id"], dpi=72)
            self.assertTrue(analysis["groups"])

            preview_paths = services.render_page_previews(page["id"], {"grid_style": "tian", "cell_size_mm": 15, "margin_mm": 15, "dpi": 72})
            self.assertTrue(preview_paths)
            self.assertTrue(all(path.exists() for path in preview_paths))

            reviewed = services.update_page_analysis(page["id"], analysis["groups"])
            self.assertEqual(reviewed["status"], "reviewed")

            post = services.export_page_to_generated_post(
                page["id"],
                {"grid_style": "mi", "cell_size_mm": 15, "margin_mm": 15, "dpi": 72},
                "卷一",
                "pdf",
            )
            self.assertEqual(post["name"], "卷一")
            self.assertEqual(post["output_format"], "pdf")
            self.assertTrue(Path(post["original_pdf_path"]).exists())

    def test_api_start_clears_previous_queue_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            _make_ruled_image(source)
            paths = AppPaths(root / "data")
            services = LinmoServices(paths)

            imported = services.import_copybooks([str(source)])
            page = services.repo.list_pages(imported[0]["id"])[0]
            services.repo.add_queue_item(page["id"], {"mode": "row"})
            self.assertEqual(len(services.repo.list_queue_items()), 1)

            api = LinmoApi(paths)
            self.assertEqual(api.list_queue_items(), [])

    def test_api_add_pages_to_queue_does_not_duplicate_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            _make_ruled_image(source)
            api = LinmoApi(AppPaths(root / "data"))
            api.append_runtime_log("warning", "frontend.test", "test warning")
            diagnostics = api.get_runtime_diagnostics()
            self.assertTrue(diagnostics["log_path"].endswith("logs/linmo.log"))
            self.assertTrue(any(entry["message"] == "test warning" for entry in diagnostics["entries"]))

            imported = api.import_copybooks([str(source)])
            page = api.list_pages(imported[0]["id"])[0]

            first_items = api.add_pages_to_queue([page["id"], page["id"]])
            second_items = api.add_pages_to_queue([page["id"]])
            queue_items = api.list_queue_items()

            self.assertEqual(len(first_items), 1)
            self.assertEqual(first_items[0]["id"], second_items[0]["id"])
            self.assertEqual(len(queue_items), 1)
            self.assertEqual(queue_items[0]["page_id"], page["id"])

    def test_api_page_detail_crop_analysis_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            _make_margin_image(source)
            api = LinmoApi(AppPaths(root / "data"))

            imported = api.import_copybooks([str(source)])
            page = api.list_pages(imported[0]["id"])[0]
            detail = api.get_page_detail(page["id"])
            self.assertEqual(detail["copybook_title"], imported[0]["title"])

            updated = api.update_page_crop(page["id"], {"crop_left_ratio": 0.1, "crop_right_ratio": 0.05, "crop_top_ratio": 0.15, "crop_bottom_ratio": 0.05})
            self.assertAlmostEqual(updated["crop_left_ratio"], 0.1)
            self.assertAlmostEqual(updated["crop_right_ratio"], 0.05)
            self.assertAlmostEqual(updated["crop_top_ratio"], 0.15)
            self.assertAlmostEqual(updated["crop_bottom_ratio"], 0.05)
            self.assertTrue(api.get_page_preview(page["id"]).startswith("data:image/"))

            analysis = api.analyze_page(page["id"])
            self.assertTrue(analysis["groups"])
            saved = api.update_page_analysis(page["id"], analysis["groups"])
            self.assertEqual(saved["status"], "reviewed")

            previews = api.render_page_previews(page["id"], {"grid_style": "tian", "cell_size_mm": 15, "margin_mm": 15, "dpi": 72})
            self.assertTrue(previews)

            post = api.export_page_to_generated_post(page["id"], {"grid_style": "mi", "cell_size_mm": 15, "margin_mm": 15, "dpi": 72}, "卷一", "png")
            self.assertEqual(post["output_format"], "png")
            self.assertTrue(Path(post["original_pdf_path"]).exists())

    def test_api_import_pdf_and_preset_crud(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "sample.pdf"
            _make_pdf(pdf)
            api = LinmoApi(AppPaths(root / "data"))

            imported = api.import_copybooks([str(pdf)])
            self.assertEqual(imported[0]["page_count"], 2)

            pages = api.list_pages(imported[0]["id"])
            self.assertEqual([page["page_no"] for page in pages], [1, 2])
            self.assertTrue(api.get_page_preview(pages[0]["id"]).startswith("data:image/"))

            cover_source = root / "cover.png"
            _make_ruled_image(cover_source)
            updated_copybook = api.update_copybook_metadata(
                imported[0]["id"],
                {
                    "title": "样帖",
                    "author": "作者",
                    "cover_source_path": str(cover_source),
                    "crop_left_ratio": 0.05,
                    "crop_right_ratio": 0.1,
                    "crop_top_ratio": 0.1,
                    "crop_bottom_ratio": 0.15,
                },
            )
            self.assertEqual(updated_copybook["title"], "样帖")
            self.assertEqual(updated_copybook["author"], "作者")
            self.assertAlmostEqual(updated_copybook["crop_left_ratio"], 0.05)
            self.assertAlmostEqual(updated_copybook["crop_right_ratio"], 0.1)
            self.assertAlmostEqual(updated_copybook["crop_top_ratio"], 0.1)
            self.assertAlmostEqual(updated_copybook["crop_bottom_ratio"], 0.15)
            self.assertTrue(updated_copybook["cover_path"])
            self.assertNotEqual(Path(updated_copybook["cover_path"]).resolve(), cover_source.resolve())
            self.assertTrue(api.get_copybook_cover(imported[0]["id"]).startswith("data:image/"))

            preset = api.create_preset(
                {
                    "name": "古帖",
                    "ink_color": "#000000",
                    "foreground_threshold": 35,
                    "mode": "col",
                    "column_detection": "ink",
                }
            )
            self.assertEqual(api.list_presets()[0]["name"], "古帖")
            updated = api.update_preset(preset["id"], {"name": "古帖黑字"})
            self.assertEqual(updated["name"], "古帖黑字")
            self.assertTrue(api.delete_preset(preset["id"])["ok"])
            self.assertEqual(api.list_presets(), [])

    def test_webdav_treats_gone_collection_as_missing_and_uses_collection_urls(self) -> None:
        client = _WebDavClient.__new__(_WebDavClient)
        client.base_url = "https://dav.example.test/dav/"
        client._opener = _FakeWebDavOpener()

        client.ensure_dir("Linmo")

        self.assertEqual(client._opener.calls[0], ("PROPFIND", "https://dav.example.test/dav/Linmo/"))
        self.assertEqual(client._opener.calls[1], ("MKCOL", "https://dav.example.test/dav/Linmo/"))
        self.assertFalse(client.exists("Linmo/missing.pdf"))


def _make_ruled_image(path: Path) -> None:
    image = Image.new("RGB", (360, 260), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for y in [40, 100, 160, 220]:
        draw.line((20, y, 340, y), fill=(120, 120, 120), width=2)
    draw.text((42, 62), "linmo", fill=(0, 0, 0))
    draw.text((42, 122), "copy", fill=(0, 0, 0))
    image.save(path)


def _make_margin_image(path: Path) -> None:
    image = Image.new("RGB", (120, 100), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 119, 19), fill=(200, 0, 0))
    draw.rectangle((0, 70, 119, 99), fill=(0, 0, 200))
    draw.text((20, 40), "body", fill=(0, 0, 0))
    image.save(path)


def _make_pdf(path: Path) -> None:
    document = fitz.open()
    for index in range(2):
        page = document.new_page(width=240, height=320)
        page.insert_text((60, 120), f"Page {index + 1}", fontsize=24)
    document.save(path)
    document.close()


class _FakeWebDavOpener:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def open(self, request, timeout: int):
        method = request.get_method()
        self.calls.append((method, request.full_url))
        if method == "PROPFIND":
            raise urllib.error.HTTPError(request.full_url, 410, "Gone", {}, None)
        return _FakeWebDavResponse()


class _FakeWebDavResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return b""


if __name__ == "__main__":
    unittest.main()
