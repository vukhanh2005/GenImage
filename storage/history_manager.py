from __future__ import annotations

from pathlib import Path

from models import HistoryEntry
from storage.json_store import JsonStore
from utils.paths import HISTORY_PATH


class HistoryManager:
    def __init__(self, path: Path = HISTORY_PATH) -> None:
        self._store = JsonStore(path, [])

    def list_entries(self) -> list[HistoryEntry]:
        data = self._store.read()
        if not isinstance(data, list):
            return []
        return [HistoryEntry.from_dict(item) for item in data if isinstance(item, dict)]

    def add(self, entry: HistoryEntry) -> None:
        entries = self.list_entries()
        entries.insert(0, entry)
        self._store.write([item.to_dict() for item in entries[:500]])

    def clear(self) -> None:
        self._store.write([])

