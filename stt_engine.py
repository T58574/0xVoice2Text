import os
import io
import wave
import threading
import numpy as np
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH)

def numpy_to_wav_bytes(audio_data: np.ndarray, sample_rate=16000) -> io.BytesIO:
    """Converts 16kHz float32 numpy array into an in-memory WAV file buffer."""
    pcm_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data.tobytes())
    
    wav_io.seek(0)
    wav_io.name = "audio.wav"
    return wav_io

class STTEngine:
    def __init__(self, model_size="whisper-large-v3", device="cloud", compute_type="default", language="ru"):
        self.model_name = "whisper-large-v3" # User specifically requested non-turbo whisper-large-v3
        self.language = language if language != "auto" else None
        
        self.client = None
        self._lock = threading.Lock()
        self.is_loading = False
        self.is_ready = False
        self.status_message = "GROQ CLOUD API"

    def get_api_key(self):
        # Reload dotenv in case user edited .env while app was running
        load_dotenv(ENV_PATH, override=True)
        key = os.getenv("GROQ_API_KEY", "").strip()
        return key

    def load_model(self, on_complete=None):
        """Initializes Groq Cloud API client."""
        def _worker():
            with self._lock:
                if self.is_loading:
                    return
                self.is_loading = True

            api_key = self.get_api_key()
            if not api_key or api_key == "gsk_your_groq_api_key_here":
                print("[STTEngine] Warning: GROQ_API_KEY is not set in .env file!")
                self.is_ready = False
                self.status_message = "NO GROQ KEY IN .ENV"
            else:
                try:
                    self.client = Groq(api_key=api_key)
                    self.is_ready = True
                    self.status_message = "GROQ API READY"
                    print("[STTEngine] Groq API client initialized successfully with 'whisper-large-v3'!")
                except Exception as e:
                    print(f"[STTEngine] Error initializing Groq client: {e}")
                    self.is_ready = False
                    self.status_message = "GROQ CLIENT ERR"

            self.is_loading = False
            if on_complete:
                on_complete(self.is_ready)

        thread = threading.Thread(target=_worker, daemon=True).start()

    def transcribe(self, audio_data: np.ndarray):
        """
        Sends audio buffer to Groq Cloud API for ultra-fast Whisper Large V3 transcription.
        """
        api_key = self.get_api_key()
        if not api_key or api_key == "gsk_your_groq_api_key_here":
            print("[STTEngine] Error: GROQ_API_KEY missing from .env!")
            return "ERROR: Add GROQ_API_KEY to .env file!"

        if self.client is None:
            try:
                self.client = Groq(api_key=api_key)
                self.is_ready = True
            except Exception as e:
                print(f"[STTEngine] Failed to create Groq client: {e}")
                return ""

        if audio_data is None or len(audio_data) < 1600:
            return ""

        try:
            import time
            t0 = time.time()
            wav_file = numpy_to_wav_bytes(audio_data, sample_rate=16000)

            print(f"[STTEngine] Sending audio ({len(audio_data)/16000:.2f}s) to Groq Cloud API (whisper-large-v3)...")

            kwargs = {
                "file": ("speech.wav", wav_file.read()),
                "model": self.model_name,
                "response_format": "text",
                "temperature": 0.0
            }
            if self.language:
                kwargs["language"] = self.language

            response = self.client.audio.transcriptions.create(**kwargs)

            # Response is string if response_format="text"
            text = str(response).strip() if response else ""
            dt = time.time() - t0
            print(f"[STTEngine] [Groq Cloud] Transcribed in {dt:.3f}s: '{text}'")
            return text
        except Exception as e:
            print(f"[STTEngine] Groq API transcription error: {e}")
            err_msg = str(e)
            if "api_key" in err_msg.lower() or "401" in err_msg:
                return "ERR: Invalid GROQ_API_KEY in .env"
            return ""

    def change_model(self, model_size="whisper-large-v3", language="ru", device="cloud", on_complete=None):
        self.language = language if language != "auto" else None
        self.load_model(on_complete=on_complete)
