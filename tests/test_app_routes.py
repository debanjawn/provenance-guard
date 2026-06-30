import app as app_module
import audit_log
import verification


def _create_test_app(monkeypatch, tmp_path, **config):
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(tmp_path / "routes_test.db"))
    return app_module.create_app({
        "TESTING": True,
        "RATELIMIT_ENABLED": False,
        **config,
    })


def _stub_submit_detectors(monkeypatch, expected_provider_override=None):
    def stubbed_llm_signal(text, provider_override=None):
        assert provider_override == expected_provider_override
        return {"score": 0.2, "reason": "stubbed llm"}

    monkeypatch.setattr(app_module, "get_llm_signal", stubbed_llm_signal)
    monkeypatch.setattr(
        app_module,
        "get_stylometric_signal",
        lambda text: {"score": 0.3, "reason": "stubbed stylometric", "metrics": {}},
    )
    monkeypatch.setattr(
        app_module,
        "get_predictability_signal",
        lambda text: {"score": 0.1, "reason": "stubbed predictability", "metrics": {}},
    )


def _submit_text(client, creator_id="creator-1", text="A test submission.", llm_provider=None):
    payload = {
        "creator_id": creator_id,
        "text": text,
    }
    if llm_provider is not None:
        payload["llm_provider"] = llm_provider
    return client.post("/submit", json=payload)


def test_health_route_returns_ok(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "message": "Provenance Guard API is running",
    }


def test_llm_provider_route_returns_default_provider_info(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.get("/llm-provider")

    assert response.status_code == 200
    assert response.get_json() == {
        "default_provider": "ollama",
        "default_provider_label": "Local Ollama/Qwen",
    }


def test_submit_without_text_returns_400(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.post("/submit", json={"creator_id": "creator-1"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_submit_without_request_override_uses_env_groq(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    _stub_submit_detectors(monkeypatch, expected_provider_override=None)

    client = _create_test_app(monkeypatch, tmp_path).test_client()
    response = _submit_text(
        client,
        creator_id="creator-2",
        text="This is a test submission that should never call the real Groq API.",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["llm_provider"] == "groq"


def test_submit_without_request_override_uses_env_ollama(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    _stub_submit_detectors(monkeypatch, expected_provider_override=None)

    client = _create_test_app(monkeypatch, tmp_path).test_client()
    response = _submit_text(
        client,
        creator_id="creator-ollama-default",
        text="This request should use the env-configured Ollama provider.",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["llm_provider"] == "ollama"


def test_submit_request_override_groq_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    _stub_submit_detectors(monkeypatch, expected_provider_override="groq")

    client = _create_test_app(monkeypatch, tmp_path).test_client()
    response = _submit_text(
        client,
        creator_id="creator-override-groq",
        text="This request should explicitly choose the Groq provider.",
        llm_provider="groq",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["llm_provider"] == "groq"


def test_submit_request_override_ollama_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    _stub_submit_detectors(monkeypatch, expected_provider_override="ollama")

    client = _create_test_app(monkeypatch, tmp_path).test_client()
    response = _submit_text(
        client,
        creator_id="creator-3",
        text="This request should explicitly choose the Ollama provider.",
        llm_provider="ollama",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "classified"
    assert payload["attribution"] == "likely_human"
    assert "content_id" in payload
    assert payload["llm_provider"] == "ollama"
    assert payload["signal_scores"] == {
        "llm": 0.2,
        "stylometric": 0.3,
        "predictability": 0.1,
    }


def test_appeal_with_valid_content_id_returns_under_review_and_is_visible_in_log(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    _stub_submit_detectors(monkeypatch, expected_provider_override=None)
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    submit_response = _submit_text(
        client,
        creator_id="appeal-creator",
        text="This is a submission that will later be appealed.",
    )
    content_id = submit_response.get_json()["content_id"]

    appeal_response = client.post(
        "/appeal",
        json={
            "content_id": content_id,
            "creator_reasoning": "I wrote this text myself.",
        },
    )
    log_response = client.get("/log")

    assert appeal_response.status_code == 200
    assert appeal_response.get_json() == {
        "content_id": content_id,
        "status": "under_review",
        "message": "Appeal received.",
    }

    entries = log_response.get_json()["entries"]
    assert len(entries) == 2
    assert entries[0]["content_id"] == content_id
    assert entries[0]["status"] == "classified"
    assert entries[1]["content_id"] == content_id
    assert entries[1]["status"] == "under_review"
    assert entries[1]["appeal_reasoning"] == "I wrote this text myself."


def test_appeal_missing_fields_returns_400(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    missing_content_id = client.post(
        "/appeal",
        json={"creator_reasoning": "I wrote this text myself."},
    )
    missing_reasoning = client.post(
        "/appeal",
        json={"content_id": "missing-reason"},
    )

    assert missing_content_id.status_code == 400
    assert "error" in missing_content_id.get_json()
    assert missing_reasoning.status_code == 400
    assert "error" in missing_reasoning.get_json()


def test_appeal_unknown_content_id_returns_404(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.post(
        "/appeal",
        json={
            "content_id": "does-not-exist",
            "creator_reasoning": "This should not be found.",
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Content not found."}


def test_log_route_returns_entries_wrapper(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    _stub_submit_detectors(monkeypatch, expected_provider_override=None)
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    _submit_text(client, creator_id="log-creator", text="This is a logged submission.")
    response = client.get("/log")
    payload = response.get_json()

    assert response.status_code == 200
    assert isinstance(payload, dict)
    assert "entries" in payload
    assert isinstance(payload["entries"], list)


def test_log_route_includes_classification_and_appeal_entries(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    _stub_submit_detectors(monkeypatch, expected_provider_override=None)
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    submit_response = _submit_text(
        client,
        creator_id="log-appeal-creator",
        text="This is a submission that should create two log entries.",
    )
    content_id = submit_response.get_json()["content_id"]

    client.post(
        "/appeal",
        json={
            "content_id": content_id,
            "creator_reasoning": "Please review this classification.",
        },
    )
    entries = client.get("/log").get_json()["entries"]

    assert len(entries) == 2
    assert {entry["status"] for entry in entries} == {"classified", "under_review"}


def test_analytics_route_returns_expected_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(tmp_path / "analytics_test.db"))
    app = app_module.create_app({
        "TESTING": True,
        "RATELIMIT_ENABLED": False,
    })
    audit_log.write_submission_log(
        {
            "timestamp": "2026-06-29T00:00:00+00:00",
            "content_id": "analytics-human",
            "creator_id": "creator-human",
            "status": "classified",
            "attribution": "likely_human",
            "confidence": 0.2,
            "llm_score": 0.2,
            "stylometric_score": 0.2,
            "predictability_score": 0.2,
        }
    )
    audit_log.write_submission_log(
        {
            "timestamp": "2026-06-29T00:01:00+00:00",
            "content_id": "analytics-uncertain",
            "creator_id": "creator-uncertain",
            "status": "classified",
            "attribution": "uncertain",
            "confidence": 0.5,
            "llm_score": 0.5,
            "stylometric_score": 0.5,
            "predictability_score": 0.5,
        }
    )
    audit_log.write_submission_log(
        {
            "timestamp": "2026-06-29T00:02:00+00:00",
            "content_id": "analytics-ai",
            "creator_id": "creator-ai",
            "status": "classified",
            "attribution": "likely_ai",
            "confidence": 0.8,
            "llm_score": 0.8,
            "stylometric_score": 0.8,
            "predictability_score": 0.8,
        }
    )
    audit_log.write_appeal_log("analytics-ai", "I want this reviewed.")

    client = app.test_client()
    response = client.get("/analytics")

    assert response.status_code == 200
    assert response.get_json() == {
        "total_submissions": 3,
        "likely_ai_count": 1,
        "likely_human_count": 1,
        "uncertain_count": 1,
        "appeal_count": 1,
        "appeal_rate": 0.3333,
        "average_confidence": 0.5,
    }


def test_submit_metadata_human_process_route(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.post(
        "/submit-metadata",
        json={
            "creator_id": "metadata-human",
            "content_type": "image_metadata",
            "metadata": {
                "tool_used": "Photoshop",
                "declared_ai_assistance": False,
                "has_process_notes": True,
                "edit_history_available": True,
                "human_reviewed": True,
            },
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["metadata_attribution"] == "likely_human_process"
    assert payload["provenance_score"] < 0.4


def test_submit_metadata_ai_assisted_route(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.post(
        "/submit-metadata",
        json={
            "creator_id": "metadata-ai",
            "content_type": "image_metadata",
            "metadata": {
                "tool_used": "Midjourney",
                "declared_ai_assistance": True,
                "has_process_notes": False,
                "edit_history_available": False,
                "human_reviewed": False,
            },
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["metadata_attribution"] == "likely_ai_assisted"
    assert payload["provenance_score"] >= 0.8


def test_submit_metadata_missing_metadata_returns_400(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.post(
        "/submit-metadata",
        json={
            "creator_id": "metadata-missing",
            "content_type": "image_metadata",
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_verify_creator_route_returns_verified_certificate(monkeypatch, tmp_path):
    monkeypatch.setattr(
        verification,
        "VERIFIED_CREATORS_PATH",
        tmp_path / "verified_creators.json",
    )
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.post(
        "/verify-creator",
        json={
            "creator_id": "verified-creator",
            "verification_method": "writing_sample_review",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["creator_id"] == "verified-creator"
    assert payload["verified"] is True
    assert payload["verification_method"] == "writing_sample_review"
    assert "certificate_label" in payload


def test_verify_creator_missing_creator_id_returns_400(monkeypatch, tmp_path):
    client = _create_test_app(monkeypatch, tmp_path).test_client()

    response = client.post(
        "/verify-creator",
        json={"verification_method": "writing_sample_review"},
    )

    assert response.status_code == 400
    assert "error" in response.get_json()
