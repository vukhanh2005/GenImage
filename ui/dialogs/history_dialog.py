from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models import HistoryEntry
from storage.history_manager import HistoryManager


class HistoryDialog(QDialog):
    def __init__(self, manager: HistoryManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.entries: list[HistoryEntry] = []
        self.setWindowTitle("Lịch sử tạo ảnh")
        self.resize(900, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)
        title = QLabel("Lịch sử tạo ảnh")
        title.setObjectName("title")
        root.addWidget(title)
        body = QHBoxLayout()
        body.setSpacing(12)
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(330)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        body.addWidget(self.list_widget, 2)
        body.addWidget(self.details, 3)
        root.addLayout(body, 1)

        actions = QHBoxLayout()
        self.open_button = QPushButton("Mở ảnh")
        self.folder_button = QPushButton("Mở thư mục")
        self.clear_button = QPushButton("Xóa lịch sử")
        self.clear_button.setObjectName("dangerButton")
        close_button = QPushButton("Đóng")
        actions.addWidget(self.open_button)
        actions.addWidget(self.folder_button)
        actions.addStretch()
        actions.addWidget(self.clear_button)
        actions.addWidget(close_button)
        root.addLayout(actions)

        self.list_widget.currentRowChanged.connect(self._show_entry)
        self.open_button.clicked.connect(self._open_image)
        self.folder_button.clicked.connect(self._open_folder)
        self.clear_button.clicked.connect(self._clear)
        close_button.clicked.connect(self.accept)
        self.refresh()

    def refresh(self) -> None:
        self.entries = self.manager.list_entries()
        self.list_widget.clear()
        for entry in self.entries:
            mode = "Chỉnh/Ghép" if entry.mode == "edit" else "Tạo ảnh"
            text = (
                f"{entry.time}\n{mode} · {entry.model} · {entry.size}\n"
                f"{entry.input_prompt[:80]}"
            )
            item = QListWidgetItem(text)
            item.setToolTip(entry.input_prompt)
            self.list_widget.addItem(item)
        has_entries = bool(self.entries)
        self.open_button.setEnabled(has_entries)
        self.folder_button.setEnabled(has_entries)
        self.clear_button.setEnabled(has_entries)
        if has_entries:
            self.list_widget.setCurrentRow(0)
        else:
            self.details.setPlainText("Chưa có ảnh nào được lưu vào lịch sử.")

    def _show_entry(self, row: int) -> None:
        if not 0 <= row < len(self.entries):
            return
        entry = self.entries[row]
        paths = "\n".join(entry.image_paths or [entry.image_path])
        mode = "Chỉnh/Ghép ảnh" if entry.mode == "edit" else "Tạo ảnh"
        source = (
            f"\nẢnh nguồn:\n{entry.source_image_path}\n"
            if entry.source_image_path
            else ""
        )
        self.details.setPlainText(
            f"Thời gian: {entry.time}\n"
            f"Chế độ: {mode}\n"
            f"Model: {entry.model}\n"
            f"Kích thước: {entry.size}\n\n"
            f"Prompt đầu vào:\n{entry.input_prompt}\n\n"
            f"Prompt đã dùng:\n{entry.generated_prompt or entry.input_prompt}\n"
            f"{source}\n"
            f"Tệp ảnh:\n{paths}"
        )

    def _selected_path(self) -> Path | None:
        row = self.list_widget.currentRow()
        if not 0 <= row < len(self.entries):
            return None
        entry = self.entries[row]
        paths = entry.image_paths or [entry.image_path]
        return Path(paths[0]) if paths and paths[0] else None

    def _open_image(self) -> None:
        path = self._selected_path()
        if path and path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else:
            QMessageBox.warning(self, "Không tìm thấy", "Tệp ảnh không còn tồn tại.")

    def _open_folder(self) -> None:
        path = self._selected_path()
        folder = path.parent if path else None
        if not folder or not folder.exists():
            QMessageBox.warning(self, "Không tìm thấy", "Thư mục ảnh không còn tồn tại.")
            return
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def _clear(self) -> None:
        answer = QMessageBox.question(
            self,
            "Xóa lịch sử",
            "Xóa toàn bộ lịch sử? Các tệp ảnh trên ổ đĩa sẽ được giữ lại.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.manager.clear()
            self.refresh()
