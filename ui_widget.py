from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QLinearGradient, QCursor

class SciFiWaveVisualizer(QWidget):
    """
    14-bar spectrum visualizer tuned for OLED Black theme.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 24)
        self.num_bars = 14
        self.target_levels = [0.08] * self.num_bars
        self.current_levels = [0.08] * self.num_bars
        self.peaks = [0.08] * self.num_bars
        self.is_active = False
        self.state = "idle" # idle, recording, transcribing

        # Smooth animation timer 60 FPS
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16) # ~60 fps
        self.anim_timer.timeout.connect(self._update_physics)
        self.anim_timer.start()

    def update_rms(self, rms):
        import random
        if not self.is_active:
            self.target_levels = [0.08] * self.num_bars
        else:
            base = min(1.0, max(0.12, rms * 9.0))
            new_targets = []
            for i in range(self.num_bars):
                center_factor = 1.0 - abs(i - self.num_bars / 2) / (self.num_bars / 2) * 0.4
                val = min(1.0, max(0.08, base * center_factor * (0.6 + random.random() * 0.8)))
                new_targets.append(val)
            self.target_levels = new_targets

    def set_state(self, state: str):
        self.state = state
        self.is_active = (state == "recording")
        if not self.is_active:
            self.target_levels = [0.08] * self.num_bars

    def _update_physics(self):
        changed = False
        for i in range(self.num_bars):
            target = self.target_levels[i]
            curr = self.current_levels[i]
            diff = target - curr
            self.current_levels[i] += diff * 0.25

            if self.current_levels[i] > self.peaks[i]:
                self.peaks[i] = self.current_levels[i]
            else:
                self.peaks[i] = max(0.08, self.peaks[i] - 0.02)

            if abs(diff) > 0.001:
                changed = True

        if changed or self.is_active or self.state == "transcribing":
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_w = 4
        spacing = 2
        total_w = self.num_bars * bar_w + (self.num_bars - 1) * spacing
        start_x = (w - total_w) // 2

        import time
        t = time.time() * 8.0

        for i in range(self.num_bars):
            if self.state == "transcribing":
                import math
                val = 0.3 + 0.6 * (0.5 + 0.5 * math.sin(t - i * 0.4))
                bar_h = max(3, int(h * val))
            else:
                bar_h = max(2, int(h * self.current_levels[i]))

            x = start_x + i * (bar_w + spacing)
            y = h - bar_h

            if self.state == "recording":
                color_top = QColor(255, 255, 255)
                color_bot = QColor(0, 240, 255)
            elif self.state == "transcribing":
                color_top = QColor(255, 230, 100)
                color_bot = QColor(255, 140, 0)
            else:
                color_top = QColor(160, 160, 160, 180)
                color_bot = QColor(60, 60, 60, 120)

            gradient = QLinearGradient(x, h, x, y)
            gradient.setColorAt(0, color_bot)
            gradient.setColorAt(1, color_top)

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, 1, 1)

            if self.state == "recording":
                peak_y = int(h - (h * self.peaks[i])) - 2
                peak_y = max(0, min(h - 2, peak_y))
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.drawRect(x, peak_y, bar_w, 1)


class CyberpunkHistoryDrawer(QFrame):
    """Collapsible OLED Black History Drawer."""
    item_reinject_signal = pyqtSignal(str)

    def __init__(self, history_mgr, parent=None):
        super().__init__(parent)
        self.history_mgr = history_mgr
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 1px solid #27272a;
                border-top: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                color: #f4f4f5;
            }
            QListWidget::item {
                background: #050505;
                border: 1px solid #1f1f23;
                border-radius: 6px;
                padding: 6px 8px;
                margin-bottom: 4px;
                font-size: 11px;
            }
            QListWidget::item:hover {
                background: #00f0ff;
                border-color: #00f0ff;
                color: #000000;
            }
            QLabel {
                color: #a1a1aa;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton#btnClear {
                background: transparent;
                color: #a1a1aa;
                border: none;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton#btnClear:hover {
                color: #ef4444;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        hdr_layout = QHBoxLayout()
        lbl_hdr = QLabel("ИСТОРИЯ ВВОДА")
        self.btn_clear = QPushButton("ОЧИСТИТЬ", self)
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear.clicked.connect(self.clear_history)

        hdr_layout.addWidget(lbl_hdr)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self.btn_clear)
        layout.addLayout(hdr_layout)

        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def reload_items(self):
        self.list_widget.clear()
        items = self.history_mgr.get_all()
        if not items:
            empty_item = QListWidgetItem("История пуста")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(empty_item)
            return

        for item in items:
            display_text = f"[{item['timestamp']}]  {item['text']}"
            widget_item = QListWidgetItem(display_text)
            widget_item.setData(Qt.ItemDataRole.UserRole, item['text'])
            self.list_widget.addItem(widget_item)

    def clear_history(self):
        self.history_mgr.clear()
        self.reload_items()

    def _on_item_clicked(self, item):
        text = item.data(Qt.ItemDataRole.UserRole)
        if text:
            self.item_reinject_signal.emit(text)


class DesktopWidget(QWidget):
    open_settings_signal = pyqtSignal()
    reinject_text_signal = pyqtSignal(str)

    def __init__(self, config, history_mgr=None):
        super().__init__()
        self.config = config
        self.history_mgr = history_mgr
        self.drag_position = QPoint()
        self.is_dragging = False
        self.history_expanded = False

        self.init_window_flags()
        self.init_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.current_rms_provider = None

    def init_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        pos = self.config.get("widget_position", {"x": 100, "y": 100})
        self.move(pos.get("x", 100), pos.get("y", 100))

    def init_ui(self):
        self.setFixedWidth(320)
        self.setFixedHeight(70)

        main_v_layout = QVBoxLayout(self)
        main_v_layout.setContentsMargins(0, 0, 0, 0)
        main_v_layout.setSpacing(0)

        # Main OLED Black Frame
        self.main_frame = QFrame(self)
        self.main_frame.setFixedHeight(64)
        self.main_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 1px solid #27272a;
                border-radius: 14px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 255))
        shadow.setOffset(0, 4)
        self.main_frame.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.main_frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.visualizer = SciFiWaveVisualizer(self.main_frame)
        layout.addWidget(self.visualizer)

        mid_layout = QVBoxLayout()
        mid_layout.setSpacing(2)

        self.lbl_status = QLabel("READY")
        self.lbl_status.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #ffffff; border: none; background: transparent; letter-spacing: 0.5px;")

        self.lbl_hotkey = QLabel(f"HOLD [{self.config.get('hotkey', 'caps_lock').upper()}]")
        self.lbl_hotkey.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.lbl_hotkey.setStyleSheet("""
            background: #09090b;
            color: #a1a1aa;
            border-radius: 3px;
            padding: 1px 5px;
            border: 1px solid #27272a;
        """)

        mid_layout.addWidget(self.lbl_status)
        mid_layout.addWidget(self.lbl_hotkey)
        layout.addLayout(mid_layout)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(3)

        cyber_btn_style = """
            QPushButton {
                background: #000000;
                color: #a1a1aa;
                border: 1px solid #27272a;
                font-family: 'Consolas', sans-serif;
                font-size: 10px;
                font-weight: bold;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPushButton:hover {
                color: #000000;
                background: #00f0ff;
                border-color: #00f0ff;
            }
        """

        self.btn_hist = QPushButton("HIST", self.main_frame)
        self.btn_hist.setStyleSheet(cyber_btn_style)
        self.btn_hist.setToolTip("История вводов")
        self.btn_hist.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_hist.clicked.connect(self.toggle_history_drawer)

        self.btn_settings = QPushButton("⚙", self.main_frame)
        self.btn_settings.setStyleSheet(cyber_btn_style)
        self.btn_settings.setToolTip("Настройки")
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.clicked.connect(self.open_settings_signal.emit)

        self.btn_close = QPushButton("✕", self.main_frame)
        self.btn_close.setStyleSheet(cyber_btn_style)
        self.btn_close.setToolTip("Свернуть в трей")
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.clicked.connect(self.hide)

        btn_layout.addWidget(self.btn_hist)
        btn_layout.addWidget(self.btn_settings)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        main_v_layout.addWidget(self.main_frame)

        if self.history_mgr:
            self.history_drawer = CyberpunkHistoryDrawer(self.history_mgr, self)
            self.history_drawer.item_reinject_signal.connect(self.reinject_text_signal.emit)
            self.history_drawer.hide()
            main_v_layout.addWidget(self.history_drawer)

    def toggle_history_drawer(self):
        if not hasattr(self, 'history_drawer'):
            return

        self.history_expanded = not self.history_expanded
        if self.history_expanded:
            self.history_drawer.reload_items()
            self.history_drawer.show()
            self.setFixedHeight(230)
            self.btn_hist.setStyleSheet("""
                QPushButton {
                    background: #00f0ff;
                    color: #000000;
                    border: 1px solid #00f0ff;
                    font-family: 'Consolas', sans-serif;
                    font-size: 10px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 3px 6px;
                }
            """)
        else:
            self.history_drawer.hide()
            self.setFixedHeight(70)
            self.btn_hist.setStyleSheet("""
                QPushButton {
                    background: #000000;
                    color: #a1a1aa;
                    border: 1px solid #27272a;
                    font-family: 'Consolas', sans-serif;
                    font-size: 10px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 3px 6px;
                }
            """)

    def set_rms_provider(self, provider_func):
        self.current_rms_provider = provider_func
        self.timer.timeout.connect(self._on_timer_tick)
        self.timer.start()

    def _on_timer_tick(self):
        if self.current_rms_provider:
            rms = self.current_rms_provider()
            self.visualizer.update_rms(rms)

    def update_hotkey_badge(self):
        hk = self.config.get('hotkey', 'ctrl+space').upper()
        mode = "PRESS" if self.config.get('hotkey_mode') == 'toggle' else "HOLD"
        self.lbl_hotkey.setText(f"{mode} [{hk}]")

    def set_state_idle(self, message="READY"):
        self.visualizer.set_state("idle")
        self.lbl_status.setText(message)
        self.lbl_status.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        self.main_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 1px solid #27272a;
                border-radius: 14px;
            }
        """)

    def set_state_recording(self):
        self.visualizer.set_state("recording")
        self.lbl_status.setText("● LISTENING")
        self.lbl_status.setStyleSheet("color: #00f0ff; font-weight: bold; border: none; background: transparent;")
        self.main_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 1.5px solid #00f0ff;
                border-radius: 14px;
            }
        """)

    def set_state_transcribing(self):
        self.visualizer.set_state("transcribing")
        self.lbl_status.setText("⚡ PROCESSING")
        self.lbl_status.setStyleSheet("color: #eab308; font-weight: bold; border: none; background: transparent;")
        self.main_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 1.5px solid #eab308;
                border-radius: 14px;
            }
        """)

    def set_state_inserted(self, text_preview=""):
        self.visualizer.set_state("idle")
        display = f"✓ {text_preview[:10]}..." if len(text_preview) > 10 else f"✓ {text_preview}" if text_preview else "✓ COPIED"
        self.lbl_status.setText(display)
        self.lbl_status.setStyleSheet("color: #22c55e; font-weight: bold; border: none; background: transparent;")
        self.main_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 1.5px solid #22c55e;
                border-radius: 14px;
            }
        """)
        QTimer.singleShot(1800, self.set_state_idle)

    # Mouse drag handlers
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            new_pos = {"x": self.x(), "y": self.y()}
            self.config.set("widget_position", new_pos)
            event.accept()
