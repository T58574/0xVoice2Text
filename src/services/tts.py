import os
import hashlib
import random
import threading
import ctypes
import time
import asyncio
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

def get_phrase_filename(phrase: str, voice: str = "ru-RU-SvetlanaNeural", rate: str = "+20%") -> str:
    h = hashlib.md5(f"{voice}_{rate}_{phrase}".encode("utf-8")).hexdigest()[:10]
    return f"tts_{h}.mp3"

class JarvisVoiceService:
    """
    Modular plug-and-play Text-to-Speech (TTS) Service for Jarvis.
    - Zero lock-in: toggle on/off in config via 'tts_voice_enabled' (default: True).
    - Female (Svetlana) & Male (Dmitry) voice selection + configurable speech speed (+20%).
    - Automatic startup background pre-caching for 0ms instant local playback.
    - Native Windows MCI MP3 playback via ctypes (0 extra dependencies).
    - Echo prevention tracking via is_speaking() & is_jarvis_phrase().
    """
    def __init__(self, config):
        self.config = config
        self.cache_dir = CACHE_DIR
        self._lock = threading.Lock()
        self.current_alias = None
        self.is_speaking_flag = False
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Start silent background pre-caching of all voice phrases on startup
        self.start_background_precaching()

    def is_enabled(self) -> bool:
        return bool(self.config.get("tts_voice_enabled", True))

    def is_speaking(self) -> bool:
        return self.is_speaking_flag

    def is_jarvis_phrase(self, text: str) -> bool:
        if not text:
            return False
        norm_text = text.lower().strip().rstrip(".!?,")
        for cat_phrases in PRESET_PHRASES.values():
            for p in cat_phrases:
                p_norm = p.lower().strip().rstrip(".!?,")
                if p_norm in norm_text or norm_text in p_norm:
                    return True
        return False

    def start_background_precaching(self):
        """
        Pre-caches all phrase variations in the background on startup
        so all phrases play with 0ms lag from local disk cache.
        """
        def _precache_worker():
            try:
                import edge_tts
                voices = [
                    ("ru-RU-SvetlanaNeural", "+0Hz"),
                    ("ru-RU-DmitryNeural", "-5Hz")
                ]
                rate = self.config.get("tts_rate", "+20%")

                for voice, pitch in voices:
                    for cat_phrases in PRESET_PHRASES.values():
                        for phrase in cat_phrases:
                            fname = get_phrase_filename(phrase, voice, rate)
                            fpath = os.path.join(self.cache_dir, fname)
                            if not os.path.exists(fpath):
                                try:
                                    comm = edge_tts.Communicate(phrase, voice=voice, pitch=pitch, rate=rate)
                                    asyncio.run(comm.save(fpath))
                                except Exception:
                                    pass
            except Exception as e:
                print(f"[JarvisVoiceService] Pre-caching exception: {e}")

        threading.Thread(target=_precache_worker, daemon=True).start()

    def _play_mp3_file(self, mp3_path: str):
        if not os.path.exists(mp3_path):
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
                open_cmd = f'open "{mp3_path}" type mpegvideo alias {alias}'
                res_open = ctypes.windll.winmm.mciSendStringW(open_cmd, None, 0, 0)
                if res_open == 0:
                    ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, 0)
                    ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, 0)
            except Exception as e:
                print(f"[JarvisVoiceService] Playback error: {e}")
            finally:
                with self._lock:
                    if self.current_alias == alias:
                        self.current_alias = None
                    self.is_speaking_flag = False

        threading.Thread(target=_worker, daemon=True).start()

    def play_category(self, category: str):
        if not self.is_enabled():
            return

        phrases = PRESET_PHRASES.get(category, [])
        if not phrases:
            return

        phrase = random.choice(phrases)
        voice = self.config.get("tts_voice", "ru-RU-SvetlanaNeural")
        rate = self.config.get("tts_rate", "+20%")
        fname = get_phrase_filename(phrase, voice, rate)
        fpath = os.path.join(self.cache_dir, fname)

        if os.path.exists(fpath):
            self._play_mp3_file(fpath)
        else:
            self.speak_text(phrase)

    def speak_text(self, text: str):
        if not self.is_enabled() or not text:
            return

        voice = self.config.get("tts_voice", "ru-RU-SvetlanaNeural")
        pitch = self.config.get("tts_pitch", "-5Hz" if "Dmitry" in voice else "+0Hz")
        rate = self.config.get("tts_rate", "+20%")
        fname = get_phrase_filename(text, voice, rate)
        fpath = os.path.join(self.cache_dir, fname)

        if os.path.exists(fpath):
            self._play_mp3_file(fpath)
            return

        def _worker():
            try:
                import edge_tts
                comm = edge_tts.Communicate(text, voice=voice, pitch=pitch, rate=rate)
                asyncio.run(comm.save(fpath))
                if os.path.exists(fpath):
                    self._play_mp3_file(fpath)
            except Exception as e:
                print(f"[JarvisVoiceService] Dynamic synthesis failed for '{text}': {e}")

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
