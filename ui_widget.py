from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QLinearGradient, QCursor

class SciFiWaveVisualizer(QWidget):
    """
    14-bar Cyberpunk spectrum visualizer with smooth physics interpolation and peak caps.
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
                # Frequency distribution curve effect
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
            # Smooth lerp
            target = self.target_levels[i]
            curr = self.current_levels[i]
            diff = target - curr
            self.current_levels[i] += diff * 0.25

            # Peak decay physics
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

        # Transcribing pulse animation effect
        import time
        t = time.time() * 8.0

        for i in range(self.num_bars):
            if self.state == "transcribing":
                # Travelling wave during transcription
                import math
                val = 0.3 + 0.6 * (0.5 + 0.5 * math.sin(t - i * 0.4))
                bar_h = max(3, int(h * val))
            else:
                bar_h = max(2, int(h * self.current_levels[i]))

            x = start_x + i * (bar_w + spacing)
            y = h - bar_h

            # Color scheme based on state
            if self.state == "recording":
                color_top = QColor(255, 255, 255)
                color_bot = QColor(0, 240, 255)
            elif self.state == "transcribing":
                color_top = QColor(255, 230, 100)
                color_bot = QColor(255, 140, 0)
            else:
                color_top = QColor(160, 175, 195, 180)
                color_bot = QColor(80, 95, 115, 120)

            gradient = QLinearGradient(x, h, x, y)
            gradient.setColorAt(0, color_bot)
            gradient.setColorAt(1, color_top)

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, 1, 1)

            # Draw peak caps
            if self.state == "recording":
                peak_y = int(h - (h * self.peaks[i])) - 2
                peak_y = max(0, min(h - 2, peak_y))
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.drawRect(x, peak_y, bar_w, 1)


class CyberpunkHistoryDrawer(QFrame):
    """Collapsible Frosted Glass History Drawer."""
    item_reinject_signal = pyqtSignal(str)

    def __init__(self, history_mgr, parent=None):
        super().__init__(parent)
        self.history_mgr = history_mgr
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: rgba(10, 12, 16, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-top: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                color: #e2e8f0;
            }
            QListWidget::item {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 6px 8px;
                margin-bottom: 4px;
                font-size: 11px;
            }
            QListWidget::item:hover {
                background: rgba(0, 240, 255, 0.15);
                border-color: rgba(0, 240, 255, 0.4);
                color: #ffffff;
            }
            QLabel {
                color: #718096;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton#btnClear {
                background: transparent;
                color: #718096;
                border: none;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton#btnClear:hover {
                color: #ff3366;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header bar inside history drawer
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

        # List Widget
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

        # Audio metering timer (60 FPS)
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
        self.setFixedHeight(70) # Default compact height without history drawer

        main_v_layout = QVBoxLayout(self)
        main_v_layout.setContentsMargins(0, 0, 0, 0)
        main_v_layout.setSpacing(0)

        # 1. Main Frosted Glass Top Widget Frame
        self.main_frame = QFrame(self)
        self.main_frame.setFixedHeight(64)
        self.main_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgba(18, 20, 26, 0.94),
                            stop:1 rgba(10, 12, 16, 0.96));
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 14px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.main_frame.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.main_frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # 1. Cyberpunk 14-bar Wave Spectrum Visualizer
        self.visualizer = SciFiWaveVisualizer(self.main_frame)
        layout.addWidget(self.visualizer)

        # 2. Middle Column: Status Text & Hotkey Badge (No redundant app title!)
        mid_layout = QVBoxLayout()
        mid_layout.setSpacing(2)

        self.lbl_status = QLabel("READY")
        self.lbl_status.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #ffffff; border: none; background: transparent; letter-spacing: 0.5px;")

        self.lbl_hotkey = QLabel(f"HOLD [{self.config.get('hotkey', 'caps_lock').upper()}]")
        self.lbl_hotkey.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.lbl_hotkey.setStyleSheet("""
            background: rgba(255, 255, 255, 0.08);
            color: #a0aec0;
            border-radius: 3px;
            padding: 1px 5px;
            border: 1px solid rgba(255, 255, 255, 0.12);
        """)

        mid_layout.addWidget(self.lbl_status)
        mid_layout.addWidget(self.lbl_hotkey)
        layout.addLayout(mid_layout)

        layout.addStretch()

        # 3. Action Buttons (HIST, ⚙, ✕)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(3)

        cyber_btn_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #a0aec0;
                border: 1px solid rgba(255, 255, 255, 0.08);
                font-family: 'Consolas', sans-serif;
                font-size: 10px;
                font-weight: bold;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(0, 240, 255, 0.2);
                border-color: rgba(0, 240, 255, 0.5);
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

        # 2. History Drawer (Collapsible)
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
                    background: rgba(0, 240, 255, 0.25);
                    color: #ffffff;
                    border: 1px solid rgba(0, 240, 255, 0.6);
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
                    background: rgba(255, 255, 255, 0.05);
                    color: #a0aec0;
                    border: 1px solid rgba(255, 255, 255, 0.08);
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(18, 20, 26, 0.94), stop:1 rgba(10, 12, 16, 0.96));
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 14px;
            }
        """)

    def set_state_recording(self):
        self.visualizer.set_state("recording")
        self.lbl_status.setText("● LISTENING")
        self.lbl_status.setStyleSheet("color: #00f0ff; font-weight: bold; border: none; background: transparent;")
        self.main_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(12, 30, 42, 0.96), stop:1 rgba(8, 18, 28, 0.98));
                border: 1.5px solid rgba(0, 240, 255, 0.85);
                border-radius: 14px;
            }
        """)

    def set_state_transcribing(self):
        self.visualizer.set_state("transcribing")
        self.lbl_status.setText("⚡ PROCESSING")
        self.lbl_status.setStyleSheet("color: #ffcc00; font-weight: bold; border: none; background: transparent;")
        self.main_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(32, 28, 12, 0.96), stop:1 rgba(18, 15, 8, 0.98));
                border: 1.5px solid rgba(255, 204, 0, 0.85);
                border-radius: 14px;
            }
        """)

    def set_state_inserted(self, text_preview=""):
        self.visualizer.set_state("idle")
        display = f"✓ {text_preview[:10]}..." if len(text_preview) > 10 else f"✓ {text_preview}" if text_preview else "✓ COPIED"
        self.lbl_status.setText(display)
        self.lbl_status.setStyleSheet("color: #00ffaa; font-weight: bold; border: none; background: transparent;")
        self.main_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(10, 32, 22, 0.96), stop:1 rgba(6, 18, 12, 0.98));
                border: 1.5px solid rgba(0, 255, 170, 0.85);
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
