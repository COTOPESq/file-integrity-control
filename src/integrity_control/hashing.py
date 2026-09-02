from __future__ import annotations

import hashlib
from pathlib import Path


DEFAULT_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Calculate SHA-256 for a file without loading it fully into memory."""
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)

    return digest.hexdigest()


def is_inside_path(candidate: Path, parent: Path) -> bool:
    """Return True when candidate is located inside parent or equals parent."""
    try:
        candidate.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
