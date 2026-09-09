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
[KWS: Wake Word Manager (Vosk)] ──► Voice Trigger: "джарвис" (SoundFX: Wake Ping) / Stop: "стоп"
     │ (Triggered or Hotkey Ctrl+Space)
     ▼
[Audio Recorder: Ring Buffer] ──► (SoundFX: Start Tone) Ingestion & RMS meter for UI Widget
     │ (Recording Completed)
     ▼
[STT Facade: STTEngine (src/core/stt/)]
     ├── [Primary] Qwen3ONNXAdapter (andrewleech/qwen3-asr-1.7b-onnx) [DirectML GPU / AVX2, Russian Forced]
     └── [Fallback] Qwen3ASRAdapter (PyTorch CPU AVX2)
     │
     ▼
[Text Injector / Macro Manager] ──► (SoundFX: Success Chime) Auto-paste into focused window / App launcher
     │ (Error on failure)
     ▼
[SoundFX: Error Tone] (Procedural synthesized audio feedback, 0ms latency, 0 external files/APIs)
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
│   │   ├── sounds.py           # Procedural SoundEffects engine (scifi, subtle, classic in-memory)
│   │   ├── tts/                # Procedural SoundFeedback bridge (legacy TTS fully deprecated)
│   │   │   ├── service.py      # JarvisVoiceService (lightweight sound feedback bridge)
│   │   │   └── __init__.py     # TTS package exports
│   │   ├── hotkeys.py          # Global hotkey listener (pynput, Toggle/PTT)
│   │   ├── injector.py         # pywin32 / pyperclip text injection
│   │   └── macros.py           # Voice command and macro execution
│   └── ui/
│       ├── widget.py           # Cyberpunk desktop floating widget with RMS visualizer
│       ├── settings.py         # Tabbed configuration modal (STT, SoundFX, VAD, Hotkeys)
│       ├── history.py          # Transcription history drawer window
│       ├── mouse_hud.py        # Cursor holographic HUD overlay ring
│       ├── error_dialog.py     # System error dialog with resolution hints
│       └── tray.py             # System tray icon and context menu
├── tests/
├── test_full_system.py         # End-to-End full system & pipeline validation
├── test_stt_adapter.py         # STT adapter unit and architecture verification
├── test_tts_adapter.py         # Procedural SoundFX verification test
├── test_mic_and_lifecycle.py   # Microphone & Single-Instance verification suite
└── tests_audit.py              # Full architecture and code audit suite
```

---

## 4. Configuration Reference (`data/config.json`)

| Key | Default Value | Options / Description |
| :--- | :--- | :--- |
| `stt_engine` | `"qwen3"` | `"qwen3"`, `"qwen3_hf"` |
| `qwen_model` | `"andrewleech/qwen3-asr-1.7b-onnx"` | ONNX DirectML repo or PyTorch model tag |
| `stt_device` | `"auto"` | `"auto"`, `"directml"`, `"cpu"`, `"cuda"` |
| `language` | `"ru"` | Target dictation language (Russian forced via prompt tokens) |
| `sound_feedback` | `True` | Master toggle for procedural status audio beeps/chimes |
| `sound_pack` | `"scifi"` | `"scifi"`, `"subtle"`, `"classic"` |
| `sound_volume` | `0.28` | Audio feedback amplitude `[0.05 - 1.0]` |
| `vad_enabled` | `True` | Neural Silero VAD toggle |
| `vad_threshold` | `0.5` | VAD probability cutoff `[0.1 - 0.95]` |
| `silence_timeout`| `3.0` | Pause duration (seconds) to finalize dictation |
| `wake_word_enabled` | `True` | Vosk offline wake word listener toggle |
| `wake_words` | `"джарвис, джарвиз, жарвис"` | Trigger keywords list |
| `stop_words` | `"стоп"` | Stop keywords list |
| `hotkey` | `"ctrl+space"` | Activation hotkey |
| `hotkey_mode` | `"toggle"` | `"toggle"`, `"push_to_talk"` |
| `auto_paste` | `True` | Automatically inject transcribed text into focused window |
| `add_trailing_space` | `True` | Append space after text injection |
| `always_on_top` | `True` | Keep widget pinned above all windows |

---

## 5. Critical Engineering Rules & Concurrency Patterns
1. **Thread-Safe Facades:** All STT/TTS properties (`is_ready`, `status_message`, `adapter`) MUST be read/modified within `with self._lock:` guards.
2. **Memory Flushing:** Any adapter `unload()` MUST execute `gc.collect()` and `torch.cuda.empty_cache()` (if CUDA/Torch is loaded) to prevent VRAM accumulation across model switches.
3. **Anti-Self-Echo Guard:** TTS service maintains `is_jarvis_phrase(text)` to filter out phrases spoken by the assistant from re-entering the STT pipeline.
4. **No Emojis in Code/UI:** Strict ASCII markers only (`[SYS]`, `[STT]`, `[TTS]`, `[VAD]`, `[AI]`, `[CMD]`, `[OK]`, `[WARN]`, `[CRIT]`, `[FAIL]`).
5. **Non-Blocking Background Tasks:** All model loading and disk pre-caching run in background threads (`daemon=True`) to never block the PyQt6 event loop.
6. **Robust Process Lifecycle:** `sys.stdout` and `sys.stderr` null-stream handling guaranteed for `pythonw` background execution.
7. **Single-Instance Mutex Guard:** Windows named mutex (`CreateMutexW`) prevents duplicate processes, focusing the existing window and avoiding RAM/VRAM exhaustion.
8. **Deterministic Process Termination:** Closing the widget (`✕`) cleanly frees audio streams and models, hides the tray icon, and terminates the process via `os._exit(0)`.
9. **Native Window Dragging:** Frameless desktop widget uses Windows native window manager (`startSystemMove`) with event filters across child frames.
10. **Microphone Hardware Verification:** Proactive audio device accessibility testing (`check_microphone_available`) with visual status badge (`MIC: OK` / `NO MIC`) and interactive re-check.

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

# Run Microphone & Lifecycle Suite
.\venv\Scripts\python.exe test_mic_and_lifecycle.py

# Run Security & Integrity Audit
.\venv\Scripts\python.exe tests_audit.py
```
