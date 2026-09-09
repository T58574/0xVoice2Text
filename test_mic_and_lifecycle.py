import os
import sys
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QEvent
from PyQt6.QtGui import QMouseEvent

from src.config import AppConfig
from src.core.audio_recorder import check_microphone_available, AudioRecorder
from src.ui.widget import DesktopWidget
from main import acquire_single_instance_mutex

def test_mic_availability():
    print("[*] TEST 1: Microphone availability checking...")
    ok, name, err = check_microphone_available()
    print(f"    [+] check_microphone_available -> ok={ok}, name='{name}', err='{err}'")
    assert isinstance(ok, bool)
    assert isinstance(name, str)

    rec = AudioRecorder()
    rec_ok, rec_name, _ = rec.check_availability()
    print(f"    [+] AudioRecorder.check_availability -> ok={rec_ok}, name='{rec_name}'")
    assert rec_ok == ok
    print("    [OK] Microphone availability check passed!")

def test_single_instance_mutex():
    print("[*] TEST 2: Single-Instance Mutex Guard...")
    m1 = acquire_single_instance_mutex()
    assert m1 is not None, "First instance must acquire mutex"

    # Second acquisition attempt must fail and detect running instance
    m2 = acquire_single_instance_mutex()
    assert m2 is None, "Second instance must be rejected"

    # Release handle
    ctypes.windll.kernel32.CloseHandle(m1)
    print("    [OK] Single-Instance Mutex Guard verified successfully!")

def test_widget_controls_and_dragging():
    print("[*] TEST 3: DesktopWidget Dragging, Controls & Exit Signals...")
    app = QApplication.instance() or QApplication(sys.argv)
    cfg = AppConfig()
    widget = DesktopWidget(cfg)

    # Verify window title for OS window focus
    assert widget.windowTitle() == "0xVoice2Text_Widget", "Window title must match single instance locator"

    # Verify microphone status badge
    widget.set_mic_status(True, "TestMic")
    assert widget.btn_mic.text() == "MIC: OK"
    widget.set_mic_status(False, "TestMic", "Device busy")
    assert widget.btn_mic.text() == "NO MIC"

    # Verify exit signal is wired to close button and closeEvent
    exit_triggered = []
    widget.exit_app_signal.connect(lambda: exit_triggered.append(True))
    widget.btn_close.click()
    assert len(exit_triggered) == 1, "Clicking close button must emit exit_app_signal"

    # Verify minimize button hides widget
    widget.show()
    assert widget.isVisible()
    widget.btn_min.click()
    assert not widget.isVisible()

    # Verify event filter intercepts mouse press on main_frame for dragging
    press_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(20, 20),
        QPointF(20, 20),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    # Filter should handle the event (return True) for draggable area
    filtered = widget.eventFilter(widget.main_frame, press_event)
    assert filtered is True, "Event filter must handle drag press on main_frame"

    widget.close()
    print("    [OK] DesktopWidget Controls, Dragging & Lifecycle verified successfully!")

if __name__ == "__main__":
    test_mic_availability()
    test_single_instance_mutex()
    test_widget_controls_and_dragging()
    print("\n[OK] ALL MIC & LIFECYCLE TESTS COMPLETED SUCCESSFULLY!")
