from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from models import HistoryEntry
from storage.history_manager import HistoryManager
from storage.settings_manager import SettingsManager


class StorageTests(unittest.TestCase):
    def test_settings_and_env_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manager = SettingsManager(root / "settings.json", root / ".env")
            manager.set("last_count", "3")
            manager.save_api_key("secret-key")
            self.assertEqual(manager.get("last_count"), "3")
            self.assertEqual(manager.load_api_config().api_key, "secret-key")

    def test_history_round_trip_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            manager = HistoryManager(Path(folder) / "history.json")
            entry = HistoryEntry(
                time="2026-06-08T10:00:00+07:00",
                input_prompt="input",
                generated_prompt="generated",
                image_path="one.png",
                image_paths=["one.png", "two.png"],
                model="gpt-image-1.5",
                size="1024x1024",
                mode="edit",
                source_image_path="source.png",
            )
            manager.add(entry)
            loaded = manager.list_entries()
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].image_paths, ["one.png", "two.png"])
            self.assertEqual(loaded[0].mode, "edit")
            self.assertEqual(loaded[0].source_image_path, "source.png")
            manager.clear()
            self.assertEqual(manager.list_entries(), [])


if __name__ == "__main__":
    unittest.main()
