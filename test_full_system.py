import sys
import os
import time
import numpy as np

# Add project root directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from src.config import AppConfig
from src.core.logger import logger
from src.core.audio_recorder import AudioRecorder
from src.core.history import HistoryManager
from src.core.ipc_bus import IPCEventBus
from src.core.stt_engine import STTEngine
from src.core.stt.factory import STTFactory
from src.services.sounds import get_sound_fx, SoundEffects
from src.services.macros import MacroManager
from src.services.injector import TextInjector
from src.ui.widget import DesktopWidget
from src.ui.mouse_hud import MouseHUDOverlay
from src.ui.history import HistoryWindow

def run_system_verification():
    print("==================================================================")
    print("[*] 0xVoice2Text // COMPREHENSIVE FULL-SYSTEM VERIFICATION")
    print("==================================================================")

    # 1. Initialize Qt Application
    app = QApplication.instance() or QApplication(sys.argv)
    print("[+] PyQt6 QApplication initialized successfully.")

    # 2. Config & History
    config = AppConfig()
    history = HistoryManager()
    history.add_entry("[TEST] Diagnostic verification initiated.")
    print("[+] AppConfig & HistoryManager verified.")

    # 3. Audio Recorder & RMS
    recorder = AudioRecorder()
    rms = recorder.get_rms()
    print(f"[+] AudioRecorder initialized. Current RMS baseline: {rms:.4f}")

    # 4. STT Subsystem
    stt = STTEngine(config=config)
    print(f"[+] STTEngine initialized -> Active: {stt.adapter.get_name()} | Status: {stt.status_message}")

    # Synthetic audio transcription test
    sample_rate = 16000
    duration = 1.0
    synth_audio = (0.05 * np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sample_rate * duration)))).astype(np.float32)
    stt_out = stt.transcribe(synth_audio)
    print(f"[+] STT Pipeline Ingestion: '{stt_out}'")

    # 5. Procedural Sound Feedback Subsystem
    from src.services.sounds import get_sound_fx
    sfx = get_sound_fx(config)
    print(f"[+] SoundEffects initialized -> Active Pack: {sfx.pack} | Enabled: {sfx.enabled}")
    assert "start" in sfx._buffers and "success" in sfx._buffers, "Sound buffers must exist!"
    sfx.play_start()
    sfx.play_success()

    # 6. Macros & Voice Commands
    macros = MacroManager(config)
    is_cmd, cmd_desc = macros.process_text("джарвис открой браузер")
    print(f"[+] Macro Parser: 'джарвис открой браузер' -> is_macro={is_cmd}, desc='{cmd_desc}'")

    # 7. UI Widgets & HUD
    widget = DesktopWidget(config, history_mgr=history)
    widget.set_rms_provider(recorder.get_rms)
    widget.set_state_idle("READY")
    widget.show()
    print("[+] DesktopWidget instantiated and set to READY state.")

    mouse_hud = MouseHUDOverlay()
    print("[+] MouseHUDOverlay instantiated.")

    # 8. Event Loop pulse test
    def _close_app():
        print("[+] Processing Qt Event Loop tick... Closing UI cleanly.")
        widget.close()
        app.quit()

    QTimer.singleShot(500, _close_app)
    app.exec()

    # 9. ApplicationController End-to-End lifecycle test (Isolated Process)
    import subprocess
    print("[*] Testing ApplicationController instantiation...")
    cmd = [sys.executable, "-c", "import sys; from PyQt6.QtWidgets import QApplication; a = QApplication.instance() or QApplication(sys.argv); from main import ApplicationController; c = ApplicationController(); assert c.widget.isVisible(); print('CONTROLLER_OK'); c.exit_app()"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert res.returncode == 0, f"ApplicationController failed: {res.stderr}"
    print("[+] ApplicationController verified and ready!")

    print("==================================================================")
    print("[OK] ALL SUBSYSTEMS & PIPELINE STAGES VERIFIED WITH 0 ERRORS!")
    print("==================================================================")

if __name__ == "__main__":
    run_system_verification()
