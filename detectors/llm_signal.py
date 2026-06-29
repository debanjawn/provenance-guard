import json
import os
import re
from urllib import error, request

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

DEFAULT_SIGNAL = {
    "score": 0.5,
    "reason": "Unable to complete LLM-based attribution check, so the result is marked uncertain."
}

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:14b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
PROVIDER_LABELS = {
    "groq": "Groq cloud",
    "ollama": "Local Ollama/Qwen",
}

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


def _uncertain_signal(reason: str) -> dict:
    return {
        "score": 0.5,
        "reason": reason,
    }


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


def parse_llm_json_response(raw_text: str) -> dict:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Model response was empty.")

    stripped_text = raw_text.strip()
    decoder = json.JSONDecoder()

    fenced_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        stripped_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced_match:
        stripped_text = fenced_match.group(1).strip()

    try:
        return _normalize_signal(json.loads(stripped_text))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    for index, character in enumerate(stripped_text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped_text[index:])
            return _normalize_signal(parsed)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    raise ValueError("No valid JSON object found in model response.")


def _normalize_provider_name(provider: str | None) -> str | None:
    if not isinstance(provider, str):
        return None

    normalized = provider.strip().lower()
    if normalized in {"", "default"}:
        return None
    if normalized in PROVIDER_LABELS:
        return normalized
    return None


def get_default_provider() -> str:
    provider = _normalize_provider_name(os.getenv("LLM_PROVIDER"))
    if provider == "ollama":
        return "ollama"
    return "groq"


def get_effective_provider(provider_override: str | None = None) -> str:
    normalized_override = _normalize_provider_name(provider_override)
    if normalized_override:
        return normalized_override
    return get_default_provider()


def get_provider_label(provider: str | None) -> str:
    return PROVIDER_LABELS.get(get_effective_provider(provider), PROVIDER_LABELS["groq"])


def get_groq_signal(text: str) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _uncertain_signal(
            "GROQ_API_KEY is not configured, so the result is marked uncertain."
        )

    model_name = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        raw_content = response.choices[0].message.content or ""
        return parse_llm_json_response(raw_content)
    except (KeyError, IndexError, TypeError, ValueError):
        return _uncertain_signal(
            "The Groq attribution response could not be parsed, so the result is marked uncertain."
        )
    except Exception:
        return DEFAULT_SIGNAL.copy()


def get_ollama_signal(text: str) -> dict:
    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    model_name = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    payload = {
        "model": model_name,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }

    request_body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{base_url}/api/chat",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=60) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.URLError:
        return _uncertain_signal(
            "The local Ollama service could not be reached, so the result is marked uncertain."
        )
    except (TimeoutError, OSError):
        return _uncertain_signal(
            "The local Ollama request failed, so the result is marked uncertain."
        )
    except json.JSONDecodeError:
        return _uncertain_signal(
            "The Ollama response was not valid JSON, so the result is marked uncertain."
        )

    try:
        raw_content = response_payload["message"]["content"]
        return parse_llm_json_response(raw_content)
    except (KeyError, TypeError, ValueError):
        return _uncertain_signal(
            "The Ollama attribution response could not be parsed, so the result is marked uncertain."
        )


def get_llm_signal(text: str, provider_override: str | None = None) -> dict:
    if not isinstance(text, str) or not text.strip():
        return _uncertain_signal(
            "No usable text was provided, so the result is marked uncertain."
        )

    provider = get_effective_provider(provider_override)
    if provider == "ollama":
        return get_ollama_signal(text)
    return get_groq_signal(text)
