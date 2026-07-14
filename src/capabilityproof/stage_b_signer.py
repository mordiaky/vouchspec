"""Constrained signing gate for receipts produced by verified Stage B workers."""

from __future__ import annotations

from datetime import timedelta
import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .commerce import load_strict_commerce_json
from .errors import InputRejected
from .receipt import deterministic_json, verify_receipt_integrity
from .signing import (
    MAX_RECEIPT_BYTES,
    _require_safe_regular_file,
    jwk_thumbprint,
    public_jwk,
    sign_receipt_bytes,
    verify_receipt_envelope,
)
from .stage_b import (
    WORKER_PROFILE,
    _IMAGE_REFERENCE,
    verify_frozen_source,
)


MAX_EXECUTION_REPORT_BYTES = 64_000
_EXECUTION_FIELDS = {
    "schema_version",
    "profile",
    "container_image",
    "network",
    "root_filesystem",
    "input_mount",
    "capabilities",
    "no_new_privileges",
    "uid_gid",
    "pids_limit",
    "memory_limit_bytes",
    "cpu_limit",
    "tmpfs",
    "ipc",
    "open_files_limit",
    "file_size_limit_bytes",
    "stop_timeout_seconds",
    "output_channel",
    "started_at",
    "completed_at",
    "duration_ms",
    "receipt_id",
    "receipt_sha256",
    "freeze_manifest_digest",
    "artifact_execution",
}


def _timestamp(value: Any):
    from datetime import datetime, timezone

    if not isinstance(value, str):
        raise InputRejected("worker timestamp is invalid", code="signing_gate_failed")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InputRejected("worker timestamp is invalid", code="signing_gate_failed") from exc
    if parsed.tzinfo is None:
        raise InputRejected("worker timestamp requires a timezone", code="signing_gate_failed")
    return parsed.astimezone(timezone.utc)


def sign_verified_worker_result(
    frozen_root: Path,
    worker_output_root: Path,
    envelope_output: Path,
    private_key: Ed25519PrivateKey,
    *,
    allowed_image_references: set[str],
) -> dict[str, Any]:
    """Sign exact receipt bytes only after all freeze/worker constraints re-verify."""

    frozen = verify_frozen_source(frozen_root)
    if not allowed_image_references or any(
        not isinstance(reference, str) or not _IMAGE_REFERENCE.fullmatch(reference)
        for reference in allowed_image_references
    ):
        raise ValueError("at least one immutable allowed worker image is required")
    output_root = worker_output_root.resolve(strict=True)
    receipt_path = output_root / "receipt.json"
    execution_path = output_root / "worker-execution.json"
    try:
        _require_safe_regular_file(receipt_path, "worker receipt")
        _require_safe_regular_file(execution_path, "worker execution report")
        receipt_bytes = receipt_path.read_bytes()
        execution_bytes = execution_path.read_bytes()
    except OSError as exc:
        raise InputRejected("worker result files are missing", code="signing_gate_failed") from exc
    if not receipt_bytes or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise InputRejected("worker receipt is empty or oversized", code="signing_gate_failed")
    if not execution_bytes or len(execution_bytes) > MAX_EXECUTION_REPORT_BYTES:
        raise InputRejected("worker execution report is empty or oversized", code="signing_gate_failed")
    try:
        receipt = load_strict_commerce_json(receipt_bytes.decode("utf-8", errors="strict"))
        execution = load_strict_commerce_json(execution_bytes.decode("utf-8", errors="strict"))
    except UnicodeError as exc:
        raise InputRejected("worker result is not UTF-8", code="signing_gate_failed") from exc
    if not isinstance(receipt, dict) or not verify_receipt_integrity(receipt):
        raise InputRejected("worker receipt integrity failed", code="signing_gate_failed")
    if not isinstance(execution, dict) or set(execution) != _EXECUTION_FIELDS:
        raise InputRejected("worker execution fields are invalid", code="signing_gate_failed")
    if (
        execution["schema_version"] != "1.0.0"
        or execution["profile"] != WORKER_PROFILE
        or not isinstance(execution["container_image"], str)
        or not _IMAGE_REFERENCE.fullmatch(execution["container_image"])
        or execution["container_image"] not in allowed_image_references
        or execution["network"] != "none"
        or execution["root_filesystem"] != "read_only"
        or execution["input_mount"] != "read_only"
        or execution["capabilities"] != "all_dropped"
        or execution["no_new_privileges"] is not True
        or execution["uid_gid"] != "65532:65532"
        or execution["pids_limit"] != 64
        or execution["memory_limit_bytes"] != 268_435_456
        or execution["cpu_limit"] != "1.0"
        or execution["tmpfs"] != "16MiB_noexec_nosuid_nodev"
        or execution["ipc"] != "none"
        or execution["open_files_limit"] != 128
        or execution["file_size_limit_bytes"] != 1_048_576
        or execution["stop_timeout_seconds"] != 1
        or execution["output_channel"] != "bounded_stdout_1000000_bytes"
        or isinstance(execution["duration_ms"], bool)
        or not isinstance(execution["duration_ms"], int)
        or not 0 <= execution["duration_ms"] <= 75_000
        or execution["artifact_execution"] != "not_performed"
    ):
        raise InputRejected("worker isolation evidence failed", code="signing_gate_failed")
    started = _timestamp(execution["started_at"])
    completed = _timestamp(execution["completed_at"])
    generated = _timestamp(receipt.get("validity", {}).get("generated_at"))
    elapsed_ms = int((completed - started).total_seconds() * 1_000)
    if (
        completed < started
        or elapsed_ms > 77_000
        or execution["duration_ms"] > elapsed_ms + 2_000
        or not started - timedelta(minutes=5) <= generated <= completed + timedelta(minutes=5)
    ):
        raise InputRejected("worker timing evidence is inconsistent", code="signing_gate_failed")
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
    if (
        execution["receipt_id"] != receipt["receipt_id"]
        or execution["receipt_sha256"] != receipt_sha256
        or execution["freeze_manifest_digest"] != frozen.manifest["manifest_digest"]
        or receipt["artifact"]["digest"]["sha256"] != frozen.manifest["artifact_directory_sha256"]
        or receipt["artifact"]["root_directory"] != frozen.artifact_root.name
        or receipt["provenance"]["source_repository"] != frozen.manifest["repository_url"]
        or receipt["provenance"]["source_commit"] != frozen.manifest["fetched_commit"]
        or receipt["provenance"]["artifact_path"] != frozen.manifest["source"]["skill_path"]
        or receipt["provenance"]["source_verification"]
        != {"status": "completed", "method": "exact-local-git-blob-match-v1"}
        or receipt["methodology"]["artifact_execution"] != "not-performed"
        or "INDEPENDENT_STATIC_SCAN" not in receipt["evidence_labels"]
    ):
        raise InputRejected("receipt is not bound to approved worker evidence", code="signing_gate_failed")
    envelope = sign_receipt_bytes(receipt_bytes, private_key)
    envelope_bytes = deterministic_json(envelope) + b"\n"
    _, verified_payload = verify_receipt_envelope(
        envelope_bytes,
        public_jwk(private_key.public_key()),
    )
    if verified_payload != receipt_bytes:
        raise InputRejected("signing self-verification changed payload bytes", code="signing_gate_failed")
    target = envelope_output.expanduser().resolve(strict=False)
    if target.exists():
        raise InputRejected("refusing to overwrite signed output", code="output_exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as stream:
            stream.write(envelope_bytes)
    except OSError as exc:
        raise InputRejected("signed output could not be written", code="signing_gate_failed") from exc
    return {
        "schema_version": "1.0.0",
        "receipt_id": receipt["receipt_id"],
        "receipt_sha256": receipt_sha256,
        "envelope_sha256": hashlib.sha256(envelope_bytes).hexdigest(),
        "signing_keyid": jwk_thumbprint(public_jwk(private_key.public_key())),
        "freeze_manifest_digest": frozen.manifest["manifest_digest"],
        "worker_profile": execution["profile"],
        "container_image": execution["container_image"],
        "artifact_execution": "not_performed",
    }
