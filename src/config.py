import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
OLD_CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "stt_engine": "whisper",         # whisper (faster-whisper AVX2 / CUDA)
    "whisper_model": "large-v3-turbo", # large-v3-turbo, large-v3
    "stt_device": "auto",            # auto (CPU AVX2 / CUDA), cpu, cuda
    "compute_type": "int8",          # int8 (fastest CPU), float32, float16 (CUDA)
    "beam_size": 1,                  # 1 for sub-300ms turbo, 3-5 for max accuracy
    "language": "ru",
    "hotkey": "ctrl+space",          # ctrl+space, alt+3, caps_lock, f8, f9, etc.
    "hotkey_mode": "toggle",         # toggle, push_to_talk
    "wake_word_enabled": True,       # Enable voice wake word trigger
    "wake_words": "джарвис, джарвиз, жарвис",
    "stop_words": "стоп",
    "vad_enabled": True,             # Enable neural Silero VAD (Voice Activity Detection)
    "vad_threshold": 0.5,            # Speech probability threshold [0.0 - 1.0]
    "silence_timeout": 3.0,          # Pause timeout in seconds before auto-stop
    "voice_macros_enabled": True,    # Enable voice app launching and macro commands
    "audio_device": None,
    "auto_paste": True,
    "add_trailing_space": True,
    "sound_feedback": True,
    "sound_pack": "scifi",           # scifi (Cyberpunk HUD), subtle, classic
    "sound_volume": 0.28,
    "always_on_top": True,
    "widget_opacity": 0.92,
    "theme": "cyberpunk_dark",
    "tts_voice_enabled": True,
    "tts_engine": "qwen3",           # qwen3, edge
    "qwen_tts_model": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "tts_ref_voice": "",             # Path to custom voice .wav file for zero-shot cloning
    "tts_device": "auto",            # auto, directml, cpu, cuda
    "tts_voice": "ru-RU-SvetlanaNeural",
    "tts_pitch": "+0Hz",
    "tts_rate": "+20%",
    "ai_mode": "direct",              # direct, clean, smart
    "gemini_api_key": "",
    "gemma_model": "gemini-3.5-flash-lite",
    "gemini_model": "gemini-3.6-flash",
    "system_prompt_clean": "",
    "system_prompt_smart": ""
}

class AppConfig:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        os.makedirs(DATA_DIR, exist_ok=True)
        self.load()

    def load(self):
        target_path = CONFIG_FILE
        if not os.path.exists(CONFIG_FILE) and os.path.exists(OLD_CONFIG_FILE):
            target_path = OLD_CONFIG_FILE

        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"[Config] Error loading config: {e}")

    def save(self) -> tuple[bool, str]:
        """Atomically writes config to disk. Returns (success, error_message)."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            tmp_path = CONFIG_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            # Atomic rename: prevents partial writes from corrupting config
            if os.path.exists(CONFIG_FILE):
                os.replace(tmp_path, CONFIG_FILE)
            else:
                os.rename(tmp_path, CONFIG_FILE)
            return True, ""
        except Exception as e:
            err_msg = f"[Config] Error saving config: {e}"
            print(err_msg)
            return False, str(e)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value) -> tuple[bool, str]:
        """Sets a single key and immediately persists to disk."""
        self.data[key] = value
        return self.save()

    def set_many(self, updates: dict) -> tuple[bool, str]:
        """Batch-sets multiple keys with a single disk write."""
        self.data.update(updates)
        return self.save()
