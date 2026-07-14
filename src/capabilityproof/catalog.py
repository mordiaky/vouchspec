"""Read-only Stage A catalog storage and validation."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any

from .errors import InputRejected, PathRejected
from .signing import _strict_json


CATALOG_SCHEMA_VERSION = "1.0.0"
RECEIPT_ID = re.compile(r"^cpr_[0-9a-f]{24}$")
COMMIT_ID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_LABELS = {
    "DIGEST_PINNED",
    "STRUCTURE_VALIDATED",
    "STATIC_INSPECTION_COMPLETED",
    "PUBLISHER_CI_ATTESTED",
    "INDEPENDENT_STATIC_SCAN",
    "SANDBOX_BEHAVIOR_OBSERVED",
    "TASK_EVALUATED",
}
class CatalogStore:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise PathRejected("catalog root must be a directory")

    def _read(self, relative: str, maximum: int) -> bytes:
        if "\\" in relative or relative.startswith("/") or ".." in relative.split("/"):
            raise PathRejected("catalog path is invalid")
        candidate = self.root / Path(*relative.split("/"))
        target = candidate.resolve(strict=True)
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise PathRejected("catalog path escaped its root") from exc
        metadata = candidate.lstat()
        if not target.is_file() or candidate.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise PathRejected("catalog item must be a regular file")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(candidate, flags)
        try:
            opened = os.fstat(descriptor)
            current = candidate.stat()
            resolved_after_open = candidate.resolve(strict=True)
            try:
                resolved_after_open.relative_to(self.root)
            except ValueError as exc:
                raise PathRejected("catalog item changed outside its root") from exc
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise PathRejected("catalog item changed during open")
            if opened.st_size < 1 or opened.st_size > maximum:
                raise InputRejected("catalog item is empty or too large", code="invalid_catalog")
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                content = stream.read(maximum + 1)
            if len(content) > maximum:
                raise InputRejected("catalog item exceeds its read limit", code="invalid_catalog")
            return content
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def index_bytes(self) -> bytes:
        return self._read("index.json", 5_000_000)

    def index_envelope_bytes(self) -> bytes:
        return self._read("index.dsse.json", 7_000_000)

    def index(self) -> dict[str, Any]:
        value = _strict_json(self.index_bytes(), code="invalid_catalog")
        return validate_catalog_index(value)

    def list_entries(self, *, query: str | None = None, repository_owner: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise InputRejected("limit must be from 1 through 100", code="invalid_query")
        if query is not None and (not isinstance(query, str) or len(query) > 200):
            raise InputRejected("query is too long", code="invalid_query")
        if repository_owner is not None and (not isinstance(repository_owner, str) or len(repository_owner) > 100):
            raise InputRejected("repository_owner is too long", code="invalid_query")
        query_folded = query.casefold().strip() if query else None
        owner_folded = repository_owner.casefold().strip() if repository_owner else None
        results: list[dict[str, Any]] = []
        for entry in self.index()["entries"]:
            if owner_folded and entry["repository_owner"].casefold() != owner_folded:
                continue
            haystack = " ".join(
                str(entry[field])
                for field in ("repository_owner", "skill_name", "source_repository", "artifact_path", "receipt_id")
            ).casefold()
            if query_folded and query_folded not in haystack:
                continue
            results.append(entry)
            if len(results) == limit:
                break
        return results

    def entry(self, receipt_id: str) -> dict[str, Any]:
        validate_receipt_id(receipt_id)
        for entry in self.index()["entries"]:
            if entry["receipt_id"] == receipt_id:
                return entry
        raise InputRejected("receipt was not found", code="not_found")

    def receipt_envelope_bytes(self, receipt_id: str) -> bytes:
        self.entry(receipt_id)
        return self._read(f"receipts/{receipt_id}.dsse.json", 2_000_000)

    def lifecycle_envelope_bytes(self) -> bytes:
        return self._read("lifecycle.dsse.json", 2_000_000)

    def root_jwk_bytes(self) -> bytes:
        return self._read("keys/root.jwk.json", 16_384)

    def issuer_jwk_bytes(self) -> bytes:
        return self._read("keys/issuer.jwk.json", 16_384)


def filter_catalog_entries(
    index: dict[str, Any],
    *,
    query: str | None = None,
    repository_owner: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Filter an already validated catalog snapshot without rereading disk."""

    validate_catalog_index(index)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise InputRejected("limit must be from 1 through 100", code="invalid_query")
    if query is not None and (not isinstance(query, str) or len(query) > 200):
        raise InputRejected("query is too long", code="invalid_query")
    if repository_owner is not None and (not isinstance(repository_owner, str) or len(repository_owner) > 100):
        raise InputRejected("repository_owner is too long", code="invalid_query")
    query_folded = query.casefold().strip() if query else None
    owner_folded = repository_owner.casefold().strip() if repository_owner else None
    results: list[dict[str, Any]] = []
    for entry in index["entries"]:
        if owner_folded and entry["repository_owner"].casefold() != owner_folded:
            continue
        haystack = " ".join(
            str(entry[field])
            for field in ("repository_owner", "skill_name", "source_repository", "artifact_path", "receipt_id")
        ).casefold()
        if query_folded and query_folded not in haystack:
            continue
        results.append(entry)
        if len(results) == limit:
            break
    return results


def validate_receipt_id(value: Any) -> str:
    if not isinstance(value, str) or RECEIPT_ID.fullmatch(value) is None:
        raise InputRejected("receipt_id is invalid", code="invalid_receipt_id")
    return value


def validate_catalog_index(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "service",
        "stage",
        "generated_at",
        "entry_count",
        "repository_owner_count",
        "entries",
    }:
        raise InputRejected("catalog index fields do not match the Stage A profile", code="invalid_catalog")
    if value.get("schema_version") != CATALOG_SCHEMA_VERSION or value.get("service") != "VouchSpec":
        raise InputRejected("catalog identity or version is unsupported", code="invalid_catalog")
    if value.get("stage") != "A_PUBLIC_ARTIFACT_INDEX":
        raise InputRejected("catalog is not a Stage A public-artifact index", code="invalid_catalog")
    entries = value.get("entries")
    if not isinstance(entries, list) or len(entries) > 100_000:
        raise InputRejected("catalog entries are invalid", code="invalid_catalog")
    seen: set[str] = set()
    publishers: set[str] = set()
    expected_fields = {
        "receipt_id",
        "repository_owner",
        "skill_name",
        "source_repository",
        "source_commit",
        "artifact_path",
        "artifact_sha256",
        "evidence_labels",
        "issued_at",
        "expires_at",
    }
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != expected_fields:
            raise InputRejected("catalog entry fields are invalid", code="invalid_catalog")
        receipt_id = validate_receipt_id(entry.get("receipt_id"))
        if receipt_id in seen:
            raise InputRejected("catalog receipt ids must be unique", code="invalid_catalog")
        seen.add(receipt_id)
        for field, maximum in (("repository_owner", 100), ("skill_name", 200), ("source_repository", 2048), ("artifact_path", 1024)):
            item = entry.get(field)
            if not isinstance(item, str) or not 1 <= len(item) <= maximum:
                raise InputRejected(f"catalog {field} is invalid", code="invalid_catalog")
        if COMMIT_ID.fullmatch(entry.get("source_commit", "")) is None or SHA256.fullmatch(entry.get("artifact_sha256", "")) is None:
            raise InputRejected("catalog immutable source binding is invalid", code="invalid_catalog")
        labels = entry.get("evidence_labels")
        if not isinstance(labels, list) or not labels or len(labels) != len(set(labels)) or set(labels) - ALLOWED_LABELS:
            raise InputRejected("catalog evidence labels are invalid", code="invalid_catalog")
        publishers.add(entry["repository_owner"])
    if value.get("entry_count") != len(entries) or value.get("repository_owner_count") != len(publishers):
        raise InputRejected("catalog summary counts are wrong", code="invalid_catalog")
    return value
