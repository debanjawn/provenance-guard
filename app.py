from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Provenance Guard API is running"
    })


@app.post("/submit")
def submit():
    payload = request.get_json(silent=True) or {}
    creator_id = payload.get("creator_id")
    text = payload.get("text")

    if not creator_id or not text:
        return jsonify({
            "error": "Both 'creator_id' and 'text' are required."
        }), 400

    return jsonify({
        "content_id": "abc123",
        "attribution": "uncertain",
        "confidence": 0.62,
        "signal_scores": {
            "llm": 0.70,
            "stylometric": 0.55,
            "predictability": 0.58
        },
        "label": "We are not confident enough to determine whether this text was written by a person or generated with AI.",
        "status": "classified"
    })


if __name__ == "__main__":
    app.run(debug=True)
