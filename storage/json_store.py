from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any


class JsonStore:
    def __init__(self, path: Path, default: Any) -> None:
        self.path = path
        self.default = default
        self._lock = RLock()

    def read(self) -> Any:
        with self._lock:
            if not self.path.exists():
                return self.default
            try:
                with self.path.open("r", encoding="utf-8") as stream:
                    return json.load(stream)
            except (json.JSONDecodeError, OSError):
                return self.default

    def write(self, data: Any) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    json.dump(data, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

