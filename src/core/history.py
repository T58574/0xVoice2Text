import os
import json
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
OLD_HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

class HistoryManager:
    def __init__(self, max_items=50):
        self.max_items = max_items
        self.items = []
        os.makedirs(DATA_DIR, exist_ok=True)
        self.load()

    def load(self):
        target_path = HISTORY_FILE
        if not os.path.exists(HISTORY_FILE) and os.path.exists(OLD_HISTORY_FILE):
            target_path = OLD_HISTORY_FILE

        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception as e:
                print(f"[HistoryManager] Error loading history: {e}")
                self.items = []

    def save(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[HistoryManager] Error saving history: {e}")

    def add_entry(self, text: str):
        text = text.strip()
        if not text:
            return
        
        entry = {
            "id": int(time.time() * 1000),
            "timestamp": time.strftime("%H:%M:%S"),
            "text": text
        }
        self.items.insert(0, entry)
        if len(self.items) > self.max_items:
            self.items = self.items[:self.max_items]
        self.save()
        return entry

    def clear(self):
        self.items = []
        self.save()

    def get_all(self):
        return self.items
