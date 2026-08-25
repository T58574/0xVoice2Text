from typing import Optional, Dict, Any
from src.services.tts.base import BaseTTSAdapter
from src.services.tts.edge_adapter import EdgeTTSAdapter
from src.services.tts.qwen3_tts_adapter import Qwen3TTSAdapter
from src.core.logger import logger

class TTSFactory:
    """
    Factory for instantiating and configuring TTS engine adapters dynamically.
    """

    @staticmethod
    def create_adapter(engine_name: str = "qwen3", options: Optional[Dict[str, Any]] = None) -> BaseTTSAdapter:
        opts = options or {}
        engine = (engine_name or "qwen3").lower().strip()

        if engine in ("qwen3", "qwen3_tts", "qwen", "local"):
            model_name = opts.get("qwen_tts_model", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
            ref_audio = opts.get("tts_ref_voice", None)
            device = opts.get("tts_device", "auto")
            logger.info(f"[TTSFactory] Creating Qwen3TTSAdapter (model={model_name}, device={device})")
            return Qwen3TTSAdapter(model_name=model_name, ref_audio_path=ref_audio, device=device)

        elif engine in ("edge", "edge_tts", "cloud"):
            voice = opts.get("tts_voice", "ru-RU-SvetlanaNeural")
            rate = opts.get("tts_rate", "+20%")
            pitch = opts.get("tts_pitch", "+0Hz")
            logger.info(f"[TTSFactory] Creating EdgeTTSAdapter (voice={voice}, rate={rate})")
            return EdgeTTSAdapter(voice=voice, rate=rate, pitch=pitch)

        else:
            logger.warning(f"[TTSFactory] Unknown TTS engine '{engine_name}', defaulting to Qwen3TTSAdapter")
            return Qwen3TTSAdapter(
                model_name=opts.get("qwen_tts_model", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
                device=opts.get("tts_device", "auto")
            )
