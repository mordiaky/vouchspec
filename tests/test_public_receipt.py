from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from capabilityproof.catalog import CatalogStore
from capabilityproof.lifecycle import evaluate_receipt_lifecycle, verify_lifecycle_envelope
from capabilityproof.receipt import deterministic_json
from capabilityproof.signing import verify_receipt_envelope
from capabilityproof.signing import CATALOG_INDEX_PAYLOAD_TYPE, jwk_thumbprint, verify_dsse_envelope


ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "catalog" / "public"
SCHEMA_PATH = ROOT / "src" / "capabilityproof" / "schemas" / "capability-receipt.schema.json"
LOCK_PATH = ROOT / "requirements.lock"
BUILD_TIME = datetime(2026, 7, 14, 6, 0, tzinfo=timezone.utc)
PINNED_ROOT_KEYID = "zccWAwcnMzkQQUn8MXQDnpfUeGF0oavBZgYDoYfKgs4"


def test_checked_in_public_catalog_has_25_signed_immutable_receipts_from_12_owner_namespaces() -> None:
    store = CatalogStore(CATALOG)
    index = store.index()
    issuer_jwk = json.loads(store.issuer_jwk_bytes())
    root_jwk = json.loads(store.root_jwk_bytes())
    assert jwk_thumbprint(root_jwk) == PINNED_ROOT_KEYID
    assert (ROOT / "distribution" / "trust" / "root.jwk.json").read_bytes() == store.root_jwk_bytes()
    assert (ROOT / "distribution" / "trust" / "issuer.jwk.json").read_bytes() == store.issuer_jwk_bytes()
    lifecycle_envelope = store.lifecycle_envelope_bytes()
    feed, _ = verify_lifecycle_envelope(lifecycle_envelope, root_jwk)

    assert index["entry_count"] == 25
    assert index["repository_owner_count"] == 12
    assert len(feed["receipts"]) == 25
    assert len(list((CATALOG / "receipts").glob("*.dsse.json"))) == 25
    exact_index = verify_dsse_envelope(
        store.index_envelope_bytes(),
        CATALOG_INDEX_PAYLOAD_TYPE,
        issuer_jwk,
        maximum_payload_bytes=5_000_000,
    )
    assert exact_index == store.index_bytes()

    for entry in index["entries"]:
        envelope_bytes = store.receipt_envelope_bytes(entry["receipt_id"])
        receipt, exact_payload = verify_receipt_envelope(envelope_bytes, issuer_jwk)
        assert exact_payload == deterministic_json(receipt)
        assert receipt["receipt_id"] == entry["receipt_id"]
        assert receipt["artifact"]["digest"]["sha256"] == entry["artifact_sha256"]
        assert receipt["provenance"]["source_commit"] == entry["source_commit"]
        assert receipt["provenance"]["artifact_path"] == entry["artifact_path"]
        assert receipt["evidence_labels"] == entry["evidence_labels"]
        assert {"DIGEST_PINNED", "STATIC_INSPECTION_COMPLETED", "INDEPENDENT_STATIC_SCAN"}.issubset(
            receipt["evidence_labels"]
        )
        assert hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest() == receipt["schema_sha256"]
        assert hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest() == receipt["methodology"]["reference_dependency_lock_sha256"]
        status = evaluate_receipt_lifecycle(
            envelope_bytes,
            lifecycle_envelope,
            root_jwk,
            now=BUILD_TIME,
        )
        assert status["signature"] == "valid"
        assert status["lifecycle"] == "CURRENT"


def test_public_catalog_contains_no_signing_secrets_or_private_keys() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.splitlines()
    assert all("private" not in path.casefold() and "passphrase" not in path.casefold() for path in tracked)
    for path in CATALOG.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            assert b"BEGIN PRIVATE KEY" not in content
            assert path.suffix == ".json"


def test_git_preserves_every_byte_hashed_or_signed_into_public_receipts() -> None:
    attributes = {
        line.strip()
        for line in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "* text=auto eol=lf" in attributes
    assert "catalog/public/**/*.json text eol=lf" in attributes
    assert "requirements.lock text eol=lf" in attributes
    assert "src/capabilityproof/schemas/*.json text eol=lf" in attributes
