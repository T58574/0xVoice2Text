import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCursor
import pyperclip
from src.core.logger import get_log_file_path, logger

class ErrorNotificationDialog(QDialog):
    """
    Cyberpunk-styled Error Notification Window for Groq API & Gemini/Gemma AI failures.
    Displays detailed error diagnostic information, solution hints, copy log actions, and settings shortcut.
    """
    open_settings_requested = pyqtSignal()

    def __init__(self, title: str, error_msg: str, solution_hint: str = "", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.error_msg = error_msg
        self.solution_hint = solution_hint

        self.setWindowTitle(f"⚠️ {title}")
        self.resize(500, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint | Qt.WindowType.WindowStaysOnTopHint)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: #ffffff;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
            }
            QFrame#mainFrame {
                background: #000000;
                border: 1.5px solid #ef4444;
                border-radius: 10px;
            }
            QLabel#lblTitle {
                color: #ef4444;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QLabel#lblHint {
                color: #fbbf24;
                font-size: 11px;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #09090b;
                color: #f87171;
                border: 1px solid #27272a;
                border-radius: 6px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QPushButton {
                background: #09090b;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3f3f46;
                border-radius: 5px;
                padding: 7px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #ffffff;
                color: #000000;
                border-color: #ffffff;
            }
            QPushButton#btnSettings {
                background: #ef4444;
                color: #ffffff;
                border: 1px solid #ef4444;
            }
            QPushButton#btnSettings:hover {
                background: #dc2626;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame(self)
        frame.setObjectName("mainFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 14, 16, 14)
        frame_layout.setSpacing(10)

        # Header
        lbl_title = QLabel(f"❌ {self.title_text.upper()}", frame)
        lbl_title.setObjectName("lblTitle")
        frame_layout.addWidget(lbl_title)

        # Solution hint if provided
        if self.solution_hint:
            lbl_hint = QLabel(f"💡 РЕКОМЕНДАЦИЯ: {self.solution_hint}", frame)
            lbl_hint.setObjectName("lblHint")
            lbl_hint.setWordWrap(True)
            frame_layout.addWidget(lbl_hint)

        # Error log view text box
        self.txt_error = QTextEdit(frame)
        self.txt_error.setReadOnly(True)
        self.txt_error.setPlainText(self.error_msg)
        frame_layout.addWidget(self.txt_error)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        btn_copy = QPushButton("📋 Скопировать", frame)
        btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_copy.clicked.connect(self.copy_error_to_clipboard)

        btn_log = QPushButton("📂 Открыть лог", frame)
        btn_log.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_log.clicked.connect(self.open_log_file)

        btn_settings = QPushButton("⚙️ Настройки", frame)
        btn_settings.setObjectName("btnSettings")
        btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_settings.clicked.connect(self.on_settings_clicked)

        btn_close = QPushButton("✕ Закрыть", frame)
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(btn_copy)
        btn_layout.addWidget(btn_log)
        btn_layout.addWidget(btn_settings)
        btn_layout.addWidget(btn_close)
        frame_layout.addLayout(btn_layout)

        main_layout.addWidget(frame)

    def copy_error_to_clipboard(self):
        full_text = f"=== 0xVoice2Text Error Log ===\nTitle: {self.title_text}\nHint: {self.solution_hint}\nDetails:\n{self.error_msg}"
        pyperclip.copy(full_text)
        logger.info("[ErrorDialog] Error log copied to clipboard.")

    def open_log_file(self):
        log_path = get_log_file_path()
        logger.info(f"[ErrorDialog] Opening log file: {log_path}")
        if os.path.exists(log_path):
            try:
                if os.name == 'nt':
                    os.startfile(log_path)
                else:
                    subprocess.Popen(['xdg-open', log_path])
            except Exception as e:
                logger.error(f"[ErrorDialog] Failed to open log file: {e}")

    def on_settings_clicked(self):
        self.accept()
        self.open_settings_requested.emit()
