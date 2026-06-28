import json
from datetime import datetime, timezone
from pathlib import Path


VERIFIED_CREATORS_PATH = Path(__file__).resolve().parent / "verified_creators.json"
CERTIFICATE_LABEL = (
    "Verified creator: this creator completed an additional provenance check. "
    "This does not guarantee authorship of a specific submission, but it provides "
    "extra context."
)


def _read_verified_creators() -> list[dict]:
    if not VERIFIED_CREATORS_PATH.exists():
        return []

    try:
        creators = json.loads(VERIFIED_CREATORS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    return creators if isinstance(creators, list) else []


def _write_verified_creators(creators: list[dict]) -> None:
    VERIFIED_CREATORS_PATH.write_text(
        json.dumps(creators, indent=2),
        encoding="utf-8",
    )


def get_creator_verification(creator_id: str) -> dict:
    for creator in _read_verified_creators():
        if creator.get("creator_id") == creator_id:
            return creator
    return {}


def verify_creator(creator_id: str, verification_method: str) -> dict:
    creators = _read_verified_creators()
    verification_record = {
        "creator_id": creator_id,
        "verified": True,
        "verification_method": verification_method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "certificate_label": CERTIFICATE_LABEL,
    }

    updated_creators = [
        creator for creator in creators
        if creator.get("creator_id") != creator_id
    ]
    updated_creators.append(verification_record)
    _write_verified_creators(updated_creators)

    return verification_record
