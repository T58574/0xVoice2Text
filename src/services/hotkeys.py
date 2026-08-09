from pynput import keyboard
import threading
import time
from src.core.logger import logger

class HotkeyManager:
    def __init__(self, target_key="ctrl+space", mode="toggle", on_start=None, on_stop=None):
        self.target_key_str = target_key.lower().strip()
        self.mode = mode # toggle or push_to_talk
        self.on_start = on_start
        self.on_stop = on_stop

        self.currently_pressed = set()
        self.is_recording_state = False
        self.combo_triggered = False
        self.listener = None

        self._parse_target_key(self.target_key_str)

    def _parse_target_key(self, key_str):
        self.target_key_str = key_str.lower().strip()
        parts = [p.strip() for p in self.target_key_str.split("+")]
        self.required_keys = set()

        for p in parts:
            if p in ("alt", "alt_l", "alt_r"):
                self.required_keys.add("alt")
            elif p in ("ctrl", "ctrl_l", "ctrl_r"):
                self.required_keys.add("ctrl")
            elif p in ("shift", "shift_l", "shift_r"):
                self.required_keys.add("shift")
            elif p in ("space", "spacebar", " "):
                self.required_keys.add("space")
            elif p == "caps_lock":
                self.required_keys.add("caps_lock")
            elif p == "f8":
                self.required_keys.add("f8")
            elif p == "f9":
                self.required_keys.add("f9")
            elif p == "f10":
                self.required_keys.add("f10")
            elif p == "scroll_lock":
                self.required_keys.add("scroll_lock")
            else:
                self.required_keys.add(p)

        print(f"[HotkeyManager] Parsed required keys for '{self.target_key_str}': {self.required_keys}")

    def update_key(self, key_str, mode="toggle"):
        self.mode = mode
        self._parse_target_key(key_str)
        self.currently_pressed.clear()
        self.combo_triggered = False
        print(f"[HotkeyManager] Updated hotkey to '{key_str}' (mode: {mode})")

    def _normalize_key(self, key):
        if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return "alt"
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return "ctrl"
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            return "shift"
        if key == keyboard.Key.space or (hasattr(key, 'char') and key.char == ' '):
            return "space"
        if key == keyboard.Key.caps_lock:
            return "caps_lock"
        if key == keyboard.Key.f8:
            return "f8"
        if key == keyboard.Key.f9:
            return "f9"
        if key == keyboard.Key.f10:
            return "f10"
        if key == keyboard.Key.scroll_lock:
            return "scroll_lock"
        
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        if hasattr(key, 'vk') and key.vk is not None:
            if 48 <= key.vk <= 57:
                return str(key.vk - 48)
            if 96 <= key.vk <= 105:
                return str(key.vk - 96)
        
        return str(key).lower()

    def _on_press(self, key):
        norm_key = self._normalize_key(key)
        self.currently_pressed.add(norm_key)

        if self.required_keys.issubset(self.currently_pressed):
            if not self.combo_triggered:
                self.combo_triggered = True
                self._handle_trigger()

    def _handle_trigger(self):
        if self.mode == "toggle":
            self.is_recording_state = not self.is_recording_state
            print(f"[HotkeyManager] Toggle triggered. New recording state: {self.is_recording_state}")
            if self.is_recording_state:
                if self.on_start:
                    self.on_start()
            else:
                if self.on_stop:
                    self.on_stop()
        elif self.mode == "push_to_talk":
            if not self.is_recording_state:
                self.is_recording_state = True
                print("[HotkeyManager] Push-to-talk started")
                if self.on_start:
                    self.on_start()

    def _on_release(self, key):
        norm_key = self._normalize_key(key)
        self.currently_pressed.discard(norm_key)

        if not self.required_keys.issubset(self.currently_pressed):
            self.combo_triggered = False

        if self.mode == "push_to_talk":
            if self.is_recording_state and not self.required_keys.issubset(self.currently_pressed):
                self.is_recording_state = False
                print("[HotkeyManager] Push-to-talk stopped")
                if self.on_stop:
                    self.on_stop()

    def start(self):
        if self.listener is not None:
            return
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        print(f"[HotkeyManager] Keyboard listener started for '{self.target_key_str}' (mode: {self.mode})")

    def stop(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            print("[HotkeyManager] Keyboard listener stopped")
