from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from analytics import get_analytics
from audit_log import (
    find_submission_by_content_id,
    get_log,
    write_appeal_log,
    write_submission_log,
)
from detectors.llm_signal import get_llm_signal
from detectors.predictability_signal import get_predictability_signal
from detectors.stylometric_signal import get_stylometric_signal
from labels import generate_label
from scoring import combine_scores

app = Flask(__name__)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=[],
)


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

    if not creator_id or not text:
        return jsonify({
            "error": "Both 'creator_id' and 'text' are required."
        }), 400

    llm_signal = get_llm_signal(text)
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
        "status": status
    })


if __name__ == "__main__":
    app.run(debug=True)
