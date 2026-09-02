from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import FileRecord, utc_now_iso


SCHEMA_VERSION = 1
HASH_ALGORITHM = "SHA-256"


def save_hash_database(
    records: dict[str, FileRecord],
    database_path: Path,
    controlled_folder: Path,
) -> None:
    """Save file hash records to a JSON database."""
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": HASH_ALGORITHM,
        "created_at": utc_now_iso(),
        "controlled_folder": str(controlled_folder.resolve()),
        "files": [records[path].to_dict() for path in sorted(records)],
    }

    database_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_hash_database(database_path: Path) -> tuple[dict[str, FileRecord], dict[str, Any]]:
    """Load a JSON hash database and return records plus metadata."""
    database_path = database_path.resolve()
    raw = json.loads(database_path.read_text(encoding="utf-8"))

    if int(raw.get("schema_version", 0)) != SCHEMA_VERSION:
        raise ValueError("Неподдерживаемая версия базы хэшей")

    if raw.get("algorithm") != HASH_ALGORITHM:
        raise ValueError("База создана для другого алгоритма хэширования")

    records = {
        record.path: record
        for record in (FileRecord.from_dict(item) for item in raw.get("files", []))
    }
    metadata = {
        "schema_version": raw["schema_version"],
        "algorithm": raw["algorithm"],
        "created_at": raw["created_at"],
        "controlled_folder": raw.get("controlled_folder", ""),
    }
    return records, metadata
