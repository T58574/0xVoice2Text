# GEMINI.md: 0xVoice2Text Core Architecture & Session State

> **Protocol:** J.A.R.V.I.S. Standard (Concise, technical, ASCII status markers: `[+]`, `[-]`, `[*]`, `[!]`, `[OK]`, `[FAIL]`, `[CRIT]`, `[WARN]`, `[SYS]`, `[STT]`, `[TTS]`, `[VAD]`, `[AI]`, `[CMD]`).

---

## 1. Hardware Profile & Compute Targets
- **GPU:** AMD Radeon RX 7800 XT (16 GB VRAM, RDNA 3, DirectX 12 / DirectML).
- **CPU:** Intel Core i7-14700KF (20 Cores / 28 Threads, AVX2).
- **OS:** Windows 11.
- **Python:** 3.14.6 in `.\venv\`.
- **Primary STT Engine:** `onnxruntime-directml` with `DmlExecutionProvider` (DirectX 12 GPU acceleration in 16 GB VRAM).

---

## 2. System Pipeline Architecture

```
[Audio Input: sounddevice (16kHz 16-bit Mono)]
     │
     ▼
[VAD: Silero VAD v5 ONNX (src/core/vad_engine.py)] ──(Silence / Below Threshold)──► [Drop / Auto-Stop]
     │ (Speech Detected)
     ▼
[KWS: Wake Word Manager (Vosk)] ──► Voice Trigger: "джарвис" / Stop: "стоп"
     │ (Triggered or Hotkey Ctrl+Space)
     ▼
[Audio Recorder: Ring Buffer] ──► Ingestion & RMS meter for UI Widget
     │ (Recording Completed)
     ▼
[STT Facade: STTEngine (src/core/stt/)]
     ├── [Adapter 1] Qwen3ONNXAdapter (andrewleech/qwen3-asr-1.7b-onnx) [DirectML GPU / AVX2]
     └── [Adapter 2] GroqSTTAdapter (whisper-large-v3) [Cloud Fallback]
     │
     ▼
[AI Post-Processing: AIEngine (Optional)] ──► Direct / Clean (Gemma) / Smart (Gemini)
     │
     ▼
[Text Injector / Macro Manager] ──► Auto-paste into focused window / App launcher
     │
     ▼
[TTS Facade: JarvisVoiceService (src/services/tts/)]
     ├── [Adapter 1] Qwen3TTSAdapter (Qwen/Qwen3-TTS-12Hz-0.6B / 1.7B) [Zero-Shot Cloning]
     └── [Adapter 2] EdgeTTSAdapter (ru-RU-SvetlanaNeural / ru-RU-DmitryNeural) [Cloud]
```

---

## 3. Directory Layout & Key Modules

```
0xVoice2Text/
├── main.py                     # Master Application Controller, Qt Event Loop & Bridge
├── run.bat                     # Robust One-Click Launcher (venv auto-detect, pythonw / debug)
├── requirements.txt            # Python Dependencies (onnxruntime-directml, PyQt6, Vosk, etc.)
├── .env.example                # API Credentials template (Groq, Gemini)
├── GEMINI.md                   # Core Architecture & Engineering Blueprint
├── README.md                   # Project Documentation, Features & Guides
├── src/
│   ├── config.py               # AppConfig (JSON-backed dynamic configuration)
│   ├── core/
│   │   ├── stt/                # Pluggable STT Subsystem
│   │   │   ├── base.py         # BaseSTTAdapter ABC
│   │   │   ├── factory.py      # STTFactory (dynamic adapter loader)
│   │   │   ├── qwen3_onnx_adapter.py # Qwen3-ASR ONNX DirectML/AVX2 adapter
│   │   │   ├── groq_adapter.py # Groq Cloud Whisper Large V3 adapter
│   │   │   └── __init__.py     # STT package exports
│   │   ├── stt_engine.py       # STTEngine unified facade (thread-safe, lock-guarded)
│   │   ├── vad_engine.py       # Silero VAD v5 ONNX Engine
│   │   ├── audio_recorder.py   # sounddevice recording worker & RMS level provider
│   │   ├── wake_word.py        # Vosk Wake Word & Silero VAD session manager
│   │   ├── ai_engine.py        # Gemini Flash / Gemma text post-processor
│   │   ├── history.py          # SQLite / JSON history manager
│   │   ├── ipc_bus.py          # Local IPC event broadcasting (~/.0xvoice2text)
│   │   └── logger.py           # Centralized rotating file & stream logger
│   ├── services/
│   │   ├── tts/                # Pluggable TTS Subsystem
│   │   │   ├── base.py         # BaseTTSAdapter ABC
│   │   │   ├── factory.py      # TTSFactory (dynamic adapter loader)
│   │   │   ├── qwen3_tts_adapter.py # Qwen3-TTS-12Hz neural adapter
│   │   │   ├── edge_adapter.py # Edge-TTS cloud adapter
│   │   │   ├── service.py      # JarvisVoiceService (caching, MCI, anti-echo)
│   │   │   └── __init__.py     # TTS package exports
│   │   ├── hotkeys.py          # Global hotkey listener (pynput, Toggle/PTT)
│   │   ├── injector.py         # pywin32 / pyperclip text injection
│   │   └── macros.py           # Voice command and macro execution
│   └── ui/
│       ├── widget.py           # Cyberpunk desktop floating widget with RMS visualizer
│       ├── settings.py         # Tabbed configuration modal (STT, TTS, VAD, AI, Hotkeys)
│       ├── history.py          # Transcription history drawer window
│       ├── mouse_hud.py        # Cursor holographic HUD overlay ring
│       ├── error_dialog.py     # System error dialog with resolution hints
│       └── tray.py             # System tray icon and context menu
├── tests/
├── test_full_system.py         # End-to-End full system & pipeline validation
├── test_stt_adapter.py         # STT adapter unit and architecture verification
├── test_tts_adapter.py         # TTS adapter unit and echo detection verification
└── tests_audit.py              # Full architecture and code audit suite
```

---

## 4. Configuration Reference (`data/config.json`)

| Key | Default Value | Options / Description |
| :--- | :--- | :--- |
| `stt_engine` | `"qwen3"` | `"qwen3"`, `"groq"` |
| `qwen_model` | `"Qwen/Qwen3-ASR-1.7B-hf"` | HuggingFace repo or ONNX model tag |
| `stt_device` | `"auto"` | `"auto"`, `"directml"`, `"cpu"`, `"cuda"` |
| `groq_model` | `"whisper-large-v3"` | Groq cloud transcription model |
| `tts_engine` | `"qwen3"` | `"qwen3"`, `"edge"` |
| `qwen_tts_model` | `"Qwen/Qwen3-TTS-12Hz-0.6B-Base"` | `"Qwen/Qwen3-TTS-12Hz-0.6B-Base"`, `"Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"` |
| `tts_ref_voice` | `""` | Optional path to reference `.wav` for zero-shot cloning |
| `tts_device` | `"auto"` | `"auto"`, `"directml"`, `"cpu"`, `"cuda"` |
| `tts_voice_enabled`| `True` | Master toggle for Jarvis vocal responses |
| `vad_enabled` | `True` | Neural Silero VAD toggle |
| `vad_threshold` | `0.5` | VAD probability cutoff `[0.1 - 0.95]` |
| `silence_timeout`| `3.0` | Pause duration (seconds) to finalize dictation |
| `hotkey` | `"ctrl+space"` | Activation hotkey |
| `hotkey_mode` | `"toggle"` | `"toggle"`, `"push_to_talk"` |
| `ai_mode` | `"direct"` | `"direct"`, `"clean"`, `"smart"` |

---

## 5. Critical Engineering Rules & Concurrency Patterns
1. **Thread-Safe Facades:** All STT/TTS properties (`is_ready`, `status_message`, `adapter`) MUST be read/modified within `with self._lock:` guards.
2. **Memory Flushing:** Any adapter `unload()` MUST execute `gc.collect()` and `torch.cuda.empty_cache()` (if CUDA/Torch is loaded) to prevent VRAM accumulation across model switches.
3. **Anti-Self-Echo Guard:** TTS service maintains `is_jarvis_phrase(text)` to filter out phrases spoken by the assistant from re-entering the STT pipeline.
4. **No Emojis in Code/UI:** Strict ASCII markers only (`[SYS]`, `[STT]`, `[TTS]`, `[VAD]`, `[AI]`, `[CMD]`, `[OK]`, `[WARN]`, `[CRIT]`, `[FAIL]`).
5. **Non-Blocking Background Tasks:** All model loading and disk pre-caching run in background threads (`daemon=True`) to never block the PyQt6 event loop.
6. **Robust Process Lifecycle:** `sys.stdout` and `sys.stderr` null-stream handling guaranteed for `pythonw` background execution.

---

## 6. Verification Commands
```powershell
# Run Full App Launcher (Background)
run.bat

# Run Full App in Interactive Debug Console
run.bat --debug

# Run Full System Test Suite
.\venv\Scripts\python.exe test_full_system.py

# Run STT Suite
.\venv\Scripts\python.exe test_stt_adapter.py

# Run TTS Suite
.\venv\Scripts\python.exe test_tts_adapter.py
```
