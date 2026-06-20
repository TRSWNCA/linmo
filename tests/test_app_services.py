from __future__ import annotations

import tempfile
import unittest
import urllib.error
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from linmo_app.api import LinmoApi
from linmo_app.paths import AppPaths
from linmo_app.services import LinmoServices, _WebDavClient


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
                "mode": "row",
                "blank_ratio": 0.5,
                "ink_color": "#000000",
                "foreground_threshold": 18,
            }
            queue_item = services.repo.add_queue_item(pages[0]["id"], params)
            preview = services.render_queue_preview(queue_item["id"])
            self.assertTrue(preview.exists())

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
                {"mode": "row", "blank_ratio": 0.5, "ink_color": "#000000"},
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

            imported = api.import_copybooks([str(source)])
            page = api.list_pages(imported[0]["id"])[0]

            first_items = api.add_pages_to_queue([page["id"], page["id"]])
            second_items = api.add_pages_to_queue([page["id"]])
            queue_items = api.list_queue_items()

            self.assertEqual(len(first_items), 1)
            self.assertEqual(first_items[0]["id"], second_items[0]["id"])
            self.assertEqual(len(queue_items), 1)
            self.assertEqual(queue_items[0]["page_id"], page["id"])

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
                {"title": "样帖", "author": "作者", "cover_source_path": str(cover_source)},
            )
            self.assertEqual(updated_copybook["title"], "样帖")
            self.assertEqual(updated_copybook["author"], "作者")
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
