from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from capabilityproof.errors import InputRejected
from capabilityproof.receipt import deterministic_json, inspect_skill
from capabilityproof.signing import (
    RECEIPT_PAYLOAD_TYPE,
    dsse_pae,
    jwk_thumbprint,
    public_jwk,
    sign_receipt_bytes,
    verify_receipt_envelope,
)


FIXTURES = Path(__file__).parent / "fixtures"


def _material() -> tuple[Ed25519PrivateKey, bytes, dict, bytes]:
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("1f" * 32))
    receipt = inspect_skill(FIXTURES / "valid-skill", generated_at="2026-07-14T03:00:00Z")
    payload = deterministic_json(receipt)
    envelope = sign_receipt_bytes(payload, key)
    raw_envelope = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    return key, payload, envelope, raw_envelope


def test_dsse_pae_known_shape_and_exact_signed_bytes_round_trip() -> None:
    assert dsse_pae("text/plain", b"hello") == b"DSSEv1 10 text/plain 5 hello"
    key, payload, _, raw_envelope = _material()
    receipt, verified_payload = verify_receipt_envelope(raw_envelope, public_jwk(key.public_key()))
    assert verified_payload == payload
    assert receipt["artifact"]["root_directory"] == "valid-skill"


def test_jwk_thumbprint_is_stable_and_wrong_key_is_rejected() -> None:
    key, _, _, raw_envelope = _material()
    jwk = public_jwk(key.public_key())
    assert jwk_thumbprint(jwk) == jwk_thumbprint({"x": jwk["x"], "crv": "Ed25519", "kty": "OKP"})
    wrong = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("2f" * 32))
    with pytest.raises(InputRejected, match="keyid") as error:
        verify_receipt_envelope(raw_envelope, public_jwk(wrong.public_key()))
    assert error.value.code == "untrusted_key"


@pytest.mark.parametrize("field", ["payload", "payloadType", "sig"])
def test_one_bit_mutations_fail_closed(field: str) -> None:
    key, _, envelope, _ = _material()
    mutated = json.loads(json.dumps(envelope))
    if field == "payload":
        payload = bytearray(base64.b64decode(mutated["payload"]))
        payload[-1] ^= 1
        mutated["payload"] = base64.b64encode(payload).decode()
    elif field == "payloadType":
        mutated["payloadType"] = RECEIPT_PAYLOAD_TYPE[:-1] + "x"
    else:
        signature = bytearray(base64.b64decode(mutated["signatures"][0]["sig"]))
        signature[0] ^= 1
        mutated["signatures"][0]["sig"] = base64.b64encode(signature).decode()
    raw = json.dumps(mutated, separators=(",", ":")).encode()
    with pytest.raises(InputRejected):
        verify_receipt_envelope(raw, public_jwk(key.public_key()))


def test_duplicate_envelope_keys_and_signature_count_fail_profile() -> None:
    key, _, envelope, _ = _material()
    duplicate = b'{"payloadType":"x","payloadType":"y","payload":"eA==","signatures":[]}'
    with pytest.raises(InputRejected) as error:
        verify_receipt_envelope(duplicate, public_jwk(key.public_key()))
    assert error.value.code == "invalid_envelope"
    envelope["signatures"] = []
    with pytest.raises(InputRejected, match="exactly one"):
        verify_receipt_envelope(json.dumps(envelope).encode(), public_jwk(key.public_key()))


def test_signed_but_internally_tampered_receipt_fails_after_signature() -> None:
    key, payload, _, _ = _material()
    receipt = json.loads(payload)
    receipt["decision"]["status"] = "review-required"
    tampered_payload = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    signature = key.sign(dsse_pae(RECEIPT_PAYLOAD_TYPE, tampered_payload))
    envelope = {
        "payloadType": RECEIPT_PAYLOAD_TYPE,
        "payload": base64.b64encode(tampered_payload).decode(),
        "signatures": [{
            "keyid": jwk_thumbprint(public_jwk(key.public_key())),
            "sig": base64.b64encode(signature).decode(),
        }],
    }
    with pytest.raises(InputRejected) as error:
        verify_receipt_envelope(json.dumps(envelope).encode(), public_jwk(key.public_key()))
    assert error.value.code == "invalid_receipt_integrity"
