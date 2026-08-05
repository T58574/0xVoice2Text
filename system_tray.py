from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

def create_tray_icon_pixmap():
    """Generates a crisp monochrome B&W OLED microphone tray icon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor(0, 0, 0))
    painter.setPen(QColor(255, 255, 255))
    painter.drawRoundedRect(2, 2, 28, 28, 8, 8)

    painter.setBrush(QColor(255, 255, 255))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(12, 8, 8, 11, 4, 4)

    painter.setPen(QColor(255, 255, 255))
    painter.drawLine(16, 21, 16, 24)
    painter.drawLine(12, 24, 20, 24)

    painter.end()
    return pixmap

class SystemTrayApp:
    def __init__(self, app, widget, on_open_settings, on_open_history, on_exit):
        self.app = app
        self.widget = widget
        self.on_open_settings = on_open_settings
        self.on_open_history = on_open_history
        self.on_exit = on_exit

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(create_tray_icon_pixmap()))
        self.tray.setToolTip("0xVoice2Text // B&W OLED EDITION")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #000000;
                color: #ffffff;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Consolas', sans-serif;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ffffff;
                color: #000000;
            }
        """)

        action_history = menu.addAction("📜 ИСТОРИЯ ЗАПРОСОВ")
        action_history.triggered.connect(self.on_open_history)

        action_toggle = menu.addAction("👁 TOGGLE WIDGET")
        action_toggle.triggered.connect(self.toggle_widget)

        action_settings = menu.addAction("⚙ CONFIGURATION")
        action_settings.triggered.connect(self.on_open_settings)

        menu.addSeparator()

        action_exit = menu.addAction("🚪 EXIT")
        action_exit.triggered.connect(self.on_exit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def toggle_widget(self):
        if self.widget.isVisible():
            self.widget.hide()
        else:
            self.widget.show()
            self.widget.raise_()
            self.widget.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_widget()
