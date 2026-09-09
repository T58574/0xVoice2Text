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

def check_microphone_available(device_id=None) -> tuple[bool, str, str]:
    """
    Validates whether the requested (or default) microphone device is available and operational.
    Returns: (is_available: bool, device_name: str, error_message: str)
    """
    try:
        devices = sd.query_devices()
        if not devices:
            return False, "None", "В системе не обнаружено аудиоустройств ввода (микрофонов)."

        target_idx = device_id
        if target_idx is None:
            def_in = sd.default.device[0]
            if def_in is None or def_in < 0:
                input_devs = [i for i, d in enumerate(devices) if d.get('max_input_channels', 0) > 0]
                if not input_devs:
                    return False, "None", "В системе не найдено доступных микрофонов."
                target_idx = input_devs[0]
            else:
                target_idx = def_in

        if isinstance(target_idx, int) and (target_idx < 0 or target_idx >= len(devices)):
            return False, f"Device #{target_idx}", f"Устройство с индексом #{target_idx} не найдено."

        dev_info = sd.query_devices(target_idx)
        if dev_info.get('max_input_channels', 0) <= 0:
            return False, str(dev_info.get('name', target_idx)), "Выбранное устройство не имеет каналов ввода звука."

        dev_name = dev_info.get('name', f"Device #{target_idx}")

        # Quick test opening input stream to ensure no exclusive lock or permission block
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', device=target_idx):
            pass

        return True, dev_name, "OK"
    except Exception as e:
        err_msg = str(e)
        return False, f"Device {device_id if device_id is not None else 'Default'}", err_msg

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
        self.last_error = None

    def check_availability(self) -> tuple[bool, str, str]:
        """Checks if the currently configured audio device is available."""
        return check_microphone_available(self.device_id)

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

    def start_recording(self) -> bool:
        with self._lock:
            if self.is_recording:
                return True
            self.is_recording = True
            self.audio_chunks = []
            self.current_rms = 0.0
            self.last_error = None

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
            print(f"[AudioRecorder] [OK] Started recording on device {device}")
            return True
        except Exception as e:
            err_msg = str(e)
            print(f"[AudioRecorder] [FAIL] Failed to start recording stream: {err_msg}")
            with self._lock:
                self.is_recording = False
                self.last_error = err_msg
            return False

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
