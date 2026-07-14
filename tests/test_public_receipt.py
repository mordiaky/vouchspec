import hashlib
import json
from pathlib import Path

import jsonschema

from capabilityproof.receipt import verify_receipt_integrity


ROOT = Path(__file__).parents[1]
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "public"
    / "openai-skill-creator-49f948faa9258a0c61caceaf225e179651397431.json"
)
SCHEMA_PATH = ROOT / "src" / "capabilityproof" / "schemas" / "capability-receipt.schema.json"
LOCK_PATH = ROOT / "requirements.lock"


def test_checked_in_public_receipt_matches_current_contract() -> None:
    receipt_bytes = RECEIPT_PATH.read_bytes()
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(receipt)
    assert verify_receipt_integrity(receipt)
    assert hashlib.sha256(receipt_bytes).hexdigest() == (
        "f08ee57a1377c196557f1688a4ff7cc340a721a522580e1e4cabf749c775347c"
    )
    assert hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest() == receipt["schema_sha256"]
    assert hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest() == (
        receipt["methodology"]["reference_dependency_lock_sha256"]
    )
    assert receipt["receipt_id"] == "cpr_b37e70baa4bf79bb8cdb3425"
    assert receipt["integrity"]["evidence_sha256"] == (
        "b37e70baa4bf79bb8cdb3425ae53bf944ee549f00cea76e264743f9887fc2fed"
    )
    assert receipt["artifact"]["digest"]["sha256"] == (
        "8145c5d9c0acc1926a17757a3ee68083ddcf813e9fc313894f8ae08b36a2efc4"
    )
    assert receipt["provenance"]["source_commit"] == "49f948faa9258a0c61caceaf225e179651397431"
    assert receipt["artifact"]["file_count"] == 7
    assert receipt["artifact"]["total_bytes"] == 56_734
    assert receipt["format_validation"]["status"] == "pass"
    assert receipt["evidence_levels"]["highest_contiguous_level"] == 3
    assert receipt["integrity_assurance"] == "digest-only-unauthenticated"


def test_git_preserves_every_byte_hashed_into_public_receipts() -> None:
    attributes = {
        line.strip()
        for line in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "* text=auto eol=lf" in attributes
    assert "receipts/public/*.json text eol=lf" in attributes
    assert "requirements.lock text eol=lf" in attributes
    assert "src/capabilityproof/schemas/*.json text eol=lf" in attributes
