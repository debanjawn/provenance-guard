import json
import os
import re
import time
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
DEFAULT_LLM_MAX_OUTPUT_TOKENS = 80
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 8
PROVIDER_LABELS = {
    "groq": "Groq cloud",
    "ollama": "Local Ollama/Qwen",
}

SYSTEM_PROMPT = (
    "Judge whether the text appears human-written, AI-generated, or uncertain. "
    "Return compact JSON only: {\"score\": number from 0 to 1, \"reason\": \"one short sentence\"}. "
    "Keep the reason under 20 words. "
    "Use 0 for strongly human-like, 0.5 for uncertain or mixed, and 1 for strongly AI-like. "
    "Be conservative about false positives; polished writing alone is not enough. "
    "Assistant preambles such as 'Certainly! Here is...', generic transition-heavy wording, and repeated corporate phrases "
    "may be evidence of AI generation when they appear together. "
    "Do not treat merely polished human writing as strong AI evidence."
)


def _uncertain_signal(reason: str, latency_ms: int = 0) -> dict:
    return {
        "score": 0.5,
        "reason": reason,
        "latency_ms": latency_ms,
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


def _get_env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return default
    return parsed_value if parsed_value > 0 else default


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


def get_max_output_tokens() -> int:
    return _get_env_int("LLM_MAX_OUTPUT_TOKENS", DEFAULT_LLM_MAX_OUTPUT_TOKENS)


def get_ollama_timeout_seconds() -> int:
    return _get_env_int("OLLAMA_TIMEOUT_SECONDS", DEFAULT_OLLAMA_TIMEOUT_SECONDS)


def get_groq_signal(text: str) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _uncertain_signal(
            "GROQ_API_KEY is not configured, so the result is marked uncertain."
        )

    model_name = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    max_output_tokens = get_max_output_tokens()

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            max_tokens=max_output_tokens,
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
    timeout_seconds = get_ollama_timeout_seconds()
    payload = {
        "model": model_name,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "options": {
            "num_predict": get_max_output_tokens(),
        },
    }

    request_body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{base_url}/api/chat",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.URLError:
        return _uncertain_signal(
            "Ollama was unavailable, so the result is uncertain."
        )
    except (TimeoutError, OSError):
        return _uncertain_signal(
            "Ollama timed out, so the result is uncertain."
        )
    except json.JSONDecodeError:
        return _uncertain_signal(
            "Ollama returned invalid JSON, so the result is uncertain."
        )

    try:
        raw_content = response_payload["message"]["content"]
        return parse_llm_json_response(raw_content)
    except (KeyError, TypeError, ValueError):
        return _uncertain_signal(
            "Ollama returned an invalid attribution result."
        )


def get_llm_signal(text: str, provider_override: str | None = None) -> dict:
    if not isinstance(text, str) or not text.strip():
        return _uncertain_signal(
            "No usable text was provided, so the result is marked uncertain."
        )

    provider = get_effective_provider(provider_override)
    provider_fn = get_ollama_signal if provider == "ollama" else get_groq_signal
    start_time = time.perf_counter()
    result = provider_fn(text)
    latency_ms = int(round((time.perf_counter() - start_time) * 1000))
    return {
        **result,
        "provider": provider,
        "latency_ms": latency_ms,
    }
