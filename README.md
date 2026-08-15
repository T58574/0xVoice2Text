# 🎙️ 0xVoice2Text — Real-Time Voice AI Assistant & Desktop Dictation Hub

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Whisper](https://img.shields.io/badge/STT-Whisper_Large_V3-teal?style=flat-square)](https://github.com/openai/whisper)
[![Silero VAD](https://img.shields.io/badge/VAD-Silero_Voice_Activity-blueviolet?style=flat-square)](https://github.com/snakers4/silero-vad)
[![Gemini](https://img.shields.io/badge/AI_Engine-Gemini_3.6_%2F_Gemma-4285F4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**An ultra-low latency (<500ms), privacy-focused Windows desktop voice transcription engine, neural speech assistant, and AI prompt refiner powered by Whisper Large V3, Silero VAD, Edge-TTS, and Google Gemini AI.**

[Key Features](#-key-features) • [Architecture](#-architecture) • [AI Post-Processing](#-ai-intelligence-modes) • [IPC Bus](#-universal-ipc-event-bus) • [Quick Start](#-quick-start) • [License](#-license)

</div>

---

## 📖 Overview

**0xVoice2Text** is a high-performance desktop voice dictation engine and AI speech assistant crafted for software engineers, power users, and writers on Windows. It eliminates the friction of voice typing by capturing microphone audio, isolating speech with **Silero Voice Activity Detection (VAD)**, transcribing at ultra-high speed via **Whisper Large V3**, and automatically injecting clean, punctuated text directly into your active code editor or browser.

Beyond simple speech-to-text, 0xVoice2Text features an intelligent **AI Post-Processing Pipeline** (powered by Gemini 3.6 Flash and Gemma) that cleans verbal debris ("um", "like", "you know"), reformats stream-of-consciousness dictation into clean code or prompts, and provides zero-latency neural voice feedback via Windows MCI audio APIs.

---

## ✨ Key Features

- ⚡ **Sub-Second Speech-to-Text (<500ms)**
  - Powered by Groq Cloud Whisper Large V3 (and local Whisper fallback) with automatic multilingual detection (`ru`, `en`, etc.) and immediate clipboard text injection.
- 🎯 **Silero Voice Activity Detection (VAD)**
  - Real-time audio stream analysis automatically detects natural speech pauses and stops recording without requiring manual hotkey release.
- 🗣️ **Wake Word & Voice Macro Automation**
  - Continuous low-power listening for wake phrases (*"Джарвис"* / *"Jarvis"*) to activate dictation hands-free, plus custom voice macros for launching applications.
- 🧠 **Multi-Tier AI Post-Processing Pipeline**
  - Toggle seamlessly between raw verbatim output, automatic speech sanitation, and smart code/prompt refactoring directly from the desktop widget.
- 🔊 **Zero-Latency Neural TTS Feedback**
  - Pre-cached Microsoft Edge Neural voices (`ru-RU-SvetlanaNeural`, `ru-RU-DmitryNeural`) played instantly via native Windows MCI (`winmm.dll`) without external media player dependencies.
- 🎨 **Futuristic Cyberpunk UI & Floating Overlays**
  - **Radial Mouse HUD**: Neon status circle tracking the cursor with animated recording rings.
  - **Glassmorphic Desktop Pill**: Compact floating widget with interactive mode toggles and audio waveform visualizer.
  - **History Window**: Dedicated searchable log with instant JSON export and replay capabilities.
- 🛰️ **Universal IPC Event Bus**
  - Emits structured JSON events (`~/.0xvoice2text/last_event.json` and `events.log`) enabling live integration with IDEs, bots, and external automation scripts.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   Microphone Audio Input Stream                  │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ 16kHz PCM Audio Stream
┌─────────────────────────────────▼────────────────────────────────┐
│             Silero Voice Activity Detection (VAD)                │
│    (Filters silence & background noise, detects natural pauses)  │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ Buffered Speech Chunk
┌─────────────────────────────────▼────────────────────────────────┐
│               Whisper Large V3 Transcription Engine              │
│       (Ultra-fast speech-to-text decoding via Groq API)          │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ Raw Transcribed Text
┌─────────────────────────────────▼────────────────────────────────┐
│             AI Post-Processing Pipeline (Gemini/Gemma)           │
│                                                                  │
│  ┌────────────────────────┐  ┌────────────────────────────────┐  │
│  │ Direct Mode (Verbatim) │  │ Clean Mode (Strip Fillers)     │  │
│  └────────────────────────┘  └────────────────────────────────┘  │
│  ┌────────────────────────┐  ┌────────────────────────────────┐  │
│  │ Smart Mode (AI Refine) │  │ Neural TTS Voice Feedback      │  │
│  └────────────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ Clean Formatted Text
┌─────────────────────────────────▼────────────────────────────────┐
│        Windows Keystroke Injector & IPC Event Bus Dispatcher     │
│        (Active Window Focus • ~/.0xvoice2text/last_event.json)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🧠 AI Intelligence Modes

| Mode | Engine | Purpose | Output Example |
|---|---|---|---|
| ⚡ **DIRECT** | Groq Whisper V3 | 0ms instant verbatim output with punctuation | *"найди в интернете инфу про танк тигр 2"* |
| ✨ **CLEAN** | Gemma 4 / Flash Lite | Strips verbal debris, hesitations ("э-э-э", "ну", "типа"), fixes syntax | *"Найди информацию про танк Tiger II."* |
| 🤖 **SMART** | Gemini 3.6 Flash | Converts dictated thoughts into clean prompts, structured specs, or code | *"Собери подробную справку по танку Tiger II: история создания, компоновка трансмиссии и бронирование."* |

---

## 🛰️ Universal IPC Event Bus

Every completed voice event is instantly broadcast to `~/.0xvoice2text/last_event.json` and appended to `events.log`:

```json
{
  "timestamp": "2026-08-15T03:15:00+0300",
  "unix_timestamp": 1786752900,
  "engine": "groq-whisper-large-v3",
  "ai_mode": "smart",
  "language": "ru",
  "text": "Refactor auth controller into modular middleware pipeline.",
  "char_count": 59,
  "word_count": 8,
  "status": "success"
}
```

### Python Real-Time Event Consumer
```python
import os, json, time

EVENT_FILE = os.path.expanduser("~/.0xvoice2text/last_event.json")
last_mtime = 0

while True:
    if os.path.exists(EVENT_FILE):
        mtime = os.path.getmtime(EVENT_FILE)
        if mtime > last_mtime:
            last_mtime = mtime
            with open(EVENT_FILE, "r", encoding="utf-8") as f:
                event = json.load(f)
                print(f"[{event['timestamp']}] ({event['ai_mode']}) {event['text']}")
    time.sleep(0.05)
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/T58574/0xVoice2Text.git
cd 0xVoice2Text
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure API Keys
Copy `.env.example` to `.env` and insert your credentials:
```bash
cp .env.example .env
```
```ini
# Required for ultra-fast transcription (https://console.groq.com/keys)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Optional: Required for Clean & Smart AI modes (https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run Application
```bash
python main.py
```
Or launch via the included shortcut batch file:
```cmd
run.bat
```

---

## 📁 Project Structure

```
0xVoice2Text/
├── src/
│   ├── core/                # Core Audio & AI Services
│   │   ├── ai_engine.py     # Gemini & Gemma AI post-processing pipeline
│   │   ├── audio_recorder.py# PyAudio stream capturer & VAD integrator
│   │   ├── history.py       # Local JSON history storage
│   │   ├── ipc_bus.py       # IPC event bus dispatcher
│   │   ├── stt_engine.py    # Whisper Large V3 API client
│   │   └── wake_word.py     # Continuous wake word listening daemon
│   ├── services/            # System & OS Integration
│   │   ├── hotkeys.py       # Global Windows keyboard hooks
│   │   ├── injector.py      # Active window keystroke/clipboard injector
│   │   ├── macros.py        # Voice command macro dispatcher
│   │   └── tts.py           # Native MCI audio & Edge-TTS synthesizer
│   └── ui/                  # PyQt6 Desktop User Interface
│       ├── error_dialog.py  # User-friendly API error diagnostic dialog
│       ├── history.py       # Full-text searchable history window
│       ├── mouse_hud.py     # Radial neon cursor HUD overlay
│       ├── settings.py      # Multi-tab settings configuration dialog
│       ├── tray.py          # Windows notification area system tray icon
│       └── widget.py        # Glassmorphic floating desktop status pill
├── .env.example             # Template for API credentials
├── .gitignore               # Strict ignore rules for audio & secrets
├── main.py                  # Master application orchestrator
├── requirements.txt         # Python package dependencies
├── run.bat                  # One-click Windows launcher
└── LICENSE                  # MIT License
```

---

## 📜 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
