"""Bounded, non-following filesystem snapshotting for hostile artifact input."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat
from typing import Iterator
import unicodedata

from .errors import InputRejected, LimitExceeded, PathRejected


DIRECTORY_DIGEST_ALGORITHM = "capabilityproof-directory-sha256-v1"
EXCLUDED_DIRECTORY_NAMES = frozenset({".git", ".hg", ".svn"})


@dataclass(frozen=True)
class ScanLimits:
    max_files: int = 1_000
    max_entries: int = 2_000
    max_directories: int = 256
    max_depth: int = 32
    max_path_bytes: int = 1_024
    max_references: int = 1_000
    max_dependencies: int = 1_000
    max_referenced_hosts: int = 500
    max_requirement_evidence_per_kind: int = 20
    max_total_bytes: int = 25_000_000
    max_file_bytes: int = 2_000_000
    max_skill_md_bytes: int = 1_000_000
    max_text_bytes: int = 1_000_000
    max_findings: int = 500
    max_findings_per_rule: int = 30

    def __post_init__(self) -> None:
        ceilings = {
            "max_files": 1_000,
            "max_entries": 2_000,
            "max_directories": 256,
            "max_depth": 32,
            "max_path_bytes": 1_024,
            "max_references": 1_000,
            "max_dependencies": 1_000,
            "max_referenced_hosts": 500,
            "max_requirement_evidence_per_kind": 20,
            "max_total_bytes": 25_000_000,
            "max_file_bytes": 2_000_000,
            "max_skill_md_bytes": 1_000_000,
            "max_text_bytes": 1_000_000,
            "max_findings": 500,
            "max_findings_per_rule": 30,
        }
        for field_name, ceiling in ceilings.items():
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= ceiling:
                raise ValueError(f"{field_name} must be an integer from 1 through {ceiling}")
        if self.max_files > self.max_entries or self.max_directories > self.max_entries:
            raise ValueError("file and directory limits may not exceed max_entries")
        if self.max_findings_per_rule > self.max_findings:
            raise ValueError("max_findings_per_rule may not exceed max_findings")


@dataclass(frozen=True)
class FileData:
    path: str
    size: int
    sha256: str
    content: bytes


@dataclass(frozen=True)
class Snapshot:
    root: Path
    files: tuple[FileData, ...]
    total_bytes: int
    directory_sha256: str
    excluded_paths: tuple[str, ...]
    capture_started_at: str
    capture_completed_at: str
    capture_timestamp_source: str

    def get(self, relative_path: str) -> FileData | None:
        for item in self.files:
            if item.path == relative_path:
                return item
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    """Return true for POSIX links and Windows reparse points such as junctions."""

    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(reparse_flag and file_attributes & reparse_flag)


def _entry_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
        getattr(metadata, "st_nlink", 1),
    )


def _validate_relative_path(relative: str, limits: ScanLimits) -> None:
    try:
        encoded = relative.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise PathRejected("artifact path is not valid Unicode") from exc
    if not relative or len(encoded) > limits.max_path_bytes:
        raise PathRejected(f"artifact path exceeds the {limits.max_path_bytes} byte limit")
    if unicodedata.normalize("NFC", relative) != relative:
        raise PathRejected(f"artifact path is not Unicode NFC: {relative[:200]}")
    if "\\" in relative or any(ord(character) < 32 or ord(character) == 127 for character in relative):
        raise PathRejected(f"artifact path contains a disallowed character: {relative[:200]}")


def resolve_operator_root(path: str | Path) -> Path:
    supplied = Path(path).expanduser()
    try:
        metadata = os.lstat(supplied)
    except OSError as exc:
        raise PathRejected("configured root does not exist") from exc
    if _is_link_or_reparse(metadata):
        raise PathRejected("configured root may not be a symbolic link or reparse point")
    try:
        root = supplied.resolve(strict=True)
    except OSError as exc:
        raise PathRejected("configured root does not exist") from exc
    if not root.is_dir():
        raise PathRejected("configured root must be a directory")
    return root


def resolve_allowed_path(allowed_root: Path, submitted_path: str) -> Path:
    """Resolve an API/MCP relative path without allowing drive or traversal escape."""

    if not isinstance(submitted_path, str) or not submitted_path.strip():
        raise PathRejected("path must be a non-empty string")
    if "\x00" in submitted_path:
        raise PathRejected("path contains a null byte")
    try:
        submitted_bytes = submitted_path.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise PathRejected("path is not valid Unicode") from exc
    if len(submitted_bytes) > 4_096:
        raise PathRejected("path exceeds the 4096 byte request limit")
    if unicodedata.normalize("NFC", submitted_path) != submitted_path:
        raise PathRejected("path is not Unicode NFC")
    if any(ord(character) < 32 or ord(character) == 127 for character in submitted_path):
        raise PathRejected("path contains a disallowed control character")

    # On Windows, Path('/tmp') and PureWindowsPath('C:\\x') have different edge cases.
    normalized = submitted_path.replace("\\", "/")
    if normalized.startswith("/") or (len(normalized) >= 2 and normalized[1] == ":"):
        raise PathRejected("path must be relative to the configured root")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PathRejected("path must not contain empty, current-directory, or parent-directory segments")
    if len(parts) > 32 or ":" in parts[0]:
        raise PathRejected("path has too many segments or resembles a URI/drive path")

    root = resolve_operator_root(allowed_root)
    lexical_candidate = root.joinpath(*parts)
    candidate = lexical_candidate.resolve(strict=True)
    if not _is_relative_to(candidate, root):
        raise PathRejected("path escapes the configured root")
    current = root
    for part in parts:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise PathRejected("path does not exist beneath the configured root") from exc
        if _is_link_or_reparse(metadata):
            raise PathRejected("path traverses a symbolic link or reparse point")
    return lexical_candidate


def _iter_entries(root: Path, limits: ScanLimits) -> Iterator[tuple[Path, os.DirEntry[str], os.stat_result, int]]:
    pending = [(root, 0)]
    entry_count = 0
    directory_count = 0
    while pending:
        directory, depth = pending.pop()
        if depth > limits.max_depth:
            raise LimitExceeded(f"artifact exceeds the {limits.max_depth} directory-depth limit")
        directory_count += 1
        if directory_count > limits.max_directories:
            raise LimitExceeded(f"artifact exceeds the {limits.max_directories} directory limit")
        try:
            directory_metadata = os.lstat(directory)
        except OSError as exc:
            raise InputRejected("artifact directory could not be stated", code="read_failed") from exc
        if _is_link_or_reparse(directory_metadata):
            raise PathRejected("symbolic links and reparse points are not allowed")
        if not stat.S_ISDIR(directory_metadata.st_mode):
            raise InputRejected("artifact directory changed during capture", code="input_changed")
        try:
            with os.scandir(directory) as iterator:
                entries: list[os.DirEntry[str]] = []
                for entry in iterator:
                    entry_count += 1
                    if entry_count > limits.max_entries:
                        raise LimitExceeded(f"artifact exceeds the {limits.max_entries} entry limit")
                    entries.append(entry)
            entries.sort(key=lambda entry: (entry.name.casefold(), entry.name))
        except OSError as exc:
            raise InputRejected("artifact directory could not be enumerated", code="read_failed") from exc

        child_directories: list[tuple[Path, int]] = []
        for entry in entries:
            try:
                metadata = os.lstat(entry.path)
            except OSError as exc:
                raise InputRejected("artifact entry could not be stated", code="read_failed") from exc
            if _is_link_or_reparse(metadata):
                relative = Path(entry.path).relative_to(root).as_posix()
                raise PathRejected(f"symbolic links and reparse points are not allowed: {relative}")
            is_directory = stat.S_ISDIR(metadata.st_mode)
            if entry.name not in EXCLUDED_DIRECTORY_NAMES and is_directory:
                child_directories.append((Path(entry.path), depth + 1))
            yield directory, entry, metadata, depth
        pending.extend(reversed(child_directories))


def _inventory_signature(root: Path, limits: ScanLimits) -> tuple[tuple[str, tuple[int, int, int, int, int, int]], ...]:
    inventory: list[tuple[str, tuple[int, int, int, int, int, int]]] = []
    for _, entry, metadata, _ in _iter_entries(root, limits):
        relative = Path(entry.path).relative_to(root).as_posix()
        _validate_relative_path(relative, limits)
        inventory.append((relative, _entry_identity(metadata)))
    inventory.sort(key=lambda item: item[0].encode("utf-8"))
    return tuple(inventory)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collect_snapshot(
    path: str | Path,
    limits: ScanLimits | None = None,
    *,
    time_override: datetime | None = None,
) -> Snapshot:
    limits = limits or ScanLimits()
    if time_override is not None:
        capture_started_at = _utc_iso(time_override)
        capture_timestamp_source = "caller-supplied-reproducibility-override"
    else:
        capture_started_at = _utc_iso(datetime.now(timezone.utc))
        capture_timestamp_source = "system-clock"
    try:
        root = resolve_operator_root(path)
    except PathRejected as exc:
        raise PathRejected(str(exc).replace("configured root", "artifact root")) from exc
    _validate_relative_path(root.name, limits)
    if len(root.name) > 255:
        raise PathRejected("artifact root name exceeds 255 characters")

    files: list[FileData] = []
    excluded: list[str] = []
    total_bytes = 0
    normalized_paths: set[str] = set()
    initial_inventory: list[tuple[str, tuple[int, int, int, int, int, int]]] = []

    for directory, entry, entry_metadata, _ in _iter_entries(root, limits):
        entry_path = Path(entry.path)
        relative = entry_path.relative_to(root).as_posix()
        _validate_relative_path(relative, limits)
        initial_inventory.append((relative, _entry_identity(entry_metadata)))

        folded = relative.casefold()
        if folded in normalized_paths:
            raise PathRejected(f"case-insensitive path collision: {relative}")
        normalized_paths.add(folded)

        if entry.name in EXCLUDED_DIRECTORY_NAMES and stat.S_ISDIR(entry_metadata.st_mode):
            excluded.append(f"{relative}/")
            continue
        if stat.S_ISDIR(entry_metadata.st_mode):
            continue
        if not stat.S_ISREG(entry_metadata.st_mode):
            raise PathRejected(f"special filesystem entries are not allowed: {relative}")
        if getattr(entry_metadata, "st_nlink", 1) != 1:
            raise PathRejected(f"hard-linked files are not allowed: {relative}")

        if len(files) >= limits.max_files:
            raise LimitExceeded(f"artifact exceeds the {limits.max_files} file limit")
        try:
            path_before = os.lstat(entry_path)
        except OSError as exc:
            raise InputRejected(f"could not stat artifact file: {relative}", code="read_failed") from exc
        if _is_link_or_reparse(path_before) or not stat.S_ISREG(path_before.st_mode):
            raise InputRejected(f"artifact file type changed before capture: {relative}", code="input_changed")
        if path_before.st_size > limits.max_file_bytes:
            raise LimitExceeded(f"file exceeds the {limits.max_file_bytes} byte limit: {relative}")
        if relative == "SKILL.md" and path_before.st_size > limits.max_skill_md_bytes:
            raise LimitExceeded("SKILL.md exceeds its configured byte limit")
        if total_bytes + path_before.st_size > limits.max_total_bytes:
            raise LimitExceeded(f"artifact exceeds the {limits.max_total_bytes} byte total limit")

        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(entry_path, flags)
            with os.fdopen(descriptor, "rb") as handle:
                opened_before = os.fstat(handle.fileno())
                content = handle.read(limits.max_file_bytes + 1)
                opened_after = os.fstat(handle.fileno())
            path_after = os.lstat(entry_path)
        except OSError as exc:
            raise InputRejected(f"could not read artifact file: {relative}", code="read_failed") from exc
        if _is_link_or_reparse(path_after) or not stat.S_ISREG(path_after.st_mode):
            raise InputRejected(f"artifact file type changed during capture: {relative}", code="input_changed")
        path_before_key = _entry_identity(path_before)
        opened_before_key = _entry_identity(opened_before)
        opened_after_key = _entry_identity(opened_after)
        path_after_key = _entry_identity(path_after)
        if (
            path_before_key != opened_before_key
            or opened_before_key != opened_after_key
            or opened_after_key != path_after_key
            or len(content) != opened_before.st_size
        ):
            raise InputRejected(f"artifact changed while it was being read: {relative}", code="input_changed")

        total_bytes += len(content)
        files.append(
            FileData(
                path=relative,
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                content=content,
            )
        )

    initial_inventory.sort(key=lambda item: item[0].encode("utf-8"))
    if tuple(initial_inventory) != _inventory_signature(root, limits):
        raise InputRejected("artifact entry set changed during capture", code="input_changed")

    files.sort(key=lambda item: item.path.encode("utf-8"))
    digest = hashlib.sha256()
    digest.update(b"capabilityproof-directory-sha256-v1\x00")
    for item in files:
        encoded_path = item.path.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(item.size.to_bytes(8, "big"))
        digest.update(item.content)

    capture_completed_at = (
        capture_started_at
        if time_override is not None
        else _utc_iso(datetime.now(timezone.utc))
    )
    return Snapshot(
        root=root,
        files=tuple(files),
        total_bytes=total_bytes,
        directory_sha256=digest.hexdigest(),
        excluded_paths=tuple(sorted(excluded)),
        capture_started_at=capture_started_at,
        capture_completed_at=capture_completed_at,
        capture_timestamp_source=capture_timestamp_source,
    )
