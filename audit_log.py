import json
from pathlib import Path


AUDIT_LOG_PATH = Path(__file__).resolve().parent / "audit_log.json"


def get_log() -> list:
    if not AUDIT_LOG_PATH.exists():
        return []

    try:
        entries = json.loads(AUDIT_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    return entries if isinstance(entries, list) else []


def write_submission_log(entry: dict) -> None:
    existing_entries = get_log()
    existing_entries.append(entry)
    AUDIT_LOG_PATH.write_text(
        json.dumps(existing_entries, indent=2),
        encoding="utf-8",
    )
