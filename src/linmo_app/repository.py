from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS copybooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    style TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    cover_path TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    crop_left_ratio REAL NOT NULL DEFAULT 0,
    crop_right_ratio REAL NOT NULL DEFAULT 0,
    crop_top_ratio REAL NOT NULL DEFAULT 0,
    crop_bottom_ratio REAL NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    copybook_id INTEGER NOT NULL REFERENCES copybooks(id) ON DELETE CASCADE,
    page_no INTEGER NOT NULL,
    source_path TEXT NOT NULL,
    width INTEGER NOT NULL DEFAULT 0,
    height INTEGER NOT NULL DEFAULT 0,
    crop_left_ratio REAL NOT NULL DEFAULT 0,
    crop_right_ratio REAL NOT NULL DEFAULT 0,
    crop_top_ratio REAL NOT NULL DEFAULT 0,
    crop_bottom_ratio REAL NOT NULL DEFAULT 0,
    rotation_degrees REAL NOT NULL DEFAULT 0,
    crop_override INTEGER NOT NULL DEFAULT 0,
    thumb_path TEXT NOT NULL DEFAULT '',
    UNIQUE(copybook_id, page_no)
);

CREATE TABLE IF NOT EXISTS queue_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    params_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS page_analyses (
    page_id INTEGER PRIMARY KEY REFERENCES pages(id) ON DELETE CASCADE,
    source_fingerprint TEXT NOT NULL,
    model_id TEXT NOT NULL,
    status TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    background_image TEXT NOT NULL DEFAULT '',
    ink_color TEXT NOT NULL DEFAULT '#000000',
    foreground_threshold INTEGER NOT NULL DEFAULT 18,
    mode TEXT NOT NULL DEFAULT 'row',
    column_detection TEXT NOT NULL DEFAULT 'gray',
    params_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    output_path TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    original_pdf_path TEXT NOT NULL DEFAULT '',
    output_format TEXT NOT NULL DEFAULT 'pdf',
    thumb_path TEXT NOT NULL DEFAULT '',
    page_count INTEGER NOT NULL DEFAULT 0,
    result_count INTEGER NOT NULL DEFAULT 0,
    sync_status TEXT NOT NULL DEFAULT 'local',
    remote_path TEXT NOT NULL DEFAULT '',
    last_synced_at INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS glyph_occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES page_analyses(page_id) ON DELETE CASCADE,
    glyph_id TEXT NOT NULL,
    text TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    bbox_json TEXT NOT NULL,
    analysis_status TEXT NOT NULL DEFAULT 'ready',
    source_fingerprint TEXT NOT NULL DEFAULT '',
    updated_at INTEGER NOT NULL,
    UNIQUE(page_id, glyph_id)
);

CREATE INDEX IF NOT EXISTS idx_glyph_occurrences_text
    ON glyph_occurrences(text);
CREATE INDEX IF NOT EXISTS idx_glyph_occurrences_page
    ON glyph_occurrences(page_id);

CREATE TABLE IF NOT EXISTS glyph_index_state (
    page_id INTEGER PRIMARY KEY REFERENCES page_analyses(page_id) ON DELETE CASCADE,
    analysis_updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    input_text TEXT NOT NULL DEFAULT '',
    direction TEXT NOT NULL DEFAULT 'horizontal',
    line_capacity INTEGER NOT NULL DEFAULT 8,
    background TEXT NOT NULL DEFAULT 'transparent',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_items (
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    character TEXT NOT NULL,
    occurrence_id INTEGER REFERENCES glyph_occurrences(id) ON DELETE SET NULL,
    PRIMARY KEY(collection_id, position)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Repository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            _ensure_column(conn, "copybooks", "cover_path", "TEXT NOT NULL DEFAULT ''")
            _ensure_column(conn, "copybooks", "crop_left_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "copybooks", "crop_right_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "copybooks", "crop_top_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "copybooks", "crop_bottom_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "pages", "crop_left_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "pages", "crop_right_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "pages", "crop_top_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "pages", "crop_bottom_ratio", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "pages", "rotation_degrees", "REAL NOT NULL DEFAULT 0")
            _ensure_column(conn, "pages", "crop_override", "INTEGER NOT NULL DEFAULT 0")
            _ensure_column(conn, "generated_posts", "thumb_path", "TEXT NOT NULL DEFAULT ''")
            _ensure_column(conn, "generated_posts", "output_format", "TEXT NOT NULL DEFAULT 'pdf'")
            _ensure_column(conn, "generated_posts", "result_count", "INTEGER NOT NULL DEFAULT 0")
            _ensure_column(conn, "generated_posts", "sync_status", "TEXT NOT NULL DEFAULT 'local'")
            _ensure_column(conn, "generated_posts", "remote_path", "TEXT NOT NULL DEFAULT ''")
            _ensure_column(conn, "generated_posts", "last_synced_at", "INTEGER NOT NULL DEFAULT 0")
            self._backfill_glyph_index(conn)

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            copybooks = conn.execute("SELECT COUNT(*) FROM copybooks").fetchone()[0]
            exported_pages = conn.execute("SELECT COALESCE(SUM(page_count), 0) FROM exports").fetchone()[0]
        return {"copybooks": int(copybooks), "exported_pages": int(exported_pages)}

    def create_copybook(self, data: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO copybooks
                    (title, author, style, source_type, source_path, cover_path, tags, notes,
                     crop_left_ratio, crop_right_ratio, crop_top_ratio, crop_bottom_ratio, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["title"],
                    data.get("author", ""),
                    data.get("style", ""),
                    data["source_type"],
                    data["source_path"],
                    data.get("cover_path", ""),
                    data.get("tags", ""),
                    data.get("notes", ""),
                    float(data.get("crop_left_ratio", 0) or 0),
                    float(data.get("crop_right_ratio", 0) or 0),
                    float(data.get("crop_top_ratio", 0) or 0),
                    float(data.get("crop_bottom_ratio", 0) or 0),
                    now,
                    now,
                ),
            )
            copybook_id = int(cur.lastrowid)
        return self.get_copybook(copybook_id)

    def list_copybooks(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*, COUNT(p.id) AS page_count
                FROM copybooks c
                LEFT JOIN pages p ON p.copybook_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC, c.id DESC
                """
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def get_copybook(self, copybook_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT c.*, COUNT(p.id) AS page_count
                FROM copybooks c
                LEFT JOIN pages p ON p.copybook_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
                """,
                (copybook_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"copybook not found: {copybook_id}")
        return _row_to_dict(row)

    def update_copybook(self, copybook_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
        allowed = [
            "title", "author", "style", "cover_path", "tags", "notes",
            "crop_left_ratio", "crop_right_ratio", "crop_top_ratio", "crop_bottom_ratio",
        ]
        values = {
            key: float(metadata[key]) if key in {"crop_left_ratio", "crop_right_ratio", "crop_top_ratio", "crop_bottom_ratio"} else str(metadata[key])
            for key in allowed
            if key in metadata
        }
        if not values:
            return self.get_copybook(copybook_id)
        values["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in values)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE copybooks SET {assignments} WHERE id = ?",
                [*values.values(), copybook_id],
            )
        return self.get_copybook(copybook_id)

    def create_page(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO pages
                    (copybook_id, page_no, source_path, width, height,
                     crop_left_ratio, crop_right_ratio, crop_top_ratio, crop_bottom_ratio,
                     rotation_degrees, crop_override, thumb_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["copybook_id"],
                    data["page_no"],
                    data["source_path"],
                    data.get("width", 0),
                    data.get("height", 0),
                    float(data.get("crop_left_ratio", 0) or 0),
                    float(data.get("crop_right_ratio", 0) or 0),
                    float(data.get("crop_top_ratio", 0) or 0),
                    float(data.get("crop_bottom_ratio", 0) or 0),
                    float(data.get("rotation_degrees", 0) or 0),
                    int(data.get("crop_override", 0) or 0),
                    data.get("thumb_path", ""),
                ),
            )
            page_id = int(cur.lastrowid)
        return self.get_page(page_id)

    def update_page_thumb(self, page_id: int, thumb_path: Path) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE pages SET thumb_path = ? WHERE id = ?", (str(thumb_path), page_id))

    def get_page_analysis(self, page_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM page_analyses WHERE page_id = ?", (page_id,)
            ).fetchone()
        if row is None:
            return None
        data = _row_to_dict(row)
        data["analysis"] = json.loads(data.pop("analysis_json"))
        return data

    def save_page_analysis(
        self,
        page_id: int,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        now = _now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO page_analyses
                    (page_id, source_fingerprint, model_id, status, analysis_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(page_id) DO UPDATE SET
                    source_fingerprint = excluded.source_fingerprint,
                    model_id = excluded.model_id,
                    status = excluded.status,
                    analysis_json = excluded.analysis_json,
                    updated_at = excluded.updated_at
                """,
                (
                    page_id,
                    str(analysis.get("source_fingerprint", "")),
                    str(analysis.get("model_id", "")),
                    str(analysis.get("status", "ready")),
                    json.dumps(analysis, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            self._sync_page_glyphs(conn, page_id, analysis, now)
        saved = self.get_page_analysis(page_id)
        assert saved is not None
        return saved

    def delete_page_analysis(self, page_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM page_analyses WHERE page_id = ?", (page_id,))

    def _backfill_glyph_index(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT pa.page_id, pa.analysis_json, pa.updated_at
            FROM page_analyses pa
            LEFT JOIN glyph_index_state gis ON gis.page_id = pa.page_id
            WHERE gis.page_id IS NULL OR gis.analysis_updated_at != pa.updated_at
            """
        ).fetchall()
        for row in rows:
            try:
                analysis = json.loads(row["analysis_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            self._sync_page_glyphs(
                conn,
                int(row["page_id"]),
                analysis,
                int(row["updated_at"]),
            )

    def _sync_page_glyphs(
        self,
        conn: sqlite3.Connection,
        page_id: int,
        analysis: dict[str, Any],
        updated_at: int,
    ) -> None:
        glyph_ids: list[str] = []
        groups = analysis.get("ocr_groups") or analysis.get("groups") or []
        status = str(analysis.get("status", "ready"))
        fingerprint = str(analysis.get("source_fingerprint", ""))
        for group in groups:
            for glyph in group.get("glyphs", []):
                if glyph.get("kind") == "punctuation":
                    continue
                text = str(glyph.get("text", "")).strip()
                glyph_id = str(glyph.get("id", ""))
                bbox = glyph.get("bbox")
                if not text or not glyph_id or not isinstance(bbox, list) or len(bbox) != 4:
                    continue
                glyph_ids.append(glyph_id)
                conn.execute(
                    """
                    INSERT INTO glyph_occurrences
                        (page_id, glyph_id, text, confidence, bbox_json,
                         analysis_status, source_fingerprint, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(page_id, glyph_id) DO UPDATE SET
                        text = excluded.text,
                        confidence = excluded.confidence,
                        bbox_json = excluded.bbox_json,
                        analysis_status = excluded.analysis_status,
                        source_fingerprint = excluded.source_fingerprint,
                        updated_at = excluded.updated_at
                    """,
                    (
                        page_id,
                        glyph_id,
                        text,
                        float(glyph.get("confidence", 0) or 0),
                        json.dumps([int(round(float(value))) for value in bbox]),
                        status,
                        fingerprint,
                        updated_at,
                    ),
                )
        if glyph_ids:
            placeholders = ", ".join("?" for _ in glyph_ids)
            conn.execute(
                f"DELETE FROM glyph_occurrences WHERE page_id = ? AND glyph_id NOT IN ({placeholders})",
                [page_id, *glyph_ids],
            )
        else:
            conn.execute("DELETE FROM glyph_occurrences WHERE page_id = ?", (page_id,))
        conn.execute(
            """
            INSERT INTO glyph_index_state (page_id, analysis_updated_at)
            VALUES (?, ?)
            ON CONFLICT(page_id) DO UPDATE SET
                analysis_updated_at = excluded.analysis_updated_at
            """,
            (page_id, updated_at),
        )

    def search_glyphs(
        self,
        text: str,
        *,
        copybook_id: int | None = None,
        author: str = "",
        limit: int = 60,
        offset: int = 0,
    ) -> dict[str, Any]:
        clauses = ["go.text = ?"]
        values: list[Any] = [text]
        if copybook_id is not None:
            clauses.append("c.id = ?")
            values.append(int(copybook_id))
        if author:
            clauses.append("c.author = ?")
            values.append(author)
        where = " AND ".join(clauses)
        with self.connect() as conn:
            total = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM glyph_occurrences go
                    JOIN pages p ON p.id = go.page_id
                    JOIN copybooks c ON c.id = p.copybook_id
                    WHERE {where}
                    """,
                    values,
                ).fetchone()[0]
            )
            rows = conn.execute(
                f"""
                SELECT go.*, p.page_no, p.copybook_id,
                       c.title AS copybook_title, c.author AS copybook_author
                FROM glyph_occurrences go
                JOIN pages p ON p.id = go.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                WHERE {where}
                ORDER BY CASE WHEN go.analysis_status = 'reviewed' THEN 0 ELSE 1 END,
                         go.confidence DESC, c.updated_at DESC, go.id
                LIMIT ? OFFSET ?
                """,
                [*values, max(1, min(int(limit), 200)), max(0, int(offset))],
            ).fetchall()
        return {"items": [_decode_glyph(row) for row in rows], "total": total}

    def get_glyph_occurrence(self, occurrence_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT go.*, p.page_no, p.copybook_id,
                       c.title AS copybook_title, c.author AS copybook_author
                FROM glyph_occurrences go
                JOIN pages p ON p.id = go.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                WHERE go.id = ?
                """,
                (occurrence_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"glyph occurrence not found: {occurrence_id}")
        return _decode_glyph(row)

    def list_page_glyph_occurrence_ids(self, page_id: int) -> list[int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id FROM glyph_occurrences WHERE page_id = ?",
                (page_id,),
            ).fetchall()
        return [int(row["id"]) for row in rows]

    def list_glyph_filters(self, text: str = "") -> dict[str, Any]:
        where = "WHERE go.text = ?" if text else ""
        values = [text] if text else []
        with self.connect() as conn:
            copybooks = conn.execute(
                f"""
                SELECT c.id, c.title, c.author, COUNT(*) AS glyph_count
                FROM glyph_occurrences go
                JOIN pages p ON p.id = go.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                {where}
                GROUP BY c.id
                ORDER BY c.title, c.id
                """,
                values,
            ).fetchall()
            authors = conn.execute(
                f"""
                SELECT c.author, COUNT(*) AS glyph_count
                FROM glyph_occurrences go
                JOIN pages p ON p.id = go.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                {where}
                AND c.author != ''
                GROUP BY c.author
                ORDER BY c.author
                """ if where else """
                SELECT c.author, COUNT(*) AS glyph_count
                FROM glyph_occurrences go
                JOIN pages p ON p.id = go.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                WHERE c.author != ''
                GROUP BY c.author
                ORDER BY c.author
                """,
                values,
            ).fetchall()
        return {
            "copybooks": [_row_to_dict(row) for row in copybooks],
            "authors": [_row_to_dict(row) for row in authors],
        }

    def list_collections(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM collections ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def create_collection(self, name: str) -> dict[str, Any]:
        normalized = name.strip()
        if not normalized:
            raise ValueError("集字方案名称不能为空")
        now = _now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO collections
                    (name, input_text, direction, line_capacity, background, created_at, updated_at)
                VALUES (?, '', 'horizontal', 8, 'transparent', ?, ?)
                """,
                (normalized, now, now),
            )
            collection_id = int(cur.lastrowid)
        return self.get_collection(collection_id)

    def get_collection(self, collection_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM collections WHERE id = ?", (collection_id,)
            ).fetchone()
            items = conn.execute(
                """
                SELECT ci.position, ci.character, ci.occurrence_id,
                       go.text, go.confidence, go.page_id,
                       p.page_no, c.id AS copybook_id,
                       c.title AS copybook_title, c.author AS copybook_author
                FROM collection_items ci
                LEFT JOIN glyph_occurrences go ON go.id = ci.occurrence_id
                LEFT JOIN pages p ON p.id = go.page_id
                LEFT JOIN copybooks c ON c.id = p.copybook_id
                WHERE ci.collection_id = ?
                ORDER BY ci.position
                """,
                (collection_id,),
            ).fetchall()
        if row is None:
            raise ValueError(f"collection not found: {collection_id}")
        result = _row_to_dict(row)
        result["items"] = [_row_to_dict(item) for item in items]
        return result

    def update_collection(
        self,
        collection_id: int,
        data: dict[str, Any],
        items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        current = self.get_collection(collection_id)
        merged = {**current, **data}
        name = str(merged["name"]).strip()
        if not name:
            raise ValueError("集字方案名称不能为空")
        direction = str(merged.get("direction", "horizontal"))
        background = str(merged.get("background", "transparent"))
        if direction not in {"horizontal", "vertical"}:
            raise ValueError("不支持的集字方向")
        if background not in {"transparent", "white"}:
            raise ValueError("不支持的集字背景")
        capacity = max(1, min(int(merged.get("line_capacity", 8)), 50))
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE collections
                SET name = ?, input_text = ?, direction = ?, line_capacity = ?,
                    background = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    str(merged.get("input_text", "")),
                    direction,
                    capacity,
                    background,
                    _now(),
                    collection_id,
                ),
            )
            if items is not None:
                conn.execute(
                    "DELETE FROM collection_items WHERE collection_id = ?",
                    (collection_id,),
                )
                for item in items:
                    conn.execute(
                        """
                        INSERT INTO collection_items
                            (collection_id, position, character, occurrence_id)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            collection_id,
                            int(item["position"]),
                            str(item["character"]),
                            int(item["occurrence_id"]) if item.get("occurrence_id") is not None else None,
                        ),
                    )
        return self.get_collection(collection_id)

    def delete_collection(self, collection_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    def list_pages(self, copybook_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM pages WHERE copybook_id = ? ORDER BY page_no",
                (copybook_id,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def get_page(self, page_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        if row is None:
            raise ValueError(f"page not found: {page_id}")
        return _row_to_dict(row)

    def update_page(self, page_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
        allowed = [
            "crop_left_ratio",
            "crop_right_ratio",
            "crop_top_ratio",
            "crop_bottom_ratio",
            "rotation_degrees",
            "crop_override",
            "thumb_path",
        ]
        values = {
            key: (
                float(metadata[key])
                if key in {"crop_left_ratio", "crop_right_ratio", "crop_top_ratio", "crop_bottom_ratio", "rotation_degrees"}
                else int(metadata[key])
                if key == "crop_override"
                else str(metadata[key])
            )
            for key in allowed
            if key in metadata
        }
        if not values:
            return self.get_page(page_id)
        assignments = ", ".join(f"{key} = ?" for key in values)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE pages SET {assignments} WHERE id = ?",
                [*values.values(), page_id],
            )
        return self.get_page(page_id)

    def get_page_with_copybook(self, page_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT p.id, p.copybook_id, p.page_no, p.source_path, p.width, p.height, p.thumb_path,
                       c.source_type AS copybook_source_type, c.source_path AS copybook_source_path,
                       c.title AS copybook_title,
                       c.crop_left_ratio AS copybook_crop_left_ratio,
                       c.crop_right_ratio AS copybook_crop_right_ratio,
                       c.crop_top_ratio AS copybook_crop_top_ratio,
                       c.crop_bottom_ratio AS copybook_crop_bottom_ratio,
                       p.crop_left_ratio AS page_crop_left_ratio,
                       p.crop_right_ratio AS page_crop_right_ratio,
                       p.crop_top_ratio AS page_crop_top_ratio,
                       p.crop_bottom_ratio AS page_crop_bottom_ratio,
                       p.rotation_degrees AS rotation_degrees,
                       p.crop_override AS page_crop_override,
                       CASE WHEN COALESCE(p.crop_override, 0) = 1 THEN p.crop_left_ratio ELSE c.crop_left_ratio END AS crop_left_ratio,
                       CASE WHEN COALESCE(p.crop_override, 0) = 1 THEN p.crop_right_ratio ELSE c.crop_right_ratio END AS crop_right_ratio,
                       CASE WHEN COALESCE(p.crop_override, 0) = 1 THEN p.crop_top_ratio ELSE c.crop_top_ratio END AS crop_top_ratio,
                       CASE WHEN COALESCE(p.crop_override, 0) = 1 THEN p.crop_bottom_ratio ELSE c.crop_bottom_ratio END AS crop_bottom_ratio
                FROM pages p
                JOIN copybooks c ON c.id = p.copybook_id
                WHERE p.id = ?
                """,
                (page_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"page not found: {page_id}")
        return _row_to_dict(row)

    def add_queue_item(self, page_id: int, params: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_queue_item_by_page_id(page_id)
        if existing is not None:
            return existing

        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO queue_items (page_id, params_json, created_at) VALUES (?, ?, ?)",
                (page_id, json.dumps(params, ensure_ascii=False), _now()),
            )
            queue_id = int(cur.lastrowid)
        return self.get_queue_item(queue_id)

    def get_queue_item_by_page_id(self, page_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT q.*, p.page_no, p.copybook_id, c.title AS copybook_title
                FROM queue_items q
                JOIN pages p ON p.id = q.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                WHERE q.page_id = ?
                ORDER BY q.created_at, q.id
                LIMIT 1
                """,
                (page_id,),
            ).fetchone()
        return _decode_params(_row_to_dict(row)) if row is not None else None

    def list_queue_items(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT q.*, p.page_no, p.copybook_id, c.title AS copybook_title
                FROM queue_items q
                JOIN pages p ON p.id = q.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                ORDER BY q.created_at, q.id
                """
            ).fetchall()
        return [_decode_params(_row_to_dict(row)) for row in rows]

    def clear_queue_items(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM queue_items")

    def get_queue_item(self, item_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT q.*, p.page_no, p.copybook_id, c.title AS copybook_title
                FROM queue_items q
                JOIN pages p ON p.id = q.page_id
                JOIN copybooks c ON c.id = p.copybook_id
                WHERE q.id = ?
                """,
                (item_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"queue item not found: {item_id}")
        return _decode_params(_row_to_dict(row))

    def update_queue_item(self, item_id: int, params: dict[str, Any]) -> dict[str, Any]:
        current = self.get_queue_item(item_id)["params"]
        current.update(params)
        with self.connect() as conn:
            conn.execute(
                "UPDATE queue_items SET params_json = ? WHERE id = ?",
                (json.dumps(current, ensure_ascii=False), item_id),
            )
        return self.get_queue_item(item_id)

    def list_presets(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM presets ORDER BY updated_at DESC, id DESC").fetchall()
        return [_decode_params(_row_to_dict(row)) for row in rows]

    def create_preset(self, data: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO presets
                    (name, background_image, ink_color, foreground_threshold, mode, column_detection,
                     params_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data.get("background_image", ""),
                    data.get("ink_color", "#000000"),
                    int(data.get("foreground_threshold", 18)),
                    data.get("mode", "row"),
                    data.get("column_detection", "gray"),
                    json.dumps(data.get("params", {}), ensure_ascii=False),
                    now,
                    now,
                ),
            )
            preset_id = int(cur.lastrowid)
        return self.get_preset(preset_id)

    def get_preset(self, preset_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM presets WHERE id = ?", (preset_id,)).fetchone()
        if row is None:
            raise ValueError(f"preset not found: {preset_id}")
        return _decode_params(_row_to_dict(row))

    def update_preset(self, preset_id: int, data: dict[str, Any]) -> dict[str, Any]:
        current = self.get_preset(preset_id)
        merged = {**current, **data, "updated_at": _now()}
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE presets
                SET name = ?, background_image = ?, ink_color = ?, foreground_threshold = ?,
                    mode = ?, column_detection = ?, params_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    merged["name"],
                    merged.get("background_image", ""),
                    merged.get("ink_color", "#000000"),
                    int(merged.get("foreground_threshold", 18)),
                    merged.get("mode", "row"),
                    merged.get("column_detection", "gray"),
                    json.dumps(merged.get("params", {}), ensure_ascii=False),
                    merged["updated_at"],
                    preset_id,
                ),
            )
        return self.get_preset(preset_id)

    def delete_preset(self, preset_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,))

    def record_export(self, output_path: Path, page_count: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO exports (output_path, page_count, created_at) VALUES (?, ?, ?)",
                (str(output_path), page_count, _now()),
            )

    def count_generated_posts(self) -> int:
        with self.connect() as conn:
            value = conn.execute("SELECT COUNT(*) FROM generated_posts").fetchone()[0]
        return int(value)

    def create_generated_post(self, name: str, page_count: int) -> dict[str, Any]:
        now = _now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO generated_posts
                    (name, page_count, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, int(page_count), now, now),
            )
            post_id = int(cur.lastrowid)
        return self.get_generated_post(post_id)

    def update_generated_post(self, post_id: int, data: dict[str, Any]) -> dict[str, Any]:
        allowed = [
            "name",
            "original_pdf_path",
            "output_format",
            "thumb_path",
            "page_count",
            "result_count",
            "sync_status",
            "remote_path",
            "last_synced_at",
        ]
        values = {key: data[key] for key in allowed if key in data}
        if not values:
            return self.get_generated_post(post_id)
        values["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in values)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE generated_posts SET {assignments} WHERE id = ?",
                [*values.values(), post_id],
            )
        return self.get_generated_post(post_id)

    def list_generated_posts(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM generated_posts ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def get_generated_post(self, post_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM generated_posts WHERE id = ?", (post_id,)).fetchone()
        if row is None:
            raise ValueError(f"generated post not found: {post_id}")
        return _row_to_dict(row)

    def get_settings(self) -> dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

    def update_settings(self, settings: dict[str, Any]) -> dict[str, str]:
        with self.connect() as conn:
            for key, value in settings.items():
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (str(key), str(value)),
                )
        return self.get_settings()


def _now() -> int:
    return int(time.time())


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if column in {str(row["name"]) for row in rows}:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _decode_glyph(row: sqlite3.Row) -> dict[str, Any]:
    data = _row_to_dict(row)
    data["bbox"] = json.loads(data.pop("bbox_json"))
    return data


def _decode_params(data: dict[str, Any]) -> dict[str, Any]:
    if "params_json" in data:
        data["params"] = json.loads(data.pop("params_json") or "{}")
    return data
