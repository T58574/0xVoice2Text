import os
import urllib.request
import numpy as np
import onnxruntime as ort

import hashlib

MODEL_URL = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
MODEL_FILENAME = "silero_vad.onnx"
EXPECTED_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"


def verify_file_sha256(filepath: str, expected_hash: str) -> bool:
    if not os.path.exists(filepath):
        return False
    sha = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest().lower() == expected_hash.lower()
    except Exception:
        return False


class SileroVAD:
    """
    Neural Voice Activity Detection (VAD) using Silero VAD v5 via ONNX Runtime.
    Processes 16kHz audio in 512-sample (32ms) frames and outputs speech probability [0.0, 1.0].
    """
    def __init__(self, model_dir=None, sample_rate=16000, threshold=0.5):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.window_size = 512 if sample_rate == 16000 else 256
        
        if model_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_dir = os.path.join(base_dir, "data", "models")
        
        os.makedirs(model_dir, exist_ok=True)
        self.model_path = os.path.join(model_dir, MODEL_FILENAME)
        
        self.session = None
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._sr_tensor = np.array([self.sample_rate], dtype=np.int64)
        self._input_names = []
        self._output_names = []
        self._buffer = np.zeros(0, dtype=np.float32)

        self._ensure_model_and_load()

    def _ensure_model_and_load(self):
        if not os.path.exists(self.model_path) or not verify_file_sha256(self.model_path, EXPECTED_SHA256):
            print(f"[SileroVAD] Downloading / Verifying Silero VAD v5 ONNX model ({self.model_path})...")
            try:
                urllib.request.urlretrieve(MODEL_URL, self.model_path)
                print(f"[SileroVAD] Download complete ({os.path.getsize(self.model_path)} bytes).")
            except Exception as e:
                print(f"[SileroVAD] [WARN] Failed to download from GitHub: {e}. Trying fallback mirror...")
                fallback_url = "https://huggingface.co/onnx-community/silero-vad/resolve/main/silero_vad.onnx"
                try:
                    urllib.request.urlretrieve(fallback_url, self.model_path)
                    print(f"[SileroVAD] Fallback download complete ({os.path.getsize(self.model_path)} bytes).")
                except Exception as ex:
                    print(f"[SileroVAD] [CRIT] Failed to download Silero VAD ONNX model: {ex}")
                    return

            if not verify_file_sha256(self.model_path, EXPECTED_SHA256):
                print(f"[SileroVAD] [CRIT] Model SHA256 checksum mismatch! Potential file corruption or tampered model.")
                return

        try:
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            opts.log_severity_level = 3  # Error only
            self.session = ort.InferenceSession(self.model_path, sess_options=opts, providers=["CPUExecutionProvider"])
            self._input_names = [inp.name for inp in self.session.get_inputs()]
            self._output_names = [out.name for out in self.session.get_outputs()]
            self.reset_state()
            print(f"[SileroVAD] Verified & loaded model: inputs={self._input_names}, outputs={self._output_names}")
        except Exception as e:
            print(f"[SileroVAD] [CRIT] Error initializing ONNX session: {e}")
            self.session = None

    def reset_state(self):
        """Reset internal recurrent neural network states."""
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._buffer = np.zeros(0, dtype=np.float32)

    def process_frame(self, frame_512: np.ndarray) -> float:
        """
        Process exactly 512 samples (32ms at 16kHz) of float32 audio [-1.0, 1.0].
        Returns speech probability [0.0, 1.0].
        """
        if self.session is None:
            return 0.0

        if frame_512.ndim == 1:
            input_tensor = frame_512.reshape(1, -1).astype(np.float32)
        else:
            input_tensor = frame_512.astype(np.float32)

        inputs = {}
        if "input" in self._input_names:
            inputs["input"] = input_tensor
        elif "x" in self._input_names:
            inputs["x"] = input_tensor
        else:
            inputs[self._input_names[0]] = input_tensor

        if "state" in self._input_names:
            inputs["state"] = self._state

        if "sr" in self._input_names:
            inputs["sr"] = self._sr_tensor

        try:
            outputs = self.session.run(None, inputs)
            prob = float(outputs[0].squeeze())
            if len(outputs) > 1 and outputs[1] is not None:
                self._state = outputs[1]
            return max(0.0, min(1.0, prob))
        except Exception as e:
            print(f"[SileroVAD] Inference error: {e}")
            return 0.0

    def process_chunk(self, audio_chunk: np.ndarray) -> tuple[float, bool]:
        """
        Processes an arbitrary-length audio chunk.
        Accumulates in internal buffer and steps through in 512-sample windows.
        Returns (max_speech_prob, is_speech).
        """
        if self.session is None or audio_chunk is None or len(audio_chunk) == 0:
            return 0.0, False

        self._buffer = np.concatenate((self._buffer, audio_chunk.astype(np.float32)))
        max_prob = 0.0

        while len(self._buffer) >= self.window_size:
            frame = self._buffer[:self.window_size]
            self._buffer = self._buffer[self.window_size:]
            prob = self.process_frame(frame)
            if prob > max_prob:
                max_prob = prob

        is_speech = max_prob >= self.threshold
        return max_prob, is_speech
