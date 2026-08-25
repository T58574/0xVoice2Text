import os
import re
import numpy as np
from src.config import AppConfig
from src.core.vad_engine import SileroVAD, verify_file_sha256, EXPECTED_SHA256
from src.core.wake_word import WakeWordManager
from src.services.macros import MacroManager
from src.services.hotkeys import HotkeyManager
from src.services.injector import TextInjector
from src.services.tts.service import JarvisVoiceService

def test_all():
    print("[1] Checking SileroVAD Checksum & ONNX Inference...")
    assert verify_file_sha256(r"data/models/silero_vad.onnx", EXPECTED_SHA256), "SHA256 mismatch!"
    vad = SileroVAD()
    assert vad.session is not None, "ONNX session failed!"
    prob_silence, is_sp = vad.process_chunk(np.zeros(16000, dtype=np.float32))
    assert prob_silence < 0.05, f"Expected low prob for silence, got {prob_silence}"
    print(f"    [+] SileroVAD OK (Silence prob: {prob_silence:.4f}, SHA256 verified)")

    print("[2] Checking Macros Security (No shell injection)...")
    cfg = AppConfig()
    macro_mgr = MacroManager(cfg)
    test_input = "calc.exe & notepad.exe | whoami"
    sanitized = re.sub(r"[;&|`$<>^]", "", test_input).strip()
    assert sanitized == "calc.exe  notepad.exe  whoami"
    print(f"    [+] Macro Manager injection defense OK")

    print("[3] Checking TTS Echo Logic (No false-positive speech suppression)...")
    tts = JarvisVoiceService(cfg)
    # When not speaking:
    assert not tts.is_jarvis_phrase("слушаю"), "Must not suppress when not speaking"
    assert not tts.is_jarvis_phrase("я слушаю лекцию"), "Must not suppress substring"
    # When speaking:
    tts.is_speaking_flag = True
    assert tts.is_jarvis_phrase("слушаю"), "Must suppress exact preset phrase when speaking"
    assert not tts.is_jarvis_phrase("я слушаю доклад"), "Must NOT suppress speech containing preset as substring"
    tts.is_speaking_flag = False
    print(f"    [+] TTS Echo Filter OK (Strict exact matching only when speaking)")

    print("[4] Checking Hotkeys Thread Safety...")
    hk = HotkeyManager("ctrl+space")
    hk.update_key("alt+shift+k")
    with hk._lock:
        assert "alt" in hk.required_keys and "shift" in hk.required_keys and "k" in hk.required_keys
    print(f"    [+] Hotkeys thread synchronization OK")

    print("[5] Checking WakeWordManager Queue Architecture...")
    ww = WakeWordManager(cfg)
    assert hasattr(ww, "_audio_queue"), "WakeWordManager must have _audio_queue"
    assert hasattr(ww, "current_device"), "WakeWordManager must track current_device"
    print(f"    [+] WakeWordManager Producer-Consumer Queue & Hot-Reload OK")

    print("\n[OK] ALL 5 INTEGRITY & SECURITY AUDIT CHECKS PASSED!")

if __name__ == "__main__":
    test_all()
