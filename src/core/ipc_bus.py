import os
import json
import time

IPC_DIR = os.path.expanduser("~/.0xvoice2text")
LAST_EVENT_FILE = os.path.join(IPC_DIR, "last_event.json")
EVENTS_LOG_FILE = os.path.join(IPC_DIR, "events.log")

class IPCEventBus:
    """
    Inter-Process Communication Event Bus.
    Emits structured JSON events when speech is transcribed,
    allowing external scripts/modules to consume recognition events.
    """
    def __init__(self):
        try:
            os.makedirs(IPC_DIR, exist_ok=True)
        except Exception as e:
            print(f"[IPCEventBus] Error creating IPC dir: {e}")

    def emit_transcription_event(self, text: str, engine: str = "groq-whisper-large-v3", language: str = "ru"):
        if not text:
            return

        t_now = time.time()
        event_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "unix_timestamp": int(t_now),
            "engine": engine,
            "language": language,
            "text": text,
            "char_count": len(text),
            "word_count": len(text.split()),
            "status": "success"
        }

        # 1. Atomic write to last_event.json
        try:
            temp_file = LAST_EVENT_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(event_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, LAST_EVENT_FILE)
        except Exception as e:
            print(f"[IPCEventBus] Error writing last_event.json: {e}")

        # 2. Append line to events.log (JSON Lines format)
        try:
            with open(EVENTS_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_data, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[IPCEventBus] Error appending to events.log: {e}")

        print(f"[IPCEventBus] Emitted JSON event -> {LAST_EVENT_FILE}")
