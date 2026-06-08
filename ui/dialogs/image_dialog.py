from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout, QWidget


class ImageDialog(QDialog):
    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(image_path.name)
        self.resize(1000, 760)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        scroll = QScrollArea()
        scroll.setObjectName("gallerySurface")
        scroll.setWidgetResizable(True)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(image_path))
        label.setPixmap(pixmap)
        label.resize(pixmap.size())
        scroll.setWidget(label)
        layout.addWidget(scroll)
