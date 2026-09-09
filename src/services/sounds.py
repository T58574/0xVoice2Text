import threading
from typing import Optional, Dict
import numpy as np
import sounddevice as sd

from src.core.logger import logger

DEFAULT_SAMPLE_RATE = 44100

class SoundEffects:
    """
    High-performance, procedural sound effects generator and player.
    Synthesizes smooth, anti-aliased mathematical waveforms in memory (0 external files, 0 API calls).
    Completely non-blocking, multi-threaded playback via PortAudio (sounddevice).
    """

    def __init__(self, config=None, pack: str = "scifi", volume: float = 0.28):
        self.config = config
        self.sample_rate = DEFAULT_SAMPLE_RATE
        self.pack = (self.config.get("sound_pack", pack) if self.config else pack).lower().strip()
        self.volume = float(self.config.get("sound_volume", volume) if self.config else volume)
        self.enabled = bool(self.config.get("sound_feedback", True) if self.config else True)

        self._lock = threading.Lock()
        self._buffers: Dict[str, np.ndarray] = {}
        self._render_pack()

    def reload_config(self, config=None):
        if config:
            self.config = config
        if self.config:
            self.pack = str(self.config.get("sound_pack", "scifi")).lower().strip()
            self.volume = float(self.config.get("sound_volume", 0.28))
            self.enabled = bool(self.config.get("sound_feedback", True))
        self._render_pack()

    def set_pack(self, pack_name: str):
        self.pack = pack_name.lower().strip()
        self._render_pack()

    def _render_pack(self):
        """Pre-computes float32 audio buffers for all feedback events with zero DC-offset click."""
        with self._lock:
            sr = self.sample_rate
            vol = max(0.05, min(1.0, self.volume))
            buffers = {}

            if self.pack == "subtle":
                # Soft subtle blips
                # Start: Soft rising 600 -> 900 Hz (60 ms)
                t = np.linspace(0, 0.06, int(sr * 0.06), False)
                f = np.linspace(600, 900, len(t))
                buffers["start"] = (vol * 0.7 * np.sin(2 * np.pi * f * t) * np.sin(np.pi * t / 0.06)).astype(np.float32)

                # Success: Dual soft bell 700 -> 1050 Hz (100 ms)
                t1 = np.linspace(0, 0.04, int(sr * 0.04), False)
                t2 = np.linspace(0, 0.06, int(sr * 0.06), False)
                w1 = vol * 0.6 * np.sin(2 * np.pi * 700 * t1) * np.sin(np.pi * t1 / 0.04)
                w2 = vol * 0.7 * np.sin(2 * np.pi * 1050 * t2) * np.sin(np.pi * t2 / 0.06)
                buffers["success"] = np.concatenate([w1, w2]).astype(np.float32)

                # Stop: Soft tick 500 -> 350 Hz (50 ms)
                t = np.linspace(0, 0.05, int(sr * 0.05), False)
                f = np.linspace(500, 350, len(t))
                buffers["stop"] = (vol * 0.6 * np.sin(2 * np.pi * f * t) * np.sin(np.pi * t / 0.05)).astype(np.float32)

                # Error: Muted low double tap (180 Hz, 60 ms + 140 Hz, 70 ms)
                t1 = np.linspace(0, 0.06, int(sr * 0.06), False)
                gap = np.zeros(int(sr * 0.025), dtype=np.float32)
                t2 = np.linspace(0, 0.07, int(sr * 0.07), False)
                e1 = vol * 0.7 * np.sin(2 * np.pi * 200 * t1) * np.sin(np.pi * t1 / 0.06)
                e2 = vol * 0.7 * np.sin(2 * np.pi * 150 * t2) * np.sin(np.pi * t2 / 0.07)
                buffers["error"] = np.concatenate([e1, gap, e2]).astype(np.float32)

                # Wake: Soft ping 800 Hz (40 ms)
                t = np.linspace(0, 0.04, int(sr * 0.04), False)
                buffers["wake"] = (vol * 0.7 * np.sin(2 * np.pi * 800 * t) * np.sin(np.pi * t / 0.04)).astype(np.float32)

            elif self.pack == "classic":
                # Clean sine beeps
                # Start: 880 Hz beep (70 ms)
                t = np.linspace(0, 0.07, int(sr * 0.07), False)
                buffers["start"] = (vol * 0.8 * np.sin(2 * np.pi * 880 * t) * np.sin(np.pi * t / 0.07)).astype(np.float32)

                # Success: 880 + 1320 Hz chord (110 ms)
                t = np.linspace(0, 0.11, int(sr * 0.11), False)
                buffers["success"] = (vol * 0.5 * (np.sin(2 * np.pi * 880 * t) + np.sin(2 * np.pi * 1320 * t)) * np.sin(np.pi * t / 0.11)).astype(np.float32)

                # Stop: 440 Hz low beep (60 ms)
                t = np.linspace(0, 0.06, int(sr * 0.06), False)
                buffers["stop"] = (vol * 0.7 * np.sin(2 * np.pi * 440 * t) * np.sin(np.pi * t / 0.06)).astype(np.float32)

                # Error: 220 Hz low buzz (140 ms)
                t = np.linspace(0, 0.14, int(sr * 0.14), False)
                buffers["error"] = (vol * 0.85 * np.sin(2 * np.pi * 220 * t) * np.sin(np.pi * t / 0.14)).astype(np.float32)

                # Wake: 1046 Hz high beep (50 ms)
                t = np.linspace(0, 0.05, int(sr * 0.05), False)
                buffers["wake"] = (vol * 0.8 * np.sin(2 * np.pi * 1046 * t) * np.sin(np.pi * t / 0.05)).astype(np.float32)

            else:
                # Default: 'scifi' (Cyberpunk HUD style)
                # 1. Start (Ввод): Ascending chirp 880 Hz -> 1400 Hz (80 ms)
                t_st = np.linspace(0, 0.08, int(sr * 0.08), False)
                buffers["start"] = (vol * np.sin(2 * np.pi * np.linspace(880, 1400, len(t_st)) * t_st) * np.sin(np.pi * t_st / 0.08)).astype(np.float32)

                # 2. Success (Вывод / Вставка текста): Harmonious A5 (880 Hz, 50 ms) -> E6 (1320 Hz, 90 ms)
                t1 = np.linspace(0, 0.05, int(sr * 0.05), False)
                t2 = np.linspace(0, 0.09, int(sr * 0.09), False)
                sc1 = vol * 0.85 * np.sin(2 * np.pi * 880 * t1) * np.sin(np.pi * t1 / 0.05)
                sc2 = vol * np.sin(2 * np.pi * 1320 * t2) * np.sin(np.pi * t2 / 0.09)
                buffers["success"] = np.concatenate([sc1, sc2]).astype(np.float32)

                # 3. Stop (Стоп / Отмена): Descending chirp 1200 Hz -> 600 Hz (70 ms)
                t_sp = np.linspace(0, 0.07, int(sr * 0.07), False)
                buffers["stop"] = (vol * 0.9 * np.sin(2 * np.pi * np.linspace(1200, 600, len(t_sp)) * t_sp) * np.sin(np.pi * t_sp / 0.07)).astype(np.float32)

                # 4. Error (Ошибка / Сбой): Alert double buzz (240 Hz, 70 ms + gap 30 ms + 170 Hz, 90 ms)
                t_e1 = np.linspace(0, 0.07, int(sr * 0.07), False)
                gap = np.zeros(int(sr * 0.03), dtype=np.float32)
                t_e2 = np.linspace(0, 0.09, int(sr * 0.09), False)
                er1 = vol * np.sin(2 * np.pi * 240 * t_e1) * np.sin(np.pi * t_e1 / 0.07)
                er2 = vol * np.sin(2 * np.pi * 170 * t_e2) * np.sin(np.pi * t_e2 / 0.09)
                buffers["error"] = np.concatenate([er1, gap, er2]).astype(np.float32)

                # 5. Wake (Детекция триггера "джарвис"): Crisp 1046 Hz C6 blip (50 ms)
                t_w = np.linspace(0, 0.05, int(sr * 0.05), False)
                buffers["wake"] = (vol * np.sin(2 * np.pi * 1046 * t_w) * np.sin(np.pi * t_w / 0.05)).astype(np.float32)

            buffers["macro"] = buffers["success"]
            buffers["listening"] = buffers["start"]
            self._buffers = buffers

    def play(self, category: str):
        """Asynchronously plays pre-rendered procedural sound buffer."""
        if not self.enabled:
            return

        cat = str(category).lower().strip()
        buf = self._buffers.get(cat)
        if buf is None:
            buf = self._buffers.get("start")
        if buf is None:
            return

        def _worker():
            try:
                sd.play(buf, self.sample_rate)
            except Exception as e:
                logger.debug(f"[SoundEffects] Playback exception: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def play_start(self):
        """Ввод: звуковой сигнал старта записи голоса."""
        self.play("start")

    def play_success(self):
        """Вывод: звуковой сигнал завершения распознавания и вставки текста."""
        self.play("success")

    def play_stop(self):
        """Звуковой сигнал остановки записи / отмены."""
        self.play("stop")

    def play_error(self):
        """Звуковой сигнал ошибки (сбой микрофона / распознавания)."""
        self.play("error")

    def play_wake(self):
        """Звуковой сигнал детекции ключевого слова активации («джарвис»)."""
        self.play("wake")

    def play_macro(self):
        """Звуковой сигнал выполнения макроса / команды."""
        self.play("macro")

    def unload(self):
        """No-op for in-memory procedural waveforms."""
        pass

# Global singleton instance
_GLOBAL_SOUNDS: Optional[SoundEffects] = None

def get_sound_fx(config=None) -> SoundEffects:
    global _GLOBAL_SOUNDS
    if _GLOBAL_SOUNDS is None:
        _GLOBAL_SOUNDS = SoundEffects(config=config)
    elif config is not None:
        _GLOBAL_SOUNDS.reload_config(config)
    return _GLOBAL_SOUNDS

def play_start_sound():
    get_sound_fx().play_start()

def play_success_sound():
    get_sound_fx().play_success()

def play_stop_sound():
    get_sound_fx().play_stop()

def play_error_sound():
    get_sound_fx().play_error()

def play_wake_sound():
    get_sound_fx().play_wake()

def set_sound_pack(pack_name: str):
    get_sound_fx().set_pack(pack_name)
