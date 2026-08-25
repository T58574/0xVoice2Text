import os
import time
import threading
from typing import Callable, Optional
import numpy as np

from src.core.logger import logger
from src.core.stt.base import BaseSTTAdapter

class Qwen3ASRAdapter(BaseSTTAdapter):
    """
    Local SOTA STT Adapter for Alibaba Qwen3-ASR (1.7B / 0.6B).
    Supports DirectML / CUDA GPU acceleration with high-throughput CPU AVX2 multi-threading.
    """
    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-ASR-1.7B-hf",
        device: str = "auto",
        language: str = "ru"
    ):
        self.model_name = model_name
        self.device_preference = device
        self.language = language
        self.model = None
        self.processor = None
        self.resolved_device = None
        self.device_name_str = "Uninitialized"

        self._lock = threading.Lock()
        self._is_loading = False
        self._is_ready = False
        self._status = "QWEN3-ASR (LOCAL)"

    def get_name(self) -> str:
        return f"Qwen3-ASR ({self.model_name.split('/')[-1]}) [{self.device_name_str}]"

    def get_status(self) -> str:
        return self._status

    def is_ready(self) -> bool:
        return self._is_ready

    def _resolve_compute_device(self, torch_mod):
        """Resolves optimal compute device: CUDA -> ROCm (HIP) -> DirectML -> CPU AVX2."""
        pref = (self.device_preference or "auto").lower()

        # 1. NVIDIA CUDA check
        if pref in ("auto", "cuda") and torch_mod.cuda.is_available():
            dev_name = torch_mod.cuda.get_device_name(0)
            # ROCm/HIP also reports via torch.cuda on AMD GPUs
            is_hip = hasattr(torch_mod.version, 'hip') and torch_mod.version.hip is not None
            if is_hip:
                logger.info(f"[Qwen3ASR] Detected AMD ROCm/HIP GPU: {dev_name}")
                return torch_mod.device("cuda"), f"ROCm ({dev_name})"
            else:
                logger.info(f"[Qwen3ASR] Detected NVIDIA CUDA GPU: {dev_name}")
                return torch_mod.device("cuda"), f"CUDA ({dev_name})"

        # 2. DirectML check (legacy fallback for older torch-directml installs)
        if pref in ("auto", "directml"):
            try:
                import torch_directml
                dml_device = torch_directml.device()
                dml_name = torch_directml.device_name(0)
                logger.info(f"[Qwen3ASR] Detected DirectML GPU: {dml_name}")
                return dml_device, f"DirectML ({dml_name})"
            except ImportError:
                if pref == "directml":
                    logger.warning("[Qwen3ASR] DirectML requested but torch-directml not installed. Falling back to CPU.")
            except Exception as e:
                logger.debug(f"[Qwen3ASR] DirectML check skipped: {e}")

        # 3. CPU AVX2 Multi-Threading Fallback (Optimized for high core-count CPUs like i7-14700KF)
        cpu_cores = os.cpu_count() or 8
        optimal_threads = min(cpu_cores, 20)
        try:
            torch_mod.set_num_threads(optimal_threads)
        except Exception:
            pass

        return torch_mod.device("cpu"), f"CPU (AVX2, {optimal_threads}T)"

    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        def _worker():
            with self._lock:
                if self._is_loading:
                    return
                self._is_loading = True

            self._status = "LOADING QWEN3..."
            logger.info(f"[Qwen3ASR] Loading model '{self.model_name}'...")
            t0 = time.time()

            try:
                import torch
                from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

                self.resolved_device, self.device_name_str = self._resolve_compute_device(torch)
                logger.info(f"[Qwen3ASR] Using compute target: {self.device_name_str}")

                # Load processor & model
                self.processor = AutoProcessor.from_pretrained(
                    self.model_name,
                    trust_remote_code=True
                )

                # Use float32 on CPU / DirectML to avoid half-precision unsupported kernel issues
                torch_dtype = torch.float16 if str(self.resolved_device).startswith("cuda") else torch.float32

                self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                    self.model_name,
                    torch_dtype=torch_dtype,
                    low_cpu_mem_usage=True,
                    trust_remote_code=True
                ).to(self.resolved_device)

                self.model.eval()

                load_time = time.time() - t0
                self._is_ready = True
                self._status = f"READY [{self.model_name.split('/')[-1]}]"
                logger.info(f"[Qwen3ASR] Model loaded successfully in {load_time:.2f}s on {self.device_name_str}")

            except Exception as e:
                logger.error(f"[Qwen3ASR] Failed to load model '{self.model_name}': {e}", exc_info=True)
                self._is_ready = False
                self._status = "QWEN3 LOAD ERROR"

            self._is_loading = False
            if on_complete:
                on_complete(self._is_ready)

        threading.Thread(target=_worker, daemon=True).start()

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "ru") -> str:
        if not self._is_ready or self.model is None or self.processor is None:
            return "ERR: QWEN3_NOT_READY"

        if audio_data is None or len(audio_data) < sample_rate * 0.1:
            return ""

        try:
            import torch

            t0 = time.time()
            # Ensure float32 1D array
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            target_lang = language or self.language
            if target_lang == "auto":
                target_lang = "ru"

            logger.info(f"[Qwen3ASR] Processing audio ({len(audio_data)/sample_rate:.2f}s) with {self.model_name}...")

            # Preprocess audio with processor
            inputs = self.processor(
                audio_data,
                sampling_rate=sample_rate,
                return_tensors="pt"
            )

            # Move inputs to target device
            inputs = {k: v.to(self.resolved_device) for k, v in inputs.items()}

            with torch.no_grad():
                # Generate transcription IDs
                gen_kwargs = {
                    "max_new_tokens": 256,
                }
                if target_lang:
                    gen_kwargs["language"] = target_lang

                generated_ids = self.model.generate(**inputs, **gen_kwargs)

            # Decode tokens
            transcription = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0].strip()

            dt = time.time() - t0
            logger.info(f"[Qwen3ASR] Transcribed in {dt:.3f}s: '{transcription}'")
            return transcription

        except Exception as e:
            logger.error(f"[Qwen3ASR] Transcription error: {e}", exc_info=True)
            return f"ERR: QWEN3_INFERENCE_ERROR ({e})"

    def unload(self) -> None:
        """Cleans up memory allocations and frees GPU/RAM."""
        with self._lock:
            self._is_ready = False
            self.model = None
            self.processor = None
            try:
                import gc
                gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            self._status = "UNLOADED"
            logger.info(f"[Qwen3ASR] Model '{self.model_name}' unloaded and VRAM flushed.")
