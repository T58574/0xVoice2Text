# Privacy and Speech Synthesis (TTS) Rules

## 1. Git Privacy & Sensitive Data Exclusion
- **Strict Exclusion**: All user interaction history (`data/history.json`, `history.json`), user configurations (`data/config.json`, `config.json`), local API keys (`.env`), and generated audio caches (`data/audio_cache/`) MUST be explicitly excluded in `.gitignore`.
- **Public Templates**: Always provide a safe `data/config.example.json` without real API keys or personal text for repository cloning.
- **Index Cleanup**: If sensitive files were previously indexed by Git, always execute `git rm --cached <files>` immediately.

## 2. TTS Microphonic Anti-Echo & Self-Loop Prevention
- **Mic Suppression**: The audio recorder callback MUST check `tts.is_speaking()` and discard microphone buffer frames while TTS audio playback is active to prevent speaker output from leaking into the microphone.
- **Phrase Filtering**: The transcription pipeline MUST check `tts.is_jarvis_phrase(text)` and ignore any detected assistant preset phrases before injecting text into active windows or recording to history.

## 3. Zero-Latency Startup Pre-Caching for Voice Assistants
- **Background Pre-caching**: On application launch, asynchronously pre-generate and cache all preset speech phrase variations across supported voices (e.g., Svetlana, Dmitry) and speed multipliers (`+20%`) into `data/audio_cache/tts/`.
- **Native Playback**: Play cached MP3 files via zero-dependency native OS interfaces (such as Windows `ctypes.windll.winmm.mciSendStringW`) for instant 0ms latency playback.
