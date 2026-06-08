from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QAbstractScrollArea,
    QSplitter,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models import HistoryEntry, ImageArtifact
from services.api_client import ApiClient
from services.image_service import ImageService
from services.prompt_service import PromptService
from services.response_parser import ResponseParser
from storage.history_manager import HistoryManager
from storage.settings_manager import SettingsManager
from ui.dialogs.history_dialog import HistoryDialog
from ui.dialogs.image_dialog import ImageDialog
from ui.dialogs.loading_dialog import LoadingDialog
from ui.widgets.image_gallery import ImageGallery
from workers import TaskWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: SettingsManager | None = None,
        history: HistoryManager | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings or SettingsManager()
        self.history = history or HistoryManager()
        self.worker: TaskWorker | None = None
        self._close_when_finished = False
        self.loading_dialog = LoadingDialog(self)
        self.current_artifacts: list[ImageArtifact] = []
        self.source_image_path: Path | None = None
        self._build_ui()
        self._load_settings()
        self._apply_mode()

    def _build_ui(self) -> None:
        self.setWindowTitle("AI Image Studio")
        self.resize(1280, 820)
        self.setMinimumSize(940, 650)

        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 14, 18, 18)
        root.setSpacing(12)
        header_panel = QFrame()
        header_panel.setObjectName("headerPanel")
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        brand = QVBoxLayout()
        brand.setSpacing(1)
        title = QLabel("AI Image Studio")
        title.setObjectName("title")
        subtitle = QLabel("Không gian sáng tạo cá nhân")
        subtitle.setObjectName("subtitle")
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setObjectName("statusBadge")
        self.history_button = QPushButton("Lịch sử")
        self.history_button.setObjectName("headerButton")
        self.history_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self.history_button.clicked.connect(self._show_history)
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(self.status_label)
        header.addWidget(self.history_button)
        header_panel.setLayout(header)
        root.addWidget(header_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_preview())
        splitter.setSizes([440, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("sidebar")
        frame.setMinimumWidth(370)
        frame.setMaximumWidth(520)
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(11)

        layout.addWidget(self._section("Kết nối API"))
        api_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Nhập API Key")
        self.api_key_input.setClearButtonEnabled(True)
        self.save_key_button = QPushButton("Lưu")
        self.save_key_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_key_button.clicked.connect(self._save_api_key)
        api_row.addWidget(self.api_key_input, 1)
        api_row.addWidget(self.save_key_button)
        layout.addLayout(api_row)

        layout.addWidget(self._section("Chế độ"))
        mode_row = QVBoxLayout()
        mode_row.setSpacing(8)
        self.direct_radio = QRadioButton("Direct Prompt")
        self.ai_radio = QRadioButton("AI Prompt Generator")
        self.edit_radio = QRadioButton("Chỉnh/Ghép ảnh")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.direct_radio)
        self.mode_group.addButton(self.ai_radio)
        self.mode_group.addButton(self.edit_radio)
        self.ai_radio.setChecked(True)
        self.direct_radio.toggled.connect(self._apply_mode)
        self.ai_radio.toggled.connect(self._apply_mode)
        self.edit_radio.toggled.connect(self._apply_mode)
        mode_row.addWidget(self.direct_radio)
        mode_row.addWidget(self.ai_radio)
        mode_row.addWidget(self.edit_radio)
        layout.addLayout(mode_row)

        self.input_title = self._section("Input Prompt")
        layout.addWidget(self.input_title)
        self.input_prompt = QTextEdit()
        self.input_prompt.setPlaceholderText("Mô tả ý tưởng hoặc nhập prompt hoàn chỉnh...")
        self.input_prompt.setMinimumHeight(125)
        layout.addWidget(self.input_prompt)

        self.source_frame = QFrame()
        self.source_frame.setObjectName("sourcePanel")
        source_layout = QVBoxLayout(self.source_frame)
        source_layout.setContentsMargins(10, 10, 10, 10)
        source_layout.setSpacing(8)
        self.source_preview = QLabel("Chưa chọn ảnh nguồn")
        self.source_preview.setObjectName("sourcePreview")
        self.source_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.source_preview.setMinimumHeight(150)
        self.source_preview.setWordWrap(True)
        self.source_path_label = QLabel()
        self.source_path_label.setObjectName("muted")
        self.source_path_label.setWordWrap(True)
        source_actions = QHBoxLayout()
        self.select_source_button = QPushButton("Chọn ảnh")
        self.select_source_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        self.select_source_button.clicked.connect(self._select_source_image)
        self.clear_source_button = QPushButton("Xóa")
        self.clear_source_button.setObjectName("dangerButton")
        self.clear_source_button.setEnabled(False)
        self.clear_source_button.clicked.connect(self._clear_source_image)
        source_actions.addWidget(self.select_source_button, 1)
        source_actions.addWidget(self.clear_source_button)
        source_layout.addWidget(self.source_preview)
        source_layout.addWidget(self.source_path_label)
        source_layout.addLayout(source_actions)
        layout.addWidget(self.source_frame)

        self.generate_prompt_button = QPushButton("Tạo prompt chi tiết")
        self.generate_prompt_button.setObjectName("secondaryButton")
        self.generate_prompt_button.clicked.connect(self._generate_prompt)
        layout.addWidget(self.generate_prompt_button)

        self.generated_title = self._section("Generated Prompt")
        layout.addWidget(self.generated_title)
        self.generated_prompt = QTextEdit()
        self.generated_prompt.setPlaceholderText("Prompt chi tiết sẽ xuất hiện tại đây và có thể chỉnh sửa.")
        self.generated_prompt.setMinimumHeight(155)
        layout.addWidget(self.generated_prompt)

        layout.addWidget(self._section("Thiết lập ảnh"))
        form = QFormLayout()
        form.setSpacing(10)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-image-1.5"])
        self.size_combo = QComboBox()
        self.size_combo.addItems(["1024x1024", "1024x1536", "1536x1024"])
        self.count_combo = QComboBox()
        self.count_combo.addItems(["1", "2", "3", "4"])
        form.addRow("Model", self.model_combo)
        form.addRow("Kích thước", self.size_combo)
        form.addRow("Số lượng", self.count_combo)
        layout.addLayout(form)

        self.generate_image_button = QPushButton("Tạo ảnh")
        self.generate_image_button.setObjectName("primaryButton")
        self.generate_image_button.clicked.connect(self._generate_image)
        layout.addWidget(self.generate_image_button)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return frame

    def _build_preview(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("previewPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 15, 16, 16)
        layout.setSpacing(12)
        toolbar = QHBoxLayout()
        label = self._section("Xem trước")
        self.image_count_label = QLabel("0 ảnh")
        self.image_count_label.setObjectName("countBadge")
        self.save_button = QPushButton("Lưu ảnh")
        self.save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_images)
        self.open_button = QPushButton("Xem lớn")
        self.open_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_selected_image)
        toolbar.addWidget(label)
        toolbar.addWidget(self.image_count_label)
        toolbar.addStretch()
        toolbar.addWidget(self.open_button)
        toolbar.addWidget(self.save_button)
        layout.addLayout(toolbar)
        self.gallery = ImageGallery()
        self.gallery.image_open_requested.connect(lambda path: self._open_image(Path(path)))
        layout.addWidget(self.gallery, 1)
        return frame

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _load_settings(self) -> None:
        config = self.settings.load_api_config()
        self.api_key_input.setText(config.api_key)
        self.size_combo.setCurrentText(str(self.settings.get("last_size", "1024x1024")))
        self.count_combo.setCurrentText(str(self.settings.get("last_count", "1")))
        mode = self.settings.get("last_mode", "ai")
        self.direct_radio.setChecked(mode == "direct")
        self.edit_radio.setChecked(mode == "edit")
        self.ai_radio.setChecked(mode not in {"direct", "edit"})

    def _apply_mode(self) -> None:
        is_ai = self.ai_radio.isChecked()
        is_edit = self.edit_radio.isChecked()
        self.generate_prompt_button.setVisible(is_ai)
        self.generated_title.setVisible(is_ai)
        self.generated_prompt.setVisible(is_ai)
        self.source_frame.setVisible(is_edit)
        self.input_title.setText("Prompt chỉnh sửa" if is_edit else "Input Prompt")
        self.input_prompt.setPlaceholderText(
            "Mô tả phần cần thay đổi và những gì cần giữ nguyên..."
            if is_edit
            else "Mô tả ý tưởng hoặc nhập prompt hoàn chỉnh..."
        )
        self.generate_image_button.setText("Chỉnh sửa ảnh" if is_edit else "Tạo ảnh")

    def _save_api_key(self) -> None:
        key = self.api_key_input.text().strip()
        self.settings.save_api_key(key)
        QMessageBox.information(self, "Đã lưu", "API Key đã được lưu trong file .env.")

    def _services(self) -> tuple[PromptService, ImageService]:
        config = self.settings.load_api_config()
        config.api_key = self.api_key_input.text().strip()
        client = ApiClient(config)
        parser = ResponseParser(client)
        return PromptService(client, parser), ImageService(client, parser)

    def _generate_prompt(self) -> None:
        description = self.input_prompt.toPlainText().strip()
        if not description:
            QMessageBox.warning(self, "Thiếu mô tả", "Hãy nhập mô tả ngắn trước khi tạo prompt.")
            return
        prompt_service, _ = self._services()
        self._start_task(
            "Đang sinh prompt...",
            lambda progress: prompt_service.generate(description, progress),
            self._prompt_ready,
        )

    def _generate_image(self) -> None:
        input_text = self.input_prompt.toPlainText().strip()
        is_ai = self.ai_radio.isChecked()
        is_edit = self.edit_radio.isChecked()
        prompt = self.generated_prompt.toPlainText().strip() if is_ai else input_text
        if not input_text:
            QMessageBox.warning(self, "Thiếu prompt", "Hãy nhập nội dung mô tả ảnh.")
            return
        if is_ai and not prompt:
            QMessageBox.warning(
                self,
                "Chưa có prompt chi tiết",
                "Hãy tạo prompt chi tiết hoặc nhập trực tiếp vào ô Generated Prompt.",
            )
            return
        if is_edit and not self.source_image_path:
            QMessageBox.warning(
                self,
                "Chưa chọn ảnh",
                "Hãy chọn một ảnh nguồn trước khi chỉnh sửa.",
            )
            return
        _, image_service = self._services()
        model = self.model_combo.currentText()
        size = self.size_combo.currentText()
        count = int(self.count_combo.currentText())
        if is_edit:
            source = self.source_image_path
            assert source is not None
            self._start_task(
                "Đang gửi ảnh nguồn để chỉnh sửa...",
                lambda progress: image_service.edit(
                    source, prompt, model, size, count, progress
                ),
                self._images_ready,
            )
        else:
            self._start_task(
                "Đang gửi yêu cầu tạo ảnh...",
                lambda progress: image_service.generate(prompt, model, size, count, progress),
                self._images_ready,
            )

    def _start_task(self, initial_status: str, task, success_handler) -> None:
        if self.worker and self.worker.isRunning():
            return
        self._set_busy(True)
        self.loading_dialog.set_status(initial_status)
        self.loading_dialog.show()
        self.worker = TaskWorker(task)
        self.worker.progress.connect(self._update_progress)
        self.worker.succeeded.connect(success_handler)
        self.worker.failed.connect(self._task_failed)
        self.worker.finished.connect(self._task_finished)
        self.worker.start()

    def _update_progress(self, message: str) -> None:
        self.status_label.setText(message)
        self.loading_dialog.set_status(message)

    def _prompt_ready(self, prompt: object) -> None:
        self.generated_prompt.setPlainText(str(prompt))
        self.status_label.setText("Đã tạo prompt")

    def _images_ready(self, artifacts: object) -> None:
        self.current_artifacts = list(artifacts)  # type: ignore[arg-type]
        paths = [artifact.path for artifact in self.current_artifacts]
        self.gallery.set_images(paths)
        self.image_count_label.setText(f"{len(paths)} ảnh")
        self.save_button.setEnabled(bool(paths))
        self.open_button.setEnabled(bool(paths))
        self.status_label.setText("Hoàn tất")
        self.settings.set("last_size", self.size_combo.currentText())
        self.settings.set("last_count", self.count_combo.currentText())
        if self.edit_radio.isChecked():
            mode = "edit"
        elif self.ai_radio.isChecked():
            mode = "ai"
        else:
            mode = "direct"
        self.settings.set("last_mode", mode)

    def _task_failed(self, message: str) -> None:
        logger.error("Background task failed: %s", message)
        self.status_label.setText("Có lỗi xảy ra")
        QMessageBox.critical(self, "Không thể hoàn tất", message)

    def _task_finished(self) -> None:
        self.loading_dialog.hide()
        self._set_busy(False)
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        if self._close_when_finished:
            self._close_when_finished = False
            self.close()

    def _set_busy(self, busy: bool) -> None:
        self.generate_prompt_button.setEnabled(not busy)
        self.generate_image_button.setEnabled(not busy)
        self.save_key_button.setEnabled(not busy)
        self.select_source_button.setEnabled(not busy)
        self.clear_source_button.setEnabled(not busy and self.source_image_path is not None)
        if busy:
            self.save_button.setEnabled(False)
            self.open_button.setEnabled(False)
        else:
            has_images = bool(self.current_artifacts)
            self.save_button.setEnabled(has_images)
            self.open_button.setEnabled(has_images)

    def _save_images(self) -> None:
        if not self.current_artifacts:
            return
        start_dir = str(self.settings.get("last_save_directory", str(Path.home() / "Pictures")))
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu ảnh", start_dir)
        if not directory:
            return
        target_dir = Path(directory)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_paths: list[Path] = []
        try:
            for index, artifact in enumerate(self.current_artifacts, start=1):
                suffix = artifact.path.suffix or ".png"
                target = self._unique_path(target_dir / f"ai_image_{timestamp}_{index}{suffix}")
                shutil.copy2(artifact.path, target)
                saved_paths.append(target)
        except OSError as exc:
            QMessageBox.critical(self, "Không thể lưu", f"Lỗi khi lưu ảnh: {exc}")
            return

        self.settings.set("last_save_directory", str(target_dir))
        input_prompt = self.input_prompt.toPlainText().strip()
        generated = self.generated_prompt.toPlainText().strip() if self.ai_radio.isChecked() else ""
        mode = "edit" if self.edit_radio.isChecked() else "generate"
        self.history.add(
            HistoryEntry(
                time=datetime.now().astimezone().isoformat(timespec="seconds"),
                input_prompt=input_prompt,
                generated_prompt=generated,
                image_path=str(saved_paths[0]),
                image_paths=[str(path) for path in saved_paths],
                model=self.model_combo.currentText(),
                size=self.size_combo.currentText(),
                mode=mode,
                source_image_path=str(self.source_image_path or ""),
            )
        )
        self.status_label.setText(f"Đã lưu {len(saved_paths)} ảnh")
        QMessageBox.information(
            self,
            "Đã lưu",
            f"Đã lưu {len(saved_paths)} ảnh vào:\n{target_dir}",
        )

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        counter = 2
        while True:
            candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _open_selected_image(self) -> None:
        path = self.gallery.selected_path()
        if path:
            self._open_image(path)

    def _open_image(self, path: Path) -> None:
        if not path.exists():
            QMessageBox.warning(self, "Không tìm thấy", "Tệp ảnh không còn tồn tại.")
            return
        dialog = ImageDialog(path, self)
        dialog.exec()

    def _show_history(self) -> None:
        HistoryDialog(self.history, self).exec()

    def _select_source_image(self) -> None:
        start_dir = str(
            self.settings.get(
                "last_source_directory",
                str(self.source_image_path.parent if self.source_image_path else Path.home()),
            )
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh nguồn",
            start_dir,
            "Ảnh (*.png *.jpg *.jpeg *.webp);;Tất cả tệp (*)",
        )
        if not file_path:
            return
        path = Path(file_path)
        if path.stat().st_size > 50 * 1024 * 1024:
            QMessageBox.warning(self, "Ảnh quá lớn", "Ảnh nguồn phải nhỏ hơn 50 MB.")
            return
        try:
            with Image.open(path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            QMessageBox.warning(self, "Ảnh không hợp lệ", f"Không thể đọc ảnh nguồn: {exc}")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            QMessageBox.warning(self, "Ảnh không hợp lệ", "Không thể hiển thị ảnh nguồn.")
            return
        self.source_image_path = path
        self.source_preview.setText("")
        self.source_preview.setPixmap(
            pixmap.scaled(
                360,
                190,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.source_path_label.setText(path.name)
        self.source_path_label.setToolTip(str(path))
        self.clear_source_button.setEnabled(True)
        self.settings.set("last_source_directory", str(path.parent))

    def _clear_source_image(self) -> None:
        self.source_image_path = None
        self.source_preview.clear()
        self.source_preview.setText("Chưa chọn ảnh nguồn")
        self.source_path_label.clear()
        self.source_path_label.setToolTip("")
        self.clear_source_button.setEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            answer = QMessageBox.question(
                self,
                "Đang xử lý",
                "Yêu cầu API vẫn đang chạy. Bạn có chắc muốn đóng ứng dụng?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._close_when_finished = True
            self.hide()
            event.ignore()
            return
        event.accept()
