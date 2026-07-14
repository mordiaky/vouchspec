from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from capabilityproof.errors import InputRejected, PathRejected
from capabilityproof.commerce_store import CommerceStore, DIRECT_COST_CATEGORIES, FakePaymentProvider
from capabilityproof.fulfillment import SandboxFulfillmentCoordinator
from capabilityproof.provenance import ProvenanceEvidence
from capabilityproof.receipt import deterministic_json, inspect_skill
from capabilityproof.signing import public_jwk, verify_receipt_envelope
from capabilityproof.snapshot import ScanLimits, collect_snapshot
from capabilityproof.stage_b import (
    DockerNoEgressWorker,
    FROZEN_SOURCE_PROFILE,
    MAX_GIT_REPOSITORY_BYTES,
    _enforce_repository_disk_limit,
    _extract_verified_archive,
    _manifest_digest,
    _parse_tree_listing,
    request_digest,
    verify_frozen_source,
)
from capabilityproof.stage_b_signer import sign_verified_worker_result


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
    "delivery_id": "delivery_1234",
}
ROOT = Path(__file__).parents[1]


def _git_blob(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def _tree_record(path: str, content: bytes, *, mode: str = "100644", kind: str = "blob") -> bytes:
    return (
        f"{mode} {kind} {_git_blob(content)} {len(content)}\t{path}".encode("utf-8") + b"\0"
    )


def _tar(entries: list[tuple[str, bytes, str]]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:") as archive:
        for name, content, kind in entries:
            member = tarfile.TarInfo(name)
            if kind == "file":
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            elif kind == "directory":
                member.type = tarfile.DIRTYPE
                archive.addfile(member)
            elif kind == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "SKILL.md"
                archive.addfile(member)
            else:  # pragma: no cover - test helper misuse
                raise AssertionError(kind)
    return output.getvalue()


def _make_frozen(tmp_path: Path) -> Path:
    root = tmp_path / "frozen"
    artifact = root / "source" / "postgres-best-practices"
    artifact.mkdir(parents=True)
    content = b"---\nname: postgres-best-practices\ndescription: test\n---\n"
    (artifact / "SKILL.md").write_bytes(content)
    snapshot = collect_snapshot(artifact)
    manifest = {
        "schema_version": "1.0.0",
        "profile": FROZEN_SOURCE_PROFILE,
        "request_digest": f"sha256:{request_digest(REQUEST)}",
        "source": REQUEST["source"],
        "repository_url": "https://github.com/supabase/agent-skills.git",
        "fetched_commit": "a" * 40,
        "frozen_artifact_path": "source/postgres-best-practices",
        "artifact_directory_sha256": snapshot.directory_sha256,
        "file_count": 1,
        "total_bytes": len(content),
        "files": [{
            "path": "SKILL.md",
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "git_blob_sha1": _git_blob(content),
            "git_mode": "100644",
        }],
        "network_phase": "completed_before_worker",
        "artifact_execution": "not_performed",
    }
    manifest["manifest_digest"] = f"sha256:{_manifest_digest(manifest)}"
    (root / "freeze-manifest.json").write_bytes(deterministic_json(manifest) + b"\n")
    return root


def _make_worker_output(tmp_path: Path, frozen_root: Path, *, image: str) -> tuple[Path, bytes]:
    frozen = verify_frozen_source(frozen_root)
    receipt = inspect_skill(
        frozen.artifact_root,
        generated_at="2026-07-14T12:00:00Z",
        expires_in_days=7,
        provenance=ProvenanceEvidence(
            repository_url=frozen.manifest["repository_url"],
            commit=frozen.manifest["fetched_commit"],
            artifact_path=frozen.manifest["source"]["skill_path"],
            method="exact-local-git-blob-match-v1",
        ),
        independent_static_scan=True,
    )
    receipt_bytes = deterministic_json(receipt) + b"\n"
    output = tmp_path / "worker-output"
    output.mkdir(parents=True)
    (output / "receipt.json").write_bytes(receipt_bytes)
    execution = {
        "schema_version": "1.0.0",
        "profile": "vouchspec-docker-no-egress-static-v1",
        "container_image": image,
        "network": "none",
        "root_filesystem": "read_only",
        "input_mount": "read_only",
        "capabilities": "all_dropped",
        "no_new_privileges": True,
        "uid_gid": "65532:65532",
        "pids_limit": 64,
        "memory_limit_bytes": 268_435_456,
        "cpu_limit": "1.0",
        "tmpfs": "16MiB_noexec_nosuid_nodev",
        "ipc": "none",
        "open_files_limit": 128,
        "file_size_limit_bytes": 1_048_576,
        "stop_timeout_seconds": 1,
        "output_channel": "bounded_stdout_1000000_bytes",
        "started_at": "2026-07-14T11:59:59Z",
        "completed_at": "2026-07-14T12:00:01Z",
        "duration_ms": 2000,
        "receipt_id": receipt["receipt_id"],
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "freeze_manifest_digest": frozen.manifest["manifest_digest"],
        "artifact_execution": "not_performed",
    }
    (output / "worker-execution.json").write_bytes(deterministic_json(execution) + b"\n")
    return output, receipt_bytes


def test_git_tree_metadata_accepts_only_bounded_regular_files() -> None:
    skill = b"---\nname: safe\ndescription: test\n---\n"
    script = b"print('text only')\n"
    raw = b"".join([
        _tree_record("skills/safe/SKILL.md", skill),
        _tree_record("skills/safe/scripts/check.py", script, mode="100755"),
    ])
    parsed = _parse_tree_listing(raw, "skills/safe", ScanLimits())
    assert list(parsed) == ["SKILL.md", "scripts/check.py"]
    assert parsed["scripts/check.py"]["git_mode"] == "100755"


@pytest.mark.parametrize(
    "raw",
    [
        _tree_record("skills/safe/SKILL.md", b"target", mode="120000"),
        b"160000 commit " + b"a" * 40 + b" -\tskills/safe/nested\x00",
        _tree_record("skills/safe/../escape", b"bad"),
        _tree_record("skills/safe/CON.txt", b"bad") + _tree_record("skills/safe/SKILL.md", b"ok"),
    ],
)
def test_git_tree_metadata_rejects_links_submodules_and_nonportable_paths(raw: bytes) -> None:
    with pytest.raises((InputRejected, PathRejected)):
        _parse_tree_listing(raw, "skills/safe", ScanLimits())


def test_git_tree_metadata_rejects_case_collisions() -> None:
    raw = (
        _tree_record("skills/safe/SKILL.md", b"one")
        + _tree_record("skills/safe/skill.md", b"two")
    )
    with pytest.raises(PathRejected, match="collision"):
        _parse_tree_listing(raw, "skills/safe", ScanLimits())


def test_git_repository_disk_ceiling_is_enforced(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    oversized = repository / "pack"
    with oversized.open("wb") as stream:
        stream.seek(MAX_GIT_REPOSITORY_BYTES)
        stream.write(b"x")
    with pytest.raises(InputRejected, match="64 MB"):
        _enforce_repository_disk_limit(repository)


def test_archive_is_manually_extracted_and_bound_to_git_blobs(tmp_path: Path) -> None:
    skill = b"---\nname: safe\ndescription: test\n---\n"
    expected = _parse_tree_listing(
        _tree_record("skills/safe/SKILL.md", skill), "skills/safe", ScanLimits()
    )
    archive = _tar([
        ("skills", b"", "directory"),
        ("skills/safe", b"", "directory"),
        ("skills/safe/SKILL.md", skill, "file"),
    ])
    artifact = tmp_path / "safe"
    _extract_verified_archive(archive, artifact, "skills/safe", expected, ScanLimits())
    assert (artifact / "SKILL.md").read_bytes() == skill
    assert expected["SKILL.md"]["sha256"] == hashlib.sha256(skill).hexdigest()


@pytest.mark.parametrize(
    "entries",
    [
        [("skills/safe/../escape", b"bad", "file")],
        [("skills/safe/SKILL.md", b"", "symlink")],
        [("skills/safe/SKILL.md", b"changed", "file")],
    ],
)
def test_archive_rejects_traversal_links_and_blob_mismatch(
    tmp_path: Path, entries: list[tuple[str, bytes, str]]
) -> None:
    expected = _parse_tree_listing(
        _tree_record("skills/safe/SKILL.md", b"expected"), "skills/safe", ScanLimits()
    )
    with pytest.raises((InputRejected, PathRejected)):
        _extract_verified_archive(_tar(entries), tmp_path / "safe", "skills/safe", expected, ScanLimits())


def test_frozen_source_is_rehashed_and_preserves_real_root_name(tmp_path: Path) -> None:
    root = _make_frozen(tmp_path)
    frozen = verify_frozen_source(root)
    assert frozen.artifact_root.name == "postgres-best-practices"
    assert frozen.manifest["request_digest"] == f"sha256:{request_digest(REQUEST)}"
    (frozen.artifact_root / "SKILL.md").write_text("mutated", encoding="utf-8")
    with pytest.raises(InputRejected, match="inventory changed"):
        verify_frozen_source(root)


@pytest.mark.parametrize("image", ["worker:latest", "worker:v1", "sha256:abc", "docker.io/x/worker"])
def test_worker_rejects_mutable_or_incomplete_image_references(image: str) -> None:
    with pytest.raises(ValueError, match="immutable"):
        DockerNoEgressWorker(image)


def test_worker_command_enforces_no_egress_and_least_privilege(tmp_path: Path) -> None:
    frozen = verify_frozen_source(_make_frozen(tmp_path))
    output = tmp_path / "output"
    output.mkdir()
    image = "sha256:" + "b" * 64
    command = DockerNoEgressWorker(image).command(
        frozen,
        generated_at="2026-07-14T12:00:00Z",
        expires_in_days=7,
        container_name="worker-test",
    )
    rendered = " ".join(command)
    for required in (
        "--pull=never", "--network none", "--read-only", "--cap-drop ALL",
        "no-new-privileges", "--pids-limit 64", "--memory 256m", "--cpus 1.0",
        "--user 65532:65532", "/tmp:rw,noexec,nosuid,nodev,size=16777216",
        "dst=/frozen,readonly",
        "--ipc none", "nofile=128:128", "fsize=1048576:1048576",
    ):
        assert required in rendered
    assert image in command
    assert "dst=/output" not in rendered
    assert "--output" not in command


def test_signing_gate_reverifies_worker_and_signs_exact_receipt_bytes(tmp_path: Path) -> None:
    frozen_root = _make_frozen(tmp_path)
    image = "sha256:" + "d" * 64
    worker_output, receipt_bytes = _make_worker_output(tmp_path, frozen_root, image=image)
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("1f" * 32))
    envelope_path = tmp_path / "delivery" / "receipt.dsse.json"
    report = sign_verified_worker_result(
        frozen_root,
        worker_output,
        envelope_path,
        key,
        allowed_image_references={image},
    )
    receipt, verified_payload = verify_receipt_envelope(
        envelope_path.read_bytes(), public_jwk(key.public_key())
    )
    assert verified_payload == receipt_bytes
    assert report["receipt_id"] == receipt["receipt_id"]
    assert report["container_image"] == image


@pytest.mark.parametrize(("field", "value"), [("network", "bridge"), ("artifact_execution", "performed")])
def test_signing_gate_rejects_weakened_worker_evidence(tmp_path: Path, field: str, value: str) -> None:
    frozen_root = _make_frozen(tmp_path)
    image = "sha256:" + "d" * 64
    worker_output, _ = _make_worker_output(tmp_path, frozen_root, image=image)
    execution_path = worker_output / "worker-execution.json"
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    execution[field] = value
    execution_path.write_bytes(deterministic_json(execution) + b"\n")
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("1f" * 32))
    with pytest.raises(InputRejected) as error:
        sign_verified_worker_result(
            frozen_root,
            worker_output,
            tmp_path / "receipt.dsse.json",
            key,
            allowed_image_references={image},
        )
    assert error.value.code == "signing_gate_failed"


def test_signing_gate_requires_explicitly_allowlisted_immutable_image(tmp_path: Path) -> None:
    frozen_root = _make_frozen(tmp_path)
    image = "sha256:" + "d" * 64
    worker_output, _ = _make_worker_output(tmp_path, frozen_root, image=image)
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("1f" * 32))
    with pytest.raises(InputRejected, match="isolation evidence"):
        sign_verified_worker_result(
            frozen_root,
            worker_output,
            tmp_path / "receipt.dsse.json",
            key,
            allowed_image_references={"sha256:" + "e" * 64},
        )


def test_sandbox_coordinator_completes_signed_nonsettling_delivery(tmp_path: Path, monkeypatch) -> None:
    frozen_root = _make_frozen(tmp_path / "freeze-fixture")
    image = "sha256:" + "d" * 64
    worker_output, _ = _make_worker_output(tmp_path / "worker-fixture", frozen_root, image=image)
    frozen = verify_frozen_source(frozen_root)

    store = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
    quote = store.create_quote(REQUEST, quote_id="q_0123456789abcdef01234567", generated_at=now)
    order = store.create_order(
        quote["quote_id"],
        idempotency_key="order_attempt_001",
        buyer_reference="buyer_test_001",
        now=now + timedelta(minutes=1),
    )
    provider = FakePaymentProvider(store)
    provider.create_checkout(order["order_id"], occurred_at="2026-07-14T12:01:00Z")
    provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T12:02:00Z",
        processing_fee_minor=172,
    )

    class FakeWorker:
        image_reference = image

        def run(self, *_args, **_kwargs):
            return SimpleNamespace(output_root=worker_output)

    monkeypatch.setattr("capabilityproof.fulfillment.freeze_public_source", lambda *_args, **_kwargs: frozen)
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("1f" * 32))
    coordinator = SandboxFulfillmentCoordinator(store, worker=FakeWorker(), signing_key=key)
    costs = {category: 0 for category in DIRECT_COST_CATEGORIES}
    delivered = coordinator.fulfill(
        order["order_id"],
        frozen_cache_root=tmp_path / "cache",
        delivery_root=tmp_path / "deliveries",
        direct_costs_minor=costs,
    )
    assert delivered["order_status"] == "delivered"
    assert delivered["counts_for_goal"] is False
    assert delivered["settlement_status"] == "sandbox_nonsettling"
    assert delivered["envelope_sha256"]
    manifest = json.loads(
        (tmp_path / "deliveries" / order["order_id"] / "delivery-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["counts_for_goal"] is False
    assert manifest["settlement_status"] == "sandbox_nonsettling"


def test_checked_in_sandbox_proof_cannot_be_mistaken_for_commercial_evidence() -> None:
    proof = json.loads(
        (ROOT / "fulfillment" / "stage-b-sandbox-proof.json").read_text(encoding="utf-8")
    )
    assert proof["environment"] == "sandbox"
    assert proof["source_classification"] == "operator_owned_demo_excluded"
    assert proof["counts_for_goal"] is False
    assert proof["settlement_status"] == "sandbox_nonsettling"
    assert proof["worker"]["network"] == "none"
    assert proof["worker"]["writable_host_mount"] is False
    assert proof["worker"]["artifact_execution"] == "not_performed"
    assert proof["accounting"] == {
        "settled_revenue_minor": 0,
        "goal_revenue_minor": 0,
        "goal_buyers": 0,
        "goal_machine_requests": 0,
    }
