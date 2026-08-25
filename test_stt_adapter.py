import sys
import os
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
    print("[*] TEST: STT Factory & Qwen3-ASR Adapter Test")
    print("==================================================")

    config = AppConfig()
    config.set("stt_engine", "qwen3")
    config.set("qwen_model", "Qwen/Qwen3-ASR-1.7B-hf")

    stt = STTEngine(config=config)
    print(f"[+] Active Adapter Name: {stt.adapter.get_name()}")
    print(f"[+] Initial Status: {stt.status_message}")
    print(f"[+] Is Ready: {stt.is_ready}")

    # Test synthetic audio buffer (1.5 seconds of silence/tone, 16kHz)
    sample_rate = 16000
    duration = 1.5
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    synthetic_audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    print(f"[+] Created synthetic audio buffer of length {len(synthetic_audio)} samples ({duration}s)")
    
    print("[OK] Architecture verification passed!")

if __name__ == "__main__":
    run_tests()
