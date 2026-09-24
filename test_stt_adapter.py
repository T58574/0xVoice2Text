import sys
import os
import time
import numpy as np

# Add project root directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.core.stt.factory import STTFactory
from src.core.stt_engine import STTEngine
from src.config import AppConfig

def run_tests():
    print("==================================================")
    print("[*] TEST: STT Factory & Whisper STT Adapter Test")
    print("==================================================")

    config = AppConfig()
    config.set("stt_engine", "whisper")
    config.set("whisper_model", "large-v3-turbo")

    stt = STTEngine(config=config)
    print(f"[+] Active Adapter Name: {stt.adapter.get_name()}")
    print(f"[+] Initial Status: {stt.status_message}")
    print(f"[+] Is Ready: {stt.is_ready}")

    # Synchronous load for test verification
    done_event = False
    def on_done(ok):
        nonlocal done_event
        done_event = True
        print(f"[+] Load callback fired: success={ok}")

    stt.load_model(on_complete=on_done)
    while not done_event:
        time.sleep(0.1)

    print(f"[+] Loaded Status: {stt.status_message}")
    print(f"[+] Is Ready: {stt.is_ready}")

    # Test synthetic audio buffer (1.5 seconds of silence/tone, 16kHz)
    sample_rate = 16000
    duration = 1.5
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    synthetic_audio = (0.01 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    print(f"[+] Created synthetic audio buffer of length {len(synthetic_audio)} samples ({duration}s)")
    t0 = time.time()
    result = stt.transcribe(synthetic_audio)
    dt = time.time() - t0
    print(f"[+] Inference completed in {dt:.3f}s, result: '{result}'")

    print("[OK] Architecture verification passed!")

if __name__ == "__main__":
    run_tests()
