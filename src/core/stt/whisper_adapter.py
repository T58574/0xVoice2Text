import os
import time
import threading
from typing import Callable, Optional
import numpy as np

from src.core.logger import logger
from src.core.stt.base import BaseSTTAdapter

# Known HF/CTranslate2 model mappings
MODEL_MAP = {
    "large-v3-turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
    "turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
    "whisper-large-v3-turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "whisper-large-v3": "Systran/faster-whisper-large-v3"
}

HF_FALLBACK_MAP = {
    "large-v3-turbo": "openai/whisper-large-v3-turbo",
    "turbo": "openai/whisper-large-v3-turbo",
    "whisper-large-v3-turbo": "openai/whisper-large-v3-turbo",
    "large-v3": "openai/whisper-large-v3",
    "large": "openai/whisper-large-v3",
    "whisper-large-v3": "openai/whisper-large-v3"
}

class WhisperSTTAdapter(BaseSTTAdapter):
    """
    Unified High-Performance STT Adapter for OpenAI Whisper (Large-v3 and Large-v3-Turbo).
    Powered by faster-whisper (CTranslate2) with optimized INT8/AVX2 multi-threading
    and automatic HuggingFace Transformers fallback.
    """
    def __init__(
        self,
        model_name: str = "large-v3-turbo",
        device: str = "auto",
        compute_type: str = "auto",
        language: str = "ru",
        beam_size: int = 1
    ):
        self.raw_model_name = model_name or "large-v3-turbo"
        self.model_alias = self._resolve_alias(self.raw_model_name)
        self.ct2_model_repo = MODEL_MAP.get(self.model_alias, self.raw_model_name)
        self.hf_model_repo = HF_FALLBACK_MAP.get(self.model_alias, "openai/whisper-large-v3-turbo")

        self.device_preference = device
        self.compute_type_preference = compute_type
        self.language = language
        self.beam_size = beam_size

        self.model = None
        self.backend = None  # "faster-whisper" or "transformers"
        self.resolved_device = "cpu"
        self.resolved_compute_type = "int8"
        self.device_name_str = "Uninitialized"

        self._lock = threading.Lock()
        self._is_loading = False
        self._is_ready = False
        self._status = f"WHISPER [{self.model_alias.upper()}]"

    def _resolve_alias(self, name: str) -> str:
        low = name.lower().strip()
        if "turbo" in low:
            return "large-v3-turbo"
        elif "large-v3" in low or "large" in low:
            return "large-v3"
        return low

    def get_name(self) -> str:
        return f"Whisper ({self.model_alias}) [{self.device_name_str}]"

    def get_status(self) -> str:
        return self._status

    def is_ready(self) -> bool:
        return self._is_ready

    def _resolve_compute_device(self):
        """Resolves optimal execution target and compute precision."""
        pref_device = (self.device_preference or "auto").lower()

        # Check CUDA
        cuda_available = False
        try:
            import torch
            cuda_available = torch.cuda.is_available()
        except ImportError:
            pass

        if pref_device in ("auto", "cuda") and cuda_available:
            import torch
            dev_name = torch.cuda.get_device_name(0)
            self.resolved_device = "cuda"
            self.resolved_compute_type = "float16" if self.compute_type_preference in ("auto", "default", None) else self.compute_type_preference
            self.device_name_str = f"CUDA ({dev_name}, {self.resolved_compute_type})"
            return

        # CPU Execution Optimized for high core-count CPUs (e.g. Intel Core i7-14700KF)
        cpu_cores = os.cpu_count() or 8
        optimal_threads = min(cpu_cores, 16)
        self.resolved_device = "cpu"
        if self.compute_type_preference in ("auto", "default", None):
            self.resolved_compute_type = "int8"
        else:
            self.resolved_compute_type = self.compute_type_preference

        self.device_name_str = f"CPU ({optimal_threads}T, {self.resolved_compute_type})"

    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        def _worker():
            with self._lock:
                if self._is_loading:
                    return
                self._is_loading = True

            self._status = f"LOADING WHISPER ({self.model_alias})..."
            logger.info(f"[WhisperSTTAdapter] Loading Whisper '{self.model_alias}' (repo: {self.ct2_model_repo})...")
            t0 = time.time()

            # 1. Primary Engine: faster-whisper (CTranslate2)
            try:
                from faster_whisper import WhisperModel

                self._resolve_compute_device()
                cpu_cores = os.cpu_count() or 8
                cpu_threads = min(cpu_cores, 16) if self.resolved_device == "cpu" else 4

                logger.info(
                    f"[WhisperSTTAdapter] Initializing faster-whisper: model='{self.ct2_model_repo}', "
                    f"device={self.resolved_device}, compute_type={self.resolved_compute_type}, threads={cpu_threads}..."
                )

                self.model = WhisperModel(
                    self.ct2_model_repo,
                    device=self.resolved_device,
                    compute_type=self.resolved_compute_type,
                    cpu_threads=cpu_threads,
                    download_root=None
                )
                self.backend = "faster-whisper"
                self._is_ready = True
                load_time = time.time() - t0
                self._status = f"READY [{self.model_alias}/{self.resolved_compute_type}]"
                logger.info(f"[WhisperSTTAdapter] faster-whisper loaded in {load_time:.2f}s ({self.device_name_str})")

            except Exception as e_fw:
                logger.warning(
                    f"[WhisperSTTAdapter] faster-whisper failed: {e_fw}. "
                    f"Falling back to HuggingFace Transformers pipeline ({self.hf_model_repo})..."
                )

                # 2. Fallback: HuggingFace Transformers
                try:
                    import torch
                    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

                    torch_dtype = torch.float16 if (torch.cuda.is_available() and self.resolved_device == "cuda") else torch.float32
                    device_str = "cuda:0" if (torch.cuda.is_available() and self.resolved_device == "cuda") else "cpu"

                    logger.info(f"[WhisperSTTAdapter] Loading HF model '{self.hf_model_repo}' on {device_str}...")
                    model = AutoModelForSpeechSeq2Seq.from_pretrained(
                        self.hf_model_repo,
                        torch_dtype=torch_dtype,
                        low_cpu_mem_usage=True
                    ).to(device_str)
                    processor = AutoProcessor.from_pretrained(self.hf_model_repo)

                    self.model = pipeline(
                        "automatic-speech-recognition",
                        model=model,
                        tokenizer=processor.tokenizer,
                        feature_extractor=processor.feature_extractor,
                        torch_dtype=torch_dtype,
                        device=device_str,
                        return_timestamps=False
                    )
                    self.backend = "transformers"
                    self.device_name_str = f"HF ({device_str})"
                    self._is_ready = True
                    load_time = time.time() - t0
                    self._status = f"READY [HF/{self.model_alias}]"
                    logger.info(f"[WhisperSTTAdapter] HuggingFace Transformers fallback loaded in {load_time:.2f}s")
                except Exception as e_hf:
                    logger.error(f"[WhisperSTTAdapter] All backends failed to load Whisper '{self.model_alias}': {e_hf}", exc_info=True)
                    self._is_ready = False
                    self._status = "WHISPER LOAD ERROR"

            self._is_loading = False
            if on_complete:
                on_complete(self._is_ready)

        threading.Thread(target=_worker, daemon=True).start()

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "ru") -> str:
        if not self._is_ready or self.model is None:
            return "ERR: WHISPER_NOT_READY"

        if audio_data is None or len(audio_data) < sample_rate * 0.1:
            return ""

        try:
            t0 = time.time()

            # Ensure 1D float32 normalized [-1.0, 1.0]
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            target_lang = (language or self.language or "ru").strip().lower()
            if target_lang in ("auto", ""):
                target_lang = None

            logger.info(
                f"[WhisperSTTAdapter] Transcribing {len(audio_data)/sample_rate:.2f}s audio "
                f"(lang={target_lang}, model={self.model_alias}, backend={self.backend})..."
            )

            if self.backend == "faster-whisper":
                # For turbo: beam_size=1 gives maximum throughput (<300ms) with near-identical quality
                beam = 1 if "turbo" in self.model_alias else max(self.beam_size, 1)

                segments, info = self.model.transcribe(
                    audio_data,
                    language=target_lang,
                    beam_size=beam,
                    best_of=1,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    vad_filter=False  # Handled upstream by 0xVoice2Text VAD
                )
                text = " ".join([seg.text.strip() for seg in segments]).strip()
            else:
                generate_kwargs = {"task": "transcribe"}
                if target_lang:
                    generate_kwargs["language"] = target_lang
                result = self.model(
                    {"raw": audio_data, "sampling_rate": sample_rate},
                    generate_kwargs=generate_kwargs
                )
                text = result.get("text", "").strip()

            dt = time.time() - t0
            logger.info(f"[WhisperSTTAdapter] Transcribed in {dt:.3f}s: '{text}'")
            return text

        except Exception as e:
            logger.error(f"[WhisperSTTAdapter] Transcription error: {e}", exc_info=True)
            return f"ERR: WHISPER_INFERENCE_ERROR ({e})"

    def unload(self) -> None:
        with self._lock:
            self._is_ready = False
            self.model = None
            self.backend = None
            try:
                import gc
                gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            self._status = "UNLOADED"
            logger.info(f"[WhisperSTTAdapter] Model '{self.model_alias}' unloaded.")
