from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QLabel,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ClickableImage(QLabel):
    clicked = Signal()
    double_clicked = Signal()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class ImageGallery(QWidget):
    selection_changed = Signal(int)
    image_open_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.paths: list[Path] = []
        self.selected_index = -1
        self._button_group = QButtonGroup(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("gallerySurface")
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(12, 12, 12, 12)
        self.grid.setSpacing(12)
        self.scroll.setWidget(self.content)
        self.placeholder = QLabel("Ảnh được tạo sẽ xuất hiện tại đây")
        self.placeholder.setObjectName("emptyState")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setMinimumHeight(360)
        root.addWidget(self.placeholder)
        root.addWidget(self.scroll)
        self.scroll.hide()

    def set_images(self, paths: list[Path]) -> None:
        self.clear()
        self.paths = paths
        if not paths:
            return
        self.placeholder.hide()
        self.scroll.show()
        columns = 2 if len(paths) > 1 else 1
        for index, path in enumerate(paths):
            frame = QFrame()
            frame.setObjectName("imageCard")
            frame.setProperty("selected", False)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(8, 8, 8, 8)
            preview = ClickableImage()
            preview.setObjectName("imagePreview")
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setMinimumSize(240, 220)
            pixmap = QPixmap(str(path))
            preview.setPixmap(
                pixmap.scaled(
                    520,
                    440,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            selector = QRadioButton(f"Ảnh {index + 1}")
            self._button_group.addButton(selector, index)
            selector.toggled.connect(
                lambda checked, current=index: checked and self._select(current)
            )
            preview.clicked.connect(lambda current=index: self._select_and_check(current))
            preview.double_clicked.connect(lambda current=path: self.image_open_requested.emit(str(current)))
            frame_layout.addWidget(preview, 1)
            frame_layout.addWidget(selector)
            self.grid.addWidget(frame, index // columns, index % columns)
        self._select_and_check(0)

    def selected_path(self) -> Path | None:
        if 0 <= self.selected_index < len(self.paths):
            return self.paths[self.selected_index]
        return None

    def clear(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for button in self._button_group.buttons():
            self._button_group.removeButton(button)
        self.paths = []
        self.selected_index = -1
        self.scroll.hide()
        self.placeholder.show()

    def _select_and_check(self, index: int) -> None:
        button = self._button_group.button(index)
        if button:
            button.setChecked(True)
        self._select(index)

    def _select(self, index: int) -> None:
        self.selected_index = index
        for card_index in range(self.grid.count()):
            card = self.grid.itemAt(card_index).widget()
            if card:
                card.setProperty("selected", card_index == index)
                card.style().unpolish(card)
                card.style().polish(card)
        self.selection_changed.emit(index)
