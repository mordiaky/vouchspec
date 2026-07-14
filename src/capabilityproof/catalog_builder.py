"""Separated collection, issuer-signing, and root-lifecycle build phases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .catalog import validate_catalog_index
from .errors import InputRejected
from .lifecycle import sign_lifecycle_feed, validate_lifecycle_feed, verify_lifecycle_envelope
from .receipt import deterministic_json, inspect_git_skill, verify_receipt_integrity
from .signing import (
    CATALOG_INDEX_PAYLOAD_TYPE,
    _strict_json,
    jwk_thumbprint,
    public_jwk,
    sign_dsse_payload,
    sign_receipt_bytes,
    verify_receipt_envelope,
)


COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_git(cwd: Path, *args: str, timeout: int = 180) -> str:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    }
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise InputRejected("public source checkout failed", code="source_checkout_failed")
    return result.stdout.decode("utf-8", errors="strict").strip()


def _repository_identity(repository: str) -> tuple[str, str]:
    parsed = urlsplit(repository)
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise InputRejected("Stage A source must be a public HTTPS github.com repository", code="source_not_allowed")
    parts = [part for part in parsed.path.strip("/").removesuffix(".git").split("/") if part]
    if len(parts) != 2:
        raise InputRejected("Stage A source must identify one GitHub owner/repository", code="source_not_allowed")
    return parts[0], "--".join(parts)


def _checkout(cache_root: Path, repository: str, commit: str) -> Path:
    _, slug = _repository_identity(repository)
    if COMMIT.fullmatch(commit) is None:
        raise InputRejected("Stage A source requires a full 40-character commit", code="invalid_source_commit")
    target = (cache_root / f"{slug}--{commit}").resolve(strict=False)
    cache_root_resolved = cache_root.resolve(strict=True)
    try:
        target.relative_to(cache_root_resolved)
    except ValueError as exc:
        raise InputRejected("source cache path escaped its root", code="source_checkout_failed") from exc
    if not target.exists():
        target.mkdir()
        _run_git(target, "init", "-q")
        _run_git(target, "config", "core.autocrlf", "false")
        _run_git(target, "config", "core.eol", "lf")
        _run_git(target, "config", "core.longpaths", "true")
        _run_git(target, "remote", "add", "origin", repository)
        _run_git(target, "fetch", "--depth=1", "--no-tags", "origin", commit)
        _run_git(target, "checkout", "--detach", "-q", "FETCH_HEAD")
    if _run_git(target, "remote", "get-url", "origin") != repository:
        raise InputRejected("cached repository remote does not match the manifest", code="source_checkout_failed")
    if _run_git(target, "rev-parse", "HEAD") != commit:
        raise InputRejected("cached repository commit does not match the manifest", code="source_checkout_failed")
    if _run_git(target, "status", "--porcelain=v1", "--untracked-files=all"):
        raise InputRejected("cached public source checkout is dirty", code="source_checkout_failed")
    return target


def load_source_manifest(path: Path) -> list[dict[str, str]]:
    manifest = _strict_json(path.read_bytes(), code="invalid_source_manifest")
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "selection", "sources"} or manifest.get("schema_version") != "1.0.0":
        raise InputRejected("source manifest fields are invalid", code="invalid_source_manifest")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise InputRejected("source manifest must contain 1 through 100 sources", code="invalid_source_manifest")
    seen: set[tuple[str, str, str]] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"repository_owner", "repository", "commit", "artifact_path"}:
            raise InputRejected("source record fields are invalid", code="invalid_source_manifest")
        if not all(isinstance(source[field], str) and source[field] for field in source):
            raise InputRejected("source record values must be non-empty strings", code="invalid_source_manifest")
        owner, _ = _repository_identity(source["repository"])
        if source["repository_owner"].casefold() != owner.casefold():
            raise InputRejected("repository_owner must exactly match the GitHub URL namespace", code="invalid_source_manifest")
        identity = (source["repository"], source["commit"], source["artifact_path"])
        if identity in seen:
            raise InputRejected("source records must be unique", code="invalid_source_manifest")
        seen.add(identity)
    return sources


def build_catalog_drafts(
    manifest_path: Path,
    cache_root: Path,
    output_root: Path,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Networked/keyless phase: checkout public commits and emit unsigned receipt drafts."""

    timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    sources = load_source_manifest(manifest_path)
    cache_root.mkdir(parents=True, exist_ok=True)
    if output_root.exists():
        raise InputRejected("refusing to overwrite existing catalog drafts", code="catalog_exists")
    output_root.mkdir(parents=True)
    (output_root / "receipts").mkdir()
    entries: list[dict[str, Any]] = []
    try:
        for source in sources:
            repository_root = _checkout(cache_root, source["repository"], source["commit"])
            artifact = (repository_root / Path(*source["artifact_path"].split("/"))).resolve(strict=True)
            try:
                artifact.relative_to(repository_root.resolve(strict=True))
            except ValueError as exc:
                raise InputRejected("artifact path escaped its checkout", code="invalid_source_manifest") from exc
            receipt = inspect_git_skill(
                artifact,
                repository_root,
                generated_at=_iso(timestamp),
                expires_in_days=30,
                independent_static_scan=True,
            )
            payload = deterministic_json(receipt)
            (output_root / "receipts" / f"{receipt['receipt_id']}.json").write_bytes(payload)
            entries.append(
                {
                    "receipt_id": receipt["receipt_id"],
                    "repository_owner": source["repository_owner"],
                    "skill_name": receipt["artifact"]["claims_untrusted"]["name"] or receipt["artifact"]["root_directory"],
                    "source_repository": receipt["provenance"]["source_repository"],
                    "source_commit": receipt["provenance"]["source_commit"],
                    "artifact_path": receipt["provenance"]["artifact_path"],
                    "artifact_sha256": receipt["artifact"]["digest"]["sha256"],
                    "evidence_labels": receipt["evidence_labels"],
                    "issued_at": receipt["validity"]["generated_at"],
                    "expires_at": receipt["validity"]["expires_at"],
                }
            )
        entries.sort(key=lambda item: (item["repository_owner"].casefold(), item["skill_name"].casefold(), item["receipt_id"]))
        index = {
            "schema_version": "1.0.0",
            "service": "VouchSpec",
            "stage": "A_PUBLIC_ARTIFACT_INDEX",
            "generated_at": _iso(timestamp),
            "entry_count": len(entries),
            "repository_owner_count": len({entry["repository_owner"].casefold() for entry in entries}),
            "entries": entries,
        }
        validate_catalog_index(index)
        report = {
            "generated_at": _iso(timestamp),
            "entry_count": len(entries),
            "repository_owner_count": index["repository_owner_count"],
            "structure_pass_count": sum("STRUCTURE_VALIDATED" in entry["evidence_labels"] for entry in entries),
            "structure_fail_count": sum("STRUCTURE_VALIDATED" not in entry["evidence_labels"] for entry in entries),
            "skipped_count": 0,
            "artifact_code_executed": False,
            "customer_uploads_accepted": False,
            "private_artifacts_processed": False,
            "receipt_expires_at": entries[0]["expires_at"],
            "build_phase": "networked-keyless-collection",
        }
        (output_root / "index.json").write_bytes(deterministic_json(index))
        (output_root / "build-report.json").write_bytes(deterministic_json(report) + b"\n")
        return report
    except Exception:
        shutil.rmtree(output_root, ignore_errors=True)
        raise


def sign_catalog_drafts(
    drafts_root: Path,
    output_root: Path,
    issuer_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    """No-network issuer phase: validate drafts and sign exact receipt/index bytes."""

    drafts_root = drafts_root.resolve(strict=True)
    if output_root.exists():
        raise InputRejected("refusing to overwrite an existing signed catalog", code="catalog_exists")
    index_bytes = (drafts_root / "index.json").read_bytes()
    index = validate_catalog_index(_strict_json(index_bytes, code="invalid_catalog"))
    payload_paths = sorted((drafts_root / "receipts").glob("*.json"))
    if len(payload_paths) != index["entry_count"]:
        raise InputRejected("draft receipt count does not match the index", code="invalid_catalog")
    output_root.mkdir(parents=True)
    (output_root / "receipts").mkdir()
    (output_root / "keys").mkdir()
    issuer_jwk = public_jwk(issuer_key.public_key())
    try:
        seen: set[str] = set()
        for entry in index["entries"]:
            path = drafts_root / "receipts" / f"{entry['receipt_id']}.json"
            payload = path.read_bytes()
            receipt = _strict_json(payload, code="invalid_receipt")
            if not isinstance(receipt, dict) or not verify_receipt_integrity(receipt):
                raise InputRejected("draft receipt integrity failed", code="invalid_receipt_integrity")
            if (
                receipt["receipt_id"] != entry["receipt_id"]
                or receipt["artifact"]["digest"]["sha256"] != entry["artifact_sha256"]
                or receipt["provenance"]["source_commit"] != entry["source_commit"]
                or receipt["provenance"]["artifact_path"] != entry["artifact_path"]
            ):
                raise InputRejected("draft receipt does not match the catalog index", code="catalog_verification_failed")
            envelope = sign_receipt_bytes(payload, issuer_key)
            verified, exact = verify_receipt_envelope(deterministic_json(envelope), issuer_jwk)
            if exact != payload or verified["receipt_id"] != entry["receipt_id"]:
                raise InputRejected("signed receipt failed issuer verification", code="catalog_verification_failed")
            (output_root / "receipts" / f"{entry['receipt_id']}.dsse.json").write_bytes(deterministic_json(envelope) + b"\n")
            seen.add(entry["receipt_id"])
        if seen != {path.stem for path in payload_paths}:
            raise InputRejected("unindexed draft receipts are present", code="invalid_catalog")
        index_envelope = sign_dsse_payload(
            CATALOG_INDEX_PAYLOAD_TYPE,
            index_bytes,
            issuer_key,
            maximum_payload_bytes=5_000_000,
        )
        (output_root / "index.json").write_bytes(index_bytes)
        (output_root / "index.dsse.json").write_bytes(deterministic_json(index_envelope) + b"\n")
        (output_root / "build-report.json").write_bytes((drafts_root / "build-report.json").read_bytes())
        (output_root / "keys" / "issuer.jwk.json").write_bytes(deterministic_json(issuer_jwk) + b"\n")
        return {"entry_count": index["entry_count"], "issuer_keyid": jwk_thumbprint(issuer_jwk), "signing_phase": "no-network-issuer"}
    except Exception:
        shutil.rmtree(output_root, ignore_errors=True)
        raise


def finalize_catalog_lifecycle(
    catalog_root: Path,
    root_key: Ed25519PrivateKey,
    *,
    generated_at: datetime | None = None,
    previous_envelope: Path | None = None,
) -> dict[str, Any]:
    """Offline root phase: authorize issuer and sign only lifecycle metadata."""

    catalog_root = catalog_root.resolve(strict=True)
    lifecycle_path = catalog_root / "lifecycle.dsse.json"
    root_path = catalog_root / "keys" / "root.jwk.json"
    if lifecycle_path.exists() and previous_envelope is None:
        raise InputRejected("existing lifecycle feed requires --previous-lifecycle", code="lifecycle_exists")
    timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    root_jwk = public_jwk(root_key.public_key())
    sequence = 1
    if previous_envelope is not None:
        previous_feed, _ = verify_lifecycle_envelope(previous_envelope.read_bytes(), root_jwk)
        sequence = previous_feed["sequence"] + 1
    issuer_jwk = _strict_json((catalog_root / "keys" / "issuer.jwk.json").read_bytes(), code="invalid_key")
    if jwk_thumbprint(root_jwk) == jwk_thumbprint(issuer_jwk):
        raise InputRejected(
            "recovery-root and receipt-issuer keys must be cryptographically distinct",
            code="key_role_collision",
        )
    index = validate_catalog_index(_strict_json((catalog_root / "index.json").read_bytes(), code="invalid_catalog"))
    receipt_ids: list[str] = []
    for entry in index["entries"]:
        envelope = (catalog_root / "receipts" / f"{entry['receipt_id']}.dsse.json").read_bytes()
        receipt, _ = verify_receipt_envelope(envelope, issuer_jwk)
        if receipt["receipt_id"] != entry["receipt_id"]:
            raise InputRejected("catalog receipt mismatch during root finalization", code="catalog_verification_failed")
        receipt_ids.append(entry["receipt_id"])
    feed = {
        "schema_version": "1.0.0",
        "sequence": sequence,
        "generated_at": _iso(timestamp),
        "expires_at": _iso(timestamp + timedelta(days=7)),
        "issuer_keys": [{"keyid": jwk_thumbprint(issuer_jwk), "jwk": issuer_jwk, "status": "active"}],
        "receipts": [{"receipt_id": receipt_id, "status": "current"} for receipt_id in receipt_ids],
    }
    validate_lifecycle_feed(feed)
    lifecycle_envelope = sign_lifecycle_feed(deterministic_json(feed), root_key)
    if root_path.exists():
        existing = _strict_json(root_path.read_bytes(), code="invalid_key")
        if existing != root_jwk:
            raise InputRejected("catalog root key does not match the recovery key", code="untrusted_key")
    temporary = lifecycle_path.with_suffix(".tmp")
    temporary.write_bytes(deterministic_json(lifecycle_envelope) + b"\n")
    os.replace(temporary, lifecycle_path)
    if not root_path.exists():
        root_path.write_bytes(deterministic_json(root_jwk) + b"\n")
    return {
        "entry_count": len(receipt_ids),
        "feed_sequence": sequence,
        "feed_expires_at": feed["expires_at"],
        "root_keyid": jwk_thumbprint(root_jwk),
        "root_phase": "offline-lifecycle-only",
    }
