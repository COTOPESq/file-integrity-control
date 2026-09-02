from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    """Return current UTC time in a stable ISO-8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class FileRecord:
    """Information saved for one controlled file."""

    path: str
    sha256: str
    size: int
    modified_at: str

    @classmethod
    def from_file(cls, root: Path, file_path: Path, sha256: str) -> "FileRecord":
        stat = file_path.stat()
        relative_path = file_path.relative_to(root).as_posix()
        modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        return cls(
            path=relative_path,
            sha256=sha256,
            size=stat.st_size,
            modified_at=modified_at.replace(microsecond=0).isoformat(),
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FileRecord":
        return cls(
            path=str(raw["path"]),
            sha256=str(raw["sha256"]),
            size=int(raw["size"]),
            modified_at=str(raw["modified_at"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size": self.size,
            "modified_at": self.modified_at,
        }


@dataclass(frozen=True)
class ChangeRecord:
    """Difference detected for a file that existed in the baseline."""

    path: str
    old_sha256: str
    new_sha256: str
    old_size: int
    new_size: int


@dataclass(frozen=True)
class IntegrityReport:
    """Result of comparing a saved hash database with the current folder."""

    generated_at: str
    controlled_folder: str
    database_path: str
    new_files: list[FileRecord]
    changed_files: list[ChangeRecord]
    deleted_files: list[FileRecord]
    unchanged_files: list[str]
    total_current_files: int

    @property
    def has_violations(self) -> bool:
        return bool(self.new_files or self.changed_files or self.deleted_files)

    @property
    def status(self) -> str:
        return "НАРУШЕНИЯ ОБНАРУЖЕНЫ" if self.has_violations else "ЦЕЛОСТНОСТЬ ПОДТВЕРЖДЕНА"

    def summary(self) -> dict[str, int]:
        return {
            "total_current_files": self.total_current_files,
            "unchanged": len(self.unchanged_files),
            "new": len(self.new_files),
            "changed": len(self.changed_files),
            "deleted": len(self.deleted_files),
        }
