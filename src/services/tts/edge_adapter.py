import os
import asyncio
import threading
from typing import Callable, Optional
from src.core.logger import logger
from src.services.tts.base import BaseTTSAdapter

class EdgeTTSAdapter(BaseTTSAdapter):
    """
    Cloud-based Text-to-Speech Adapter using Microsoft Edge-TTS.
    """
    def __init__(self, voice: str = "ru-RU-SvetlanaNeural", rate: str = "+20%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self._is_ready = True
        self._status = "EDGE-TTS READY"

    def get_name(self) -> str:
        return f"Edge-TTS ({self.voice})"

    def get_status(self) -> str:
        return self._status

    def is_ready(self) -> bool:
        return self._is_ready

    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        self._is_ready = True
        if on_complete:
            on_complete(True)

    def synthesize_to_file(self, text: str, output_path: str, voice_params: Optional[dict] = None) -> bool:
        if not text:
            return False

        opts = voice_params or {}
        voice = opts.get("voice", self.voice)
        rate = opts.get("rate", self.rate)
        pitch = opts.get("pitch", self.pitch)

        try:
            import edge_tts
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            comm = edge_tts.Communicate(text, voice=voice, pitch=pitch, rate=rate)
            asyncio.run(comm.save(output_path))
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as e:
            logger.error(f"[EdgeTTSAdapter] Synthesis error: {e}", exc_info=True)
            return False
