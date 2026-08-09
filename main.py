import sys
import os
import threading

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject

from src.config import AppConfig
from src.core.history import HistoryManager
from src.core.audio_recorder import AudioRecorder
from src.core.stt_engine import STTEngine
from src.core.wake_word import WakeWordManager
from src.core.ipc_bus import IPCEventBus

from src.services.hotkeys import HotkeyManager
from src.services.macros import MacroManager
from src.services.injector import TextInjector
import src.services.sounds as sound_effects

from src.ui.widget import DesktopWidget
from src.ui.settings import SettingsDialog
from src.ui.history import HistoryWindow
from src.ui.mouse_hud import MouseHUDOverlay
from src.ui.tray import SystemTrayApp

class SignalBridge(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_done = pyqtSignal(str)
    model_loaded = pyqtSignal(bool)

class ApplicationController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config = AppConfig()
        self.history_mgr = HistoryManager()
        self.ipc = IPCEventBus()
        self.bridge = SignalBridge()

        # Audio Recorder
        self.recorder = AudioRecorder(device_id=self.config.get("audio_device"))

        # STT Engine
        self.stt = STTEngine(
            model_size="whisper-large-v3",
            language=self.config.get("language", "ru"),
            device="cloud"
        )

        # Mouse Cursor Holographic HUD Overlay
        self.mouse_hud = MouseHUDOverlay()

        # UI Widget (with History Drawer button)
        self.widget = DesktopWidget(self.config, history_mgr=self.history_mgr)
        self.widget.set_rms_provider(self.recorder.get_rms)
        self.widget.open_settings_signal.connect(self.open_settings)
        self.widget.reinject_text_signal.connect(self.reinject_text)
        self.widget.btn_hist.clicked.disconnect() # Connect HIST button directly to open dedicated History Window!
        self.widget.btn_hist.clicked.connect(self.open_history)
        self.widget.show()

        # History Window
        self.history_window = None
        self.settings_dialog = None

        # Signals
        self.bridge.recording_started.connect(self._on_ui_recording_started)
        self.bridge.recording_stopped.connect(self._on_ui_recording_stopped)
        self.bridge.transcription_done.connect(self._on_ui_transcription_done)
        self.bridge.model_loaded.connect(self._on_model_loaded)

        # Hotkey Manager
        self.hotkey_mgr = HotkeyManager(
            target_key=self.config.get("hotkey", "ctrl+space"),
            mode=self.config.get("hotkey_mode", "toggle"),
            on_start=self.on_hotkey_start,
            on_stop=self.on_hotkey_stop
        )

        # Wake Word & Voice Stop Manager (Vosk)
        self.wake_mgr = WakeWordManager(
            config=self.config,
            on_wake_detected=self.on_hotkey_start,
            on_stop_detected=self.on_hotkey_stop
        )

        # Voice Macro & Command Manager
        self.macro_mgr = MacroManager(self.config)

        # System Tray
        self.tray = SystemTrayApp(
            app=self.app,
            widget=self.widget,
            on_open_settings=self.open_settings,
            on_open_history=self.open_history,
            on_exit=self.exit_app
        )

        self.is_transcribing = False

        # Load Groq STT Engine
        self.stt.load_model(on_complete=lambda ok: self.bridge.model_loaded.emit(ok))

        # Start listeners
        self.hotkey_mgr.start()
        self.wake_mgr.start()

    def _on_model_loaded(self, success):
        if success:
            self.widget.set_state_idle("READY")
        else:
            self.widget.set_state_idle("NO GROQ KEY")

    def on_hotkey_start(self):
        if self.is_transcribing:
            return
        self.bridge.recording_started.emit()

    def on_hotkey_stop(self):
        self.bridge.recording_stopped.emit()

    def _on_ui_recording_started(self):
        # Notify wake manager recording state
        self.wake_mgr.set_recording_state(True)

        # Trigger HUD ring animation around mouse cursor
        self.mouse_hud.trigger_around_cursor(duration_ms=1500)

        if self.config.get("sound_feedback", True):
            sound_effects.play_start_sound()
        self.widget.set_state_recording()
        self.recorder.start_recording()

    def _on_ui_recording_stopped(self):
        # Notify wake manager recording state
        self.wake_mgr.set_recording_state(False)

        if self.config.get("sound_feedback", True):
            sound_effects.play_stop_sound()

        audio_buffer = self.recorder.stop_recording()
        if audio_buffer is None or len(audio_buffer) < 1600:
            self.widget.set_state_idle("READY")
            return

        self.widget.set_state_transcribing()
        self.is_transcribing = True

        def _transcribe_worker():
            text = self.stt.transcribe(audio_buffer)
            self.bridge.transcription_done.emit(text)

        threading.Thread(target=_transcribe_worker, daemon=True).start()

    def _on_ui_transcription_done(self, text):
        self.is_transcribing = False
        if not text or text.startswith("ERR") or text.startswith("ERROR"):
            self.widget.set_state_idle("ERR: GROQ KEY")
            return

        # Clean trailing stop words if present
        text = self.wake_mgr.clean_transcription(text)
        if not text:
            self.widget.set_state_idle("READY")
            return

        # Check if phrase matches a Voice Macro / Command action
        is_macro, macro_desc = self.macro_mgr.process_text(text)
        if is_macro:
            self.history_mgr.add_entry(f"[CMD] {text} -> {macro_desc}")
            if self.history_window and self.history_window.isVisible():
                self.history_window.reload_history()

            self.ipc.emit_transcription_event(
                text=f"[CMD] {text} -> {macro_desc}",
                engine="groq-whisper-large-v3",
                language=self.config.get("language", "ru")
            )

            if self.config.get("sound_feedback", True):
                sound_effects.play_success_sound()

            self.widget.set_state_inserted(f"⚡ {macro_desc}")
            return

        # 1. Save to History Manager
        self.history_mgr.add_entry(text)
        if self.history_window and self.history_window.isVisible():
            self.history_window.reload_history()

        # 2. Emit JSON event for IPC external infrastructure
        self.ipc.emit_transcription_event(
            text=text,
            engine="groq-whisper-large-v3",
            language=self.config.get("language", "ru")
        )

        # 3. Inject text into active target window
        if self.config.get("auto_paste", True):
            success = TextInjector.inject_text(
                text,
                add_trailing_space=self.config.get("add_trailing_space", True)
            )
            if success and self.config.get("sound_feedback", True):
                sound_effects.play_success_sound()

        self.widget.set_state_inserted(text)

    def reinject_text(self, text: str):
        print(f"[Main] Re-injecting phrase from history: '{text}'")
        success = TextInjector.inject_text(
            text,
            add_trailing_space=self.config.get("add_trailing_space", True)
        )
        if success and self.config.get("sound_feedback", True):
            sound_effects.play_success_sound()
        self.widget.set_state_inserted("PASTED")

    def open_history(self):
        if self.history_window is None or not self.history_window.isVisible():
            self.history_window = HistoryWindow(self.history_mgr, parent=self.widget)
            self.history_window.reinject_text_signal.connect(self.reinject_text)
            self.history_window.show()
            self.history_window.raise_()
            self.history_window.activateWindow()

    def open_settings(self):
        if self.settings_dialog is None or not self.settings_dialog.isVisible():
            self.settings_dialog = SettingsDialog(
                config=self.config,
                parent=self.widget,
                on_save_callback=self.apply_config_changes
            )
            self.settings_dialog.show()

    def apply_config_changes(self):
        print("[Main] Applying updated configuration...")
        self.recorder.set_device(self.config.get("audio_device"))

        self.hotkey_mgr.update_key(
            self.config.get("hotkey", "ctrl+space"),
            mode=self.config.get("hotkey_mode", "toggle")
        )
        self.wake_mgr.reload_config()
        self.widget.update_hotkey_badge()

    def exit_app(self):
        self.hotkey_mgr.stop()
        self.wake_mgr.stop()
        self.recorder.stop_recording()
        self.app.quit()

    def run(self):
        return self.app.exec()

if __name__ == "__main__":
    controller = ApplicationController()
    sys.exit(controller.run())
