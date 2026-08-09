import asyncio
import os
import hashlib
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import edge_tts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "audio_cache", "tts")

PRESET_PHRASES = {
    "listening": [
        "Слушаю вас, сэр.",
        "Да, я вас слушаю.",
        "Готов к приему информации.",
        "На связи.",
        "Внимательно слушаю.",
        "Слушаю.",
        "Слушаю ваши указания."
    ],
    "success": [
        "Готово, сэр.",
        "Текст успешно введен.",
        "Принято.",
        "Выполнено.",
        "Готово.",
        "Сделано, сэр.",
        "Готово, текст на экране."
    ],
    "macro": [
        "Выполняю команду.",
        "Есть, выполняю.",
        "Запускаю, сэр.",
        "Принято, активирую.",
        "Запрос принят к исполнению.",
        "Команда активирована."
    ],
    "error": [
        "Сэр, произошла ошибка.",
        "Ключ доступа не найден.",
        "Не удалось распознать речь.",
        "Алгоритмы временно недоступны."
    ],
    "processing": [
        "Обрабатываю.",
        "Секунду, сэр.",
        "Распознаю аудио.",
        "Обработка данных."
    ]
}

def get_phrase_filename(phrase: str, voice: str = "ru-RU-DmitryNeural") -> str:
    h = hashlib.md5(f"{voice}_{phrase}".encode("utf-8")).hexdigest()[:10]
    return f"tts_{h}.mp3"

async def generate_single_phrase(phrase: str, fpath: str, voice: str, pitch: str, rate: str):
    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(phrase, voice=voice, pitch=pitch, rate=rate)
            await comm.save(fpath)
            return True
        except Exception as e:
            print(f"  [Attempt {attempt+1}] retry '{phrase}': {e}")
            await asyncio.sleep(0.5)
    return False

async def generate_all_presets():
    os.makedirs(CACHE_DIR, exist_ok=True)
    voice = "ru-RU-DmitryNeural"
    pitch = "-5Hz"
    rate = "+0%"

    count = 0
    total = sum(len(v) for v in PRESET_PHRASES.values())
    print(f"[TTS Generator] Generating {total} Jarvis voice variations...")

    for category, phrases in PRESET_PHRASES.items():
        for phrase in phrases:
            count += 1
            fname = get_phrase_filename(phrase, voice)
            fpath = os.path.join(CACHE_DIR, fname)
            if not os.path.exists(fpath):
                print(f"[{count}/{total}] Generating '{phrase}' -> {fname}")
                await generate_single_phrase(phrase, fpath, voice, pitch, rate)
            else:
                print(f"[{count}/{total}] Cached: '{phrase}'")

    print("[TTS Generator] Completed generating all 28 voice samples!")

if __name__ == "__main__":
    asyncio.run(generate_all_presets())
