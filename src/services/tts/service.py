import os
import hashlib
import random
import threading
import ctypes
import time
from typing import Optional

from src.core.logger import logger
from src.services.tts.base import BaseTTSAdapter
from src.services.tts.factory import TTSFactory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "audio_cache", "tts")

PRESET_PHRASES = {
    "listening": [
        "Слушаю вас, сэр.",
        "Да, я вас слушаю.",
        "Готов к приему информации.",
        "На связи.",
        "Внимательно слушаю.",
        "Слушаю.",
        "Слушаю ваши указания."
    ],
    "success": [
        "Готово, сэр.",
        "Текст успешно введен.",
        "Принято.",
        "Выполнено.",
        "Готово.",
        "Сделано, сэр.",
        "Готово, текст на экране."
    ],
    "macro": [
        "Выполняю команду.",
        "Есть, выполняю.",
        "Запускаю, сэр.",
        "Принято, активирую.",
        "Запрос принят к исполнению.",
        "Команда активирована."
    ],
    "error": [
        "Сэр, произошла ошибка.",
        "Ключ доступа не найден.",
        "Не удалось распознать речь.",
        "Алгоритмы временно недоступны."
    ],
    "processing": [
        "Обрабатываю.",
        "Секунду, сэр.",
        "Распознаю аудио.",
        "Обработка данных."
    ]
}

def get_phrase_filename(phrase: str, engine: str = "qwen3", voice: str = "default", rate: str = "+20%") -> str:
    h = hashlib.md5(f"{engine}_{voice}_{rate}_{phrase}".encode("utf-8")).hexdigest()[:10]
    return f"tts_{h}.wav"

class JarvisVoiceService:
    """
    Modular plug-and-play Text-to-Speech (TTS) Service for Jarvis.
    Supports Qwen3-TTS-12Hz (Local Zero-Shot) & Edge-TTS cloud engines.
    - Automatic startup background pre-caching for 0ms instant local playback.
    - Native Windows MCI playback via ctypes.
    - Echo prevention tracking via is_speaking() & is_jarvis_phrase().
    """
    def __init__(self, config):
        self.config = config
        self.cache_dir = CACHE_DIR
        self._lock = threading.Lock()
        self.current_alias = None
        self.is_speaking_flag = False
        self.last_speaking_time = 0.0
        os.makedirs(self.cache_dir, exist_ok=True)

        self.adapter: Optional[BaseTTSAdapter] = None
        self._init_adapter()

        # Start silent background pre-caching of all voice phrases on startup
        self.start_background_precaching()

    def _init_adapter(self):
        engine_name = self.config.get("tts_engine", "edge")
        options = {
            "qwen_tts_model": self.config.get("qwen_tts_model", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
            "tts_ref_voice": self.config.get("tts_ref_voice", None),
            "tts_device": self.config.get("tts_device", "auto"),
            "tts_voice": self.config.get("tts_voice", "ru-RU-SvetlanaNeural"),
            "tts_rate": self.config.get("tts_rate", "+20%"),
            "tts_pitch": self.config.get("tts_pitch", "+0Hz")
        }
        try:
            self.adapter = TTSFactory.create_adapter(engine_name, options)
            self.adapter.load_model()
        except Exception as e:
            logger.warning(f"[JarvisVoiceService] Primary TTS adapter {engine_name} failed: {e}. Falling back to Edge-TTS.")
            self.adapter = TTSFactory.create_adapter("edge", options)
            self.adapter.load_model()

    def switch_engine(self, engine_name: str, options: Optional[dict] = None):
        with self._lock:
            if self.adapter:
                try:
                    self.adapter.unload()
                except Exception as e:
                    logger.warning(f"[JarvisVoiceService] Error unloading previous TTS adapter: {e}")

            opts = options or {}
            try:
                self.adapter = TTSFactory.create_adapter(engine_name, opts)
                self.adapter.load_model()
                logger.info(f"[JarvisVoiceService] Switched TTS engine to {self.adapter.get_name()}")
            except Exception as e:
                logger.error(f"[JarvisVoiceService] Failed to switch TTS to '{engine_name}': {e}. Falling back to Edge-TTS.")
                try:
                    self.adapter = TTSFactory.create_adapter("edge", opts)
                    self.adapter.load_model()
                except Exception as e2:
                    logger.error(f"[JarvisVoiceService] Edge-TTS fallback also failed: {e2}")

    def is_enabled(self) -> bool:
        return bool(self.config.get("tts_voice_enabled", True))

    def is_speaking(self) -> bool:
        return self.is_speaking_flag

    def was_recently_speaking(self, window_sec: float = 2.0) -> bool:
        with self._lock:
            if self.is_speaking_flag:
                return True
            if self.last_speaking_time > 0 and (time.time() - self.last_speaking_time < window_sec):
                return True
            return False

    def is_jarvis_phrase(self, text: str, check_recent_only: bool = False) -> bool:
        if not text:
            return False
        if check_recent_only and not self.was_recently_speaking(window_sec=2.0):
            return False
        norm_text = text.lower().strip().rstrip(".!?, ")
        for cat_phrases in PRESET_PHRASES.values():
            for p in cat_phrases:
                p_norm = p.lower().strip().rstrip(".!?, ")
                if norm_text == p_norm or p_norm in norm_text or norm_text in p_norm:
                    return True
        return False

    def start_background_precaching(self):
        """
        Pre-caches phrase variations in background so phrases play with 0ms lag from local disk cache.
        """
        def _precache_worker():
            try:
                engine = self.config.get("tts_engine", "qwen3")
                voice = self.config.get("tts_voice", "ru-RU-SvetlanaNeural")
                rate = self.config.get("tts_rate", "+20%")

                for cat_phrases in PRESET_PHRASES.values():
                    for phrase in cat_phrases:
                        fname = get_phrase_filename(phrase, engine, voice, rate)
                        fpath = os.path.join(self.cache_dir, fname)
                        with self._lock:
                            curr_adapter = self.adapter
                        if not os.path.exists(fpath) and curr_adapter:
                            try:
                                curr_adapter.synthesize_to_file(phrase, fpath)
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"[JarvisVoiceService] Pre-caching exception: {e}")

        threading.Thread(target=_precache_worker, daemon=True).start()

    def _play_audio_file(self, file_path: str):
        if not os.path.exists(file_path):
            return

        def _worker():
            with self._lock:
                if self.current_alias:
                    try:
                        ctypes.windll.winmm.mciSendStringW(f'close {self.current_alias}', None, 0, 0)
                    except Exception:
                        pass

                alias = f"jarvis_tts_{int(time.time() * 1000)}"
                self.current_alias = alias
                self.is_speaking_flag = True

            try:
                open_cmd = f'open "{file_path}" alias {alias}'
                res_open = ctypes.windll.winmm.mciSendStringW(open_cmd, None, 0, 0)
                if res_open == 0:
                    ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, 0)
                    ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, 0)
            except Exception as e:
                logger.error(f"[JarvisVoiceService] Playback error: {e}")
            finally:
                with self._lock:
                    if self.current_alias == alias:
                        self.current_alias = None
                        self.is_speaking_flag = False
                    self.last_speaking_time = time.time()

        threading.Thread(target=_worker, daemon=True).start()

    def play_category(self, category: str):
        if not self.is_enabled():
            return

        phrases = PRESET_PHRASES.get(category, [])
        if not phrases:
            return

        phrase = random.choice(phrases)
        engine = self.config.get("tts_engine", "qwen3")
        voice = self.config.get("tts_voice", "ru-RU-SvetlanaNeural")
        rate = self.config.get("tts_rate", "+20%")
        fname = get_phrase_filename(phrase, engine, voice, rate)
        fpath = os.path.join(self.cache_dir, fname)

        if os.path.exists(fpath):
            self._play_audio_file(fpath)
        else:
            self.speak_text(phrase)

    def speak_text(self, text: str):
        if not self.is_enabled() or not text:
            return

        engine = self.config.get("tts_engine", "qwen3")
        voice = self.config.get("tts_voice", "ru-RU-SvetlanaNeural")
        rate = self.config.get("tts_rate", "+20%")
        fname = get_phrase_filename(text, engine, voice, rate)
        fpath = os.path.join(self.cache_dir, fname)

        if os.path.exists(fpath):
            self._play_audio_file(fpath)
            return

        def _worker():
            try:
                with self._lock:
                    curr_adapter = self.adapter
                if curr_adapter:
                    success = curr_adapter.synthesize_to_file(text, fpath)
                    if success and os.path.exists(fpath):
                        self._play_audio_file(fpath)
            except Exception as e:
                logger.error(f"[JarvisVoiceService] Dynamic synthesis failed for '{text}': {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def stop(self):
        with self._lock:
            if self.current_alias:
                try:
                    ctypes.windll.winmm.mciSendStringW(f'close {self.current_alias}', None, 0, 0)
                except Exception:
                    pass
                self.current_alias = None
            self.is_speaking_flag = False
