from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, request

from audit_log import get_log, write_submission_log
from detectors.llm_signal import get_llm_signal

app = Flask(__name__)


def _get_attribution(score: float) -> str:
    if score >= 0.80:
        return "likely_ai"
    if score >= 0.40:
        return "uncertain"
    return "likely_human"


def _get_label(attribution: str) -> str:
    if attribution == "likely_ai":
        return "This text shows strong signs of AI generation based on the signal reviewed."
    if attribution == "likely_human":
        return "This text appears more consistent with human-written work based on the signal reviewed."
    return "We are not confident enough to determine whether this text was written by a person or generated with AI."


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Provenance Guard API is running"
    })


@app.get("/log")
def log():
    return jsonify({"entries": get_log()})


@app.post("/submit")
def submit():
    payload = request.get_json(silent=True) or {}
    creator_id = payload.get("creator_id")
    text = payload.get("text")

    if not creator_id or not text:
        return jsonify({
            "error": "Both 'creator_id' and 'text' are required."
        }), 400

    llm_signal = get_llm_signal(text)
    confidence = llm_signal["score"]
    attribution = _get_attribution(confidence)
    content_id = uuid4().hex
    status = "classified"

    write_submission_log({
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_signal["score"],
        "status": status,
    })

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": confidence,
        "signal_scores": {
            "llm": llm_signal["score"]
        },
        "label": _get_label(attribution),
        "status": status
    })


if __name__ == "__main__":
    app.run(debug=True)
