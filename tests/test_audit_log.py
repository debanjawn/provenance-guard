import sqlite3
from concurrent.futures import ThreadPoolExecutor

import audit_log


def test_init_db_creates_audit_entries_table(tmp_path, monkeypatch):
    db_path = tmp_path / "test_audit.db"
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(db_path))

    audit_log.init_db()

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'audit_entries'"
        ).fetchone()

    assert row is not None


def test_write_log_entry_stores_a_classification_entry(tmp_path, monkeypatch):
    db_path = tmp_path / "test_audit.db"
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(db_path))
    audit_log.init_db()

    audit_log.write_log_entry(
        {
            "timestamp": "2026-06-29T00:00:00+00:00",
            "content_id": "content-123",
            "creator_id": "creator-123",
            "status": "classified",
            "attribution": "likely_human",
            "confidence": 0.2222,
            "llm_score": 0.2,
            "stylometric_score": 0.3,
            "predictability_score": 0.1,
            "entry_type": "classification",
        }
    )

    entries = audit_log.get_log()

    assert len(entries) == 1
    assert entries[0]["content_id"] == "content-123"
    assert entries[0]["status"] == "classified"
    assert entries[0]["entry_type"] == "classification"


def test_get_log_omits_none_fields(tmp_path, monkeypatch):
    db_path = tmp_path / "test_audit.db"
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(db_path))
    audit_log.init_db()

    audit_log.write_log_entry(
        {
            "timestamp": "2026-06-29T00:00:00+00:00",
            "content_id": "content-456",
            "creator_id": "creator-456",
            "status": "classified",
            "attribution": "uncertain",
            "confidence": 0.5,
            "llm_score": 0.5,
            "stylometric_score": 0.5,
            "predictability_score": 0.5,
            "label": None,
            "entry_type": "classification",
        }
    )

    entry = audit_log.get_log()[0]

    assert "label" not in entry
    assert "appeal_reasoning" not in entry
    assert "original_attribution" not in entry


def test_appeal_entries_can_be_stored_and_retrieved(tmp_path, monkeypatch):
    db_path = tmp_path / "test_audit.db"
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(db_path))
    audit_log.init_db()

    audit_log.write_submission_log(
        {
            "timestamp": "2026-06-29T00:00:00+00:00",
            "content_id": "content-789",
            "creator_id": "creator-789",
            "status": "classified",
            "attribution": "likely_ai",
            "confidence": 0.88,
            "llm_score": 0.9,
            "stylometric_score": 0.8,
            "predictability_score": 0.9,
        }
    )

    appeal_entry = audit_log.write_appeal_log("content-789", "I wrote this myself.")
    entries = audit_log.get_log()

    assert appeal_entry is not None
    assert len(entries) == 2
    assert entries[1]["entry_type"] == "appeal"
    assert entries[1]["status"] == "under_review"
    assert entries[1]["appeal_reasoning"] == "I wrote this myself."
    assert entries[1]["original_attribution"] == "likely_ai"


def test_multiple_classification_entries_can_be_written_quickly(tmp_path, monkeypatch):
    db_path = tmp_path / "test_concurrent_audit.db"
    monkeypatch.setenv("PROVENANCE_GUARD_DB_PATH", str(db_path))
    audit_log.init_db()

    def write_entry(index: int) -> None:
        audit_log.write_log_entry(
            {
                "timestamp": f"2026-06-29T00:00:{index:02d}+00:00",
                "content_id": f"content-{index}",
                "creator_id": f"creator-{index}",
                "status": "classified",
                "attribution": "uncertain",
                "confidence": 0.5,
                "llm_score": 0.5,
                "stylometric_score": 0.5,
                "predictability_score": 0.5,
                "entry_type": "classification",
            }
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(write_entry, range(10)))

    entries = audit_log.get_log()

    assert len(entries) == 10
    assert {entry["content_id"] for entry in entries} == {f"content-{index}" for index in range(10)}
