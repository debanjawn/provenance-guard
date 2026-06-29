import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "provenance_guard.db"

ENTRY_COLUMNS = (
    "timestamp",
    "content_id",
    "creator_id",
    "status",
    "attribution",
    "confidence",
    "llm_score",
    "stylometric_score",
    "predictability_score",
    "label",
    "original_attribution",
    "original_confidence",
    "appeal_reasoning",
    "entry_type",
)


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                content_id TEXT,
                creator_id TEXT,
                status TEXT,
                attribution TEXT,
                confidence REAL,
                llm_score REAL,
                stylometric_score REAL,
                predictability_score REAL,
                label TEXT,
                original_attribution TEXT,
                original_confidence REAL,
                appeal_reasoning TEXT,
                entry_type TEXT NOT NULL
            )
            """
        )
        connection.commit()


def _get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _row_to_entry(row: sqlite3.Row) -> dict:
    entry = {}
    for column in ENTRY_COLUMNS:
        value = row[column]
        if value is not None:
            entry[column] = value
    return entry


def get_log() -> list:
    init_db()
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                timestamp,
                content_id,
                creator_id,
                status,
                attribution,
                confidence,
                llm_score,
                stylometric_score,
                predictability_score,
                label,
                original_attribution,
                original_confidence,
                appeal_reasoning,
                entry_type
            FROM audit_entries
            ORDER BY id ASC
            """
        ).fetchall()
    return [_row_to_entry(row) for row in rows]


def find_submission_by_content_id(content_id: str) -> dict | None:
    init_db()
    with _get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                timestamp,
                content_id,
                creator_id,
                status,
                attribution,
                confidence,
                llm_score,
                stylometric_score,
                predictability_score,
                label,
                original_attribution,
                original_confidence,
                appeal_reasoning,
                entry_type
            FROM audit_entries
            WHERE content_id = ? AND status = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (content_id, "classified"),
        ).fetchone()
    return _row_to_entry(row) if row else None


def write_submission_log(entry: dict) -> None:
    init_db()
    payload = {column: entry.get(column) for column in ENTRY_COLUMNS}
    payload["entry_type"] = entry.get("entry_type", "classification")

    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_entries (
                timestamp,
                content_id,
                creator_id,
                status,
                attribution,
                confidence,
                llm_score,
                stylometric_score,
                predictability_score,
                label,
                original_attribution,
                original_confidence,
                appeal_reasoning,
                entry_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(payload[column] for column in ENTRY_COLUMNS),
        )
        connection.commit()


def write_appeal_log(content_id: str, appeal_reasoning: str) -> dict | None:
    original_submission = find_submission_by_content_id(content_id)
    if original_submission is None:
        return None

    appeal_entry = {
        "content_id": content_id,
        "creator_id": original_submission.get("creator_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_attribution": original_submission.get("attribution"),
        "original_confidence": original_submission.get("confidence"),
        "appeal_reasoning": appeal_reasoning,
        "status": "under_review",
        "entry_type": "appeal",
    }

    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_entries (
                timestamp,
                content_id,
                creator_id,
                status,
                attribution,
                confidence,
                llm_score,
                stylometric_score,
                predictability_score,
                label,
                original_attribution,
                original_confidence,
                appeal_reasoning,
                entry_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(appeal_entry.get(column) for column in ENTRY_COLUMNS),
        )
        connection.commit()

    return {key: value for key, value in appeal_entry.items() if value is not None}
