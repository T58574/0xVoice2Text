import os
import sys
import re
import subprocess
import threading
import time
import ctypes

try:
    import win32com.client
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class MacroManager:
    """
    Executes voice commands, app launchers, system controls, volume adjustments,
    window management, and complex preset scenarios.
    """
    def __init__(self, config):
        self.config = config
        self.load_macros()

    def load_macros(self):
        # Built-in presets and voice macros
        self.default_macros = {
            "сверни все окна": {
                "phrases": [
                    "сверни все окна", "закрой все окна", "свернуть все окна",
                    "свернуть все", "свернуть всё", "покажи рабочий стол",
                    "сверни окна", "рабочий стол", "чистый стол"
                ],
                "description": "СВЕРНУТЬ ВСЕ ОКНА",
                "actions": [{"type": "minimize_all"}]
            },
            "восстанови все окна": {
                "phrases": [
                    "восстанови все окна", "верни все окна", "разверни окна",
                    "верни окна", "восстанови окна", "покажи окна"
                ],
                "description": "ВОССТАНОВИТЬ ОКНА",
                "actions": [{"type": "restore_all"}]
            },
            "закрой окно": {
                "phrases": ["закрой окно", "закрой текущее окно", "закрыть окно"],
                "description": "ЗАКРЫТЬ ОКНО (Alt+F4)",
                "actions": [{"type": "close_active_window"}]
            },
            "закрой вкладку": {
                "phrases": ["закрой вкладку", "закрыть вкладку"],
                "description": "ЗАКРЫТЬ ВКЛАДКУ (Ctrl+W)",
                "actions": [{"type": "close_tab"}]
            },
            "громче": {
                "phrases": ["громче", "сделай громче", "прибавь звук", "добавь звук", "увеличь звук"],
                "description": "ГРОМЧЕ (+10%)",
                "actions": [{"type": "vol_up"}]
            },
            "тише": {
                "phrases": ["тише", "сделай тише", "убавь звук", "уменьши звук"],
                "description": "ТИШЕ (-10%)",
                "actions": [{"type": "vol_down"}]
            },
            "выключи звук": {
                "phrases": ["выключи звук", "без звука", "включи звук", "муте", "мьют"],
                "description": "МУЗЫКА: Вкл/Выкл Звук",
                "actions": [{"type": "vol_mute"}]
            },
            "папочка вернулся": {
                "phrases": [
                    "просыпайся папочка вернулся", "папочка вернулся",
                    "джарвис просыпайся папочка вернулся", "просыпайся джарвис",
                    "просыпайся папочка", "рабочий режим"
                ],
                "description": "РЕЖИМ: VS Code + Музыка + Свернуть окна",
                "actions": [
                    {"type": "minimize_all"},
                    {"type": "launch", "target": "code"},
                    {"type": "media_play"}
                ]
            },
            "играем в танки": {
                "phrases": [
                    "играем в танки", "вар тандер", "war thunder",
                    "запусти танки", "запусти war thunder", "погнали в танки",
                    "джарвис играем в танки", "играть в танки"
                ],
                "description": "РЕЖИМ: Запуск War Thunder / Игры",
                "actions": [
                    {"type": "launch", "target": "steam://rungameid/236390"}
                ]
            },
            "открой телеграм": {
                "phrases": ["открой телеграм", "запусти телеграм", "открой telegram", "телегу"],
                "description": "Запуск Telegram",
                "actions": [{"type": "launch", "target": "tg://"}, {"type": "launch", "target": "telegram"}]
            },
            "открой хром": {
                "phrases": ["открой хром", "запусти хром", "открой браузер", "открой chrome"],
                "description": "Запуск Chrome",
                "actions": [{"type": "launch", "target": "chrome"}]
            },
            "открой стим": {
                "phrases": ["открой стим", "запусти стим", "открой steam"],
                "description": "Запуск Steam",
                "actions": [{"type": "launch", "target": "steam://"}]
            },
            "открой код": {
                "phrases": ["открой код", "запусти код", "открой vscode", "открой вскод"],
                "description": "Запуск VS Code",
                "actions": [{"type": "launch", "target": "code"}]
            },
            "открой проводник": {
                "phrases": ["открой проводник", "открой мой компьютер", "открой папки"],
                "description": "Запуск Проводника",
                "actions": [{"type": "launch", "target": "explorer"}]
            },
            "открой диспетчер задач": {
                "phrases": ["открой диспетчер задач", "диспетчер задач", "таск менеджер", "открой таск менеджер"],
                "description": "Запуск Диспетчера Задач",
                "actions": [{"type": "launch", "target": "taskmgr"}]
            },
            "открой калькулятор": {
                "phrases": ["открой калькулятор", "запусти калькулятор"],
                "description": "Запуск Калькулятора",
                "actions": [{"type": "launch", "target": "calc"}]
            },
            "открой блокнот": {
                "phrases": ["открой блокнот", "запусти блокнот"],
                "description": "Запуск Блокнота",
                "actions": [{"type": "launch", "target": "notepad"}]
            },
            "открой ютуб": {
                "phrases": ["открой ютуб", "открой youtube", "запусти ютуб"],
                "description": "Открыть YouTube",
                "actions": [{"type": "launch", "target": "https://youtube.com"}]
            },
            "открой яндекс": {
                "phrases": ["открой яндекс", "открой yandex"],
                "description": "Открыть Яндекс",
                "actions": [{"type": "launch", "target": "https://ya.ru"}]
            },
            "закрой телеграм": {
                "phrases": ["закрой телеграм", "закрой телегу"],
                "description": "Закрыть Telegram",
                "actions": [{"type": "close", "target": "Telegram.exe"}]
            },
            "закрой хром": {
                "phrases": ["закрой хром", "закрой браузер"],
                "description": "Закрыть Chrome",
                "actions": [{"type": "close", "target": "chrome.exe"}]
            },
            "выключи компьютер": {
                "phrases": ["выключи компьютер", "выключи комп", "выключи пк", "заверши работу"],
                "description": "Выключить ПК (15с)",
                "actions": [{"type": "shutdown", "delay": 15}]
            },
            "перезагрузи компьютер": {
                "phrases": ["перезагрузи компьютер", "перезагрузи комп", "перезагрузи пк", "перезагрузка"],
                "description": "Перезагрузка ПК (15с)",
                "actions": [{"type": "restart", "delay": 15}]
            },
            "отмена выключения": {
                "phrases": ["отмени выключение", "не выключай", "стоп выключение"],
                "description": "Отмена выключения ПК",
                "actions": [{"type": "cancel_shutdown"}]
            },
            "заблокируй компьютер": {
                "phrases": ["заблокируй компьютер", "заблокируй комп", "заблокируй пк", "заблокируй экран"],
                "description": "Блокировка ПК",
                "actions": [{"type": "lock_pc"}]
            },
            "включи музыку": {
                "phrases": ["включи музыку", "музыка", "пауза", "стоп музыка", "переключи музыку"],
                "description": "Воспроизведение / Пауза",
                "actions": [{"type": "media_play"}]
            },
            "следующий трек": {
                "phrases": ["следующий трек", "следующая песня", "вперед трек"],
                "description": "Следующий трек",
                "actions": [{"type": "media_next"}]
            }
        }

    def process_text(self, text: str) -> tuple[bool, str]:
        """
        Checks if transcribed text matches a voice macro command.
        Returns (handled: bool, description: str).
        """
        if not text or not self.config.get("voice_macros_enabled", True):
            return False, ""

        raw_text = text.lower().strip()
        # Clean leading wake prefixes ('джарвис', 'джарвиз', 'жарвис', 'эй', etc.)
        cleaned_text = re.sub(r'^(джарвис|джарвиз|жарвис|эй|пожалуйста|компьютер|слушай)[\s,.!?-]*', '', raw_text, flags=re.IGNORECASE).strip()
        if not cleaned_text:
            cleaned_text = raw_text

        # Merge config custom macros with defaults
        user_macros = self.config.get("voice_macros", {})
        all_macros = {**self.default_macros, **user_macros}

        for macro_key, data in all_macros.items():
            phrases = data.get("phrases", [macro_key])
            for phrase in phrases:
                phrase_norm = phrase.lower().strip()
                if phrase_norm and (phrase_norm == cleaned_text or phrase_norm == raw_text or phrase_norm in cleaned_text or phrase_norm in raw_text):
                    desc = data.get("description", macro_key.upper())
                    print(f"[MacroManager] ⚡ EXECUTING MACRO: '{macro_key}' -> {desc}")
                    self._execute_actions(data.get("actions", []))
                    return True, desc

        # Dynamic Launch Matcher: 'открой <приложение>' / 'запусти <приложение>'
        match_launch = re.match(r'^(открой|запусти)\s+(.+)$', cleaned_text)
        if match_launch:
            app_name = match_launch.group(2).strip()
            print(f"[MacroManager] ⚡ DYNAMIC LAUNCH: '{app_name}'")
            self._execute_actions([{"type": "launch", "target": app_name}])
            return True, f"LAUNCH: {app_name.upper()}"

        # Dynamic Close Matcher: 'закрой <приложение>'
        match_close = re.match(r'^(закрой|убей|выключи)\s+(.+)$', cleaned_text)
        if match_close:
            app_name = match_close.group(2).strip()
            if app_name in ["компьютер", "комп", "пк", "систему"]:
                self._execute_actions([{"type": "shutdown", "delay": 15}])
                return True, "ВЫКЛЮЧЕНИЕ ПК"
            if app_name in ["все окна", "окна"]:
                self._execute_actions([{"type": "minimize_all"}])
                return True, "СВЕРНУТЬ ВСЕ ОКНА"
            
            proc_name = app_name if app_name.endswith(".exe") else f"{app_name}.exe"
            print(f"[MacroManager] ⚡ DYNAMIC CLOSE: '{proc_name}'")
            self._execute_actions([{"type": "close", "target": proc_name}])
            return True, f"CLOSE: {app_name.upper()}"

        return False, ""

    def _execute_actions(self, actions: list):
        def _runner():
            for action in actions:
                act_type = action.get("type")
                try:
                    if act_type == "launch":
                        target = action.get("target")
                        if target:
                            print(f"[MacroManager] Launching: {target}")
                            subprocess.Popen(f"start {target}", shell=True)

                    elif act_type == "close":
                        target = action.get("target")
                        if target:
                            print(f"[MacroManager] Closing process: {target}")
                            subprocess.run(["taskkill", "/f", "/im", target], capture_output=True)

                    elif act_type == "minimize_all":
                        print("[MacroManager] Minimizing all windows...")
                        if HAS_WIN32:
                            try:
                                shell = win32com.client.Dispatch("Shell.Application")
                                shell.MinimizeAll()
                            except Exception:
                                os.system("powershell -c \"(New-Object -ComObject Shell.Application).MinimizeAll()\"")
                        else:
                            os.system("powershell -c \"(New-Object -ComObject Shell.Application).MinimizeAll()\"")

                    elif act_type == "restore_all":
                        print("[MacroManager] Restoring windows...")
                        if HAS_WIN32:
                            try:
                                shell = win32com.client.Dispatch("Shell.Application")
                                shell.UndoMinimizeALL()
                            except Exception:
                                pass

                    elif act_type == "close_active_window":
                        print("[MacroManager] Closing active window (Alt+F4)...")
                        if HAS_WIN32:
                            VK_MENU = 0x12  # Alt
                            VK_F4 = 0x73    # F4
                            win32api.keybd_event(VK_MENU, 0, 0, 0)
                            win32api.keybd_event(VK_F4, 0, 0, 0)
                            win32api.keybd_event(VK_F4, 0, win32con.KEYEVENTF_KEYUP, 0)
                            win32api.keybd_event(VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)

                    elif act_type == "close_tab":
                        print("[MacroManager] Closing tab (Ctrl+W)...")
                        if HAS_WIN32:
                            VK_CONTROL = 0x11 # Ctrl
                            VK_W = 0x57       # W
                            win32api.keybd_event(VK_CONTROL, 0, 0, 0)
                            win32api.keybd_event(VK_W, 0, 0, 0)
                            win32api.keybd_event(VK_W, 0, win32con.KEYEVENTF_KEYUP, 0)
                            win32api.keybd_event(VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

                    elif act_type == "vol_up":
                        print("[MacroManager] Volume Up...")
                        if HAS_WIN32:
                            VK_VOLUME_UP = 0xAF
                            for _ in range(5):
                                win32api.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                                win32api.keybd_event(VK_VOLUME_UP, 0, win32con.KEYEVENTF_KEYUP, 0)

                    elif act_type == "vol_down":
                        print("[MacroManager] Volume Down...")
                        if HAS_WIN32:
                            VK_VOLUME_DOWN = 0xAE
                            for _ in range(5):
                                win32api.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                                win32api.keybd_event(VK_VOLUME_DOWN, 0, win32con.KEYEVENTF_KEYUP, 0)

                    elif act_type == "vol_mute":
                        print("[MacroManager] Mute Volume...")
                        if HAS_WIN32:
                            VK_VOLUME_MUTE = 0xAD
                            win32api.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                            win32api.keybd_event(VK_VOLUME_MUTE, 0, win32con.KEYEVENTF_KEYUP, 0)

                    elif act_type == "media_play":
                        print("[MacroManager] Toggling media play/pause...")
                        if HAS_WIN32:
                            VK_MEDIA_PLAY_PAUSE = 0xB3
                            win32api.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                            win32api.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)

                    elif act_type == "media_next":
                        print("[MacroManager] Media next track...")
                        if HAS_WIN32:
                            VK_MEDIA_NEXT_TRACK = 0xB5
                            win32api.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
                            win32api.keybd_event(VK_MEDIA_NEXT_TRACK, 0, win32con.KEYEVENTF_KEYUP, 0)

                    elif act_type == "lock_pc":
                        print("[MacroManager] Locking workstation...")
                        ctypes.windll.user32.LockWorkStation()

                    elif act_type == "shutdown":
                        delay = action.get("delay", 15)
                        print(f"[MacroManager] Scheduling PC shutdown in {delay}s...")
                        os.system(f'shutdown /s /t {delay} /c "Завершение работы по команде Джарвиса"')

                    elif act_type == "restart":
                        delay = action.get("delay", 15)
                        print(f"[MacroManager] Scheduling PC restart in {delay}s...")
                        os.system(f'shutdown /r /t {delay} /c "Перезагрузка по команде Джарвиса"')

                    elif act_type == "cancel_shutdown":
                        print("[MacroManager] Canceling PC shutdown...")
                        os.system("shutdown /a")

                    time.sleep(0.2)
                except Exception as e:
                    print(f"[MacroManager] Error executing action ({act_type}): {e}")

        threading.Thread(target=_runner, daemon=True).start()
