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
from src.services.sounds import get_sound_fx, SoundEffects
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
    model_loaded = pyqtSignal(bool)
    mic_status_changed = pyqtSignal(bool, str, str)

class ApplicationController:
    def __init__(self, single_instance_mutex=None):
        self._single_instance_mutex = single_instance_mutex
        self._is_shutting_down = False
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config = AppConfig()
        self.history_mgr = HistoryManager()
        self.ipc = IPCEventBus()
        self.sound_fx = get_sound_fx(self.config)
        self.tts = self.sound_fx  # Backwards compatibility alias
        self.bridge = SignalBridge()

        # Microphone State Tracking
        self.mic_available = False
        self.mic_name = "Checking..."
        self.mic_error = ""

        # Audio Recorder
        self.recorder = AudioRecorder(device_id=self.config.get("audio_device"))

        # STT Engine (Local SOTA DirectML GPU / AVX2)
        self.stt = STTEngine(config=self.config)

        # Mouse Cursor Holographic HUD Overlay
        self.mouse_hud = MouseHUDOverlay()

        # UI Widget (with History Drawer button)
        self.widget = DesktopWidget(self.config, history_mgr=self.history_mgr)
        self.widget.set_rms_provider(self.recorder.get_rms)
        self.widget.open_settings_signal.connect(self.open_settings)
        self.widget.reinject_text_signal.connect(self.reinject_text)
        self.widget.recheck_mic_signal.connect(self.check_mic_status_async)
        self.widget.exit_app_signal.connect(self.exit_app)
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
        self.bridge.mic_status_changed.connect(self.widget.set_mic_status)

        # Check initial microphone availability
        self.check_mic_status_async()

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
            on_wake_detected=self.on_wake_word_detected,
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

    def check_mic_status_async(self):
        """Asynchronously validates microphone hardware accessibility without blocking Qt UI."""
        def _worker():
            ok, name, err = self.recorder.check_availability()
            self.mic_available = ok
            self.mic_name = name
            self.mic_error = err
            if ok:
                logger.info(f"[Main] [MIC] [OK] Microphone operational: '{name}'")
            else:
                logger.warning(f"[Main] [MIC] [WARN] Microphone unavailable: '{name}' | Error: {err}")
            self.bridge.mic_status_changed.emit(ok, name, err)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_model_loaded(self, success):
        if success:
            self.widget.set_state_idle("READY")
        else:
            status = self.stt.status_message if self.stt else "STT ERROR"
            self.widget.set_state_idle(status[:14])

    def on_wake_word_detected(self):
        """Triggered when WakeWordManager detects wake trigger phrase ('джарвис')."""
        if self.config.get("sound_feedback", True):
            self.sound_fx.play_wake()
        self.on_hotkey_start()

    def on_hotkey_start(self):
        if self.is_transcribing:
            return
        if not self.stt.is_ready:
            status = self.stt.status_message if self.stt else "INITIALIZING..."
            logger.warning(f"[Main] Hotkey ignored: STT engine is not ready ({status})")
            if hasattr(self, 'widget') and self.widget:
                self.widget.set_state_idle(status[:14])
            return
        if not self.mic_available:
            logger.warning(f"[Main] Hotkey ignored: Microphone '{self.mic_name}' is not available.")
            if hasattr(self, 'widget') and self.widget:
                self.widget.set_state_idle("NO MIC")
            self.sound_fx.play_error()
            self.show_error_dialog(
                title="Микрофон недоступен",
                error_msg=f"Устройство ввода '{self.mic_name}' недоступно или отключено.\n\nОшибка: {self.mic_error}",
                solution_hint="Проверьте подключение микрофона и выберите правильное устройство в Настройках (⚙) -> Audio Device."
            )
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
            self.sound_fx.play_start()
        self.widget.set_state_recording()
        started = self.recorder.start_recording()
        if not started:
            self.widget.set_state_idle("MIC FAIL")
            self.sound_fx.play_error()
            self.show_error_dialog(
                title="Ошибка записи аудио",
                error_msg=f"Не удалось запустить аудиопоток с микрофона: {self.recorder.last_error}",
                solution_hint="Убедитесь, что микрофон не занят другим приложением в эксклюзивном режиме."
            )

    def _on_ui_recording_stopped(self):
        # Notify wake manager recording state
        self.wake_mgr.set_recording_state(False)

        audio_buffer = self.recorder.stop_recording()
        if audio_buffer is None or len(audio_buffer) < 1600:
            self.widget.set_state_idle("READY")
            if self.config.get("sound_feedback", True):
                self.sound_fx.play_stop()
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
            self.sound_fx.play_error()
            engine_name = self.stt.adapter.get_name() if self.stt and self.stt.adapter else "STT Engine"
            self.show_error_dialog(
                title=f"Ошибка {engine_name}",
                error_msg=text if text else "Неизвестная ошибка распознавания речи.",
                solution_hint="Проверьте конфигурацию STT движка в настройках (Settings) или подключение к микрофону / VRAM."
            )
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
                engine="qwen3-asr",
                language=self.config.get("language", "ru")
            )

            if self.config.get("sound_feedback", True):
                self.sound_fx.play_macro()

            self.widget.set_state_inserted(f"[CMD] {macro_desc}")
            return

        # Direct Voice to Text Injection (Optimized, 0 external API calls)
        self._finalize_text_injection(text)

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
            engine="qwen3-asr",
            language=self.config.get("language", "ru")
        )

        # 3. Inject text into active target window
        if self.config.get("auto_paste", True):
            success = TextInjector.inject_text(
                text,
                add_trailing_space=self.config.get("add_trailing_space", True)
            )
            if success and self.config.get("sound_feedback", True):
                self.sound_fx.play_success()

        self.widget.set_state_inserted(text)

    def reinject_text(self, text: str):
        print(f"[Main] Re-injecting phrase from history: '{text}'")
        success = TextInjector.inject_text(
            text,
            add_trailing_space=self.config.get("add_trailing_space", True)
        )
        if success and self.config.get("sound_feedback", True):
            self.sound_fx.play_success()
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
            self.check_mic_status_async()
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
                    "whisper_model": self.config.get("whisper_model", "large-v3-turbo"),
                    "stt_device": self.config.get("stt_device", "auto"),
                    "compute_type": self.config.get("compute_type", "auto"),
                    "language": self.config.get("language", "ru"),
                    "beam_size": self.config.get("beam_size", 1)
                }
                self.stt.switch_engine(
                    self.config.get("stt_engine", "whisper"),
                    options=stt_opts,
                    on_complete=lambda ok: self.bridge.model_loaded.emit(ok)
                )
            except Exception as e:
                logger.error(f"[Main] Failed to switch STT engine: {e}")
                self.bridge.model_loaded.emit(False)

        try:
            self.sound_fx.reload_config(self.config)
        except Exception as e:
            logger.error(f"[Main] Failed to reload sound feedback config: {e}")

        threading.Thread(target=_reload_stt, daemon=True).start()

    def exit_app(self):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True

        logger.info("[Main] [EXIT] Graceful shutdown initiated...")

        # 1. Stop background listeners and audio streams
        try:
            self.hotkey_mgr.stop()
        except Exception as e:
            logger.error(f"[Main] [EXIT] Error stopping hotkey manager: {e}")

        try:
            self.wake_mgr.stop()
        except Exception as e:
            logger.error(f"[Main] [EXIT] Error stopping wake manager: {e}")

        try:
            self.recorder.stop_recording()
        except Exception as e:
            logger.error(f"[Main] [EXIT] Error stopping audio recorder: {e}")

        # 2. Unload STT & TTS models to free VRAM/RAM immediately
        try:
            if hasattr(self, 'stt') and self.stt:
                self.stt.unload()
        except Exception as e:
            logger.error(f"[Main] [EXIT] Error unloading STT: {e}")

        try:
            if hasattr(self, 'tts') and self.tts:
                self.tts.unload()
        except Exception as e:
            logger.error(f"[Main] [EXIT] Error unloading TTS: {e}")

        # 3. Clean up UI elements & tray icon
        try:
            if hasattr(self, 'tray') and self.tray and self.tray.tray:
                self.tray.tray.hide()
        except Exception as e:
            logger.error(f"[Main] [EXIT] Error hiding tray: {e}")

        try:
            if hasattr(self, 'mouse_hud') and self.mouse_hud:
                self.mouse_hud.close()
            if hasattr(self, 'history_window') and self.history_window:
                self.history_window.close()
            if hasattr(self, 'settings_dialog') and self.settings_dialog:
                self.settings_dialog.close()
            if hasattr(self, 'widget') and self.widget:
                self.widget.close()
        except Exception as e:
            logger.error(f"[Main] [EXIT] Error closing windows: {e}")

        # 4. Release single instance mutex handle
        if hasattr(self, '_single_instance_mutex') and self._single_instance_mutex:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._single_instance_mutex)
                self._single_instance_mutex = None
            except Exception:
                pass

        logger.info("[Main] [EXIT] Shutdown complete. Terminating process.")
        self.app.quit()
        # Guarantee that C-threads (PortAudio, DirectML, Vosk) don't keep Python alive in Task Manager
        os._exit(0)

    def run(self):
        return self.app.exec()

def acquire_single_instance_mutex():
    """
    Ensures only a single instance of 0xVoice2Text runs on Windows.
    If an existing instance is found, brings it to foreground and returns None.
    """
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        ERROR_ALREADY_EXISTS = 183
        MUTEX_NAME = "Global\\0xVoice2Text_SingleInstance_Mutex_v1"

        mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        last_error = kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            logger.warning("[Main] [SYS] Another instance of 0xVoice2Text is already running. Focusing existing window and exiting.")
            hwnd = user32.FindWindowW(None, "0xVoice2Text_Widget")
            if hwnd:
                user32.ShowWindow(hwnd, 9) # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
            kernel32.CloseHandle(mutex)
            return None
        return mutex
    except Exception as e:
        logger.error(f"[Main] [SYS] Single instance mutex check failed: {e}")
        return None

def _global_excepthook(exctype, value, tb):
    import traceback
    err_text = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"[CRITICAL UNCAUGHT EXCEPTION]\n{err_text}")
    try:
        crash_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
        with open(crash_log_path, "w", encoding="utf-8") as f:
            f.write(err_text)
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"0xVoice2Text encountered a critical error:\n\n{value}\n\nSee crash.log for full traceback.",
            "0xVoice2Text Error",
            0x10 # MB_ICONERROR
        )
    except Exception:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = _global_excepthook

if __name__ == "__main__":
    try:
        mutex = acquire_single_instance_mutex()
        if mutex is None:
            sys.exit(0)

        controller = ApplicationController(single_instance_mutex=mutex)
        sys.exit(controller.run())
    except Exception as e:
        _global_excepthook(*sys.exc_info())
