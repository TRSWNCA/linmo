from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @property
    def db_path(self) -> Path:
        return self.root / "linmo.sqlite3"

    @property
    def library_dir(self) -> Path:
        return self.root / "library"

    @property
    def thumbs_dir(self) -> Path:
        return self.root / "cache" / "thumbs"

    @property
    def previews_dir(self) -> Path:
        return self.root / "cache" / "previews"

    @property
    def generated_thumbs_dir(self) -> Path:
        return self.root / "cache" / "generated-thumbs"

    @property
    def presets_dir(self) -> Path:
        return self.root / "presets"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def generated_dir(self) -> Path:
        return self.root / "generated"

    def ensure(self) -> None:
        for path in [
            self.root,
            self.library_dir,
            self.thumbs_dir,
            self.previews_dir,
            self.generated_thumbs_dir,
            self.presets_dir,
            self.exports_dir,
            self.generated_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


def default_app_paths() -> AppPaths:
    configured = os.environ.get("LINMO_APP_DATA")
    if configured:
        return AppPaths(Path(configured).expanduser())
    return AppPaths(Path.home() / ".local" / "share" / "linmo")
