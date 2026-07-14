from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import multiprocessing
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from capabilityproof.errors import InputRejected
from capabilityproof.lifecycle import (
    LifecycleSequenceStore,
    evaluate_receipt_lifecycle,
    evaluate_receipt_lifecycle_with_state,
    sign_lifecycle_feed,
)
from capabilityproof.receipt import deterministic_json, inspect_git_skill
from capabilityproof.signing import jwk_thumbprint, public_jwk, sign_receipt_bytes


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 14, 4, 0, tzinfo=timezone.utc)


def _record_sequence_worker(state_path: str, sequence: int, start: object) -> None:
    root = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("41" * 32))
    start.wait()  # type: ignore[attr-defined]
    try:
        LifecycleSequenceStore(Path(state_path)).record(
            public_jwk(root.public_key()),
            sequence,
            f"{sequence:064x}",
        )
    except InputRejected as exc:
        if exc.code != "lifecycle_rollback":
            raise


def _documents(tmp_path: Path) -> tuple[bytes, dict, Ed25519PrivateKey, dict]:
    repository = tmp_path / "repo"
    repository.mkdir()
    skill = repository / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: skill\ndescription: Lifecycle fixture.\n---\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=repository, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://example.invalid/fixture.git"], cwd=repository, check=True)
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repository, check=True)
    receipt = inspect_git_skill(skill, repository, generated_at="2026-07-14T03:00:00Z", independent_static_scan=True)
    issuer = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("31" * 32))
    envelope = sign_receipt_bytes(deterministic_json(receipt), issuer)
    root = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("41" * 32))
    issuer_jwk = public_jwk(issuer.public_key())
    feed = {
        "schema_version": "1.0.0",
        "sequence": 1,
        "generated_at": "2026-07-14T03:30:00Z",
        "expires_at": "2026-07-21T03:30:00Z",
        "issuer_keys": [{"keyid": jwk_thumbprint(issuer_jwk), "jwk": issuer_jwk, "status": "active"}],
        "receipts": [{"receipt_id": receipt["receipt_id"], "status": "current"}],
    }
    return json.dumps(envelope, separators=(",", ":")).encode(), feed, root, receipt


def _feed_envelope(feed: dict, root: Ed25519PrivateKey) -> bytes:
    envelope = sign_lifecycle_feed(deterministic_json(feed), root)
    return json.dumps(envelope, separators=(",", ":")).encode()


def test_current_expired_superseded_and_evaluator_revoked_states(tmp_path: Path) -> None:
    receipt_envelope, feed, root, receipt = _documents(tmp_path)
    root_jwk = public_jwk(root.public_key())
    result = evaluate_receipt_lifecycle(receipt_envelope, _feed_envelope(feed, root), root_jwk, now=NOW)
    assert result["lifecycle"] == "CURRENT"

    expired = evaluate_receipt_lifecycle(
        receipt_envelope,
        _feed_envelope(feed, root),
        root_jwk,
        now=datetime(2026, 7, 21, 3, 15, tzinfo=timezone.utc),
    )
    assert expired["lifecycle"] == "EXPIRED"

    short_feed = deepcopy(feed)
    short_feed["receipts"][0] = {
        "receipt_id": receipt["receipt_id"],
        "status": "superseded",
        "superseded_by": "cpr_0123456789abcdef01234567",
    }
    result = evaluate_receipt_lifecycle(receipt_envelope, _feed_envelope(short_feed, root), root_jwk, now=NOW)
    assert result["lifecycle"] == "SUPERSEDED"

    revoked = deepcopy(feed)
    revoked["receipts"][0] = {"receipt_id": receipt["receipt_id"], "status": "revoked_evaluator_defect", "reason": "ruleset defect"}
    result = evaluate_receipt_lifecycle(receipt_envelope, _feed_envelope(revoked, root), root_jwk, now=NOW)
    assert result["lifecycle"] == "REVOKED_EVALUATOR_DEFECT"


def test_compromised_key_revokes_every_receipt_and_stale_or_rollback_is_unknown(tmp_path: Path) -> None:
    receipt_envelope, feed, root, _ = _documents(tmp_path)
    root_jwk = public_jwk(root.public_key())
    compromised = deepcopy(feed)
    compromised["issuer_keys"][0]["status"] = "compromised"
    result = evaluate_receipt_lifecycle(receipt_envelope, _feed_envelope(compromised, root), root_jwk, now=NOW)
    assert result["lifecycle"] == "REVOKED_KEY_COMPROMISE"

    rollback = evaluate_receipt_lifecycle(
        receipt_envelope,
        _feed_envelope(feed, root),
        root_jwk,
        now=NOW,
        minimum_sequence=2,
    )
    assert rollback["lifecycle"] == "SIGNATURE_VALID_LIFECYCLE_UNKNOWN"

    stale = deepcopy(feed)
    stale["expires_at"] = "2026-07-14T03:45:00Z"
    result = evaluate_receipt_lifecycle(receipt_envelope, _feed_envelope(stale, root), root_jwk, now=NOW)
    assert result["lifecycle"] == "SIGNATURE_VALID_LIFECYCLE_UNKNOWN"

    future = deepcopy(feed)
    future["generated_at"] = "2026-07-14T04:30:00Z"
    result = evaluate_receipt_lifecycle(receipt_envelope, _feed_envelope(future, root), root_jwk, now=NOW)
    assert result["lifecycle"] == "SIGNATURE_VALID_LIFECYCLE_UNKNOWN"
    assert "future-dated" in result["reason"]

    with pytest.raises(InputRejected):
        evaluate_receipt_lifecycle(b"not even json", _feed_envelope(stale, root), root_jwk, now=NOW)


def test_highest_feed_sequence_is_persisted_and_lower_feed_cannot_restore_current(tmp_path: Path) -> None:
    receipt_envelope, feed, root, _ = _documents(tmp_path)
    root_jwk = public_jwk(root.public_key())
    state = LifecycleSequenceStore(tmp_path / "sequence-state.json")
    newer = deepcopy(feed)
    newer["sequence"] = 2
    result = evaluate_receipt_lifecycle_with_state(receipt_envelope, _feed_envelope(newer, root), root_jwk, state, now=NOW)
    assert result["lifecycle"] == "CURRENT"
    assert state.minimum(root_jwk) == 2

    replay = evaluate_receipt_lifecycle_with_state(receipt_envelope, _feed_envelope(feed, root), root_jwk, state, now=NOW)
    assert replay["signature"] == "valid"
    assert replay["lifecycle"] == "SIGNATURE_VALID_LIFECYCLE_UNKNOWN"
    assert state.minimum(root_jwk) == 2


def test_sequence_store_rejects_equal_sequence_equivocation(tmp_path: Path) -> None:
    root = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("41" * 32))
    root_jwk = public_jwk(root.public_key())
    state = LifecycleSequenceStore(tmp_path / "sequence-state.json")
    state.record(root_jwk, 3, "a" * 64)
    with pytest.raises(InputRejected, match="equivocation"):
        state.record(root_jwk, 3, "b" * 64)


def test_sequence_store_keeps_cross_process_maximum(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    state_path = tmp_path / "sequence-state.json"
    processes = [
        context.Process(target=_record_sequence_worker, args=(str(state_path), sequence, start))
        for sequence in range(1, 9)
    ]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0
    root = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("41" * 32))
    assert LifecycleSequenceStore(state_path).minimum(public_jwk(root.public_key())) == 8
