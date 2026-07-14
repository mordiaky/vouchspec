"""DSSE v1 receipt envelopes signed with Ed25519.

The signature covers the exact receipt bytes carried by the envelope. Verifiers
must authenticate those bytes before parsing them; JSON reserialization is never
part of signature verification.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
import jsonschema

from .errors import InputRejected
from .receipt import verify_receipt_integrity


RECEIPT_PAYLOAD_TYPE = "application/vnd.vouchspec.capability-receipt.v1+json"
CATALOG_INDEX_PAYLOAD_TYPE = "application/vnd.vouchspec.catalog-index.v1+json"
DSSE_PROFILE = "dsse-v1.0.2-ed25519"
MAX_ENVELOPE_BYTES = 2_000_000
MAX_RECEIPT_BYTES = 1_000_000


def _b64url_no_pad(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str, *, expected_bytes: int | None = None) -> bytes:
    if not isinstance(value, str) or not value or any(character.isspace() for character in value):
        raise InputRejected("invalid base64url value", code="invalid_base64")
    if "=" in value:
        raise InputRejected("base64url padding is not permitted in JWK fields", code="invalid_base64")
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise InputRejected("invalid base64url value", code="invalid_base64") from exc
    if _b64url_no_pad(decoded) != value:
        raise InputRejected("non-canonical base64url value", code="invalid_base64")
    if expected_bytes is not None and len(decoded) != expected_bytes:
        raise InputRejected("decoded key has the wrong length", code="invalid_key")
    return decoded


def _b64_decode(value: str, *, maximum: int) -> bytes:
    if not isinstance(value, str) or not value or any(character.isspace() for character in value):
        raise InputRejected("invalid DSSE base64 value", code="invalid_base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise InputRejected("invalid DSSE base64 value", code="invalid_base64") from exc
    if len(decoded) > maximum or base64.b64encode(decoded).decode("ascii") != value:
        raise InputRejected("invalid or oversized DSSE base64 value", code="invalid_base64")
    return decoded


def _strict_json(raw: bytes, *, code: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise InputRejected("invalid strict JSON document", code=code) from exc


def dsse_pae(payload_type: str, payload: bytes) -> bytes:
    """Return the DSSE v1 pre-authentication encoding."""

    if not isinstance(payload_type, str) or not payload_type or not payload_type.isascii():
        raise InputRejected("payload type must be non-empty ASCII", code="invalid_payload_type")
    encoded_type = payload_type.encode("ascii")
    return b"DSSEv1 " + str(len(encoded_type)).encode("ascii") + b" " + encoded_type + b" " + str(len(payload)).encode("ascii") + b" " + payload


def public_jwk(public_key: Ed25519PublicKey) -> dict[str, str]:
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"kty": "OKP", "crv": "Ed25519", "x": _b64url_no_pad(raw)}


def jwk_thumbprint(jwk: dict[str, Any]) -> str:
    if not isinstance(jwk, dict) or set(jwk) != {"kty", "crv", "x"}:
        raise InputRejected("public JWK must contain only crv, kty, and x", code="invalid_key")
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise InputRejected("public JWK is not an Ed25519 OKP key", code="invalid_key")
    _b64url_decode(jwk.get("x"), expected_bytes=32)
    canonical = json.dumps(
        {"crv": "Ed25519", "kty": "OKP", "x": jwk["x"]},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return _b64url_no_pad(hashlib.sha256(canonical).digest())


def public_key_from_jwk(jwk: dict[str, Any]) -> Ed25519PublicKey:
    jwk_thumbprint(jwk)
    return Ed25519PublicKey.from_public_bytes(_b64url_decode(jwk["x"], expected_bytes=32))


def load_public_jwk(path: Path) -> dict[str, str]:
    _require_safe_regular_file(path, "public key")
    raw = path.read_bytes()
    if len(raw) > 16_384:
        raise InputRejected("public key document is too large", code="invalid_key")
    value = _strict_json(raw, code="invalid_key")
    jwk_thumbprint(value)
    return value


def load_private_key(path: Path, passphrase: bytes) -> Ed25519PrivateKey:
    if not passphrase:
        raise InputRejected("an encrypted-key passphrase is required", code="missing_passphrase")
    _require_safe_regular_file(path, "private key")
    raw = path.read_bytes()
    if len(raw) > 64_000:
        raise InputRejected("private key document is too large", code="invalid_key")
    try:
        key = serialization.load_pem_private_key(raw, password=passphrase)
    except (TypeError, ValueError) as exc:
        raise InputRejected("private key or passphrase is invalid", code="invalid_key") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise InputRejected("private key is not Ed25519", code="invalid_key")
    return key


def generate_encrypted_keypair(private_path: Path, public_path: Path, passphrase: bytes) -> dict[str, str]:
    """Create a new encrypted PKCS#8 private key and RFC 8037 public JWK."""

    if len(passphrase) < 16:
        raise InputRejected("key passphrase must contain at least 16 bytes", code="weak_passphrase")
    if private_path.exists() or public_path.exists():
        raise InputRejected("refusing to overwrite an existing key file", code="key_exists")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase),
    )
    descriptor = public_jwk(key.public_key())
    public_bytes = (json.dumps(descriptor, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    private_fd: int | None = None
    public_fd: int | None = None
    private_created = False
    public_created = False
    try:
        private_fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        private_created = True
        with os.fdopen(private_fd, "wb") as stream:
            private_fd = None
            stream.write(private_bytes)
        public_fd = os.open(public_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        public_created = True
        with os.fdopen(public_fd, "wb") as stream:
            public_fd = None
            stream.write(public_bytes)
    except Exception:
        if private_fd is not None:
            os.close(private_fd)
        if public_fd is not None:
            os.close(public_fd)
        if private_created:
            private_path.unlink(missing_ok=True)
        if public_created:
            public_path.unlink(missing_ok=True)
        raise
    return descriptor


def sign_receipt_bytes(receipt_bytes: bytes, private_key: Ed25519PrivateKey) -> dict[str, Any]:
    if not receipt_bytes or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise InputRejected("receipt payload is empty or too large", code="invalid_receipt")
    receipt = _strict_json(receipt_bytes, code="invalid_receipt")
    if not isinstance(receipt, dict) or not verify_receipt_integrity(receipt):
        raise InputRejected("receipt embedded integrity check failed", code="invalid_receipt_integrity")
    return sign_dsse_payload(RECEIPT_PAYLOAD_TYPE, receipt_bytes, private_key)


def sign_dsse_payload(
    payload_type: str,
    payload: bytes,
    private_key: Ed25519PrivateKey,
    *,
    maximum_payload_bytes: int = MAX_RECEIPT_BYTES,
) -> dict[str, Any]:
    """Sign exact payload bytes using the Stage A one-signature DSSE profile."""

    if not payload or len(payload) > maximum_payload_bytes:
        raise InputRejected("DSSE payload is empty or too large", code="invalid_payload")
    key = public_jwk(private_key.public_key())
    signature = private_key.sign(dsse_pae(payload_type, payload))
    return {
        "payloadType": payload_type,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [{"keyid": jwk_thumbprint(key), "sig": base64.b64encode(signature).decode("ascii")}],
    }


def verify_receipt_envelope(envelope_bytes: bytes, trusted_jwk: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    """Authenticate an envelope and return both parsed receipt and exact signed bytes."""

    payload = verify_dsse_envelope(envelope_bytes, RECEIPT_PAYLOAD_TYPE, trusted_jwk)
    receipt = _strict_json(payload, code="invalid_receipt")
    if not isinstance(receipt, dict) or not verify_receipt_integrity(receipt):
        raise InputRejected("signed receipt embedded integrity check failed", code="invalid_receipt_integrity")
    schema_path = Path(__file__).with_name("schemas") / "capability-receipt.schema.json"
    schema = _strict_json(schema_path.read_bytes(), code="invalid_receipt_schema")
    try:
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(receipt)
    except jsonschema.ValidationError as exc:
        raise InputRejected("signed receipt does not match its schema", code="invalid_receipt_schema") from exc
    return receipt, payload


def verify_dsse_envelope(
    envelope_bytes: bytes,
    expected_payload_type: str,
    trusted_jwk: dict[str, Any],
    *,
    maximum_payload_bytes: int = MAX_RECEIPT_BYTES,
) -> bytes:
    """Authenticate one exact DSSE payload without parsing the payload itself."""

    if not envelope_bytes or len(envelope_bytes) > MAX_ENVELOPE_BYTES:
        raise InputRejected("envelope is empty or too large", code="invalid_envelope")
    envelope = _strict_json(envelope_bytes, code="invalid_envelope")
    if not isinstance(envelope, dict) or set(envelope) != {"payloadType", "payload", "signatures"}:
        raise InputRejected("DSSE envelope fields do not match the Stage A profile", code="invalid_envelope")
    payload_type = envelope.get("payloadType")
    if payload_type != expected_payload_type:
        raise InputRejected("unexpected DSSE payload type", code="invalid_payload_type")
    signatures = envelope.get("signatures")
    if not isinstance(signatures, list) or len(signatures) != 1:
        raise InputRejected("exactly one DSSE signature is required", code="invalid_envelope")
    signature_record = signatures[0]
    if not isinstance(signature_record, dict) or set(signature_record) != {"keyid", "sig"}:
        raise InputRejected("invalid DSSE signature record", code="invalid_envelope")
    expected_keyid = jwk_thumbprint(trusted_jwk)
    if signature_record.get("keyid") != expected_keyid:
        raise InputRejected("envelope keyid does not match the trusted public key", code="untrusted_key")
    payload = _b64_decode(envelope.get("payload"), maximum=maximum_payload_bytes)
    signature = _b64_decode(signature_record.get("sig"), maximum=128)
    if len(signature) != 64:
        raise InputRejected("Ed25519 signature has the wrong length", code="invalid_signature")
    try:
        public_key_from_jwk(trusted_jwk).verify(signature, dsse_pae(payload_type, payload))
    except InvalidSignature as exc:
        raise InputRejected("DSSE signature verification failed", code="invalid_signature") from exc
    return payload


def _require_safe_regular_file(path: Path, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise InputRejected(f"{label} file is unavailable", code="invalid_key") from exc
    if path.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400 or not path.is_file():
        raise InputRejected(f"{label} must be a non-reparse regular file", code="invalid_key")
