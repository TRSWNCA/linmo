from __future__ import annotations

import base64
import posixpath
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from linmo.processing import ProcessingParams, load_input_page, process_image

from .paths import AppPaths
from .repository import Repository

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


class LinmoServices:
    def __init__(self, paths: AppPaths):
        self.paths = paths
        self.paths.ensure()
        self.repo = Repository(paths.db_path)
        defaults = {
            "data_dir": str(paths.root),
            "default_dpi": "300",
            "default_export_dir": str(paths.exports_dir),
            "webdav_url": "",
            "webdav_username": "",
            "webdav_password": "",
            "webdav_remote_root": "Linmo",
        }
        current_settings = self.repo.get_settings()
        missing_defaults = {key: value for key, value in defaults.items() if key not in current_settings}
        if missing_defaults:
            self.repo.update_settings(missing_defaults)

    def import_copybooks(self, paths: list[str]) -> list[dict[str, Any]]:
        imported = []
        for raw in paths:
            path = Path(raw).expanduser()
            if not path.exists():
                raise ValueError(f"file does not exist: {path}")
            if path.is_dir():
                imported.append(self._import_image_dir(path))
            elif path.suffix.lower() == ".pdf":
                imported.append(self._import_pdf(path))
            elif path.suffix.lower() in IMAGE_SUFFIXES:
                imported.append(self._import_image_file(path))
            else:
                raise ValueError(f"unsupported input: {path}")
        return imported

    def create_thumbnail(self, page_id: int) -> Path:
        page = self.repo.get_page_with_copybook(page_id)
        thumb_path = self.paths.thumbs_dir / f"{page_id}.jpg"
        if thumb_path.exists():
            return thumb_path

        image = self.load_page_image(page, dpi=120)
        image.thumbnail((260, 360))
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(thumb_path, "JPEG", quality=85)
        self.repo.update_page_thumb(page_id, thumb_path)
        return thumb_path

    def create_page_preview(self, page_id: int) -> Path:
        page = self.repo.get_page_with_copybook(page_id)
        preview_path = self.paths.previews_dir / f"source-{page_id}.jpg"
        if preview_path.exists():
            return preview_path

        image = self.load_page_image(page, dpi=180)
        image.thumbnail((1200, 1200))
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(preview_path, "JPEG", quality=88)
        return preview_path

    def copybook_cover(self, copybook_id: int) -> Path | None:
        copybook = self.repo.get_copybook(copybook_id)
        cover_path = Path(copybook["cover_path"]) if copybook.get("cover_path") else None
        if cover_path and cover_path.exists():
            return cover_path

        pages = self.repo.list_pages(copybook_id)
        if not pages:
            return None
        return self.create_thumbnail(int(pages[0]["id"]))

    def update_copybook_metadata(self, copybook_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
        data = dict(metadata)
        cover_source = data.pop("cover_source_path", "")
        if cover_source:
            data["cover_path"] = str(self._copy_cover_image(copybook_id, Path(str(cover_source)).expanduser()))
        return self.repo.update_copybook(copybook_id, data)

    def load_page_image(self, page: dict[str, Any], dpi: int) -> Image.Image:
        if page["copybook_source_type"] == "pdf":
            return load_input_page(Path(page["copybook_source_path"]), int(page["page_no"]), dpi)
        return load_input_page(Path(page["source_path"]), 1, dpi)

    def render_queue_preview(self, item_id: int) -> Path:
        item = self.repo.get_queue_item(item_id)
        page = self.repo.get_page_with_copybook(int(item["page_id"]))
        params = self._params_from_dict(item["params"])
        source = self.load_page_image(page, dpi=params.dpi)
        output = process_image(source, params)
        output.thumbnail((1200, 1200))
        out_path = self.paths.previews_dir / f"queue-{item_id}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        output.convert("RGB").save(out_path, "JPEG", quality=88)
        return out_path

    def export_queue_to_pdf(
        self,
        queue_item_ids: list[int],
        preset_id: int | None = None,
        output_path: str | None = None,
    ) -> Path:
        if not queue_item_ids:
            raise ValueError("queue_item_ids cannot be empty")
        preset = self.repo.get_preset(preset_id) if preset_id else None
        images = []
        for item_id in queue_item_ids:
            item = self.repo.get_queue_item(int(item_id))
            page = self.repo.get_page_with_copybook(int(item["page_id"]))
            params_dict = dict(item["params"])
            if preset:
                params_dict = self._apply_preset(params_dict, preset)
            params = self._params_from_dict(params_dict)
            images.append(process_image(self.load_page_image(page, dpi=params.dpi), params))

        if output_path:
            out_path = Path(output_path).expanduser()
        else:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            out_path = self.paths.exports_dir / f"{stamp}-linmo.pdf"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        first, rest = [image.convert("RGB") for image in images][0], [image.convert("RGB") for image in images][1:]
        first.save(out_path, "PDF", resolution=float(self._params_from_dict({}).dpi), save_all=bool(rest), append_images=rest)
        self.repo.record_export(out_path, len(images))
        return out_path

    def next_generated_post_name(self) -> str:
        return f"卷{_chinese_number(self.repo.count_generated_posts() + 1)}"

    def export_queue_to_generated_post(
        self,
        queue_item_ids: list[int],
        name: str,
        preset_id: int | None = None,
    ) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("generated post name cannot be empty")
        if not queue_item_ids:
            raise ValueError("queue_item_ids cannot be empty")

        post = self.repo.create_generated_post(clean_name, len(queue_item_ids))
        post_dir = self._generated_post_dir(int(post["id"]))
        post_dir.mkdir(parents=True, exist_ok=True)
        results_dir = post_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        original_pdf = post_dir / "original.pdf"

        self.export_queue_to_pdf(queue_item_ids, preset_id, str(original_pdf))
        thumb = self._create_generated_post_thumbnail(int(post["id"]), original_pdf)
        return self.repo.update_generated_post(
            int(post["id"]),
            {
                "original_pdf_path": str(original_pdf),
                "thumb_path": str(thumb),
                "result_count": self._count_pdf_results(results_dir),
                "sync_status": "local",
            },
        )

    def list_generated_posts(self) -> list[dict[str, Any]]:
        posts = []
        for post in self.repo.list_generated_posts():
            posts.append(self._refresh_generated_post_file_counts(post))
        return posts

    def generated_post_thumbnail(self, post_id: int) -> Path | None:
        post = self.repo.get_generated_post(post_id)
        thumb_path = Path(post["thumb_path"]) if post.get("thumb_path") else None
        if thumb_path and thumb_path.exists():
            return thumb_path
        original = Path(post["original_pdf_path"]) if post.get("original_pdf_path") else None
        if not original or not original.exists():
            return None
        thumb = self._create_generated_post_thumbnail(post_id, original)
        self.repo.update_generated_post(post_id, {"thumb_path": str(thumb)})
        return thumb

    def list_generated_post_files(self, post_id: int) -> list[dict[str, Any]]:
        post = self.repo.get_generated_post(post_id)
        files = []
        original = Path(post["original_pdf_path"]) if post.get("original_pdf_path") else None
        if original and original.exists():
            files.append({"kind": "original", "name": "original.pdf", "path": str(original), "size": original.stat().st_size})
        results_dir = self._generated_post_dir(post_id) / "results"
        for path in sorted(results_dir.glob("*.pdf")):
            files.append({"kind": "result", "name": path.name, "path": str(path), "size": path.stat().st_size})
        return files

    def sync_generated_post(self, post_id: int) -> dict[str, Any]:
        post = self.repo.get_generated_post(post_id)
        settings = self.repo.get_settings()
        client = _WebDavClient.from_settings(settings)
        remote_root = settings.get("webdav_remote_root", "Linmo").strip("/") or "Linmo"
        remote_post_dir = posixpath.join(remote_root, _safe_remote_name(str(post["name"])))
        remote_results_dir = posixpath.join(remote_post_dir, "results")

        self.repo.update_generated_post(post_id, {"sync_status": "syncing"})
        try:
            client.ensure_dir(remote_root)
            client.ensure_dir(remote_post_dir)
            client.ensure_dir(remote_results_dir)

            local_original = Path(str(post["original_pdf_path"]))
            if not local_original.exists():
                raise ValueError(f"generated PDF does not exist: {local_original}")
            remote_original = posixpath.join(remote_post_dir, "original.pdf")
            if client.exists(remote_original):
                client.download(remote_original, local_original)
            else:
                client.upload(local_original, remote_original)

            results_dir = self._generated_post_dir(post_id) / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            for name in client.list_pdf_files(remote_results_dir):
                client.download(posixpath.join(remote_results_dir, name), results_dir / name)

            thumb = self._create_generated_post_thumbnail(post_id, local_original)
            return self.repo.update_generated_post(
                post_id,
                {
                    "thumb_path": str(thumb),
                    "result_count": self._count_pdf_results(results_dir),
                    "sync_status": "synced",
                    "remote_path": remote_post_dir,
                    "last_synced_at": int(time.time()),
                },
            )
        except Exception:
            self.repo.update_generated_post(post_id, {"sync_status": "error"})
            raise

    def _import_pdf(self, source: Path) -> dict[str, Any]:
        copybook_dir = self._new_copybook_dir()
        target = copybook_dir / "source.pdf"
        shutil.copy2(source, target)
        copybook = self.repo.create_copybook(
            {
                "title": source.stem,
                "source_type": "pdf",
                "source_path": str(target),
            }
        )
        with fitz.open(target) as document:
            for index, page in enumerate(document, start=1):
                rect = page.rect
                self.repo.create_page(
                    {
                        "copybook_id": copybook["id"],
                        "page_no": index,
                        "source_path": str(target),
                        "width": int(rect.width),
                        "height": int(rect.height),
                    }
                )
        return self.repo.get_copybook(copybook["id"])

    def _import_image_file(self, source: Path) -> dict[str, Any]:
        copybook_dir = self._new_copybook_dir()
        pages_dir = copybook_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        target = pages_dir / f"1{source.suffix.lower()}"
        shutil.copy2(source, target)
        copybook = self.repo.create_copybook(
            {
                "title": source.stem,
                "source_type": "images",
                "source_path": str(pages_dir),
            }
        )
        self._create_image_page(copybook["id"], 1, target)
        return self.repo.get_copybook(copybook["id"])

    def _import_image_dir(self, source: Path) -> dict[str, Any]:
        files = [path for path in sorted(source.iterdir()) if path.suffix.lower() in IMAGE_SUFFIXES]
        if not files:
            raise ValueError(f"no supported images in: {source}")
        copybook_dir = self._new_copybook_dir()
        pages_dir = copybook_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        copybook = self.repo.create_copybook(
            {
                "title": source.name,
                "source_type": "images",
                "source_path": str(pages_dir),
            }
        )
        for index, file_path in enumerate(files, start=1):
            target = pages_dir / f"{index}{file_path.suffix.lower()}"
            shutil.copy2(file_path, target)
            self._create_image_page(copybook["id"], index, target)
        return self.repo.get_copybook(copybook["id"])

    def _create_image_page(self, copybook_id: int, page_no: int, source: Path) -> None:
        with Image.open(source) as image:
            width, height = image.size
        self.repo.create_page(
            {
                "copybook_id": copybook_id,
                "page_no": page_no,
                "source_path": str(source),
                "width": width,
                "height": height,
            }
        )

    def _copy_cover_image(self, copybook_id: int, source: Path) -> Path:
        if not source.exists():
            raise ValueError(f"cover image does not exist: {source}")
        if source.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"unsupported cover image: {source}")
        target_dir = self._copybook_storage_dir(copybook_id)
        target = target_dir / f"cover{source.suffix.lower()}"
        shutil.copy2(source, target)
        return target

    def _copybook_storage_dir(self, copybook_id: int) -> Path:
        copybook = self.repo.get_copybook(copybook_id)
        source_path = Path(copybook["source_path"])
        if copybook["source_type"] == "pdf":
            return source_path.parent
        return source_path.parent if source_path.name != "pages" else source_path.parent

    def _new_copybook_dir(self) -> Path:
        stamp = f"{int(time.time() * 1000)}"
        path = self.paths.library_dir / stamp
        path.mkdir(parents=True, exist_ok=False)
        return path

    def _generated_post_dir(self, post_id: int) -> Path:
        return self.paths.generated_dir / str(post_id)

    def _create_generated_post_thumbnail(self, post_id: int, pdf_path: Path) -> Path:
        thumb_path = self.paths.generated_thumbs_dir / f"{post_id}.jpg"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        with fitz.open(pdf_path) as document:
            if document.page_count == 0:
                raise ValueError(f"generated PDF has no pages: {pdf_path}")
            page = document.load_page(0)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(120 / 72, 120 / 72), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        image.thumbnail((260, 360))
        image.convert("RGB").save(thumb_path, "JPEG", quality=85)
        return thumb_path

    def _count_pdf_results(self, results_dir: Path) -> int:
        if not results_dir.exists():
            return 0
        return len([path for path in results_dir.glob("*.pdf") if path.is_file()])

    def _refresh_generated_post_file_counts(self, post: dict[str, Any]) -> dict[str, Any]:
        results_dir = self._generated_post_dir(int(post["id"])) / "results"
        count = self._count_pdf_results(results_dir)
        if int(post.get("result_count") or 0) != count:
            post = self.repo.update_generated_post(int(post["id"]), {"result_count": count})
        return post

    def _params_from_dict(self, data: dict[str, Any]) -> ProcessingParams:
        return ProcessingParams(
            mode=data.get("mode", "row"),
            column_detection=data.get("column_detection", "gray"),
            columns=_optional_int(data.get("columns")),
            rows=_optional_int(data.get("rows")),
            blank_ratio=float(data.get("blank_ratio", 1.0)),
            dpi=int(data.get("dpi", 300)),
            gray_min=int(data.get("gray_min", 70)),
            gray_max=int(data.get("gray_max", 210)),
            ink_max=int(data.get("ink_max", 170)),
            line_max=int(data.get("line_max", 225)),
            background_image=_optional_path(data.get("background_image")),
            extract_foreground=bool(data.get("extract_foreground", False)),
            ink_color=data.get("ink_color", "#000000"),
            foreground_threshold=int(data.get("foreground_threshold", 18)),
        )

    def default_params_for_page(self, page_id: int) -> dict[str, Any]:
        page = self.repo.get_page_with_copybook(page_id)
        if page["copybook_source_type"] == "images":
            return {
                "mode": "col",
                "column_detection": "ink",
                "blank_ratio": 1.0,
                "ink_color": "#000000",
                "foreground_threshold": 35,
            }
        title = str(page.get("copybook_title", ""))
        if "红楼梦" in title:
            return {"mode": "col", "column_detection": "gray", "blank_ratio": 1.0, "ink_color": "#000000"}
        return {"mode": "row", "column_detection": "gray", "blank_ratio": 1.0, "ink_color": "#000000"}

    def _apply_preset(self, params: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
        merged = dict(params)
        for key in ["background_image", "ink_color", "foreground_threshold", "mode", "column_detection"]:
            if preset.get(key) not in (None, ""):
                merged[key] = preset[key]
        merged.update(preset.get("params", {}))
        return merged


def file_to_data_url(path: Path) -> str:
    mime = "image/jpeg"
    if path.suffix.lower() == ".png":
        mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value)).expanduser()


def _chinese_number(value: int) -> str:
    digits = "零一二三四五六七八九"
    if value <= 0:
        return str(value)
    if value < 10:
        return digits[value]
    if value < 20:
        return "十" + (digits[value % 10] if value % 10 else "")
    if value < 100:
        tens, ones = divmod(value, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        suffix = "" if rest == 0 else ("零" + _chinese_number(rest) if rest < 10 else _chinese_number(rest))
        return digits[hundreds] + "百" + suffix
    return str(value)


def _safe_remote_name(value: str) -> str:
    return value.replace("/", "／").replace("\\", "＼").strip() or "未命名"


class _WebDavClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/") + "/"
        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, self.base_url, username, password)
        opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(password_manager))
        self._opener = opener

    @classmethod
    def from_settings(cls, settings: dict[str, str]) -> "_WebDavClient":
        url = settings.get("webdav_url", "").strip()
        username = settings.get("webdav_username", "").strip()
        password = settings.get("webdav_password", "")
        if not url or not username or not password:
            raise ValueError("请先在设置中填写 WebDAV 地址、用户名和应用密码")
        return cls(url, username, password)

    def exists(self, path: str) -> bool:
        try:
            self._request("PROPFIND", path, headers={"Depth": "0"})
            return True
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return False
            raise

    def ensure_dir(self, path: str) -> None:
        if self.exists(path):
            return
        try:
            self._request("MKCOL", path)
        except urllib.error.HTTPError as error:
            if error.code not in {405, 409}:
                raise

    def upload(self, local_path: Path, remote_path: str) -> None:
        self._request("PUT", remote_path, data=local_path.read_bytes(), headers={"Content-Type": "application/pdf"})

    def download(self, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with self._request("GET", remote_path) as response:
            local_path.write_bytes(response.read())

    def list_pdf_files(self, path: str) -> list[str]:
        try:
            with self._request("PROPFIND", path, headers={"Depth": "1"}) as response:
                data = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return []
            raise
        names: list[str] = []
        root = ET.fromstring(data)
        for response in root.findall("{DAV:}response"):
            href = response.findtext("{DAV:}href")
            if not href:
                continue
            name = urllib.parse.unquote(href.rstrip("/").split("/")[-1])
            if name.lower().endswith(".pdf"):
                names.append(name)
        return sorted(set(names))

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ):
        quoted = "/".join(urllib.parse.quote(part) for part in path.strip("/").split("/") if part)
        url = urllib.parse.urljoin(self.base_url, quoted)
        request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        return self._opener.open(request, timeout=30)
