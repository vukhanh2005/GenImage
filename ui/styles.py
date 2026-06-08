from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f0f6fc"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#1f6feb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6e7681"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#6e7681"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#6e7681"))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLE)


APP_STYLE = """
* {
    font-family: "Segoe UI";
    font-size: 13px;
    color: #e6edf3;
    outline: 0;
}
QMainWindow, QDialog, QMessageBox {
    background: #0d1117;
}
QWidget#appRoot {
    background: #0d1117;
}
QMenuBar {
    background: #0d1117;
    border-bottom: 1px solid #21262d;
    padding: 3px 8px;
}
QMenuBar::item {
    background: transparent;
    border-radius: 4px;
    padding: 5px 9px;
}
QMenuBar::item:selected {
    background: #21262d;
}
QMenu {
    background: #161b22;
    border: 1px solid #30363d;
    padding: 5px;
}
QMenu::item {
    border-radius: 4px;
    padding: 7px 24px;
}
QMenu::item:selected {
    background: #26364a;
}
QFrame#headerPanel {
    background: transparent;
    border: none;
}
QFrame#sidebar, QFrame#previewPanel {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}
QLabel#title {
    font-size: 23px;
    font-weight: 700;
    color: #f0f6fc;
}
QLabel#subtitle {
    color: #7d8590;
    font-size: 12px;
}
QLabel#sectionTitle {
    color: #9da7b3;
    font-size: 11px;
    font-weight: 700;
}
QLabel#muted {
    color: #7d8590;
}
QLabel#statusBadge {
    color: #79c0ff;
    background: #13233a;
    border: 1px solid #1f6feb;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
}
QLabel#countBadge {
    color: #a5d6ff;
    background: #1b2738;
    border: 1px solid #303d50;
    border-radius: 9px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
QFrame#separator {
    background: #30363d;
    border: none;
    max-height: 1px;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    color: #e6edf3;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 10px;
    selection-color: #ffffff;
    selection-background-color: #1f6feb;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {
    border-color: #484f58;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #58a6ff;
    background: #111820;
}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {
    color: #6e7681;
    background: #161b22;
}
QLineEdit::placeholder, QTextEdit::placeholder {
    color: #6e7681;
}
QComboBox {
    min-height: 20px;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox QAbstractItemView {
    color: #e6edf3;
    background: #161b22;
    border: 1px solid #484f58;
    selection-background-color: #1f6feb;
    padding: 4px;
}
QPushButton {
    min-height: 34px;
    color: #e6edf3;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 0 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: #292f36;
    border-color: #6e7681;
}
QPushButton:pressed {
    background: #30363d;
}
QPushButton:disabled {
    color: #6e7681;
    background: #161b22;
    border-color: #252b33;
}
QPushButton#primaryButton {
    color: #ffffff;
    background: #238636;
    border-color: #2ea043;
    min-height: 40px;
}
QPushButton#primaryButton:hover {
    background: #2ea043;
    border-color: #3fb950;
}
QPushButton#secondaryButton {
    color: #ffffff;
    background: #1f6feb;
    border-color: #388bfd;
}
QPushButton#secondaryButton:hover {
    background: #388bfd;
    border-color: #58a6ff;
}
QPushButton#dangerButton {
    color: #ff7b72;
    background: transparent;
    border-color: #6e2b2b;
}
QPushButton#dangerButton:hover {
    color: #ffffff;
    background: #b62324;
    border-color: #f85149;
}
QPushButton#headerButton {
    min-height: 32px;
    background: transparent;
}
QRadioButton {
    color: #c9d1d9;
    spacing: 7px;
}
QProgressBar {
    color: transparent;
    background: #21262d;
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
}
QProgressBar::chunk {
    background: #58a6ff;
    border-radius: 3px;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #3b434d;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #57606a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    border: none;
    height: 0;
}
QListWidget {
    color: #c9d1d9;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
}
QListWidget::item {
    border: none;
    border-radius: 5px;
    padding: 11px;
    margin: 2px;
}
QListWidget::item:hover {
    background: #1c2128;
}
QListWidget::item:selected {
    color: #ffffff;
    background: #1f3a5f;
}
QSplitter::handle {
    background: transparent;
    width: 8px;
}
QFrame#gallerySurface {
    background: #0d1117;
    border: 1px solid #252b33;
    border-radius: 6px;
}
QFrame#imageCard {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
}
QFrame#imageCard[selected="true"] {
    background: #17243a;
    border: 1px solid #58a6ff;
}
QFrame#sourcePanel {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
}
QLabel#sourcePreview {
    color: #6e7681;
    background: #080b10;
    border: 1px dashed #30363d;
    border-radius: 5px;
}
QLabel#imagePreview {
    background: #0a0d12;
    border: none;
    border-radius: 4px;
}
QLabel#emptyState {
    color: #6e7681;
    background: #0d1117;
    border: 1px dashed #30363d;
    border-radius: 6px;
    font-size: 14px;
}
QToolTip {
    color: #f0f6fc;
    background: #21262d;
    border: 1px solid #484f58;
    padding: 5px;
}
"""
