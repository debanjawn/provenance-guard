import json
from pathlib import Path


AUDIT_LOG_PATH = Path(__file__).resolve().parent / "audit_log.json"


def write_submission_log(entry: dict) -> None:
    if AUDIT_LOG_PATH.exists():
        try:
            existing_entries = json.loads(AUDIT_LOG_PATH.read_text(encoding="utf-8"))
            if not isinstance(existing_entries, list):
                existing_entries = []
        except (json.JSONDecodeError, OSError):
            existing_entries = []
    else:
        existing_entries = []

    existing_entries.append(entry)
    AUDIT_LOG_PATH.write_text(
        json.dumps(existing_entries, indent=2),
        encoding="utf-8",
    )
