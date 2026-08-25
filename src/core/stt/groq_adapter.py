import os
import io
import wave
import threading
import time
from typing import Callable, Optional
import numpy as np
from dotenv import load_dotenv
from groq import Groq

from src.core.logger import logger
from src.core.stt.base import BaseSTTAdapter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

def numpy_to_wav_bytes(audio_data: np.ndarray, sample_rate=16000) -> io.BytesIO:
    """Converts 16kHz float32 numpy array into an in-memory WAV file buffer."""
    pcm_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data.tobytes())
    
    wav_io.seek(0)
    wav_io.name = "audio.wav"
    return wav_io

class GroqSTTAdapter(BaseSTTAdapter):
    """
    STT Adapter for Groq Cloud API (Whisper Large V3).
    """
    def __init__(self, model_name: str = "whisper-large-v3"):
        self.model_name = model_name
        self.client: Optional[Groq] = None
        self._lock = threading.Lock()
        self._is_loading = False
        self._is_ready = False
        self._status = "GROQ CLOUD API"

    def get_name(self) -> str:
        return f"Groq Cloud ({self.model_name})"

    def get_status(self) -> str:
        return self._status

    def is_ready(self) -> bool:
        return self._is_ready

    def get_api_key(self) -> str:
        load_dotenv(ENV_PATH, override=True)
        return os.getenv("GROQ_API_KEY", "").strip()

    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        def _worker():
            with self._lock:
                if self._is_loading:
                    return
                self._is_loading = True

            api_key = self.get_api_key()
            if not api_key or api_key == "gsk_your_groq_api_key_here":
                logger.warning("[GroqSTTAdapter] GROQ_API_KEY is not set in .env file!")
                self._is_ready = False
                self._status = "NO GROQ KEY IN .ENV"
            else:
                try:
                    self.client = Groq(api_key=api_key)
                    self._is_ready = True
                    self._status = "GROQ API READY"
                    logger.info(f"[GroqSTTAdapter] Initialized Groq client with model '{self.model_name}'")
                except Exception as e:
                    logger.error(f"[GroqSTTAdapter] Error initializing Groq client: {e}", exc_info=True)
                    self._is_ready = False
                    self._status = "GROQ CLIENT ERR"

            self._is_loading = False
            if on_complete:
                on_complete(self._is_ready)

        threading.Thread(target=_worker, daemon=True).start()

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "ru") -> str:
        api_key = self.get_api_key()
        if not api_key or api_key == "gsk_your_groq_api_key_here":
            logger.error("[GroqSTTAdapter] Error: GROQ_API_KEY missing from .env!")
            return "ERR: GROQ_KEY_MISSING"

        if self.client is None:
            try:
                self.client = Groq(api_key=api_key)
                self._is_ready = True
            except Exception as e:
                logger.error(f"[GroqSTTAdapter] Failed to create Groq client: {e}", exc_info=True)
                return f"ERR: GROQ_INIT_FAILED ({e})"

        if audio_data is None or len(audio_data) < sample_rate * 0.1:
            return ""

        try:
            t0 = time.time()
            wav_file = numpy_to_wav_bytes(audio_data, sample_rate=sample_rate)

            logger.info(f"[GroqSTTAdapter] Sending audio ({len(audio_data)/sample_rate:.2f}s) to Groq ({self.model_name})...")

            kwargs = {
                "file": ("speech.wav", wav_file.read()),
                "model": self.model_name,
                "response_format": "text",
                "temperature": 0.0
            }
            if language and language != "auto":
                kwargs["language"] = language

            response = self.client.audio.transcriptions.create(**kwargs)
            text = str(response).strip() if response else ""
            dt = time.time() - t0
            logger.info(f"[GroqSTTAdapter] Transcribed in {dt:.3f}s: '{text}'")
            return text
        except Exception as e:
            logger.error(f"[GroqSTTAdapter] Groq API transcription error: {e}", exc_info=True)
            err_msg = str(e)
            if "api_key" in err_msg.lower() or "401" in err_msg:
                return "ERR: GROQ_401_UNAUTHORIZED"
            return f"ERR: GROQ_API_ERROR ({err_msg})"

    def unload(self) -> None:
        self.client = None
        self._is_ready = False
