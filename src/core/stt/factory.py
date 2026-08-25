from typing import Optional, Dict, Any
from src.core.stt.base import BaseSTTAdapter
from src.core.stt.groq_adapter import GroqSTTAdapter
from src.core.stt.qwen3_adapter import Qwen3ASRAdapter
from src.core.stt.qwen3_onnx_adapter import Qwen3ONNXAdapter
from src.core.logger import logger

class STTFactory:
    """
    Factory for instantiating and configuring STT engine adapters dynamically.
    Prioritizes GPU DirectML ONNX acceleration on AMD/NVIDIA GPUs.
    """

    @staticmethod
    def create_adapter(engine_name: str = "qwen3", options: Optional[Dict[str, Any]] = None) -> BaseSTTAdapter:
        opts = options or {}
        engine = (engine_name or "qwen3").lower().strip()

        # 1. Primary SOTA Local Engine: Qwen3-ASR ONNX (DirectML GPU / DirectX 12)
        if engine in ("qwen3", "qwen3_onnx", "onnx", "local"):
            model_name = opts.get("qwen_model", "andrewleech/qwen3-asr-1.7b-onnx")
            # If standard HF repo was in config, transparently route to ONNX repo for DirectML GPU execution
            if "onnx" not in model_name.lower():
                model_name = "andrewleech/qwen3-asr-1.7b-onnx"
            device = opts.get("stt_device", "auto")
            language = opts.get("language", "ru")
            use_int4 = bool(opts.get("use_int4", False))
            logger.info(f"[STTFactory] Creating Qwen3ONNXAdapter (DirectML GPU, model={model_name}, device={device})")
            return Qwen3ONNXAdapter(model_name=model_name, device=device, language=language, use_int4=use_int4)

        # 2. PyTorch Transformers Fallback
        elif engine in ("qwen3_hf", "qwen3_pytorch", "pytorch"):
            model_name = opts.get("qwen_model", "Qwen/Qwen3-ASR-1.7B-hf")
            device = opts.get("stt_device", "auto")
            language = opts.get("language", "ru")
            logger.info(f"[STTFactory] Creating Qwen3ASRAdapter (PyTorch, model={model_name}, device={device})")
            return Qwen3ASRAdapter(model_name=model_name, device=device, language=language)

        # 3. Cloud Groq API Fallback
        elif engine in ("groq", "groq_whisper", "cloud"):
            model_name = opts.get("groq_model", "whisper-large-v3")
            logger.info(f"[STTFactory] Creating GroqSTTAdapter (model={model_name})")
            return GroqSTTAdapter(model_name=model_name)

        else:
            logger.warning(f"[STTFactory] Unknown STT engine '{engine_name}', defaulting to Qwen3ONNXAdapter (DirectML)")
            return Qwen3ONNXAdapter(
                model_name="andrewleech/qwen3-asr-1.7b-onnx",
                device=opts.get("stt_device", "auto"),
                language=opts.get("language", "ru")
            )

