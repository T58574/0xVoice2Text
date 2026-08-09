import sounddevice as sd
import numpy as np
import threading
import time

SAMPLE_RATE = 16000

def get_input_devices():
    """Returns a list of input audio devices (microphones)."""
    devices = []
    try:
        dev_list = sd.query_devices()
        for idx, dev in enumerate(dev_list):
            if dev['max_input_channels'] > 0:
                devices.append({
                    "id": idx,
                    "name": dev['name'],
                    "channels": dev['max_input_channels'],
                    "default_samplerate": dev['default_samplerate']
                })
    except Exception as e:
        print(f"[AudioRecorder] Error listing input devices: {e}")
    return devices

class AudioRecorder:
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.sample_rate = SAMPLE_RATE
        self.is_recording = False
        self.audio_chunks = []
        self.stream = None
        self._lock = threading.Lock()
        self.current_rms = 0.0
        self.tts_speaking_checker = None

    def set_device(self, device_id):
        self.device_id = device_id

    def set_tts_speaking_checker(self, checker_func):
        self.tts_speaking_checker = checker_func

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[AudioRecorder] Callback status: {status}")
        if self.is_recording:
            # Discard mic audio frames while TTS is speaking to prevent self-echo loop
            if self.tts_speaking_checker and self.tts_speaking_checker():
                return

            # indata shape: (frames, channels)
            mono_data = indata[:, 0].copy()
            with self._lock:
                self.audio_chunks.append(mono_data)
                # Calculate current RMS for UI animation
                rms = float(np.sqrt(np.mean(mono_data ** 2))) if len(mono_data) > 0 else 0.0
                self.current_rms = rms

    def start_recording(self):
        with self._lock:
            if self.is_recording:
                return
            self.is_recording = True
            self.audio_chunks = []
            self.current_rms = 0.0

        try:
            device = self.device_id if self.device_id is not None else None
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                device=device,
                callback=self._audio_callback
            )
            self.stream.start()
            print(f"[AudioRecorder] Started recording on device {device}")
        except Exception as e:
            print(f"[AudioRecorder] Failed to start recording stream: {e}")
            self.is_recording = False

    def stop_recording(self):
        with self._lock:
            if not self.is_recording:
                return None
            self.is_recording = False

        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"[AudioRecorder] Error stopping stream: {e}")
            self.stream = None

        with self._lock:
            if not self.audio_chunks:
                return None
            audio_data = np.concatenate(self.audio_chunks, axis=0)
            self.audio_chunks = []
            self.current_rms = 0.0
            print(f"[AudioRecorder] Stopped recording. Recorded {len(audio_data)} samples ({len(audio_data)/self.sample_rate:.2f}s)")
            return audio_data

    def get_rms(self):
        return self.current_rms
