from __future__ import annotations

import time
from pathlib import Path

from utils.paths import TEMP_DIR


class CacheManager:
    def __init__(self, directory: Path = TEMP_DIR, max_age_days: int = 7, max_files: int = 200) -> None:
        self.directory = directory
        self.max_age_seconds = max_age_days * 86400
        self.max_files = max_files
        self.directory.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> int:
        now = time.time()
        files = sorted(
            (path for path in self.directory.iterdir() if path.is_file() and path.name != ".gitkeep"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        removed = 0
        for index, path in enumerate(files):
            expired = now - path.stat().st_mtime > self.max_age_seconds
            over_limit = index >= self.max_files
            if expired or over_limit:
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed

