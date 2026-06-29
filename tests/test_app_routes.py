import importlib
import sys


def _load_app_module(monkeypatch, tmp_path):
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(tmp_path / "routes_test.db"))
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_health_route_returns_ok(monkeypatch, tmp_path):
    app_module = _load_app_module(monkeypatch, tmp_path)
    client = app_module.app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "message": "Provenance Guard API is running",
    }


def test_submit_without_text_returns_400(monkeypatch, tmp_path):
    app_module = _load_app_module(monkeypatch, tmp_path)
    client = app_module.app.test_client()

    response = client.post("/submit", json={"creator_id": "creator-1"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_submit_uses_monkeypatched_detectors_without_real_network(monkeypatch, tmp_path):
    app_module = _load_app_module(monkeypatch, tmp_path)
    monkeypatch.setattr(
        app_module,
        "get_llm_signal",
        lambda text: {"score": 0.2, "reason": "stubbed llm"},
    )
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

    client = app_module.app.test_client()
    response = client.post(
        "/submit",
        json={
            "creator_id": "creator-2",
            "text": "This is a test submission that should never call the real Groq API.",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "classified"
    assert payload["attribution"] == "likely_human"
    assert "content_id" in payload
    assert payload["signal_scores"] == {
        "llm": 0.2,
        "stylometric": 0.3,
        "predictability": 0.1,
    }
