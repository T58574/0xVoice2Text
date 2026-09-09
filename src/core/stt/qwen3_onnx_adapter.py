import os
import time
import threading
from typing import Callable, Optional
import numpy as np
import onnxruntime as ort
import librosa
from tokenizers import Tokenizer
from huggingface_hub import snapshot_download

from src.core.logger import logger
from src.core.stt.base import BaseSTTAdapter

DEFAULT_HF_REPO = "andrewleech/qwen3-asr-1.7b-onnx"

SUPPORTED_LANGUAGES = [
    "Chinese", "English", "Cantonese", "Arabic", "German", "French", "Spanish",
    "Portuguese", "Indonesian", "Italian", "Korean", "Russian", "Thai", "Vietnamese",
    "Japanese", "Turkish", "Hindi", "Malay", "Dutch", "Swedish", "Danish", "Finnish",
    "Polish", "Czech", "Filipino", "Persian", "Greek", "Romanian", "Hungarian", "Macedonian"
]

LANGUAGE_MAP = {
    "ru": "Russian",
    "rus": "Russian",
    "russian": "Russian",
    "русский": "Russian",
    "en": "English",
    "eng": "English",
    "english": "English",
    "zh": "Chinese",
    "chi": "Chinese",
    "chinese": "Chinese",
    "yue": "Cantonese",
    "cantonese": "Cantonese",
    "de": "German",
    "german": "German",
    "fr": "French",
    "french": "French",
    "es": "Spanish",
    "spanish": "Spanish",
    "pt": "Portuguese",
    "portuguese": "Portuguese",
    "id": "Indonesian",
    "indonesian": "Indonesian",
    "it": "Italian",
    "italian": "Italian",
    "ko": "Korean",
    "korean": "Korean",
    "ja": "Japanese",
    "japanese": "Japanese",
    "tr": "Turkish",
    "turkish": "Turkish",
    "pl": "Polish",
    "polish": "Polish",
    "uk": "Russian",
    "be": "Russian",
}

def resolve_qwen_language(lang_str: Optional[str]) -> Optional[str]:
    """
    Normalizes language codes (e.g. 'ru', 'russian', 'auto') to Qwen3-ASR canonical language names.
    Defaults to 'Russian' for Russian-first dictation.
    """
    if not lang_str:
        return "Russian"
    clean = str(lang_str).strip().lower()
    if clean in ("auto", "none", "", "detect"):
        return None
    if clean in LANGUAGE_MAP:
        return LANGUAGE_MAP[clean]
    cap = clean.capitalize()
    if cap in SUPPORTED_LANGUAGES:
        return cap
    return "Russian"

class Qwen3ONNXAdapter(BaseSTTAdapter):
    """
    High-Performance Local STT Adapter for Alibaba Qwen3-ASR (1.7B ONNX).
    Executes directly in 16 GB VRAM on AMD Radeon RX 7800 XT via DirectML (DirectX 12 Compute).
    Falls back gracefully to multi-threaded CPU if DirectML is unavailable.
    """
    def __init__(
        self,
        model_name: str = DEFAULT_HF_REPO,
        device: str = "auto",
        language: str = "ru",
        use_int4: bool = False
    ):
        self.model_name = model_name
        self.device_preference = device
        self.language = language
        self.use_int4 = use_int4

        self._lock = threading.Lock()
        self._is_loading = False
        self._is_ready = False
        self._status = "QWEN3-ONNX (UNINITIALIZED)"
        self.device_name_str = "Uninitialized"

        # ONNX Sessions & Model Assets
        self.enc_sess: Optional[ort.InferenceSession] = None
        self.dec_init_sess: Optional[ort.InferenceSession] = None
        self.dec_step_sess: Optional[ort.InferenceSession] = None
        self.tokenizer: Optional[Tokenizer] = None
        self.embed_matrix: Optional[np.ndarray] = None
        self.model_dir: Optional[str] = None

    def get_name(self) -> str:
        tag = "INT4" if self.use_int4 else "FP32"
        return f"Qwen3-ASR ONNX ({tag}) [{self.device_name_str}]"

    def get_status(self) -> str:
        return self._status

    def is_ready(self) -> bool:
        return self._is_ready

    def _resolve_providers(self) -> list[str]:
        pref = (self.device_preference or "auto").lower()
        available = ort.get_available_providers()
        
        providers = []
        if pref in ("auto", "directml") and "DmlExecutionProvider" in available:
            providers.append("DmlExecutionProvider")
            self.device_name_str = "DirectML (AMD Radeon RX 7800 XT / DX12)"
        elif pref in ("auto", "cuda") and "CUDAExecutionProvider" in available:
            providers.append("CUDAExecutionProvider")
            self.device_name_str = "CUDA GPU"
        
        # Always append CPUExecutionProvider as fallback
        providers.append("CPUExecutionProvider")
        if not self.device_name_str or self.device_name_str == "Uninitialized":
            self.device_name_str = "CPU (AVX2)"

        logger.info(f"[Qwen3ONNX] Resolved execution providers: {providers} ({self.device_name_str})")
        return providers

    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        def _worker():
            with self._lock:
                if self._is_loading:
                    return
                self._is_loading = True

            self._status = "LOADING QWEN3 ONNX..."
            logger.info(f"[Qwen3ONNX] Initializing ONNX model '{self.model_name}'...")
            t0 = time.time()

            try:
                # 1. Download or locate model snapshot (disable tqdm to prevent pythonw NoneType crash)
                os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
                os.environ["TQDM_DISABLE"] = "1"

                self.model_dir = snapshot_download(
                    repo_id=self.model_name,
                    allow_patterns=["*.onnx", "*.data", "*.json", "*.bin"],
                    tqdm_class=None
                )
                logger.info(f"[Qwen3ONNX] Model files located at: {self.model_dir}")

                # 2. Configure ONNX session options
                sess_opts = ort.SessionOptions()
                sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                sess_opts.enable_mem_pattern = True
                sess_opts.log_severity_level = 3  # Error only

                providers = self._resolve_providers()

                # 3. Choose FP32 vs INT4 variants
                init_onnx = "decoder_init.int4.onnx" if self.use_int4 else "decoder_init.onnx"
                step_onnx = "decoder_step.int4.onnx" if self.use_int4 else "decoder_step.onnx"
                enc_onnx = "encoder.int4.onnx" if (self.use_int4 and os.path.exists(os.path.join(self.model_dir, "encoder.int4.onnx"))) else "encoder.onnx"

                # 4. Load Inference Sessions
                self.enc_sess = ort.InferenceSession(
                    os.path.join(self.model_dir, enc_onnx),
                    sess_options=sess_opts,
                    providers=providers
                )
                self.dec_init_sess = ort.InferenceSession(
                    os.path.join(self.model_dir, init_onnx),
                    sess_options=sess_opts,
                    providers=providers
                )
                self.dec_step_sess = ort.InferenceSession(
                    os.path.join(self.model_dir, step_onnx),
                    sess_options=sess_opts,
                    providers=providers
                )

                # 5. Load Tokenizer & Embedding Matrix
                self.tokenizer = Tokenizer.from_file(os.path.join(self.model_dir, "tokenizer.json"))
                embed_bin_path = os.path.join(self.model_dir, "embed_tokens.bin")
                self.embed_matrix = np.frombuffer(open(embed_bin_path, "rb").read(), dtype=np.float16).reshape(151936, 2048)

                load_time = time.time() - t0
                self._is_ready = True
                self._status = f"READY [{self.device_name_str}]"
                logger.info(f"[Qwen3ONNX] Qwen3 ONNX loaded in {load_time:.2f}s on {self.device_name_str}")

            except Exception as e:
                logger.error(f"[Qwen3ONNX] Failed to load ONNX model: {e}", exc_info=True)
                self._is_ready = False
                self._status = "ONNX LOAD ERROR"

            self._is_loading = False
            if on_complete:
                on_complete(self._is_ready)

        threading.Thread(target=_worker, daemon=True).start()

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "ru") -> str:
        # If model is currently loading in background, wait up to 15 seconds for completion
        if not self._is_ready and self._is_loading:
            logger.info("[Qwen3ONNX] Transcribe called while model is loading, waiting up to 15s...")
            for _ in range(150):
                if self._is_ready:
                    break
                time.sleep(0.1)

        if not self._is_ready or self.enc_sess is None or self.dec_init_sess is None or self.dec_step_sess is None:
            return "ERR: QWEN3_ONNX_NOT_READY"

        if audio_data is None or len(audio_data) < sample_rate * 0.1:
            return ""

        try:
            t0 = time.time()

            # Ensure float32 mono array
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            # 1. Mel Spectrogram Extraction (128 mel bins, 16kHz, 160 hop)
            mel = librosa.feature.melspectrogram(
                y=audio_data,
                sr=sample_rate,
                n_fft=400,
                hop_length=160,
                n_mels=128,
                fmin=0,
                fmax=8000,
                power=2.0
            )
            # Log-mel normalization
            log_mel = np.log(np.maximum(mel, 1e-5)).astype(np.float32)
            log_mel = (log_mel + 4.0) / 4.0
            log_mel = log_mel.reshape(1, 128, -1)

            # 2. Audio Encoder (DirectML GPU)
            with self._lock:
                enc_out = self.enc_sess.run(None, {"mel": log_mel})
            audio_features = enc_out[0]  # [1, audio_len, 2048]
            audio_len = audio_features.shape[1]

            # 3. Prompt Construction & Decoder Init
            # Official Qwen3-ASR format:
            # <|im_start|>system\n<|im_end|>\n<|im_start|>user\n<|audio_start|>
            prefix = [151644, 8948, 198, 151645, 198, 151644, 872, 198, 151669]
            audio_offset = len(prefix)
            audio_pads = [151676] * audio_len
            # <|audio_end|><|im_end|>\n<|im_start|>assistant\n
            suffix = [151670, 151645, 198, 151644, 77091, 198]

            # Enforce target language (e.g. "Russian") according to official Qwen3-ASR specification
            target_lang = resolve_qwen_language(language or self.language)
            if target_lang:
                lang_prompt = f"language {target_lang}<asr_text>"
                lang_tokens = self.tokenizer.encode(lang_prompt).ids
                suffix = suffix + lang_tokens

            prompt_tokens = prefix + audio_pads + suffix

            input_ids = np.array([prompt_tokens], dtype=np.int64)
            pos_ids = np.arange(input_ids.shape[1], dtype=np.int64).reshape(1, -1)

            with self._lock:
                init_out = self.dec_init_sess.run(None, {
                    "input_ids": input_ids,
                    "position_ids": pos_ids,
                    "audio_features": audio_features,
                    "audio_offset": np.array([audio_offset], dtype=np.int64)
                })

            curr_keys = init_out[1]
            curr_vals = init_out[2]
            cur_token = int(np.argmax(init_out[0][0, -1, :]))

            # 4. Autoregressive Generation Loop (DirectML GPU)
            generated_token_ids = []
            eos_token_ids = {151643, 151645}
            max_tokens = 256

            with self._lock:
                for step in range(max_tokens):
                    if cur_token in eos_token_ids:
                        break
                    generated_token_ids.append(cur_token)

                    embed = self.embed_matrix[cur_token:cur_token+1].reshape(1, 1, 2048).astype(np.float32)
                    step_pos = np.array([[len(prompt_tokens) + step]], dtype=np.int64)

                    step_out = self.dec_step_sess.run(None, {
                        "input_embeds": embed,
                        "position_ids": step_pos,
                        "past_keys": curr_keys,
                        "past_values": curr_vals
                    })

                    cur_token = int(np.argmax(step_out[0][0, 0, :]))
                    curr_keys = step_out[1]
                    curr_vals = step_out[2]

            # 5. Decode Tokens and Clean ASR Metadata Tags
            raw_text = self.tokenizer.decode(generated_token_ids).strip()
            # If <asr_text> was generated in fallback auto mode, take following transcript
            if "<asr_text>" in raw_text:
                raw_text = raw_text.split("<asr_text>", 1)[1]

            # Strip any remaining language prefixes or control markers
            import re
            cleaned_text = re.sub(r'^(?:language\s+[a-zA-Z_]+|<asr_text>|\s)+', '', raw_text, flags=re.IGNORECASE)
            transcription = cleaned_text.replace('<|im_end|>', '').replace('<|endoftext|>', '').strip()
            
            dt = time.time() - t0
            logger.info(f"[Qwen3ONNX] Transcribed in {dt:.3f}s on {self.device_name_str}: '{transcription}'")
            return transcription

        except Exception as e:
            logger.error(f"[Qwen3ONNX] Transcription error: {e}", exc_info=True)
            return f"ERR: QWEN3_ONNX_INFERENCE_ERROR ({e})"

    def unload(self) -> None:
        """Flushes DirectML GPU memory and closes ONNX sessions."""
        with self._lock:
            self._is_ready = False
            self.enc_sess = None
            self.dec_init_sess = None
            self.dec_step_sess = None
            self.tokenizer = None
            self.embed_matrix = None
            try:
                import gc
                gc.collect()
            except Exception:
                pass
            self._status = "UNLOADED"
            logger.info("[Qwen3ONNX] Model unloaded and GPU sessions released.")
