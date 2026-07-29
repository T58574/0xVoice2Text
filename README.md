# 0xVoice2Text — Infrastructure Integration & API Docs

Модуль **0xVoice2Text** — компактный высокопроизводительный сервис голосового ввода и распознавания речи для Windows на базе **Groq Cloud API (Whisper Large V3)**.

---

## 🛰️ Инфраструктурная Интеграция (IPC & JSON Output)

Модуль проектировался с возможностью быстрой интеграции с внешней инфраструктурой (скриптами автоматизации, ботами, логгерами и локальной экосистемой).

При каждом успешном распознавании речи `0xVoice2Text` автоматически отправляет структурированный JSON-событие в локальное IPC-хранилище:

- **Последнее событие**: `~/.0xvoice2text/last_event.json`
- **Лог событий (JSON Lines)**: `~/.0xvoice2text/events.log`

### 📄 Схема JSON События (Output Spec)

```json
{
  "timestamp": "2026-07-24T01:23:45+0300",
  "unix_timestamp": 1721773425,
  "engine": "groq-whisper-large-v3",
  "language": "ru",
  "text": "Тестовая фраза распознавания речи",
  "char_count": 33,
  "word_count": 4,
  "status": "success"
}
```

---

## 💻 Пример чтения событий на Python (File Watcher)

```python
import os
import json
import time

LAST_EVENT_PATH = os.path.expanduser("~/.0xvoice2text/last_event.json")

def watch_voice_events():
    last_mtime = 0
    while True:
        if os.path.exists(LAST_EVENT_PATH):
            mtime = os.path.getmtime(LAST_EVENT_PATH)
            if mtime > last_mtime:
                last_mtime = mtime
                with open(LAST_EVENT_PATH, "r", encoding="utf-8") as f:
                    event = json.load(f)
                    print(f"[Voice Event] [{event['timestamp']}] {event['text']}")
        time.sleep(0.1)

if __name__ == "__main__":
    watch_voice_events()
```

---

## 💻 Пример чтения событий на PowerShell

```powershell
$path = "$env:USERPROFILE\.0xvoice2text\last_event.json"
Get-Content $path -Wait | ConvertFrom-Json | ForEach-Object {
    Write-Host "Новый голосовой ввод: $($_.text)"
}
```

---

## ⚙️ Конфигурация приложения (`config.json`)

Конфигурационный файл расположен в корневой директории приложения:

| Ключ | Тип | Описание |
| :--- | :--- | :--- |
| `hotkey` | string | Горячая клавиша активации (`ctrl+space`, `alt+3`, `caps_lock`, `f8`) |
| `hotkey_mode` | string | Режим записи: `toggle` (нажал/нажал) или `push_to_talk` (зажатие) |
| `auto_paste` | boolean | Автоматическая вставка текста в курсор активного окна |
| `sound_feedback` | boolean | Звуковые эффекты при старте/стопе записи |
| `theme` | string | Тема интерфейса (`cyberpunk_dark`) |

---

## 🔑 Авторизация (.env)

Переменная окружения в корне приложения `.env`:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

---

## 🎨 Особые фичи интерфейса

- **Floating Mouse HUD Overlay**: Неоновый оверлей вокруг курсора мыши при нажатии `Ctrl+Space`.
- **Dedicated History Window**: Полноценное окно истории с поиском и экспортом в JSON (доступно из системного трея и кнопкой `HIST`).
- **Cyberpunk Sound Packs**: Синтезированные темы звуковых сигналов (`scifi`, `jarvis`, `stealth`).
