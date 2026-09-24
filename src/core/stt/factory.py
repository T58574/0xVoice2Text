from typing import Optional, Dict, Any
from src.core.stt.base import BaseSTTAdapter
from src.core.stt.whisper_adapter import WhisperSTTAdapter
from src.core.logger import logger

class STTFactory:
    """
    Factory for instantiating and configuring OpenAI Whisper STT adapters.
    Supports Whisper Large-v3-Turbo and Whisper Large-v3.
    """

    @staticmethod
    def create_adapter(engine_name: str = "whisper", options: Optional[Dict[str, Any]] = None) -> BaseSTTAdapter:
        opts = options or {}
        engine = (engine_name or "whisper").lower().strip()

        # Model resolution (large-v3-turbo or large-v3)
        model_name = opts.get("whisper_model") or opts.get("model_size") or "large-v3-turbo"
        if "turbo" in engine:
            model_name = "large-v3-turbo"
        elif "large-v3" in engine and "turbo" not in engine:
            model_name = "large-v3"

        device = opts.get("stt_device", "auto")
        compute_type = opts.get("compute_type", "auto")
        language = opts.get("language", "ru")
        beam_size = int(opts.get("beam_size", 1 if "turbo" in str(model_name).lower() else 3))

        logger.info(
            f"[STTFactory] Instantiating WhisperSTTAdapter: model={model_name}, "
            f"device={device}, compute_type={compute_type}, beam_size={beam_size}, language={language}"
        )

        return WhisperSTTAdapter(
            model_name=model_name,
            device=device,
            compute_type=compute_type,
            language=language,
            beam_size=beam_size
        )
