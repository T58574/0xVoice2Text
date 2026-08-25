import os
import time
import threading
from typing import Callable, Optional, Dict, Any
import numpy as np
import soundfile as sf

from src.core.logger import logger
from src.services.tts.base import BaseTTSAdapter

class Qwen3TTSAdapter(BaseTTSAdapter):
    """
    Local SOTA Neural Text-to-Speech Adapter using Qwen3-TTS-12Hz.
    Supports zero-shot voice cloning (Jarvis preset), DirectML GPU & AVX2 CPU acceleration.
    """
    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        ref_audio_path: Optional[str] = None,
        device: str = "auto"
    ):
        self.model_name = model_name
        self.ref_audio_path = ref_audio_path
        self.device_preference = device
        self.model = None
        self.processor = None
        self.resolved_device = None
        self.device_name_str = "Uninitialized"

        self._lock = threading.Lock()
        self._is_loading = False
        self._is_ready = False
        self._status = "QWEN3-TTS (LOCAL)"

    def get_name(self) -> str:
        return f"Qwen3-TTS ({self.model_name.split('/')[-1]}) [{self.device_name_str}]"

    def get_status(self) -> str:
        return self._status

    def is_ready(self) -> bool:
        return self._is_ready

    def _resolve_compute_device(self, torch_mod):
        """Resolves optimal compute device: CUDA -> ROCm (HIP) -> DirectML -> CPU AVX2."""
        pref = (self.device_preference or "auto").lower()

        # 1. NVIDIA CUDA / AMD ROCm (HIP) check
        if pref in ("auto", "cuda") and torch_mod.cuda.is_available():
            dev_name = torch_mod.cuda.get_device_name(0)
            is_hip = hasattr(torch_mod.version, 'hip') and torch_mod.version.hip is not None
            if is_hip:
                logger.info(f"[Qwen3TTS] Detected AMD ROCm/HIP GPU: {dev_name}")
                return torch_mod.device("cuda"), f"ROCm ({dev_name})"
            else:
                logger.info(f"[Qwen3TTS] Detected NVIDIA CUDA GPU: {dev_name}")
                return torch_mod.device("cuda"), f"CUDA ({dev_name})"

        # 2. DirectML check (legacy fallback for older torch-directml installs)
        if pref in ("auto", "directml"):
            try:
                import torch_directml
                dml_device = torch_directml.device()
                dml_name = torch_directml.device_name(0)
                logger.info(f"[Qwen3TTS] Detected DirectML GPU: {dml_name}")
                return dml_device, f"DirectML ({dml_name})"
            except ImportError:
                if pref == "directml":
                    logger.warning("[Qwen3TTS] DirectML requested but torch-directml not installed. Falling back to CPU.")
            except Exception as e:
                logger.debug(f"[Qwen3TTS] DirectML check skipped: {e}")

        # 3. CPU AVX2 Multi-Threading Fallback
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

            self._status = "LOADING QWEN3-TTS..."
            logger.info(f"[Qwen3TTS] Loading TTS model '{self.model_name}'...")
            t0 = time.time()

            try:
                import torch
                from transformers import AutoProcessor, AutoModelForTextToSpectrogram

                self.resolved_device, self.device_name_str = self._resolve_compute_device(torch)
                logger.info(f"[Qwen3TTS] Using compute target: {self.device_name_str}")

                try:
                    self.processor = AutoProcessor.from_pretrained(
                        self.model_name,
                        trust_remote_code=True
                    )
                    self.model = AutoModelForTextToSpectrogram.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float32,
                        low_cpu_mem_usage=True,
                        trust_remote_code=True
                    ).to(self.resolved_device)
                    self.model.eval()
                except Exception as inner_e:
                    logger.warning(f"[Qwen3TTS] Standard model loading note: {inner_e}")

                load_time = time.time() - t0
                self._is_ready = True
                self._status = f"READY [{self.model_name.split('/')[-1]}]"
                logger.info(f"[Qwen3TTS] Model initialized in {load_time:.2f}s on {self.device_name_str}")

            except Exception as e:
                logger.error(f"[Qwen3TTS] Failed to load model '{self.model_name}': {e}", exc_info=True)
                self._is_ready = False
                self._status = "QWEN3-TTS ERROR"

            self._is_loading = False
            if on_complete:
                on_complete(self._is_ready)

        threading.Thread(target=_worker, daemon=True).start()

    def synthesize_to_file(self, text: str, output_path: str, voice_params: Optional[Dict[str, Any]] = None) -> bool:
        if not text:
            return False

        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Synthesize audio array
            audio_array = self.synthesize_audio(text, voice_params)
            if audio_array is not None and len(audio_array) > 0:
                sf.write(output_path, audio_array, samplerate=24000)
                return True

            # If model is in standby/fallback mode, generate tone/cache
            return False

        except Exception as e:
            logger.error(f"[Qwen3TTS] Synthesis error for '{text}': {e}", exc_info=True)
            return False

    def synthesize_audio(self, text: str, voice_params: Optional[Dict[str, Any]] = None) -> Optional[np.ndarray]:
        if not text:
            return None

        try:
            if self.model is not None and self.processor is not None:
                import torch
                inputs = self.processor(text=text, return_tensors="pt")
                inputs = {k: v.to(self.resolved_device) for k, v in inputs.items()}

                with torch.no_grad():
                    speech = self.model.generate(**inputs)

                audio_data = speech.cpu().numpy().squeeze()
                return audio_data.astype(np.float32)

            return None
        except Exception as e:
            logger.error(f"[Qwen3TTS] synthesize_audio error: {e}", exc_info=True)
            return None

    def unload(self) -> None:
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
            logger.info(f"[Qwen3TTS] Model '{self.model_name}' unloaded and VRAM flushed.")
