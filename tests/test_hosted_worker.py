from pathlib import Path

import pytest

from capabilityproof.hosted_worker import (
    HostedWorkerConfig,
    HostedWorkerError,
    _load_preclaimed_job,
    _normalize_api_base_url,
    _parse_claim,
    _safe_signer_failure_code,
    build_no_egress_signer_command,
)
from capabilityproof.stage_b import FrozenSource


REQUEST = {
    "schema_version": "1.0.0",
    "operation": "fresh_public_static_validation",
    "source": {
        "host": "github.com",
        "owner": "example",
        "repository": "agent-skill",
        "commit": "a" * 40,
        "skill_path": "skills/example",
    },
    "profile": "vouchspec-public-static-v1",
    "max_price": {"currency": "usd", "amount_minor": 4_900},
    "delivery_id": "agent_delivery_1",
}


def test_hosted_api_origin_is_https_only_and_redirect_free() -> None:
    assert _normalize_api_base_url("https://VOUCHSPEC.EXAMPLE/") == "https://vouchspec.example"
    for value in (
        "http://vouchspec.example",
        "https://user@vouchspec.example",
        "https://vouchspec.example/path",
        "https://vouchspec.example?next=elsewhere",
        "https://vouchspec.example:8443",
    ):
        with pytest.raises(HostedWorkerError):
            _normalize_api_base_url(value)


def test_signer_diagnostics_emit_only_allowlisted_codes() -> None:
    assert _safe_signer_failure_code(
        b'{"error":{"code":"signing_gate_failed","message":"worker isolation evidence failed"}}'
    ) == "isolated_signer_isolation_evidence"
    assert _safe_signer_failure_code(
        b'{"error":{"code":"invalid_key","message":"private key or passphrase is invalid"}}'
    ) == "isolated_signer_invalid_key"
    assert _safe_signer_failure_code(
        b'bounded runtime warning\n{"error":{"code":"signing_gate_failed","message":"worker timing evidence is inconsistent"}}\n'
    ) == "isolated_signer_timing_evidence"
    assert _safe_signer_failure_code(
        b'docker: Error response from daemon: unable to find user 1001: no matching entries in passwd file'
    ) == "isolated_signer_container_user"
    assert _safe_signer_failure_code(
        b'Traceback (most recent call last):\nModuleNotFoundError: No module named capabilityproof'
    ) == "isolated_signer_runtime_import"
    assert _safe_signer_failure_code(
        b'{"error":{"code":"signing_gate_failed","message":"secret=/tmp/private.pem"}}'
    ) is None
    assert _safe_signer_failure_code(
        b'{"error":{"code":"signing_gate_failed","message":"worker isolation evidence failed","path":"/tmp/key"}}'
    ) is None


def test_claim_contract_is_exact_and_lease_bound() -> None:
    value = {
        "worker_version": "vouchspec-stage-b-worker-v1",
        "lease_seconds": 1_200,
        "job": {
            "order_id": "ord_" + "1" * 24,
            "lease_token": "11111111-1111-4111-8111-111111111111",
            "attempt": 1,
            "request_digest": "sha256:" + "2" * 64,
            "request": REQUEST,
            "paid_at": "2026-07-14T12:00:00Z",
            "claimed_at": "2026-07-14T12:00:01Z",
        },
    }
    assert _parse_claim(value)["request"] == REQUEST
    value["job"]["unexpected"] = True
    with pytest.raises(HostedWorkerError):
        _parse_claim(value)


def test_preclaimed_job_is_revalidated_before_any_artifact_work(tmp_path: Path) -> None:
    value = {
        "worker_version": "vouchspec-stage-b-worker-v1",
        "lease_seconds": 1_200,
        "job": {
            "order_id": "ord_" + "1" * 24,
            "lease_token": "11111111-1111-4111-8111-111111111111",
            "attempt": 1,
            "request_digest": "sha256:" + "2" * 64,
            "request": REQUEST,
            "paid_at": "2026-07-14T12:00:00Z",
            "claimed_at": "2026-07-14T12:00:01Z",
        },
    }
    path = tmp_path / "claim.json"
    import json
    path.write_text(json.dumps(value), encoding="utf-8")
    assert _load_preclaimed_job(path)["order_id"] == value["job"]["order_id"]
    path.write_text('{"worker_version":"duplicate","worker_version":"duplicate"}', encoding="utf-8")
    with pytest.raises(HostedWorkerError):
        _load_preclaimed_job(path)


def test_signer_command_is_separate_no_egress_and_receives_only_read_only_inputs(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    frozen_root = tmp_path / "frozen"
    artifact = frozen_root / "source" / "example"
    worker_output = tmp_path / "worker"
    signed = tmp_path / "signed"
    for directory in (secret, artifact, worker_output, signed):
        directory.mkdir(parents=True)
    private = secret / "issuer-private.pem"
    passphrase = secret / "issuer-passphrase"
    public = tmp_path / "issuer-public.jwk.json"
    for path in (private, passphrase, public):
        path.write_text("test", encoding="utf-8")
    config = HostedWorkerConfig(
        api_base_url="https://vouchspec.example",
        worker_token="vsw_test_" + "A" * 43,
        worker_id="github-actions-stage-b",
        image_reference="sha256:" + "b" * 64,
        issuer_private_key=private,
        issuer_passphrase=passphrase,
        issuer_public_key=public,
        work_root=tmp_path / "unused",
    )
    frozen = FrozenSource(root=frozen_root, artifact_root=artifact, manifest={})
    command = build_no_egress_signer_command(
        config, frozen, worker_output, signed, uid_gid="1001:1001"
    )
    joined = " ".join(command)
    assert "--network none" in joined
    assert "--read-only" in command
    assert "--cap-drop ALL" in joined
    assert "--security-opt no-new-privileges" in joined
    assert f"src={secret.resolve()},dst=/secrets,readonly" in joined
    assert f"src={frozen_root.resolve()},dst=/frozen,readonly" in joined
    assert f"src={worker_output.resolve()},dst=/worker-output,readonly" in joined
    assert f"src={signed.resolve()},dst=/signed" in joined
    assert f"src={signed.resolve()},dst=/signed,readonly" not in joined
    assert "VOUCHSPEC_WORKER_TOKEN" not in joined
    assert "from capabilityproof.stage_b_signer_cli import main" in joined
    assert "from capabilityproof.cli import main" not in joined
