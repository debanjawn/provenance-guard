import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

DEFAULT_SIGNAL = {
    "score": 0.5,
    "reason": "Unable to complete LLM-based attribution check, so the result is marked uncertain."
}

MODEL_NAME = "llama-3.1-8b-instant"

SYSTEM_PROMPT = (
    "You are an attribution scoring assistant. Review the user's text and estimate how "
    "AI-like it appears. Return valid JSON only with exactly two fields: "
    "\"score\" and \"reason\". "
    "\"score\" must be a number from 0.0 to 1.0 where 0.0 means strongly human-like, "
    "0.5 means mixed or uncertain, and 1.0 means strongly AI-like. "
    "Be conservative about false positives. Casual personal writing, informal slang, "
    "specific lived experience, uneven grammar, emotional phrasing, and idiosyncratic "
    "wording should generally score lower. Formal or polished writing alone is not "
    "enough for a high AI score. Do not treat simple vocabulary as AI-like by itself. "
    "Use scores near 0.5 to 0.7 for uncertain or mixed cases. Only assign 0.8 or higher "
    "when there are strong signs of generic, templated, overly polished AI-style writing. "
    "\"reason\" must be a short plain-English explanation."
)


def _normalize_signal(payload: dict) -> dict:
    score = payload.get("score")
    reason = payload.get("reason")

    if not isinstance(score, (int, float)):
        raise ValueError("Signal score must be numeric.")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Signal reason must be a non-empty string.")

    clamped_score = max(0.0, min(1.0, float(score)))

    return {
        "score": clamped_score,
        "reason": reason.strip()
    }


def get_llm_signal(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        return {
            "score": 0.5,
            "reason": "No usable text was provided, so the result is marked uncertain."
        }

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "score": 0.5,
            "reason": "GROQ_API_KEY is not configured, so the result is marked uncertain."
        }

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        raw_content = response.choices[0].message.content or ""
        parsed_content = json.loads(raw_content)
        return _normalize_signal(parsed_content)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return {
            "score": 0.5,
            "reason": "The attribution response could not be parsed, so the result is marked uncertain."
        }
    except Exception:
        return DEFAULT_SIGNAL.copy()
