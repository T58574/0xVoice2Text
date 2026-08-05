import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

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
    "widget_position": {"x": 100, "y": 100},
    "widget_opacity": 0.92,
    "theme": "cyberpunk_dark"
}

class AppConfig:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"[Config] Error loading config: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
