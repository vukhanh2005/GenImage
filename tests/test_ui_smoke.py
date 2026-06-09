from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from storage.history_manager import HistoryManager
from storage.settings_manager import SettingsManager
from ui.main_window import MainWindow


class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_constructs(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            window = MainWindow(
                SettingsManager(root / "settings.json", root / ".env"),
                HistoryManager(root / "history.json"),
            )
            self.assertEqual(window.model_combo.currentText(), "gpt-image-2")
            self.assertFalse(window.save_button.isEnabled())
            window.close()

    def test_edit_mode_shows_source_picker_and_changes_action(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            window = MainWindow(
                SettingsManager(root / "settings.json", root / ".env"),
                HistoryManager(root / "history.json"),
            )
            window.show()
            window.edit_radio.setChecked(True)
            self.app.processEvents()

            self.assertTrue(window.source_frame.isVisible())
            self.assertFalse(window.generated_prompt.isVisible())
            self.assertEqual(window.generate_image_button.text(), "Chỉnh sửa ảnh")
            self.assertEqual(window.input_title.text(), "Prompt chỉnh sửa")
            window.close()


if __name__ == "__main__":
    unittest.main()
