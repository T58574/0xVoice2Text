import os
import json
import re
import threading
import time
import numpy as np
import sounddevice as sd
import vosk

# Suppress debug logs from Vosk C++ core
vosk.SetLogLevel(-1)

class WakeWordManager:
    """
    Background manager powered by Vosk (ru model) for:
    1. Wake word detection (e.g., 'джарвис') -> Triggers recording start.
    2. Voice stop detection (e.g., 'стоп') -> Triggers recording stop.
    """
    def __init__(self, config, on_wake_detected=None, on_stop_detected=None):
        self.config = config
        self.on_wake_detected = on_wake_detected
        self.on_stop_detected = on_stop_detected

        self.model = None
        self.is_running = False
        self.is_recording_state = False
        self._thread = None
        self._lock = threading.Lock()
        self.stream = None
        self.last_trigger_time = 0.0
        self.last_speech_time = 0.0
        self.has_spoken_in_recording = False

        self.wake_words = self._parse_word_list("wake_words", ["джарвис", "джарвиз", "жарвис"])
        self.stop_words = self._parse_word_list("stop_words", ["стоп", "стопнули"])

    def _parse_word_list(self, key, default):
        val = self.config.get(key, default)
        if isinstance(val, str):
            return [w.strip().lower() for w in val.split(",") if w.strip()]
        if isinstance(val, list):
            return [str(w).strip().lower() for w in val if str(w).strip()]
        return default

    def reload_config(self):
        with self._lock:
            self.wake_words = self._parse_word_list("wake_words", ["джарвис", "джарвиз", "жарвис"])
            self.stop_words = self._parse_word_list("stop_words", ["стоп", "стопнули"])
        print(f"[WakeWordManager] Reloaded config. Wake words: {self.wake_words}, Stop words: {self.stop_words}")

    def start(self):
        if not self.config.get("wake_word_enabled", True):
            print("[WakeWordManager] Wake word activation is disabled in config.")
            return

        if self.is_running:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def set_recording_state(self, is_recording: bool):
        """Notifies the manager whether recording is currently active."""
        with self._lock:
            self.is_recording_state = is_recording
            if is_recording:
                self.has_spoken_in_recording = False
                self.last_speech_time = time.time()

    def _run_loop(self):
        print("[WakeWordManager] Loading local Vosk Russian model (vosk-model-small-ru-0.22)...")
        try:
            self.model = vosk.Model(lang="ru")
            print("[WakeWordManager] Vosk model loaded successfully!")
        except Exception as e:
            print(f"[WakeWordManager] Failed to load Vosk model: {e}")
            self.is_running = False
            return

        rec = vosk.KaldiRecognizer(self.model, 16000)

        def audio_callback(indata, frames, time_info, status):
            if not self.is_running:
                return
            
            # Convert float32 input buffer [-1.0, 1.0] to 16-bit int PCM bytes
            mono_float = indata[:, 0]
            pcm16 = (mono_float * 32767).astype(np.int16).tobytes()

            # Calculate RMS for Silence Detection (VAD)
            rms = float(np.sqrt(np.mean(mono_float ** 2))) if len(mono_float) > 0 else 0.0
            now = time.time()

            with self._lock:
                rec_state = self.is_recording_state

            if rec_state:
                # Voice Activity Detection during active recording
                if rms > 0.015:
                    self.last_speech_time = now
                    self.has_spoken_in_recording = True
                elif self.has_spoken_in_recording and (now - self.last_speech_time > 1.2) and (now - self.last_trigger_time > 1.5):
                    print("[WakeWordManager] ⏱️ SILENCE DETECTED (1.2s pause) -> Auto-stopping recording!")
                    self.has_spoken_in_recording = False
                    self.last_trigger_time = now
                    if self.on_stop_detected:
                        self.on_stop_detected()

            if rec.AcceptWaveform(pcm16):
                result_json = json.loads(rec.Result())
                text = result_json.get("text", "").lower()
                self._check_text(text)
            else:
                partial_json = json.loads(rec.PartialResult())
                partial_text = partial_json.get("partial", "").lower()
                if partial_text:
                    self._check_text(partial_text)

        device = self.config.get("audio_device")
        print(f"[WakeWordManager] Starting Vosk stream listener on audio device {device}...")

        try:
            self.stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                device=device,
                callback=audio_callback,
                blocksize=4000
            )
            self.stream.start()
            while self.is_running:
                time.sleep(0.1)
        except Exception as e:
            print(f"[WakeWordManager] Stream execution error: {e}")
        finally:
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

    def _check_text(self, text):
        if not text:
            return

        now = time.time()
        # Cooldown of 1.5s between triggers
        if now - self.last_trigger_time < 1.5:
            return

        with self._lock:
            currently_recording = self.is_recording_state
            wake_list = list(self.wake_words)
            stop_list = list(self.stop_words)

        if not currently_recording:
            # Listening for Wake Word ("джарвис")
            for w in wake_list:
                if w in text:
                    self.last_trigger_time = now
                    print(f"[WakeWordManager] 🎯 WAKE WORD DETECTED: '{w}' in '{text}'!")
                    if self.on_wake_detected:
                        self.on_wake_detected()
                    break
        else:
            # Listening for Stop Word ("стоп")
            for s in stop_list:
                if s in text:
                    self.last_trigger_time = now
                    print(f"[WakeWordManager] 🛑 STOP WORD DETECTED: '{s}' in '{text}'!")
                    if self.on_stop_detected:
                        self.on_stop_detected()
                    break

    def clean_transcription(self, text: str) -> str:
        """Helper to trim trailing stop word from transcription if user spoke 'стоп' at the end."""
        if not text:
            return text

        with self._lock:
            stop_list = list(self.stop_words)

        cleaned = text.strip()
        for sw in stop_list:
            pattern = re.compile(rf'(?:[\s.,!?\-]+|^){re.escape(sw)}[\s.,!?\-]*$', re.IGNORECASE)
            cleaned = pattern.sub('', cleaned).strip()

        return cleaned
