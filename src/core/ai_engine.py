import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

DEFAULT_CLEAN_PROMPT = """You are a precision real-time speech cleaner for Windows desktop dictation.
Target environment: Active application window (text document, chat, email, or IDE).
Input: Raw speech-to-text transcription.

Rules:
1. Eliminate all spoken hesitation, filler words, stuttering, and verbal debris (e.g. "э-э-э", "ну", "типа", "в общем", "как бы", "хм", "так сказать").
2. Correct punctuation, capitalization, sentence structure, and grammatical slips naturally.
3. Preserve the exact original language, meaning, and intent. Do NOT summarize or shorten unless removing filler.
4. Do NOT reply conversationally. Do NOT add preambles like "Вот ваш текст:" or "Исправленный вариант:".
5. Return ONLY the final polished text ready for direct typing at the cursor.
"""

DEFAULT_SMART_PROMPT = """You are an intelligent desktop AI assistant & real-time speech transformer.
Target environment: Active Windows desktop workspace.
Input: Raw speech-to-text transcription containing user dictation, text modification requests, or action commands.

Rules:
1. CONTEXTUAL ANALYSIS:
   - If the user dictates a command or task (e.g., "напиши вежливый ответ...", "создай структуру...", "переведи на английский...", "напиши функцию на python..."), EXECUTE the request and generate the required content directly.
   - If the user dictates text meant for a document, rewrite, organize, and format it cleanly (use Markdown headers, lists, clean code blocks where applicable).
2. Adapt formatting strictly for direct insertion into the user's active application cursor position.
3. Do NOT include polite conversational fluff (no "Конечно! Вот вариант:", "С радостью помогу:").
4. Output ONLY the final processed result, code snippet, reply draft, or formatted text.
"""

class AIEngine:
    """
    Google Gemini / Gemma API post-processing engine for 0xVoice2Text.
    Provides sub-second LLM text cleanup (Mode 2) and AI smart assistant execution (Mode 3).
    """

    def __init__(self, config):
        self.config = config

    def get_api_key(self) -> str:
        # 1. Check .env file
        load_dotenv(ENV_PATH, override=True)
        key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        if not key:
            # 2. Fallback to config
            key = self.config.get("gemini_api_key", "").strip()
        return key

    def process_text(self, raw_text: str, mode: str = "direct") -> str:
        """
        Processes transcribed text based on active AI mode:
        - direct: returns raw_text unchanged.
        - clean: uses Gemma 4 / Gemini Flash Lite to clean speech filler & punctuation.
        - smart: uses Gemini 3.5/3.6 Flash for intelligent commands & transformation.
        """
        if not raw_text or mode == "direct":
            return raw_text

        api_key = self.get_api_key()
        if not api_key:
            print("[AIEngine] Warning: GEMINI_API_KEY / GOOGLE_API_KEY not found in .env or config!")
            return raw_text

        model_name = self.config.get("gemma_model", "gemma-4-31b-it") if mode == "clean" else self.config.get("gemini_model", "gemini-2.5-flash")
        system_prompt = self.config.get("system_prompt_clean", DEFAULT_CLEAN_PROMPT) if mode == "clean" else self.config.get("system_prompt_smart", DEFAULT_SMART_PROMPT)

        try:
            print(f"[AIEngine] Requesting [{mode.upper()}] via model '{model_name}'...")
            processed = self._call_gemini_api(
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_text=raw_text
            )
            if processed and processed.strip():
                print(f"[AIEngine] [{mode.upper()} Result]: '{processed.strip()}'")
                return processed.strip()
            return raw_text
        except Exception as e:
            print(f"[AIEngine] Error during AI post-processing ({mode}): {e}")
            return raw_text

    def _call_gemini_api(self, api_key: str, model_name: str, system_prompt: str, user_text: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        payload = {
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            },
            "contents": [
                {
                    "parts": [
                        {"text": user_text}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2 if "clean" in system_prompt.lower() else 0.4,
                "maxOutputTokens": 2048
            }
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)

            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        return ""
