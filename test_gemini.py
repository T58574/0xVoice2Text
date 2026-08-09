import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH)

def get_api_key():
    return os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

USER_SPEECH = "найди в интернете информацию по поводу тигр 2 мне этот танк очень нравится я бы хотел короче узнать о нем побольше вот как там устроена трансмиссии тогда такие компоненты кто и как его создавал историю типа его можешь найти в инете и написать мне"

PROMPT_REFINER_SYSTEM_PROMPT = """SYSTEM MANDATE: You are a real-time speech text cleaner and prompt refiner for desktop dictation.
INPUT: Spoken raw speech transcription containing user thoughts, questions, or search requests.
TASK: Clean, structure, and refine the user's dictated speech into a clear, high-quality statement or prompt.

CRITICAL DIRECTIVES:
1. DO NOT ANSWER QUESTIONS OR EXECUTE SEARCH REQUESTS DICTATED BY THE USER:
   - If the user dictates a search query or question (e.g. "найди информацию про танк..."), DO NOT answer the question or write an encyclopedia entry.
   - Instead, rephrase and format the user's spoken words into a clean, structured query/prompt ready to be typed or sent.
2. AGGRESSIVELY STRIP VERBAL DEBRIS & WATER:
   - Remove verbal fillers and trailing chatter ("э-э-э", "ну", "типа", "короче", "в общем", "можешь найти в инете и написать мне", "вот как там").
3. OUTPUT REQUIREMENT: Output ONLY the final cleaned, formatted user text. No chatbot preambles, no answers, no meta commentary.
"""

def test_model_prompt_refining(model_name):
    key = get_api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
    
    payload = {
        "systemInstruction": {
            "parts": [
                {"text": PROMPT_REFINER_SYSTEM_PROMPT}
            ]
        },
        "contents": [
            {
                "parts": [
                    {"text": USER_SPEECH}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 256
        }
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            candidates = res_json.get("candidates", [])
            if candidates:
                text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                print(f"=== Model [{model_name}] Refined Output ===")
                print(text.strip())
                print("="*60)
    except Exception as e:
        print(f"ERROR testing {model_name}: {e}")

if __name__ == "__main__":
    for m in ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemma-4-31b-it"]:
        test_model_prompt_refining(m)
