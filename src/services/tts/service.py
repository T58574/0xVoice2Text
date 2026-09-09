import os
import threading
import time
from typing import Optional

from src.core.logger import logger
from src.services.sounds import get_sound_fx, SoundEffects

# Preserved for backwards compatibility with any imports/tests
PRESET_PHRASES = {
    "listening": ["Слушаю."],
    "success": ["Готово."],
    "macro": ["Выполняю."],
    "error": ["Ошибка."],
    "processing": ["Обработка."]
}

def get_phrase_filename(phrase: str, engine: str = "qwen3", voice: str = "default", rate: str = "+20%") -> str:
    return "sound_feedback.wav"

class JarvisVoiceService:
    """
    Lightweight, procedural sound effect bridge replacing legacy heavy neural TTS.
    Emits instant generated audio tones for start (listening), success (text pasted),
    error, stop, and macro execution with 0ms lag, 0 external files, and 0 memory consumption.
    """
    def __init__(self, config=None):
        self.config = config
        self.sounds = get_sound_fx(config)
        self._lock = threading.Lock()
        self.is_speaking_flag = False
        self.last_speaking_time = 0.0
        logger.info("[JarvisVoiceService] Initialized procedural sound feedback (TTS voice engine disabled).")

    def switch_engine(self, engine_name: str, options: Optional[dict] = None):
        """No-op for procedural sound feedback."""
        pass

    def unload(self) -> None:
        """No-op for procedural sound feedback."""
        pass

    def is_speaking(self) -> bool:
        """Always False since assistant uses procedural audio beeps instead of vocal speech."""
        return False

    def was_recently_speaking(self, window_sec: float = 2.0) -> bool:
        return False

    def is_jarvis_phrase(self, text: str, check_recent_only: bool = False) -> bool:
        """Always False since there is no speech self-echo from procedural beeps."""
        return False

    def start_background_precaching(self):
        """No-op: procedural sounds are already pre-computed in RAM."""
        pass

    def play_category(self, category: str):
        """Plays procedural status sound corresponding to the category."""
        cat = category.lower().strip()
        if cat in ("listening", "start"):
            self.sounds.play_start()
        elif cat in ("success", "macro", "done"):
            self.sounds.play_success()
        elif cat in ("error", "fail"):
            self.sounds.play_error()
        elif cat in ("stop", "cancel"):
            self.sounds.play_stop()
        elif cat in ("wake", "trigger"):
            self.sounds.play_wake()
        else:
            self.sounds.play_start()

    def speak(self, text: str, voice_params: Optional[dict] = None, wait: bool = False):
        """Legacy method: plays notification chime."""
        self.sounds.play_success()
