import json
from pathlib import Path
from datetime import datetime, timezone


AUDIT_LOG_PATH = Path(__file__).resolve().parent / "audit_log.json"


def get_log() -> list:
    if not AUDIT_LOG_PATH.exists():
        return []

    try:
        entries = json.loads(AUDIT_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    return entries if isinstance(entries, list) else []


def _write_log(entries: list) -> None:
    AUDIT_LOG_PATH.write_text(
        json.dumps(entries, indent=2),
        encoding="utf-8",
    )


def find_submission_by_content_id(content_id: str) -> dict | None:
    for entry in get_log():
        if entry.get("content_id") == content_id and entry.get("status") == "classified":
            return entry
    return None


def write_submission_log(entry: dict) -> None:
    existing_entries = get_log()
    existing_entries.append(entry)
    _write_log(existing_entries)


def write_appeal_log(content_id: str, appeal_reasoning: str) -> dict | None:
    original_submission = find_submission_by_content_id(content_id)
    if original_submission is None:
        return None

    entries = get_log()
    appeal_entry = {
        "content_id": content_id,
        "creator_id": original_submission.get("creator_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_attribution": original_submission.get("attribution"),
        "original_confidence": original_submission.get("confidence"),
        "appeal_reasoning": appeal_reasoning,
        "status": "under_review",
    }
    entries.append(appeal_entry)
    _write_log(entries)
    return appeal_entry
