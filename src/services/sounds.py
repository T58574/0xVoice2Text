import threading
import numpy as np
import sounddevice as sd

CURRENT_SOUND_PACK = "disabled" # Legacy synth bleeps disabled in favor of natural TTS voice

def set_sound_pack(pack_name):
    global CURRENT_SOUND_PACK
    CURRENT_SOUND_PACK = pack_name.lower().strip()

def _play_buffer(samples, sr=22050):
    def _worker():
        try:
            sd.play(samples, sr)
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()

def play_start_sound():
    if CURRENT_SOUND_PACK == "disabled":
        return

    sr = 22050
    if CURRENT_SOUND_PACK == "jarvis":
        # Metallic dual-tone ascending chime
        t1 = np.linspace(0, 0.08, int(sr * 0.08), False)
        t2 = np.linspace(0, 0.12, int(sr * 0.12), False)
        wave1 = 0.3 * np.sin(2 * np.pi * 1200 * t1) * np.exp(-t1 * 25)
        wave2 = 0.4 * np.sin(2 * np.pi * 1600 * t2) * np.exp(-t2 * 20)
        audio = np.concatenate([wave1, wave2]).astype(np.float32)
        _play_buffer(audio, sr)
    elif CURRENT_SOUND_PACK == "stealth":
        # Soft subtle tick
        t = np.linspace(0, 0.03, int(sr * 0.03), False)
        audio = (0.15 * np.sin(2 * np.pi * 600 * t) * np.exp(-t * 80)).astype(np.float32)
        _play_buffer(audio, sr)
    else: # scifi (default)
        # Sci-Fi synth pulse (880Hz -> 1320Hz chirp)
        t = np.linspace(0, 0.09, int(sr * 0.09), False)
        freq = np.linspace(880, 1400, len(t))
        audio = (0.35 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 15)).astype(np.float32)
        _play_buffer(audio, sr)

def play_stop_sound():
    if CURRENT_SOUND_PACK == "disabled":
        return

    sr = 22050
    if CURRENT_SOUND_PACK == "jarvis":
        t = np.linspace(0, 0.1, int(sr * 0.1), False)
        audio = (0.3 * np.sin(2 * np.pi * 800 * t) * np.exp(-t * 30)).astype(np.float32)
        _play_buffer(audio, sr)
    elif CURRENT_SOUND_PACK == "stealth":
        t = np.linspace(0, 0.03, int(sr * 0.03), False)
        audio = (0.15 * np.sin(2 * np.pi * 400 * t) * np.exp(-t * 80)).astype(np.float32)
        _play_buffer(audio, sr)
    else: # scifi
        t = np.linspace(0, 0.09, int(sr * 0.09), False)
        freq = np.linspace(1200, 600, len(t))
        audio = (0.35 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 18)).astype(np.float32)
        _play_buffer(audio, sr)

def play_success_sound():
    if CURRENT_SOUND_PACK == "disabled":
        return

    sr = 22050
    t1 = np.linspace(0, 0.06, int(sr * 0.06), False)
    t2 = np.linspace(0, 0.1, int(sr * 0.1), False)
    wave1 = 0.3 * np.sin(2 * np.pi * 1400 * t1)
    wave2 = 0.4 * np.sin(2 * np.pi * 1800 * t2) * np.exp(-t2 * 15)
    audio = np.concatenate([wave1, wave2]).astype(np.float32)
    _play_buffer(audio, sr)
