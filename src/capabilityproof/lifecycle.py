"""Root-signed receipt and issuer-key lifecycle state."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import threading
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .errors import InputRejected
from .signing import (
    _strict_json,
    jwk_thumbprint,
    sign_dsse_payload,
    verify_dsse_envelope,
    verify_receipt_envelope,
)


LIFECYCLE_PAYLOAD_TYPE = "application/vnd.vouchspec.receipt-lifecycle.v1+json"
LIFECYCLE_SCHEMA_VERSION = "1.0.0"
ISSUER_STATUSES = {"active", "retired", "compromised"}
RECEIPT_STATUSES = {
    "current",
    "superseded",
    "revoked_evaluator_defect",
    "revoked_key_compromise",
}
PUBLIC_LIFECYCLE_STATES = {
    "CURRENT",
    "SUPERSEDED",
    "EXPIRED",
    "REVOKED_EVALUATOR_DEFECT",
    "REVOKED_KEY_COMPROMISE",
    "SIGNATURE_VALID_LIFECYCLE_UNKNOWN",
}

_PATH_LOCKS: dict[Path, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


def _shared_thread_lock(path: Path) -> threading.Lock:
    with _PATH_LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(path, threading.Lock())


@contextmanager
def _exclusive_file_lock(path: Path):
    """Hold a cross-process advisory lock on one regular lock file."""

    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    locked = False
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise InputRejected("lifecycle lock path is not a regular file", code="invalid_sequence_state")
        if os.name == "nt":
            import msvcrt

            if metadata.st_size == 0:
                os.write(descriptor, b"\0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked = True
        yield
    finally:
        if locked:
            if os.name == "nt":
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


class LifecycleSequenceStore:
    """Persist the highest root-feed sequence outside mutable catalog storage."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve(strict=False)
        self.lock_path = self.path.with_name(f".{self.path.name}.lock")
        self._lock = _shared_thread_lock(self.path)

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        if self.path.is_symlink() or self.path.stat().st_size > 64_000:
            raise InputRejected("lifecycle sequence state is unsafe or too large", code="invalid_sequence_state")
        value = _strict_json(self.path.read_bytes(), code="invalid_sequence_state")
        if not isinstance(value, dict) or value.get("schema_version") not in {1, 2} or set(value) != {"schema_version", "roots"}:
            raise InputRejected("lifecycle sequence state is invalid", code="invalid_sequence_state")
        roots = value.get("roots")
        if not isinstance(roots, dict) or len(roots) > 100:
            raise InputRejected("lifecycle sequence roots are invalid", code="invalid_sequence_state")
        normalized: dict[str, dict[str, Any]] = {}
        for keyid, record in roots.items():
            if value["schema_version"] == 1:
                record = {"sequence": record, "feed_sha256": None}
            if not isinstance(record, dict) or set(record) != {"sequence", "feed_sha256"}:
                raise InputRejected("lifecycle sequence entry is invalid", code="invalid_sequence_state")
            sequence = record.get("sequence")
            feed_sha256 = record.get("feed_sha256")
            if (
                not isinstance(keyid, str)
                or isinstance(sequence, bool)
                or not isinstance(sequence, int)
                or sequence < 1
                or (feed_sha256 is not None and (not isinstance(feed_sha256, str) or len(feed_sha256) != 64))
            ):
                raise InputRejected("lifecycle sequence entry is invalid", code="invalid_sequence_state")
            normalized[keyid] = {"sequence": sequence, "feed_sha256": feed_sha256}
        return normalized

    def minimum(self, trusted_root_jwk: dict[str, Any]) -> int:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with _exclusive_file_lock(self.lock_path):
                record = self._load().get(jwk_thumbprint(trusted_root_jwk))
                return record["sequence"] if record is not None else 0

    def record(self, trusted_root_jwk: dict[str, Any], sequence: int, feed_sha256: str) -> None:
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise InputRejected("lifecycle sequence is invalid", code="invalid_sequence_state")
        if not isinstance(feed_sha256, str) or len(feed_sha256) != 64 or any(character not in "0123456789abcdef" for character in feed_sha256):
            raise InputRejected("lifecycle feed digest is invalid", code="invalid_sequence_state")
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with _exclusive_file_lock(self.lock_path):
                roots = self._load()
                keyid = jwk_thumbprint(trusted_root_jwk)
                current = roots.get(keyid)
                if current is not None and sequence < current["sequence"]:
                    raise InputRejected("lifecycle feed rollback detected", code="lifecycle_rollback")
                if current is not None and sequence == current["sequence"]:
                    if current["feed_sha256"] is not None and feed_sha256 != current["feed_sha256"]:
                        raise InputRejected("equal-sequence lifecycle feed equivocation detected", code="lifecycle_equivocation")
                    if current["feed_sha256"] == feed_sha256:
                        return
                roots[keyid] = {"sequence": sequence, "feed_sha256": feed_sha256}
                document = {"schema_version": 2, "roots": roots}
                temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write((json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, self.path)
                finally:
                    temporary.unlink(missing_ok=True)


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise InputRejected(f"{field} must be a short ISO 8601 string", code="invalid_lifecycle_feed")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        result = datetime.fromisoformat(normalized)
        if result.tzinfo is None:
            raise ValueError("timezone missing")
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise InputRejected(f"{field} must be valid ISO 8601", code="invalid_lifecycle_feed") from exc


def validate_lifecycle_feed(feed: Any) -> dict[str, Any]:
    if not isinstance(feed, dict) or set(feed) != {
        "schema_version",
        "sequence",
        "generated_at",
        "expires_at",
        "issuer_keys",
        "receipts",
    }:
        raise InputRejected("lifecycle feed fields do not match the Stage A profile", code="invalid_lifecycle_feed")
    if feed.get("schema_version") != LIFECYCLE_SCHEMA_VERSION:
        raise InputRejected("unsupported lifecycle feed schema", code="invalid_lifecycle_feed")
    sequence = feed.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise InputRejected("lifecycle sequence must be a positive integer", code="invalid_lifecycle_feed")
    generated = _time(feed.get("generated_at"), "generated_at")
    expires = _time(feed.get("expires_at"), "expires_at")
    if expires <= generated:
        raise InputRejected("lifecycle feed expiry must follow generation", code="invalid_lifecycle_feed")

    issuer_keys = feed.get("issuer_keys")
    if not isinstance(issuer_keys, list) or not 1 <= len(issuer_keys) <= 100:
        raise InputRejected("lifecycle feed must contain bounded issuer keys", code="invalid_lifecycle_feed")
    seen_keys: set[str] = set()
    for record in issuer_keys:
        if not isinstance(record, dict) or set(record) != {"keyid", "jwk", "status"}:
            raise InputRejected("invalid issuer key record", code="invalid_lifecycle_feed")
        if record.get("status") not in ISSUER_STATUSES:
            raise InputRejected("invalid issuer key status", code="invalid_lifecycle_feed")
        keyid = jwk_thumbprint(record.get("jwk"))
        if record.get("keyid") != keyid or keyid in seen_keys:
            raise InputRejected("issuer keyid is wrong or duplicated", code="invalid_lifecycle_feed")
        seen_keys.add(keyid)

    receipts = feed.get("receipts")
    if not isinstance(receipts, list) or len(receipts) > 100_000:
        raise InputRejected("invalid lifecycle receipt list", code="invalid_lifecycle_feed")
    seen_receipts: set[str] = set()
    for record in receipts:
        if not isinstance(record, dict) or not {"receipt_id", "status"}.issubset(record):
            raise InputRejected("invalid lifecycle receipt record", code="invalid_lifecycle_feed")
        if set(record) - {"receipt_id", "status", "superseded_by", "reason"}:
            raise InputRejected("unsupported lifecycle receipt field", code="invalid_lifecycle_feed")
        receipt_id = record.get("receipt_id")
        status = record.get("status")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("cpr_") or receipt_id in seen_receipts:
            raise InputRejected("receipt id is invalid or duplicated", code="invalid_lifecycle_feed")
        if status not in RECEIPT_STATUSES:
            raise InputRejected("invalid receipt lifecycle status", code="invalid_lifecycle_feed")
        if status == "superseded":
            superseded_by = record.get("superseded_by")
            if not isinstance(superseded_by, str) or not superseded_by.startswith("cpr_"):
                raise InputRejected("superseded receipt must name its successor", code="invalid_lifecycle_feed")
        elif "superseded_by" in record:
            raise InputRejected("only superseded receipts may name a successor", code="invalid_lifecycle_feed")
        reason = record.get("reason")
        if reason is not None and (not isinstance(reason, str) or not 1 <= len(reason) <= 500):
            raise InputRejected("lifecycle reason is invalid", code="invalid_lifecycle_feed")
        seen_receipts.add(receipt_id)
    return feed


def sign_lifecycle_feed(feed_bytes: bytes, root_private_key: Ed25519PrivateKey) -> dict[str, Any]:
    feed = _strict_json(feed_bytes, code="invalid_lifecycle_feed")
    validate_lifecycle_feed(feed)
    return sign_dsse_payload(LIFECYCLE_PAYLOAD_TYPE, feed_bytes, root_private_key)


def verify_lifecycle_envelope(envelope_bytes: bytes, trusted_root_jwk: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    payload = verify_dsse_envelope(
        envelope_bytes,
        LIFECYCLE_PAYLOAD_TYPE,
        trusted_root_jwk,
        maximum_payload_bytes=1_000_000,
    )
    feed = _strict_json(payload, code="invalid_lifecycle_feed")
    return validate_lifecycle_feed(feed), payload


def _envelope_keyid(envelope_bytes: bytes) -> str:
    envelope = _strict_json(envelope_bytes, code="invalid_envelope")
    if not isinstance(envelope, dict):
        raise InputRejected("invalid receipt envelope", code="invalid_envelope")
    signatures = envelope.get("signatures")
    if not isinstance(signatures, list) or len(signatures) != 1 or not isinstance(signatures[0], dict):
        raise InputRejected("invalid receipt signature set", code="invalid_envelope")
    keyid = signatures[0].get("keyid")
    if not isinstance(keyid, str):
        raise InputRejected("receipt envelope has no keyid", code="invalid_envelope")
    return keyid


def evaluate_receipt_lifecycle(
    receipt_envelope_bytes: bytes,
    lifecycle_envelope_bytes: bytes,
    trusted_root_jwk: dict[str, Any],
    *,
    now: datetime | None = None,
    minimum_sequence: int = 0,
) -> dict[str, Any]:
    """Verify both signatures and conservatively derive current lifecycle state."""

    feed, _ = verify_lifecycle_envelope(lifecycle_envelope_bytes, trusted_root_jwk)
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    keyid = _envelope_keyid(receipt_envelope_bytes)
    issuer = next((item for item in feed["issuer_keys"] if item["keyid"] == keyid), None)
    if issuer is None:
        raise InputRejected("receipt signer is not authorized by the root feed", code="untrusted_key")
    receipt, _ = verify_receipt_envelope(receipt_envelope_bytes, issuer["jwk"])
    receipt_id = receipt["receipt_id"]

    if feed["sequence"] < minimum_sequence:
        return {
            "signature": "valid",
            "lifecycle": "SIGNATURE_VALID_LIFECYCLE_UNKNOWN",
            "reason": "lifecycle feed sequence is lower than the verifier's last-seen sequence",
            "feed_sequence": feed["sequence"],
        }
    if _time(feed["generated_at"], "generated_at") > current_time:
        return {
            "signature": "valid",
            "lifecycle": "SIGNATURE_VALID_LIFECYCLE_UNKNOWN",
            "reason": "root-signed lifecycle feed is future-dated",
            "feed_sequence": feed["sequence"],
        }
    if _time(feed["expires_at"], "expires_at") <= current_time:
        return {
            "signature": "valid",
            "lifecycle": "SIGNATURE_VALID_LIFECYCLE_UNKNOWN",
            "reason": "root-signed lifecycle feed is stale",
            "feed_sequence": feed["sequence"],
        }
    if issuer["status"] == "compromised":
        state = "REVOKED_KEY_COMPROMISE"
        reason = "root feed marks the receipt-signing key compromised"
    else:
        record = next((item for item in feed["receipts"] if item["receipt_id"] == receipt_id), None)
        if record is None:
            state = "SIGNATURE_VALID_LIFECYCLE_UNKNOWN"
            reason = "receipt is absent from the current root-signed lifecycle feed"
        elif record["status"] == "revoked_key_compromise":
            state = "REVOKED_KEY_COMPROMISE"
            reason = record.get("reason", "receipt revoked for signing-key compromise")
        elif record["status"] == "revoked_evaluator_defect":
            state = "REVOKED_EVALUATOR_DEFECT"
            reason = record.get("reason", "receipt revoked for evaluator defect")
        elif _time(receipt["validity"]["expires_at"], "receipt expires_at") <= current_time:
            state = "EXPIRED"
            reason = "receipt expiration time has passed"
        elif record["status"] == "superseded":
            state = "SUPERSEDED"
            reason = record.get("reason", f"superseded by {record['superseded_by']}")
        else:
            state = "CURRENT"
            reason = "receipt signature, expiry, signer status, and lifecycle entry are current"
    return {
        "signature": "valid",
        "lifecycle": state,
        "reason": reason,
        "receipt_id": receipt_id,
        "artifact_sha256": receipt["artifact"]["digest"]["sha256"],
        "source_commit": receipt["provenance"]["source_commit"],
        "issuer_keyid": keyid,
        "feed_sequence": feed["sequence"],
    }


def evaluate_receipt_lifecycle_with_state(
    receipt_envelope_bytes: bytes,
    lifecycle_envelope_bytes: bytes,
    trusted_root_jwk: dict[str, Any],
    sequence_store: LifecycleSequenceStore,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    feed, payload = verify_lifecycle_envelope(lifecycle_envelope_bytes, trusted_root_jwk)
    minimum = sequence_store.minimum(trusted_root_jwk)
    result = evaluate_receipt_lifecycle(
        receipt_envelope_bytes,
        lifecycle_envelope_bytes,
        trusted_root_jwk,
        now=now,
        minimum_sequence=minimum,
    )
    if result["feed_sequence"] >= minimum:
        sequence_store.record(trusted_root_jwk, feed["sequence"], hashlib.sha256(payload).hexdigest())
    return result
