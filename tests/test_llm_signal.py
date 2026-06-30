from urllib import error

from detectors import llm_signal


def test_provider_defaults_to_groq_when_missing(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setattr(
        llm_signal,
        "get_groq_signal",
        lambda text: {"score": 0.2, "reason": "groq selected"},
    )
    monkeypatch.setattr(
        llm_signal,
        "get_ollama_signal",
        lambda text: {"score": 0.8, "reason": "ollama selected"},
    )

    result = llm_signal.get_llm_signal("A real piece of text for routing.")

    assert result["reason"] == "groq selected"
    assert isinstance(result["latency_ms"], int)
    assert llm_signal.get_default_provider() == "groq"


def test_provider_selects_ollama_when_requested(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setattr(
        llm_signal,
        "get_groq_signal",
        lambda text: {"score": 0.2, "reason": "groq selected"},
    )
    monkeypatch.setattr(
        llm_signal,
        "get_ollama_signal",
        lambda text: {"score": 0.8, "reason": "ollama selected"},
    )

    result = llm_signal.get_llm_signal("A real piece of text for routing.")

    assert result["reason"] == "ollama selected"
    assert isinstance(result["latency_ms"], int)
    assert llm_signal.get_effective_provider("ollama") == "ollama"


def test_invalid_provider_falls_back_to_groq(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "something-else")
    monkeypatch.setattr(
        llm_signal,
        "get_groq_signal",
        lambda text: {"score": 0.3, "reason": "groq fallback"},
    )

    result = llm_signal.get_llm_signal("A real piece of text for routing.")

    assert result["reason"] == "groq fallback"
    assert isinstance(result["latency_ms"], int)
    assert llm_signal.get_effective_provider("something-else") == "groq"


def test_provider_label_maps_to_user_friendly_text(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    assert llm_signal.get_provider_label("groq") == "Groq cloud"
    assert llm_signal.get_provider_label("ollama") == "Local Ollama/Qwen"
    assert llm_signal.get_provider_label("default") == "Local Ollama/Qwen"


def test_parse_llm_json_response_handles_clean_json():
    result = llm_signal.parse_llm_json_response(
        '{"score": 0.72, "reason": "Mixed but somewhat AI-like."}'
    )

    assert result == {
        "score": 0.72,
        "reason": "Mixed but somewhat AI-like.",
    }


def test_parse_llm_json_response_handles_json_fence():
    result = llm_signal.parse_llm_json_response(
        '```json\n{"score": 0.7, "reason": "test"}\n```'
    )

    assert result == {
        "score": 0.7,
        "reason": "test",
    }


def test_parse_llm_json_response_handles_plain_fence():
    result = llm_signal.parse_llm_json_response(
        '```\n{"score": 0.6, "reason": "plain fence"}\n```'
    )

    assert result == {
        "score": 0.6,
        "reason": "plain fence",
    }


def test_parse_llm_json_response_extracts_json_from_extra_text():
    result = llm_signal.parse_llm_json_response(
        'Here is the result: {"score": 0.8, "reason": "looks AI-like"} Thanks.'
    )

    assert result == {
        "score": 0.8,
        "reason": "looks AI-like",
    }


def test_get_ollama_signal_returns_fallback_on_http_failure(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:14b")

    def raise_url_error(*args, **kwargs):
        raise error.URLError("connection refused")

    monkeypatch.setattr(llm_signal.request, "urlopen", raise_url_error)

    result = llm_signal.get_ollama_signal("A real piece of text for routing.")

    assert result["score"] == 0.5
    assert "Ollama" in result["reason"]


def test_get_llm_signal_includes_measured_latency(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    timings = iter([10.0, 10.1234])
    monkeypatch.setattr(llm_signal.time, "perf_counter", lambda: next(timings))
    monkeypatch.setattr(
        llm_signal,
        "get_groq_signal",
        lambda text: {"score": 0.2, "reason": "groq selected"},
    )

    result = llm_signal.get_llm_signal("A real piece of text for routing.")

    assert result == {
        "score": 0.2,
        "reason": "groq selected",
        "latency_ms": 123,
    }
