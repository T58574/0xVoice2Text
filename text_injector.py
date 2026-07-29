import time
import pyperclip
import win32api
import win32con

VK_CONTROL = 0x11
VK_V = 0x56

class TextInjector:
    @staticmethod
    def inject_text(text: str, add_trailing_space: bool = True):
        if not text:
            return False

        if add_trailing_space and not text.endswith(" "):
            text += " "

        print(f"[TextInjector] Injecting text: '{text}' into active window...")

        try:
            # 1. Backup existing clipboard content
            old_clipboard = ""
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass

            # 2. Copy new text to clipboard
            pyperclip.copy(text)
            time.sleep(0.02)

            # 3. Simulate Ctrl + V key combo via Win32 API
            win32api.keybd_event(VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.03)
            win32api.keybd_event(VK_V, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

            time.sleep(0.1)

            # 4. Optional restore clipboard after a short delay in background
            # (We keep the transcribed text in clipboard for convenience if user wants to re-paste)
            
            return True
        except Exception as e:
            print(f"[TextInjector] Error injecting text: {e}")
            return False
