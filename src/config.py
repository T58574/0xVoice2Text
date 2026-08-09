import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
OLD_CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "model_size": "whisper-large-v3",
    "language": "ru",
    "device": "cloud",
    "compute_type": "default",
    "hotkey": "ctrl+space",          # ctrl+space, alt+3, caps_lock, f8, f9, etc.
    "hotkey_mode": "toggle",         # toggle, push_to_talk
    "wake_word_enabled": True,       # Enable voice wake word trigger
    "wake_words": "джарвис, джарвиз, жарвис",
    "stop_words": "стоп",
    "silence_timeout": 3.0,          # Pause timeout in seconds before auto-stop
    "voice_macros_enabled": True,    # Enable voice app launching and macro commands
    "audio_device": None,
    "auto_paste": True,
    "add_trailing_space": True,
    "sound_feedback": True,
    "always_on_top": True,
    "widget_opacity": 0.92,
    "theme": "cyberpunk_dark",
    "tts_voice_enabled": True,
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

    def save(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
