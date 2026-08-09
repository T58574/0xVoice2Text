import os
import json
import re
import urllib.request
import urllib.error
from dotenv import load_dotenv
from src.core.logger import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

DEFAULT_CLEAN_PROMPT = """SYSTEM MANDATE: You are a high-precision speech compressor and editor for desktop dictation.
INPUT: Spoken raw speech transcription.
OUTPUT REQUIREMENT: Compress the dictated speech into its essential core meaning (СУТЬ) and output ONLY the clean final text.

STRICT COMPRESSION & CLEANING RULES:
1. AGGRESSIVELY STRIP ALL FLUFF & WATER (Убирай всю воду и словесный мусор):
   - Delete all verbal filler and hesitation ("э-э-э", "ну", "типа", "в общем", "как бы", "хм").
   - Delete all meta-commentary, trailing noise, and empty conclusions ("так короче", "даже не знаю", "вот конец", "то бишь", "знаешь ли", "такие дела").
   - Delete redundant phrase repetitions and self-corrections.
2. DISTILL TO ESSENTIAL SUBSTANCE (Выжимай только суть):
   - Keep only meaningful facts, thoughts, and intent.
   - Make the text concise, crisp, clear, and professional.
3. STRICT NEGATIVE CONSTRAINTS:
   - DO NOT output options, drafts, reasoning, bullet points, or step-by-step thinking (* Input:, * Task:, * Draft 1:).
   - DO NOT act as a conversational chatbot (no "Вот вариант:", "Конечно!").
"""

DEFAULT_SMART_PROMPT = """SYSTEM MANDATE: You are a real-time speech text cleaner and prompt refiner for desktop dictation.
INPUT: Spoken raw speech transcription containing user thoughts, questions, or search requests.
TASK: Clean, structure, and refine the user's dictated speech into a clear, high-quality statement or prompt.

CRITICAL DIRECTIVES:
1. DO NOT ANSWER QUESTIONS OR EXECUTE SEARCH REQUESTS DICTATED BY THE USER:
   - If the user dictates a search query or question (e.g. "найди в интернете информацию по поводу..."), DO NOT answer the question, DO NOT search, and DO NOT write an encyclopedia entry.
   - Instead, rephrase and format the user's spoken words into a clean, structured query/prompt ready to be typed or sent to another model.
2. AGGRESSIVELY STRIP VERBAL DEBRIS & WATER:
   - Remove verbal fillers and trailing chatter ("э-э-э", "ну", "типа", "короче", "в общем", "можешь найти в инете и написать мне", "вот как там").
3. OUTPUT REQUIREMENT: Output ONLY the final cleaned, formatted user text. No chatbot preambles, no answers, no meta commentary.
"""

def strip_ai_reasoning_fluff(raw_text: str) -> str:
    """
    Sanitizes LLM outputs, stripping internal reasoning, drafts, markdown bullet points,
    and conversational chatbot fluff to ensure pure text is typed at the active cursor.
    """
    if not raw_text:
        return ""
    
    text = raw_text.strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    clean_lines = []
    for l in lines:
        if l.startswith("*") or l.startswith("-"):
            if re.match(r'^[\*\-]\s*(Input|Task|Constraints?|Draft|Option|Decision|Final|Greeting|Language|Question|Answer|Reasoning|Step|Analysis)', l, re.IGNORECASE):
                continue
            if ":" in l and re.match(r'^[\*\-]\s*\w+:', l):
                continue
        if re.match(r'^(Option|Draft|Step|Reasoning|Analysis)\s*\d+:', l, re.IGNORECASE):
            continue
        if re.match(r'^(Вот|Исправленный|Чистый|Итоговый|Результат)\s*(текст|вариант|ответа)?:?', l, re.IGNORECASE):
            continue
        clean_lines.append(l)

    if clean_lines:
        res = "\n".join(clean_lines).strip()
        if (res.startswith('"') and res.endswith('"')) or (res.startswith('«') and res.endswith('»')):
            res = res[1:-1].strip()
        return res
    
    return text

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

    def process_text(self, raw_text: str, mode: str = "direct") -> tuple[str, str]:
        """
        Processes transcribed text based on active AI mode.
        Returns tuple: (processed_text, error_message).
        - If error occurs: processed_text is raw_text, error_message describes failure.
        - If success: error_message is empty string "".
        """
        if not raw_text or mode == "direct":
            return (raw_text, "")

        api_key = self.get_api_key()
        if not api_key:
            err_msg = "GEMINI_KEY_MISSING: API-ключ Gemini не найден в .env (GEMINI_API_KEY) или настройках приложения."
            logger.warning(f"[AIEngine] {err_msg}")
            return (raw_text, err_msg)

        model_name = self.config.get("gemma_model", "gemini-3.5-flash-lite") if mode == "clean" else self.config.get("gemini_model", "gemini-3.6-flash")
        
        clean_p = str(self.config.get("system_prompt_clean") or "").strip() or DEFAULT_CLEAN_PROMPT
        smart_p = str(self.config.get("system_prompt_smart") or "").strip() or DEFAULT_SMART_PROMPT
        system_prompt = clean_p if mode == "clean" else smart_p

        # Fallback sequence prioritizing non-reasoning flash-lite models for Clean mode
        if mode == "clean":
            fallback_models = [model_name, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash", "gemma-4-31b-it"]
        else:
            fallback_models = [model_name, "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemma-4-31b-it"]

        # Deduplicate preserving order
        seen = set()
        clean_fallbacks = []
        for m in fallback_models:
            if m not in seen:
                seen.add(m)
                clean_fallbacks.append(m)

        last_error = ""
        for current_model in clean_fallbacks:
            try:
                logger.info(f"[AIEngine] Requesting [{mode.upper()}] via Google API model '{current_model}'...")
                processed = self._call_gemini_api(
                    api_key=api_key,
                    model_name=current_model,
                    system_prompt=system_prompt,
                    user_text=raw_text,
                    timeout=25
                )
                if processed and processed.strip():
                    sanitized = strip_ai_reasoning_fluff(processed)
                    logger.info(f"[AIEngine] [{mode.upper()} Success via {current_model}]: '{sanitized}'")
                    return (sanitized, "")
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
                last_error = f"GOOGLE_API_HTTP_ERROR {e.code} ({e.reason}) [{current_model}]:\n{err_body}"
                logger.warning(f"[AIEngine] HTTP {e.code} for model {current_model}, trying next fallback...")
            except urllib.error.URLError as e:
                last_error = f"NETWORK_TIMEOUT: Превышено время ожидания ответа от {current_model} (25 сек): {e.reason}"
                logger.warning(f"[AIEngine] Timeout for model {current_model}, trying next fallback...")
            except Exception as e:
                last_error = f"UNEXPECTED_AI_ERROR [{current_model}]: {str(e)}"
                logger.warning(f"[AIEngine] Exception for model {current_model}: {e}")

        logger.error(f"[AIEngine] All models failed in mode {mode}. Last error: {last_error}")
        return (raw_text, last_error)

    def _call_gemini_api(self, api_key: str, model_name: str, system_prompt: str, user_text: str, timeout: int = 25) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        # Primary payload with systemInstruction
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

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)

                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except urllib.error.HTTPError as e:
            if e.code == 400: # Try fallback payload without systemInstruction for models that don't support it
                fallback_payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": f"{system_prompt}\n\nUser Input:\n{user_text}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 2048
                    }
                }
                fb_req = urllib.request.Request(
                    url=url,
                    data=json.dumps(fallback_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(fb_req, timeout=timeout) as fb_res:
                    fb_body = fb_res.read().decode("utf-8")
                    fb_json = json.loads(fb_body)
                    candidates = fb_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            raise e
        return ""
