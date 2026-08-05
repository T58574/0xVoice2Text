from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCursor
import pyperclip
import json

class HistoryWindow(QDialog):
    reinject_text_signal = pyqtSignal(str)

    def __init__(self, history_mgr, parent=None):
        super().__init__(parent)
        self.history_mgr = history_mgr
        self.setWindowTitle("0xVoice2Text // TRANSCRIPTION HISTORY")
        self.resize(560, 480)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: #ffffff;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #09090b;
                color: #ffffff;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #ffffff;
            }
            QListWidget {
                background: #000000;
                border: 1px solid #27272a;
                border-radius: 8px;
                outline: none;
                color: #ffffff;
                padding: 6px;
            }
            QListWidget::item {
                background: #050505;
                border: 1px solid #1f1f23;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 6px;
            }
            QListWidget::item:hover {
                background: #ffffff;
                border-color: #ffffff;
                color: #000000;
            }
            QPushButton {
                background: #000000;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #ffffff;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 11px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: #ffffff;
                color: #000000;
            }
            QPushButton#btnDanger {
                background: #000000;
                color: #a1a1aa;
                border-color: #3f3f46;
            }
            QPushButton#btnDanger:hover {
                background: #ffffff;
                color: #000000;
                border-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        hdr_layout = QHBoxLayout()
        title_lbl = QLabel("📜 TRANSCRIPTION HISTORY")
        title_lbl.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #ffffff;")
        
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch()

        btn_export = QPushButton("EXPORT JSON")
        btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_export.clicked.connect(self.export_json)

        btn_clear = QPushButton("CLEAR ALL")
        btn_clear.setObjectName("btnDanger")
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.clicked.connect(self.clear_all)

        hdr_layout.addWidget(btn_export)
        hdr_layout.addWidget(btn_clear)
        layout.addLayout(hdr_layout)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search transcription history...")
        self.search_input.textChanged.connect(self.filter_items)
        layout.addWidget(self.search_input)

        # History List Widget
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget)

        # Footer info
        self.lbl_count = QLabel("Total entries: 0")
        self.lbl_count.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        layout.addWidget(self.lbl_count)

        self.reload_history()

    def reload_history(self, filter_text=""):
        self.list_widget.clear()
        items = self.history_mgr.get_all()

        count = 0
        for item in items:
            text = item.get("text", "")
            ts = item.get("timestamp", "")

            if filter_text and filter_text.lower() not in text.lower():
                continue

            count += 1
            char_count = len(text)
            display_text = f"[{ts}] ({char_count} chars)\n{text}"
            
            widget_item = QListWidgetItem(display_text)
            widget_item.setData(Qt.ItemDataRole.UserRole, text)
            self.list_widget.addItem(widget_item)

        self.lbl_count.setText(f"Showing {count} entries (Double-click to paste into active window)")

    def filter_items(self, text):
        self.reload_history(filter_text=text)

    def _on_double_click(self, item):
        text = item.data(Qt.ItemDataRole.UserRole)
        if text:
            self.reinject_text_signal.emit(text)
            self.close()

    def clear_all(self):
        self.history_mgr.clear()
        self.reload_history()

    def export_json(self):
        items = self.history_mgr.get_all()
        if not items:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save History JSON", "0xvoice2text_history.json", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(items, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[HistoryWindow] Error exporting JSON: {e}")
