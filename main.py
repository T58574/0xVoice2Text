import sys
import os
import io
import threading

# 1. Disable TQDM and Hugging Face progress bars globally for GUI / pythonw mode
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

# 2. Redirect stdout/stderr if None (essential when running under pythonw.exe)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
elif hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')
elif hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
from src.core.ai_engine import AIEngine
from src.core.wake_word import WakeWordManager
from src.core.ipc_bus import IPCEventBus

from src.services.hotkeys import HotkeyManager
from src.services.macros import MacroManager
from src.services.injector import TextInjector
from src.services.tts import JarvisVoiceService
from src.core.logger import logger
from src.ui.widget import DesktopWidget
from src.ui.settings import SettingsDialog
from src.ui.history import HistoryWindow
from src.ui.mouse_hud import MouseHUDOverlay
from src.ui.tray import SystemTrayApp
from src.ui.error_dialog import ErrorNotificationDialog

class SignalBridge(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_done = pyqtSignal(str)
    ai_done = pyqtSignal(str)
    ai_error = pyqtSignal(str)
    model_loaded = pyqtSignal(bool)

class ApplicationController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config = AppConfig()
        self.history_mgr = HistoryManager()
        self.ipc = IPCEventBus()
        self.tts = JarvisVoiceService(self.config)
        self.bridge = SignalBridge()

        # Audio Recorder
        self.recorder = AudioRecorder(device_id=self.config.get("audio_device"))
        self.recorder.set_tts_speaking_checker(self.tts.is_speaking)

        # STT & AI Engine
        self.stt = STTEngine(config=self.config)
        self.ai_engine = AIEngine(self.config)

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
        self.bridge.ai_done.connect(self._finalize_text_injection)
        self.bridge.ai_error.connect(self._on_ai_error)
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

        # Set initial UI state while model compiles / initializes
        self.widget.set_state_idle("INITIALIZING...")

        # Load STT Engine
        self.stt.load_model(on_complete=lambda ok: self.bridge.model_loaded.emit(ok))

        # Start listeners
        self.hotkey_mgr.start()
        self.wake_mgr.start()

    def _on_model_loaded(self, success):
        if success:
            self.widget.set_state_idle("READY")
        else:
            status = self.stt.status_message if self.stt else "STT ERROR"
            self.widget.set_state_idle(status[:14])

    def on_hotkey_start(self):
        if self.is_transcribing:
            return
        if not self.stt.is_ready:
            status = self.stt.status_message if self.stt else "INITIALIZING..."
            logger.warning(f"[Main] Hotkey ignored: STT engine is not ready ({status})")
            if hasattr(self, 'widget') and self.widget:
                self.widget.set_state_idle(status[:14])
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
            self.tts.play_category("listening")
        self.widget.set_state_recording()
        self.recorder.start_recording()

    def _on_ui_recording_stopped(self):
        # Notify wake manager recording state
        self.wake_mgr.set_recording_state(False)

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
            self.widget.set_state_idle("ERR: STT")
            self.tts.play_category("error")
            engine_name = self.stt.adapter.get_name() if self.stt and self.stt.adapter else "STT Engine"
            self.show_error_dialog(
                title=f"Ошибка {engine_name}",
                error_msg=text if text else "Неизвестная ошибка распознавания речи.",
                solution_hint="Проверьте конфигурацию STT движка в настройках (Settings) или подключение к API / VRAM."
            )
            return

        # Clean trailing stop words if present
        text = self.wake_mgr.clean_transcription(text)
        if not text:
            self.widget.set_state_idle("READY")
            return

        # Ignore self-echo of Jarvis's own TTS response phrases
        if self.tts.is_jarvis_phrase(text):
            logger.info(f"[Main] [FILTER] Filtered out self-echo Jarvis voice phrase: '{text}'")
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
                self.tts.play_category("macro")

            self.widget.set_state_inserted(f"[CMD] {macro_desc}")
            return

        # Check AI Processing Mode
        ai_mode = self.config.get("ai_mode", "direct")
        if ai_mode in ("clean", "smart"):
            self.widget.set_state_ai_thinking(ai_mode)
            def _ai_worker():
                processed_text, err_msg = self.ai_engine.process_text(text, mode=ai_mode)
                if err_msg:
                    self.bridge.ai_error.emit(err_msg)
                    # Also fallback to injecting raw transcript if available
                    self.bridge.ai_done.emit(processed_text)
                else:
                    self.bridge.ai_done.emit(processed_text)
            threading.Thread(target=_ai_worker, daemon=True).start()
        else:
            self._finalize_text_injection(text)

    def _on_ai_error(self, err_msg: str):
        self.widget.set_state_idle("ERR: GEMINI")
        self.tts.play_category("error")
        self.show_error_dialog(
            title="Ошибка Google Gemini / Gemma API",
            error_msg=err_msg,
            solution_hint="Укажите действительный GEMINI_API_KEY в файле .env или переключите модель/режим в настройках."
        )

    def show_error_dialog(self, title: str, error_msg: str, solution_hint: str = ""):
        logger.error(f"[Main] Showing Error Dialog: {title} | Details: {error_msg}")
        dialog = ErrorNotificationDialog(
            title=title,
            error_msg=error_msg,
            solution_hint=solution_hint,
            parent=self.widget
        )
        dialog.open_settings_requested.connect(self.open_settings)
        dialog.exec()

    def _finalize_text_injection(self, text: str):
        if not text:
            self.widget.set_state_idle("READY")
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
                self.tts.play_category("success")

        self.widget.set_state_inserted(text)

    def reinject_text(self, text: str):
        print(f"[Main] Re-injecting phrase from history: '{text}'")
        success = TextInjector.inject_text(
            text,
            add_trailing_space=self.config.get("add_trailing_space", True)
        )
        if success and self.config.get("sound_feedback", True):
            self.tts.play_category("success")
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
        logger.info("[Main] Applying updated configuration...")

        # --- Lightweight config applications (safe, fast) ---
        try:
            self.recorder.set_device(self.config.get("audio_device"))
        except Exception as e:
            logger.error(f"[Main] Failed to update audio device: {e}")

        try:
            self.hotkey_mgr.update_key(
                self.config.get("hotkey", "ctrl+space"),
                mode=self.config.get("hotkey_mode", "toggle")
            )
        except Exception as e:
            logger.error(f"[Main] Failed to update hotkey: {e}")

        try:
            self.wake_mgr.reload_config()
        except Exception as e:
            logger.error(f"[Main] Failed to reload wake word config: {e}")

        try:
            self.widget.update_hotkey_badge()
        except Exception as e:
            logger.error(f"[Main] Failed to update hotkey badge: {e}")

        # --- Heavy engine reloads (background threads to avoid GUI freeze) ---
        def _reload_stt():
            try:
                stt_opts = {
                    "qwen_model": self.config.get("qwen_model", "Qwen/Qwen3-ASR-1.7B-hf"),
                    "groq_model": self.config.get("groq_model", "whisper-large-v3"),
                    "stt_device": self.config.get("stt_device", "auto"),
                    "language": self.config.get("language", "ru")
                }
                self.stt.switch_engine(
                    self.config.get("stt_engine", "qwen3"),
                    options=stt_opts,
                    on_complete=lambda ok: self.bridge.model_loaded.emit(ok)
                )
            except Exception as e:
                logger.error(f"[Main] Failed to switch STT engine: {e}")
                self.bridge.model_loaded.emit(False)

        def _reload_tts():
            try:
                tts_opts = {
                    "qwen_tts_model": self.config.get("qwen_tts_model", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
                    "tts_ref_voice": self.config.get("tts_ref_voice", None),
                    "tts_device": self.config.get("tts_device", "auto"),
                    "tts_voice": self.config.get("tts_voice", "ru-RU-SvetlanaNeural"),
                    "tts_rate": self.config.get("tts_rate", "+20%"),
                    "tts_pitch": self.config.get("tts_pitch", "+0Hz")
                }
                self.tts.switch_engine(self.config.get("tts_engine", "qwen3"), options=tts_opts)
            except Exception as e:
                logger.error(f"[Main] Failed to switch TTS engine: {e}")

        threading.Thread(target=_reload_stt, daemon=True).start()
        threading.Thread(target=_reload_tts, daemon=True).start()

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
