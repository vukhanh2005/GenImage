from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from storage.cache_manager import CacheManager
from ui.main_window import MainWindow
from ui.styles import apply_dark_theme
from utils.logging_config import configure_logging
from utils.paths import ensure_app_directories


def main() -> int:
    ensure_app_directories()
    configure_logging()
    removed = CacheManager().cleanup()
    logging.getLogger(__name__).info("Application starting; cache files removed=%s", removed)

    app = QApplication(sys.argv)
    app.setApplicationName("AI Image Studio")
    app.setOrganizationName("Personal")
    app.setFont(QFont("Segoe UI", 10))
    apply_dark_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
