import threading
from typing import Callable, Optional
import numpy as np

from src.core.logger import logger
from src.core.stt.base import BaseSTTAdapter
from src.core.stt.factory import STTFactory

class STTEngine:
    """
    Unified STT Engine Facade.
    Delegates transcription and model management to pluggable STT adapters (Qwen3-ASR, Groq, etc.).
    Thread-safe implementation with strict concurrency locks.
    """
    def __init__(
        self,
        engine_name: str = "qwen3",
        model_size: str = "Qwen/Qwen3-ASR-1.7B-hf",
        device: str = "auto",
        compute_type: str = "default",
        language: str = "ru",
        config = None
    ):
        self.config = config
        self.language = language if language != "auto" else "ru"
        self.device = device
        self.engine_name = engine_name

        if self.config:
            self.engine_name = self.config.get("stt_engine", self.engine_name)
            self.language = self.config.get("language", self.language)
            self.device = self.config.get("stt_device", self.device)

        self._lock = threading.Lock()
        self.adapter: Optional[BaseSTTAdapter] = None
        self._init_adapter()

    def _init_adapter(self):
        with self._lock:
            options = {
                "qwen_model": self.config.get("qwen_model", "Qwen/Qwen3-ASR-1.7B-hf") if self.config else "Qwen/Qwen3-ASR-1.7B-hf",
                "groq_model": self.config.get("groq_model", "whisper-large-v3") if self.config else "whisper-large-v3",
                "stt_device": self.device,
                "language": self.language
            }
            self.adapter = STTFactory.create_adapter(self.engine_name, options)

    @property
    def is_ready(self) -> bool:
        with self._lock:
            return self.adapter.is_ready() if self.adapter else False

    @property
    def is_loading(self) -> bool:
        return not self.is_ready

    @property
    def status_message(self) -> str:
        with self._lock:
            return self.adapter.get_status() if self.adapter else "NO ADAPTER"

    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        """Asynchronously loads the underlying STT adapter model."""
        with self._lock:
            if not self.adapter:
                self._init_adapter()
            curr_adapter = self.adapter

        logger.info(f"[STTEngine] Loading STT Adapter: {curr_adapter.get_name()}")
        curr_adapter.load_model(on_complete=on_complete)

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribes incoming audio array through the active adapter."""
        with self._lock:
            curr_adapter = self.adapter
            curr_lang = self.language

        if not curr_adapter:
            return "ERR: NO_ADAPTER"

        return curr_adapter.transcribe(audio_data, sample_rate=16000, language=curr_lang)

    def switch_engine(
        self,
        engine_name: str,
        options: Optional[dict] = None,
        on_complete: Optional[Callable[[bool], None]] = None
    ) -> None:
        """Hot-swaps the STT adapter at runtime in a thread-safe manner."""
        try:
            with self._lock:
                if self.adapter:
                    try:
                        self.adapter.unload()
                    except Exception as e:
                        logger.warning(f"[STTEngine] Error unloading previous adapter: {e}")

                self.engine_name = engine_name
                opts = options or {}
                if "language" in opts:
                    self.language = opts["language"]
                if "stt_device" in opts:
                    self.device = opts["stt_device"]

                self.adapter = STTFactory.create_adapter(engine_name, opts)
                curr_adapter = self.adapter

            logger.info(f"[STTEngine] Switched to adapter: {curr_adapter.get_name()}")
            curr_adapter.load_model(on_complete=on_complete)
        except Exception as e:
            logger.error(f"[STTEngine] Failed to switch engine to '{engine_name}': {e}")
            if on_complete:
                on_complete(False)

    def unload(self) -> None:
        """Unloads underlying adapter and frees model memory / VRAM."""
        with self._lock:
            if self.adapter:
                try:
                    self.adapter.unload()
                except Exception as e:
                    logger.warning(f"[STTEngine] Error unloading adapter: {e}")
