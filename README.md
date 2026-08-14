# 🎙️ 0xVoice2Text — Real-Time Voice Assistant & Desktop Transcription Hub

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Whisper](https://img.shields.io/badge/Speech--to--Text-Whisper_Large_V3-teal?style=flat-square)](https://github.com/openai/whisper)
[![Silero VAD](https://img.shields.io/badge/Voice_Detection-Silero_VAD-blueviolet?style=flat-square)](https://github.com/snakers4/silero-vad)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**An ultra-responsive, privacy-focused Windows desktop voice transcription engine and AI assistant powered by Whisper Large V3, Silero Voice Activity Detection (VAD), Neural Edge-TTS, and Google Gemini AI.**

</div>

---

## ⚡ Overview

**0xVoice2Text** is a lightweight, low-latency voice-to-text pipeline engineered for programmers, power users, and writers. It captures speech from your microphone, eliminates pauses using real-time Voice Activity Detection (VAD), transcribes audio with Whisper Large V3 in under 500ms, and automatically pastes clean text directly into whatever window or code editor is active.

It also features intelligent AI post-processing (formatting raw thoughts into clean prose, code, or structured bullet points), neural text-to-speech feedback, customizable voice macros, and a file-based IPC event bus.

---

## ✨ Key Features

- ⚡ **Sub-Second Speech-to-Text**: Powered by Whisper Large V3 with automatic language detection (`ru`, `en`, etc.) and instant clipboard injection.
- 🎯 **Silero Voice Activity Detection (VAD)**: Smart silence detection automatically stops recording when you finish speaking.
- 🗣️ **Wake Word & Voice Macros**: Hands-free voice trigger ("Jarvis") and custom voice macros to launch applications or execute system actions.
- 🧠 **AI Intelligence Modes (Gemini 3.6 / Gemma)**:
  - `Direct`: Exact verbatim transcription.
  - `Clean`: Removes verbal fluff, hesitations, stutters, and fixes grammar.
  - `Smart`: Converts dictated thoughts into clean code, Markdown docs, or structured lists.
- 🎨 **Futuristic Cyberpunk HUD & Floating Overlays**:
  - Radial mouse HUD overlay following the cursor.
  - Glassmorphic desktop status pill with real-time waveform visualizer.
  - History viewer with instant full-text search and JSON export.
- 🔊 **Neural TTS Feedback**: High-definition text-to-speech audio feedback powered by Microsoft Edge Neural Voices.
- 🛰️ **Universal IPC Event Bus**: Emits structured JSON events (`~/.0xvoice2text/last_event.json` and `events.log`) enabling easy integration with external scripts, bots, or IDE extensions.

---

## 🏗️ Architecture

```
  [Microphone Input] ──► [Silero VAD (Silence Detector)]
                                │
                                ▼
  [Audio Preprocessor] ──► [Whisper Large V3 Engine]
                                │
                                ▼
  [AI Post-Processor (Gemini)] ──► [OS Keystroke / Text Injector]
                                │
                                ├──► [Neural Edge-TTS Voice Feedback]
                                └──► [IPC Bus: ~/.0xvoice2text/events.log]
```

---

## 🚀 Getting Started

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

### 3. Configure Credentials
Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
```

### 4. Run Application
```bash
python main.py
```
Or launch via the included batch file:
```bash
run.bat
```

---

## 🛰️ IPC Integration Specification

Every completed transcription writes a structured event to `~/.0xvoice2text/last_event.json`:

```json
{
  "timestamp": "2026-08-15T02:30:00+0300",
  "unix_timestamp": 1786750200,
  "engine": "groq-whisper-large-v3",
  "language": "ru",
  "text": "Autonomous AI agent architecture initialized.",
  "char_count": 46,
  "word_count": 5,
  "status": "success"
}
```

### Python File Watcher Integration
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
                print(f"[{event['timestamp']}] {event['text']}")
    time.sleep(0.1)
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.
