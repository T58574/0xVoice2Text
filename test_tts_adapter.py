import sys
import os

# Add project root directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.services.sounds import SoundEffects, get_sound_fx
from src.services.tts import JarvisVoiceService
from src.config import AppConfig

def test_sound_fx_subsystem():
    print("==================================================")
    print("[*] TEST: Procedural Sound Feedback & Status Audio")
    print("==================================================")

    config = AppConfig()
    config.set("sound_feedback", True)
    config.set("sound_pack", "scifi")

    sfx = SoundEffects(config)
    print(f"[+] Active Sound Pack: {sfx.pack}")
    print(f"[+] Sound Feedback Enabled: {sfx.enabled}")
    print(f"[+] Pre-computed Buffers: {list(sfx._buffers.keys())}")

    for key in ["start", "success", "error", "stop", "wake"]:
        assert key in sfx._buffers, f"Missing buffer for sound '{key}'"
        assert len(sfx._buffers[key]) > 0, f"Empty buffer for sound '{key}'"
        assert sfx._buffers[key].dtype == "float32", f"Invalid buffer dtype for '{key}'"

    # Test legacy JarvisVoiceService bridge compatibility
    voice_svc = JarvisVoiceService(config)
    assert voice_svc.is_speaking() == False, "TTS is_speaking must be False"
    assert voice_svc.is_jarvis_phrase("test") == False, "is_jarvis_phrase must be False"

    # Play non-blocking test sounds
    sfx.play_start()
    sfx.play_success()
    sfx.play_error()
    sfx.play_stop()
    sfx.play_wake()

    print("[OK] Procedural Sound Feedback verification passed successfully!")

if __name__ == "__main__":
    test_sound_fx_subsystem()
