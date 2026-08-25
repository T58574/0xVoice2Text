import sys
import os

# Add project root directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.services.tts.factory import TTSFactory
from src.services.tts import JarvisVoiceService
from src.config import AppConfig

def test_tts_subsystem():
    print("==================================================")
    print("[*] TEST: TTS Factory & Qwen3-TTS Adapter Test")
    print("==================================================")

    config = AppConfig()
    config.set("tts_engine", "qwen3")
    config.set("qwen_tts_model", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")

    voice_svc = JarvisVoiceService(config)
    print(f"[+] Active TTS Adapter: {voice_svc.adapter.get_name()}")
    print(f"[+] Initial Status: {voice_svc.adapter.get_status()}")
    print(f"[+] Is Ready: {voice_svc.adapter.is_ready()}")
    print(f"[+] Voice Enabled: {voice_svc.is_enabled()}")

    # Test Jarvis phrase echo detection
    test_phrase = "Слушаю вас, сэр."
    is_echo = voice_svc.is_jarvis_phrase(test_phrase)
    print(f"[+] Echo detection for '{test_phrase}': {is_echo} (Expected: True)")
    assert is_echo == True, "Echo detection failed for preset phrase!"

    # Test edge adapter factory creation
    edge_adapter = TTSFactory.create_adapter("edge", {"tts_voice": "ru-RU-SvetlanaNeural"})
    print(f"[+] Edge Adapter Created: {edge_adapter.get_name()}")

    print("[OK] TTS Architecture verification passed successfully!")

if __name__ == "__main__":
    test_tts_subsystem()
