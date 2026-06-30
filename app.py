from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from analytics import get_analytics
from audit_log import (
    find_submission_by_content_id,
    get_log,
    init_db,
    write_appeal_log,
    write_submission_log,
)
from detectors.llm_signal import (
    get_default_provider,
    get_effective_provider,
    get_llm_signal,
    get_provider_label,
)
from detectors.predictability_signal import get_predictability_signal
from detectors.stylometric_signal import get_stylometric_signal
from labels import generate_label
from metadata_signal import analyze_metadata
from scoring import combine_scores
from verification import verify_creator

def register_routes(app: Flask, limiter: Limiter) -> None:
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({
            "status": "ok",
            "message": "Provenance Guard API is running"
        })

    @app.get("/log")
    def log():
        return jsonify({"entries": get_log()})

    @app.get("/analytics")
    def analytics():
        entries = get_log()
        return jsonify(get_analytics(entries))

    @app.get("/llm-provider")
    def llm_provider():
        default_provider = get_default_provider()
        return jsonify({
            "default_provider": default_provider,
            "default_provider_label": get_provider_label(default_provider),
        })

    @app.post("/verify-creator")
    def verify_creator_route():
        payload = request.get_json(silent=True) or {}
        creator_id = payload.get("creator_id")
        verification_method = payload.get("verification_method")

        if not creator_id or not verification_method:
            return jsonify({
                "error": "Both 'creator_id' and 'verification_method' are required."
            }), 400

        return jsonify(verify_creator(creator_id, verification_method))

    @app.post("/appeal")
    def appeal():
        payload = request.get_json(silent=True) or {}
        content_id = payload.get("content_id")
        creator_reasoning = payload.get("creator_reasoning")

        if not content_id or not creator_reasoning:
            return jsonify({
                "error": "Both 'content_id' and 'creator_reasoning' are required."
            }), 400

        if find_submission_by_content_id(content_id) is None:
            return jsonify({
                "error": "Content not found."
            }), 404

        write_appeal_log(content_id, creator_reasoning)

        return jsonify({
            "content_id": content_id,
            "status": "under_review",
            "message": "Appeal received."
        })

    @app.post("/submit")
    @limiter.limit("10 per minute;50 per day")
    def submit():
        payload = request.get_json(silent=True) or {}
        creator_id = payload.get("creator_id")
        text = payload.get("text")
        provider_override = payload.get("llm_provider")

        if not creator_id or not text:
            return jsonify({
                "error": "Both 'creator_id' and 'text' are required."
            }), 400

        llm_signal = get_llm_signal(text, provider_override)
        llm_provider = get_effective_provider(provider_override)
        llm_latency_ms = llm_signal.get("latency_ms")
        stylometric_signal = get_stylometric_signal(text)
        predictability_signal = get_predictability_signal(text)
        combined_result = combine_scores(
            llm_signal,
            stylometric_signal,
            predictability_signal,
        )

        confidence = combined_result["confidence"]
        attribution = combined_result["attribution"]
        content_id = uuid4().hex
        status = "classified"

        write_submission_log({
            "content_id": content_id,
            "creator_id": creator_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attribution": attribution,
            "confidence": confidence,
            "llm_score": llm_signal["score"],
            "llm_provider": llm_provider,
            "llm_latency_ms": llm_latency_ms,
            "stylometric_score": stylometric_signal["score"],
            "predictability_score": predictability_signal["score"],
            "status": status,
        })

        return jsonify({
            "content_id": content_id,
            "attribution": attribution,
            "confidence": confidence,
            "signal_scores": combined_result["signal_scores"],
            "label": generate_label(attribution, confidence),
            "llm_provider": llm_provider,
            "llm_latency_ms": llm_latency_ms,
            "status": status
        })

    @app.post("/submit-metadata")
    def submit_metadata():
        payload = request.get_json(silent=True) or {}
        creator_id = payload.get("creator_id")
        content_type = payload.get("content_type")
        metadata = payload.get("metadata")

        if not creator_id or not content_type or metadata is None:
            return jsonify({
                "error": "Fields 'creator_id', 'content_type', and 'metadata' are required."
            }), 400

        metadata_result = analyze_metadata(metadata)
        content_id = uuid4().hex

        return jsonify({
            "content_id": content_id,
            "creator_id": creator_id,
            "content_type": content_type,
            "provenance_score": metadata_result["provenance_score"],
            "metadata_attribution": metadata_result["metadata_attribution"],
            "reason": metadata_result["reason"],
            "metadata_checks": metadata_result["metadata_checks"],
            "status": "classified",
        })


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if config:
        app.config.update(config)

    init_db()

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        storage_uri="memory://",
        default_limits=[],
        enabled=app.config.get("RATELIMIT_ENABLED", True),
    )
    app.extensions["provenance_guard_limiter"] = limiter
    register_routes(app, limiter)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
