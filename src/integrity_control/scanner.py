from __future__ import annotations

from pathlib import Path

from .hashing import is_inside_path, sha256_file
from .models import ChangeRecord, FileRecord, IntegrityReport, utc_now_iso


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def _resolve_ignored_paths(paths: set[Path] | None) -> set[Path]:
    if not paths:
        return set()
    return {path.resolve() for path in paths}


def _should_skip(path: Path, root: Path, ignored_paths: set[Path], excluded_dirs: set[str]) -> bool:
    if path.is_symlink():
        return True

    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    if any(part in excluded_dirs for part in relative.parts[:-1]):
        return True

    resolved = path.resolve()
    for ignored in ignored_paths:
        if resolved == ignored or is_inside_path(resolved, ignored):
            return True

    return False


def iter_controlled_files(
    root: Path,
    ignored_paths: set[Path] | None = None,
    excluded_dirs: set[str] | None = None,
) -> list[Path]:
    """Return a sorted list of regular files that must be hashed."""
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Папка не найдена: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Путь не является папкой: {root}")

    ignored = _resolve_ignored_paths(ignored_paths)
    excluded = excluded_dirs or DEFAULT_EXCLUDED_DIRS
    files: list[Path] = []

    for path in root.rglob("*"):
        if path.is_file() and not _should_skip(path, root, ignored, excluded):
            files.append(path.resolve())

    return sorted(files, key=lambda file_path: file_path.relative_to(root).as_posix().lower())


def scan_folder(
    root: Path,
    ignored_paths: set[Path] | None = None,
    excluded_dirs: set[str] | None = None,
) -> dict[str, FileRecord]:
    """Calculate hashes for all controlled files in a folder."""
    root = root.resolve()
    records: dict[str, FileRecord] = {}

    for file_path in iter_controlled_files(root, ignored_paths, excluded_dirs):
        file_hash = sha256_file(file_path)
        record = FileRecord.from_file(root, file_path, file_hash)
        records[record.path] = record

    return records


def compare_records(
    baseline: dict[str, FileRecord],
    current: dict[str, FileRecord],
    controlled_folder: Path,
    database_path: Path,
) -> IntegrityReport:
    """Compare saved records with current records and build a report object."""
    baseline_paths = set(baseline)
    current_paths = set(current)

    new_files = [current[path] for path in sorted(current_paths - baseline_paths)]
    deleted_files = [baseline[path] for path in sorted(baseline_paths - current_paths)]
    unchanged_files: list[str] = []
    changed_files: list[ChangeRecord] = []

    for path in sorted(baseline_paths & current_paths):
        old_record = baseline[path]
        new_record = current[path]

        if old_record.sha256 == new_record.sha256:
            unchanged_files.append(path)
            continue

        changed_files.append(
            ChangeRecord(
                path=path,
                old_sha256=old_record.sha256,
                new_sha256=new_record.sha256,
                old_size=old_record.size,
                new_size=new_record.size,
            )
        )

    return IntegrityReport(
        generated_at=utc_now_iso(),
        controlled_folder=str(controlled_folder.resolve()),
        database_path=str(database_path.resolve()),
        new_files=new_files,
        changed_files=changed_files,
        deleted_files=deleted_files,
        unchanged_files=unchanged_files,
        total_current_files=len(current),
    )
