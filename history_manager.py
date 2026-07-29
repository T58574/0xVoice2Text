import os
import json
import time

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")

class HistoryManager:
    def __init__(self, max_items=50):
        self.max_items = max_items
        self.items = []
        self.load()

    def load(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception as e:
                print(f"[HistoryManager] Error loading history: {e}")
                self.items = []

    def save(self):
        try:
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
        # Prepend latest
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
