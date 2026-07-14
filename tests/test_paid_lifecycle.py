from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from capabilityproof.commerce_store import CommerceStore, DIRECT_COST_CATEGORIES, FakePaymentProvider
from capabilityproof.cli import main
from capabilityproof.errors import InputRejected
from capabilityproof.lifecycle import sign_lifecycle_feed
from capabilityproof.paid_lifecycle import PaidReceiptLifecycleStore
from capabilityproof.receipt import deterministic_json, inspect_git_skill
from capabilityproof.signing import jwk_thumbprint, public_jwk, sign_receipt_bytes


NOW = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
REQUEST = {
    "schema_version": "1.0.0",
    "operation": "fresh_public_static_validation",
    "source": {
        "host": "github.com",
        "owner": "supabase",
        "repository": "agent-skills",
        "commit": "a" * 40,
        "skill_path": "skills/postgres-best-practices",
    },
    "profile": "vouchspec-public-static-v1",
    "max_price": {"currency": "usd", "amount_minor": 4_900},
    "delivery_id": "delivery_paid_lifecycle",
}


def _receipt(tmp_path: Path, index: int, issuer: Ed25519PrivateKey) -> tuple[dict, bytes, bytes]:
    repository = tmp_path / f"repo-{index}"
    skill = repository / "skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: paid-{index}\ndescription: Paid lifecycle fixture {index}.\n---\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=repository, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", f"https://example.invalid/fixture-{index}.git"],
        cwd=repository,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repository, check=True)
    receipt = inspect_git_skill(
        skill,
        repository,
        generated_at="2026-07-14T11:00:00Z",
        independent_static_scan=True,
    )
    payload = deterministic_json(receipt)
    envelope = deterministic_json(sign_receipt_bytes(payload, issuer))
    return receipt, payload, envelope


def _deliver(
    store: CommerceStore,
    tmp_path: Path,
    index: int,
    issuer: Ed25519PrivateKey,
) -> tuple[dict, dict, bytes]:
    receipt, payload, envelope = _receipt(tmp_path, index, issuer)
    request = deepcopy(REQUEST)
    request["delivery_id"] = f"delivery_paid_{index:04d}"
    quote = store.create_quote(
        request,
        quote_id=f"q_{index:024x}",
        generated_at=NOW,
    )
    order = store.create_order(
        quote["quote_id"],
        idempotency_key=f"order_attempt_{index:03d}",
        buyer_reference=f"buyer_test_{index:03d}",
        now=NOW + timedelta(minutes=1),
    )
    provider = FakePaymentProvider(store)
    provider.create_checkout(order["order_id"], occurred_at="2026-07-14T12:01:00Z")
    provider.event(order["order_id"], "payment.captured", occurred_at="2026-07-14T12:02:00Z")
    store.record_direct_costs(
        order["order_id"],
        {category: 0 for category in DIRECT_COST_CATEGORIES},
        idempotency_key=f"cost_record_{index:03d}",
        recorded_at="2026-07-14T12:03:00Z",
    )
    store.begin_fulfillment(
        order["order_id"],
        source_reference=f"job_test_{index:03d}",
        occurred_at="2026-07-14T12:04:00Z",
    )
    delivered = store.deliver(
        order["order_id"],
        receipt_id=receipt["receipt_id"],
        receipt_sha256=hashlib.sha256(payload).hexdigest(),
        envelope_sha256=hashlib.sha256(envelope).hexdigest(),
        signing_keyid=jwk_thumbprint(public_jwk(issuer.public_key())),
        source_reference=f"job_test_{index:03d}",
        occurred_at="2026-07-14T12:05:00Z",
    )
    return delivered, receipt, envelope


def _keys() -> tuple[Ed25519PrivateKey, Ed25519PrivateKey, dict, list[dict]]:
    issuer = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("31" * 32))
    root = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("41" * 32))
    issuer_jwk = public_jwk(issuer.public_key())
    root_jwk = public_jwk(root.public_key())
    issuers = [{"keyid": jwk_thumbprint(issuer_jwk), "jwk": issuer_jwk, "status": "active"}]
    return issuer, root, root_jwk, issuers


def _signed(draft: bytes, root: Ed25519PrivateKey) -> bytes:
    return deterministic_json(sign_lifecycle_feed(draft, root))


def test_publish_and_evaluate_exact_paid_receipt_lifecycle(tmp_path: Path) -> None:
    issuer, root, root_jwk, issuers = _keys()
    commerce = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    order, receipt, receipt_envelope = _deliver(commerce, tmp_path, 1, issuer)
    lifecycle = PaidReceiptLifecycleStore(commerce)
    draft = lifecycle.build_draft(
        issuers,
        generated_at=NOW,
        expires_at=NOW + timedelta(days=7),
    )
    envelope = _signed(draft, root)
    publication = lifecycle.publish(envelope, root_jwk, published_at=NOW + timedelta(minutes=1))

    assert publication["sequence"] == 1
    assert publication["receipts"] == [
        {"receipt_id": receipt["receipt_id"], "status": "current", "order_id": order["order_id"]}
    ]
    assert lifecycle.latest_envelope() == envelope
    result = lifecycle.evaluate_order_receipt(
        order["order_id"],
        receipt_envelope,
        root_jwk,
        now=NOW + timedelta(minutes=2),
    )
    assert result["lifecycle"] == "CURRENT"
    assert result["receipt_id"] == receipt["receipt_id"]
    assert bytes.fromhex("41" * 32) not in (tmp_path / "commerce.db").read_bytes()

    with pytest.raises(InputRejected, match="timezone"):
        lifecycle.build_draft(
            issuers,
            generated_at=datetime(2026, 7, 14, 12, 0),
            expires_at=NOW + timedelta(days=1),
        )


def test_revocation_is_terminal_and_history_remains_exact(tmp_path: Path) -> None:
    issuer, root, root_jwk, issuers = _keys()
    commerce = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    order, receipt, receipt_envelope = _deliver(commerce, tmp_path, 1, issuer)
    lifecycle = PaidReceiptLifecycleStore(commerce)
    first = lifecycle.build_draft(issuers, generated_at=NOW, expires_at=NOW + timedelta(days=7))
    lifecycle.publish(_signed(first, root), root_jwk, published_at=NOW + timedelta(minutes=1))

    changes = {
        receipt["receipt_id"]: {
            "status": "revoked_evaluator_defect",
            "reason": "published evaluator rules were defective",
        }
    }
    second = lifecycle.build_draft(
        issuers,
        generated_at=NOW + timedelta(minutes=10),
        expires_at=NOW + timedelta(days=7, minutes=10),
        changes=changes,
    )
    lifecycle.publish(_signed(second, root), root_jwk, published_at=NOW + timedelta(minutes=11))
    result = lifecycle.evaluate_order_receipt(
        order["order_id"], receipt_envelope, root_jwk, now=NOW + timedelta(minutes=12)
    )
    assert result["lifecycle"] == "REVOKED_EVALUATOR_DEFECT"
    publications = lifecycle.publications()
    assert publications[0]["receipts"][0]["status"] == "current"
    assert publications[1]["receipts"][0]["status"] == "revoked_evaluator_defect"

    with pytest.raises(InputRejected, match="terminal"):
        lifecycle.build_draft(
            issuers,
            generated_at=NOW + timedelta(minutes=20),
            expires_at=NOW + timedelta(days=7, minutes=20),
            changes={receipt["receipt_id"]: {"status": "current"}},
        )


def test_publication_rejects_equivocation_gaps_root_change_and_issuer_restoration(tmp_path: Path) -> None:
    issuer, root, root_jwk, issuers = _keys()
    commerce = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    _deliver(commerce, tmp_path, 1, issuer)
    lifecycle = PaidReceiptLifecycleStore(commerce)
    draft = lifecycle.build_draft(issuers, generated_at=NOW, expires_at=NOW + timedelta(days=7))
    envelope = _signed(draft, root)
    first = lifecycle.publish(envelope, root_jwk, published_at=NOW + timedelta(minutes=1))
    assert lifecycle.publish(envelope, root_jwk, published_at=NOW + timedelta(minutes=2)) == first

    changed = json.loads(draft)
    changed["expires_at"] = "2026-07-21T11:59:59Z"
    with pytest.raises(InputRejected, match="equivocation"):
        lifecycle.publish(
            _signed(deterministic_json(changed), root),
            root_jwk,
            published_at=NOW + timedelta(minutes=2),
        )

    gap = json.loads(draft)
    gap["sequence"] = 3
    with pytest.raises(InputRejected, match="contiguous"):
        lifecycle.publish(
            _signed(deterministic_json(gap), root),
            root_jwk,
            published_at=NOW + timedelta(minutes=2),
        )

    other_root = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("51" * 32))
    second = json.loads(draft)
    second["sequence"] = 2
    with pytest.raises(InputRejected, match="root changed"):
        lifecycle.publish(
            _signed(deterministic_json(second), other_root),
            public_jwk(other_root.public_key()),
            published_at=NOW + timedelta(minutes=2),
        )

    compromised = deepcopy(issuers)
    compromised[0]["status"] = "compromised"
    draft2 = lifecycle.build_draft(
        compromised,
        generated_at=NOW + timedelta(minutes=10),
        expires_at=NOW + timedelta(days=7, minutes=10),
    )
    lifecycle.publish(_signed(draft2, root), root_jwk, published_at=NOW + timedelta(minutes=11))
    with pytest.raises(InputRejected, match="cannot be restored"):
        lifecycle.build_draft(
            issuers,
            generated_at=NOW + timedelta(minutes=20),
            expires_at=NOW + timedelta(days=7, minutes=20),
        )


def test_exact_coverage_and_real_successor_are_required(tmp_path: Path) -> None:
    issuer, root, root_jwk, issuers = _keys()
    commerce = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    lifecycle = PaidReceiptLifecycleStore(commerce)
    with pytest.raises(InputRejected, match="no delivered"):
        lifecycle.build_draft(issuers, generated_at=NOW, expires_at=NOW + timedelta(days=1))

    first_order, first_receipt, first_envelope = _deliver(commerce, tmp_path, 1, issuer)
    extra_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("61" * 32))
    extra_jwk = public_jwk(extra_key.public_key())
    with pytest.raises(InputRejected, match="exactly match"):
        lifecycle.build_draft(
            [*issuers, {"keyid": jwk_thumbprint(extra_jwk), "jwk": extra_jwk, "status": "active"}],
            generated_at=NOW,
            expires_at=NOW + timedelta(days=1),
        )
    with pytest.raises(InputRejected, match="unknown"):
        lifecycle.build_draft(
            issuers,
            generated_at=NOW,
            expires_at=NOW + timedelta(days=1),
            changes={"cpr_" + "f" * 24: {"status": "current"}},
        )
    with pytest.raises(InputRejected, match="first publish as current"):
        lifecycle.build_draft(
            issuers,
            generated_at=NOW,
            expires_at=NOW + timedelta(days=1),
            changes={
                first_receipt["receipt_id"]: {
                    "status": "revoked_evaluator_defect",
                    "reason": "invalid first state",
                }
            },
        )

    first = lifecycle.build_draft(issuers, generated_at=NOW, expires_at=NOW + timedelta(days=7))
    lifecycle.publish(_signed(first, root), root_jwk, published_at=NOW + timedelta(minutes=1))
    with pytest.raises(InputRejected, match="successor"):
        lifecycle.build_draft(
            issuers,
            generated_at=NOW + timedelta(minutes=10),
            expires_at=NOW + timedelta(days=7, minutes=10),
            changes={
                first_receipt["receipt_id"]: {
                    "status": "superseded",
                    "superseded_by": "cpr_" + "e" * 24,
                }
            },
        )

    _, successor, _ = _deliver(commerce, tmp_path, 2, issuer)
    second = lifecycle.build_draft(
        issuers,
        generated_at=NOW + timedelta(minutes=10),
        expires_at=NOW + timedelta(days=7, minutes=10),
        changes={
            first_receipt["receipt_id"]: {
                "status": "superseded",
                "superseded_by": successor["receipt_id"],
                "reason": "replaced by a newly delivered validation",
            }
        },
    )
    lifecycle.publish(_signed(second, root), root_jwk, published_at=NOW + timedelta(minutes=11))
    assert lifecycle.evaluate_order_receipt(
        first_order["order_id"], first_envelope, root_jwk, now=NOW + timedelta(minutes=12)
    )["lifecycle"] == "SUPERSEDED"


def test_cli_keeps_root_signing_offline_and_publishes_exact_envelope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    issuer, root, root_jwk, issuers = _keys()
    database = tmp_path / "commerce.db"
    commerce = CommerceStore(database, environment="sandbox")
    _deliver(commerce, tmp_path, 1, issuer)
    issuer_records = tmp_path / "issuers.json"
    issuer_records.write_bytes(deterministic_json(issuers))
    draft = tmp_path / "lifecycle-draft.json"
    assert main([
        "prepare-paid-lifecycle",
        "--database", str(database),
        "--environment", "sandbox",
        "--issuer-records", str(issuer_records),
        "--generated-at", "2026-07-14T12:00:00Z",
        "--expires-at", "2026-07-21T12:00:00Z",
        "--output", str(draft),
    ]) == 0
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["sequence"] == 1
    assert prepared["receipt_count"] == 1

    envelope = _signed(draft.read_bytes(), root)
    envelope_path = tmp_path / "lifecycle.dsse.json"
    root_path = tmp_path / "root.public.jwk.json"
    envelope_path.write_bytes(envelope)
    root_path.write_bytes(deterministic_json(root_jwk))
    assert main([
        "publish-paid-lifecycle",
        "--database", str(database),
        "--environment", "sandbox",
        "--envelope", str(envelope_path),
        "--root-key", str(root_path),
    ]) == 0
    assert json.loads(capsys.readouterr().out)["sequence"] == 1

    exported = tmp_path / "exported-lifecycle.dsse.json"
    assert main([
        "export-paid-lifecycle",
        "--database", str(database),
        "--environment", "sandbox",
        "--output", str(exported),
    ]) == 0
    assert exported.read_bytes() == envelope
