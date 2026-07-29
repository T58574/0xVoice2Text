import win32api
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class MouseHUDOverlay(QWidget):
    """
    Transparent holographic Cyberpunk ring HUD overlay that pops up centered around the mouse cursor.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 90)

        # Window flags: Frameless, Always on Top, Tool Window, Transparent to Mouse Input
        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.pulse_phase = 0.0
        self.is_animating = False

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16) # ~60 fps
        self.anim_timer.timeout.connect(self._on_anim_tick)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_hud)

    def trigger_around_cursor(self, duration_ms=1200):
        try:
            x, y = win32api.GetCursorPos()
            # Center 90x90 around cursor
            self.move(x - 45, y - 45)
        except Exception:
            pass

        self.pulse_phase = 0.0
        self.is_animating = True
        self.show()
        self.raise_()

        self.anim_timer.start()
        self.hide_timer.start(duration_ms)

    def _on_anim_tick(self):
        self.pulse_phase += 0.1
        if self.pulse_phase > 6.28:
            self.pulse_phase = 0.0
        self.update()

    def hide_hud(self):
        self.anim_timer.stop()
        self.is_animating = False
        self.hide()

    def paintEvent(self, event):
        if not self.is_animating:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        import math
        pulse_scale = 1.0 + 0.08 * math.sin(self.pulse_phase)
        radius = 32 * pulse_scale

        # 1. Outer dashed target ring
        pen_outer = QPen(QColor(0, 240, 255, 210), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        # 2. Inner crisp neon ring
        pen_inner = QPen(QColor(255, 255, 255, 230), 2.0)
        painter.setPen(pen_inner)
        painter.drawEllipse(QRectF(cx - (radius - 6), cy - (radius - 6), (radius - 6) * 2, (radius - 6) * 2))

        # 3. Center micro dot
        painter.setBrush(QBrush(QColor(0, 240, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - 3, cy - 3, 6, 6))

        # 4. Sci-Fi Corner Brackets
        pen_bracket = QPen(QColor(0, 240, 255, 180), 1.5)
        painter.setPen(pen_bracket)
        b_len = 8
        b_off = radius + 6

        # Top-Left bracket
        painter.drawLine(int(cx - b_off), int(cy - b_off), int(cx - b_off + b_len), int(cy - b_off))
        painter.drawLine(int(cx - b_off), int(cy - b_off), int(cx - b_off), int(cy - b_off + b_len))

        # Top-Right bracket
        painter.drawLine(int(cx + b_off), int(cy - b_off), int(cx + b_off - b_len), int(cy - b_off))
        painter.drawLine(int(cx + b_off), int(cy - b_off), int(cx + b_off), int(cy - b_off + b_len))

        # Bottom-Left bracket
        painter.drawLine(int(cx - b_off), int(cy + b_off), int(cx - b_off + b_len), int(cy + b_off))
        painter.drawLine(int(cx - b_off), int(cy + b_off), int(cx - b_off), int(cy + b_off - b_len))

        # Bottom-Right bracket
        painter.drawLine(int(cx + b_off), int(cy + b_off), int(cx + b_off - b_len), int(cy + b_off))
        painter.drawLine(int(cx + b_off), int(cy + b_off), int(cx + b_off), int(cy + b_off - b_len))
