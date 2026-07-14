"""Trusted hosted fulfillment bridge for the agent-only VouchSpec x402 API.

The networked phase claims one already-paid request and freezes an immutable
public Git commit. Artifact inspection and receipt signing each run in separate
Docker containers with no network. The worker never receives a buyer API key,
delivery capability, wallet credential, or CDP secret.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from uuid import UUID

from .commerce import load_strict_commerce_json, parse_fresh_validation_request
from .errors import CapabilityProofError
from .receipt import deterministic_json
from .signing import jwk_thumbprint, load_public_jwk, verify_receipt_envelope
from .stage_b import (
    DockerNoEgressWorker,
    FrozenSource,
    _IMAGE_REFERENCE,
    _run_bounded,
    _safe_docker_environment,
    freeze_public_source,
)


WORKER_VERSION = "vouchspec-stage-b-worker-v1"
MAX_API_RESPONSE_BYTES = 1_000_000
MAX_ENVELOPE_BYTES = 1_500_000
_WORKER_TOKEN = re.compile(r"vsw_test_[A-Za-z0-9_-]{43}")
_WORKER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{7,63}")
_ORDER_ID = re.compile(r"ord_[0-9a-f]{24}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_ERROR_CODE = re.compile(r"[a-z][a-z0-9_]{2,99}")
_SAFE_SIGNER_FAILURES = {
    ("invalid_key", "private key or passphrase is invalid"): "isolated_signer_invalid_key",
    ("missing_passphrase", "an encrypted-key passphrase is required"): "isolated_signer_missing_passphrase",
    ("signing_gate_failed", "worker result files are missing"): "isolated_signer_result_missing",
    ("signing_gate_failed", "worker receipt is empty or oversized"): "isolated_signer_receipt_size",
    ("signing_gate_failed", "worker execution report is empty or oversized"): "isolated_signer_execution_size",
    ("signing_gate_failed", "worker result is not UTF-8"): "isolated_signer_result_encoding",
    ("signing_gate_failed", "worker receipt integrity failed"): "isolated_signer_receipt_integrity",
    ("signing_gate_failed", "worker execution fields are invalid"): "isolated_signer_execution_fields",
    ("signing_gate_failed", "worker isolation evidence failed"): "isolated_signer_isolation_evidence",
    ("signing_gate_failed", "worker timing evidence is inconsistent"): "isolated_signer_timing_evidence",
    ("signing_gate_failed", "receipt is not bound to approved worker evidence"): "isolated_signer_receipt_binding",
    ("signing_gate_failed", "signing self-verification changed payload bytes"): "isolated_signer_self_verification",
    ("signing_gate_failed", "signed output could not be written"): "isolated_signer_output_write",
}
_SAFE_SIGNER_RUNTIME_MARKERS = (
    (b"permission denied", "isolated_signer_container_permission"),
    (b"read-only file system", "isolated_signer_container_readonly"),
    (b"invalid mount config", "isolated_signer_container_mount"),
    (b"mounts denied", "isolated_signer_container_mount"),
    (b"unable to find user", "isolated_signer_container_user"),
    (b"no such image", "isolated_signer_container_image"),
    (b"no such file or directory", "isolated_signer_container_path"),
    (b"modulenotfounderror", "isolated_signer_runtime_import"),
    (b"importerror", "isolated_signer_runtime_import"),
    (b"unrecognized arguments", "isolated_signer_cli_arguments"),
    (b"docker: error response from daemon", "isolated_signer_container_runtime"),
    (b"traceback (most recent call last)", "isolated_signer_runtime_exception"),
)


class HostedWorkerError(CapabilityProofError):
    """A redacted hosted-worker failure safe to emit in CI logs."""

    def __init__(self, message: str, *, code: str, retryable: bool = False) -> None:
        super().__init__(message, code=code)
        self.retryable = retryable


def _safe_signer_failure_code(stderr: bytes) -> str | None:
    """Map fixed signer failures to bounded codes without exposing stderr text."""
    if not stderr or len(stderr) > 16_384:
        return None
    try:
        lines = stderr.decode("utf-8", errors="strict").splitlines()
    except UnicodeError:
        return None
    for line in reversed(lines):
        if not line or len(line) > 4_096:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or set(value) != {"error"}:
            continue
        error = value["error"]
        if not isinstance(error, dict) or set(error) != {"code", "message"}:
            continue
        code = error["code"]
        message = error["message"]
        if not isinstance(code, str) or not isinstance(message, str):
            continue
        mapped = _SAFE_SIGNER_FAILURES.get((code, message))
        if mapped is not None:
            return mapped
    lowered = stderr.lower()
    for marker, mapped in _SAFE_SIGNER_RUNTIME_MARKERS:
        if marker in lowered:
            return mapped
    return None


@dataclass(frozen=True)
class HostedWorkerConfig:
    api_base_url: str
    worker_token: str
    worker_id: str
    image_reference: str
    issuer_private_key: Path
    issuer_passphrase: Path
    issuer_public_key: Path
    work_root: Path
    preclaimed_job: Path | None = None

    @classmethod
    def from_environment(cls) -> "HostedWorkerConfig":
        required = {
            name: os.environ.get(name, "").strip()
            for name in (
                "VOUCHSPEC_API_BASE_URL",
                "VOUCHSPEC_WORKER_TOKEN",
                "VOUCHSPEC_WORKER_IMAGE",
                "VOUCHSPEC_ISSUER_PRIVATE_KEY",
                "VOUCHSPEC_ISSUER_PASSPHRASE",
                "VOUCHSPEC_ISSUER_PUBLIC_KEY",
                "VOUCHSPEC_WORK_ROOT",
            )
        }
        if any(not value for value in required.values()):
            raise HostedWorkerError(
                "hosted worker configuration is incomplete",
                code="worker_configuration_invalid",
            )
        worker_id = os.environ.get("VOUCHSPEC_WORKER_ID", "github-actions-stage-b").strip()
        config = cls(
            api_base_url=_normalize_api_base_url(required["VOUCHSPEC_API_BASE_URL"]),
            worker_token=required["VOUCHSPEC_WORKER_TOKEN"],
            worker_id=worker_id,
            image_reference=required["VOUCHSPEC_WORKER_IMAGE"],
            issuer_private_key=Path(required["VOUCHSPEC_ISSUER_PRIVATE_KEY"]),
            issuer_passphrase=Path(required["VOUCHSPEC_ISSUER_PASSPHRASE"]),
            issuer_public_key=Path(required["VOUCHSPEC_ISSUER_PUBLIC_KEY"]),
            work_root=Path(required["VOUCHSPEC_WORK_ROOT"]),
            preclaimed_job=(
                Path(os.environ["VOUCHSPEC_PRECLAIMED_JOB"])
                if os.environ.get("VOUCHSPEC_PRECLAIMED_JOB", "").strip()
                else None
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not _WORKER_TOKEN.fullmatch(self.worker_token):
            raise HostedWorkerError(
                "hosted worker credential is invalid",
                code="worker_configuration_invalid",
            )
        if not _WORKER_ID.fullmatch(self.worker_id):
            raise HostedWorkerError(
                "hosted worker identity is invalid",
                code="worker_configuration_invalid",
            )
        if not _IMAGE_REFERENCE.fullmatch(self.image_reference):
            raise HostedWorkerError(
                "hosted worker image is not immutable",
                code="worker_configuration_invalid",
            )
        for path, label in (
            (self.issuer_private_key, "issuer private key"),
            (self.issuer_passphrase, "issuer passphrase"),
            (self.issuer_public_key, "issuer public key"),
        ):
            try:
                metadata = path.lstat()
            except OSError as exc:
                raise HostedWorkerError(
                    f"{label} is unavailable",
                    code="worker_configuration_invalid",
                ) from exc
            if path.is_symlink() or not path.is_file() or metadata.st_size <= 0:
                raise HostedWorkerError(
                    f"{label} is invalid",
                    code="worker_configuration_invalid",
                )
        if self.issuer_private_key.parent.resolve() != self.issuer_passphrase.parent.resolve():
            raise HostedWorkerError(
                "issuer secret files must share one private directory",
                code="worker_configuration_invalid",
            )
        if self.work_root.exists() or self.work_root.is_symlink():
            raise HostedWorkerError(
                "hosted worker output root already exists",
                code="worker_configuration_invalid",
            )
        if self.preclaimed_job is not None:
            try:
                metadata = self.preclaimed_job.lstat()
            except OSError as exc:
                raise HostedWorkerError(
                    "preclaimed worker job is unavailable",
                    code="worker_configuration_invalid",
                ) from exc
            if (
                self.preclaimed_job.is_symlink()
                or not self.preclaimed_job.is_file()
                or not 1 <= metadata.st_size <= MAX_API_RESPONSE_BYTES
            ):
                raise HostedWorkerError(
                    "preclaimed worker job is invalid",
                    code="worker_configuration_invalid",
                )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str):
        return None


def _normalize_api_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port not in {None, 443}
    ):
        raise HostedWorkerError(
            "hosted worker API URL must be an origin-only HTTPS URL",
            code="worker_configuration_invalid",
        )
    return f"https://{parsed.hostname.lower()}"


def _exact_object(value: Any, keys: set[str], *, code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise HostedWorkerError("worker API response is invalid", code=code)
    return value


def _post_json(
    config: HostedWorkerConfig,
    path: str,
    value: dict[str, Any],
    *,
    expected_status: int | tuple[int, ...],
) -> Any:
    body = deterministic_json(value)
    request = Request(
        f"{config.api_base_url}{path}",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.worker_token}",
            "Content-Type": "application/json",
            "User-Agent": "VouchSpec-Stage-B-Worker/1",
            "X-VouchSpec-Worker-Id": config.worker_id,
        },
    )
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    accepted = (expected_status,) if isinstance(expected_status, int) else expected_status
    try:
        with opener.open(request, timeout=30) as response:
            if response.status not in accepted:
                raise HostedWorkerError(
                    "worker API returned an unexpected status",
                    code="worker_api_rejected",
                    retryable=response.status == 429 or response.status >= 500,
                )
            raw = response.read(MAX_API_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise HostedWorkerError(
            "worker API rejected the request",
            code="worker_api_rejected",
            retryable=exc.code == 429 or exc.code >= 500,
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise HostedWorkerError(
            "worker API is temporarily unreachable",
            code="worker_api_unreachable",
            retryable=True,
        ) from exc
    if len(raw) > MAX_API_RESPONSE_BYTES:
        raise HostedWorkerError("worker API response is oversized", code="worker_api_invalid")
    if response.status == 204:
        if raw:
            raise HostedWorkerError("idle worker API response was not empty", code="worker_api_invalid")
        return None
    try:
        return load_strict_commerce_json(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, CapabilityProofError) as exc:
        raise HostedWorkerError("worker API response is invalid", code="worker_api_invalid") from exc


def _parse_claim(value: Any) -> dict[str, Any]:
    response = _exact_object(value, {"worker_version", "lease_seconds", "job"}, code="worker_claim_invalid")
    job = _exact_object(
        response["job"],
        {"order_id", "lease_token", "attempt", "request_digest", "request", "paid_at", "claimed_at"},
        code="worker_claim_invalid",
    )
    try:
        lease = UUID(job["lease_token"], version=4)
        paid_at = datetime.fromisoformat(job["paid_at"].replace("Z", "+00:00"))
        claimed_at = datetime.fromisoformat(job["claimed_at"].replace("Z", "+00:00"))
        normalized_request = parse_fresh_validation_request(job["request"])
    except (TypeError, ValueError, AttributeError, CapabilityProofError) as exc:
        raise HostedWorkerError("worker claim is invalid", code="worker_claim_invalid") from exc
    if (
        response["worker_version"] != WORKER_VERSION
        or response["lease_seconds"] != 1_200
        or not isinstance(job["order_id"], str)
        or not _ORDER_ID.fullmatch(job["order_id"])
        or str(lease) != job["lease_token"].lower()
        or isinstance(job["attempt"], bool)
        or not isinstance(job["attempt"], int)
        or not 1 <= job["attempt"] <= 3
        or not isinstance(job["request_digest"], str)
        or not _DIGEST.fullmatch(job["request_digest"])
        or job["request"] != normalized_request
        or paid_at.tzinfo is None
        or claimed_at.tzinfo is None
    ):
        raise HostedWorkerError("worker claim is invalid", code="worker_claim_invalid")
    return {**job, "request": normalized_request}


def _claim(config: HostedWorkerConfig) -> dict[str, Any] | None:
    value = _post_json(
        config,
        "/api/vouchspec/v1/internal/fulfillment/claim",
        {"worker_version": WORKER_VERSION},
        expected_status=(200, 204),
    )
    if value is None:
        return None
    return _parse_claim(value)


def _load_preclaimed_job(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = load_strict_commerce_json(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, CapabilityProofError) as exc:
        raise HostedWorkerError("preclaimed worker job is invalid", code="worker_claim_invalid") from exc
    return _parse_claim(value)


def _mount(source: Path, target: str, *, readonly: bool) -> str:
    option = f"type=bind,src={source.resolve(strict=True)},dst={target}"
    return f"{option},readonly" if readonly else option


def build_no_egress_signer_command(
    config: HostedWorkerConfig,
    frozen: FrozenSource,
    worker_output: Path,
    signed_output: Path,
    *,
    uid_gid: str,
) -> list[str]:
    secret_root = config.issuer_private_key.parent
    return [
        "docker", "run", "--rm", "--pull=never",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "32",
        "--memory", "256m",
        "--cpus", "1.0",
        "--ipc", "none",
        "--ulimit", "nofile=64:64",
        "--ulimit", "fsize=1048576:1048576",
        "--stop-timeout", "1",
        "--user", uid_gid,
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=8388608",
        "--mount", _mount(frozen.root, "/frozen", readonly=True),
        "--mount", _mount(worker_output, "/worker-output", readonly=True),
        "--mount", _mount(secret_root, "/secrets", readonly=True),
        "--mount", _mount(signed_output, "/signed", readonly=False),
        "--entrypoint", "python",
        config.image_reference,
        "-I", "-c",
        "import sys;sys.path.insert(0,'/app');from capabilityproof.stage_b_signer_cli import main;raise SystemExit(main())",
        "/frozen",
        "--worker-output", "/worker-output",
        "--allowed-worker-image", config.image_reference,
        "--private-key", f"/secrets/{config.issuer_private_key.name}",
        "--passphrase-file", f"/secrets/{config.issuer_passphrase.name}",
        "--output", "/signed/receipt.dsse.json",
    ]


def _sign_no_egress(
    config: HostedWorkerConfig,
    frozen: FrozenSource,
    worker_output: Path,
    signed_output: Path,
) -> Path:
    if os.name != "posix" or not hasattr(os, "getuid") or not hasattr(os, "getgid"):
        raise HostedWorkerError(
            "hosted signing requires a Linux container host",
            code="worker_configuration_invalid",
        )
    signed_output.mkdir(mode=0o700)
    command = build_no_egress_signer_command(
        config,
        frozen,
        worker_output,
        signed_output,
        uid_gid=f"{os.getuid()}:{os.getgid()}",
    )
    try:
        _run_bounded(
            command,
            cwd=signed_output,
            timeout_seconds=60,
            stdout_limit=64_000,
            code="isolated_signer_failed",
            environment=_safe_docker_environment(),
            error_code_parser=_safe_signer_failure_code,
        )
    except CapabilityProofError as exc:
        raise HostedWorkerError(
            "isolated signing gate failed",
            code=getattr(exc, "code", "isolated_signer_failed"),
        ) from exc
    envelope = signed_output / "receipt.dsse.json"
    if not envelope.is_file() or envelope.is_symlink():
        raise HostedWorkerError("isolated signer produced no envelope", code="isolated_signer_failed")
    return envelope


def _failure_code(error: Exception) -> tuple[str, bool]:
    code = getattr(error, "code", "worker_internal_error")
    if not isinstance(code, str) or not _ERROR_CODE.fullmatch(code):
        code = "worker_internal_error"
    retryable = bool(getattr(error, "retryable", False)) or code in {
        "source_checkout_failed",
        "isolated_worker_failed",
        "worker_api_unreachable",
        "worker_internal_error",
    }
    return code, retryable


def _fail(config: HostedWorkerConfig, job: dict[str, Any], error: Exception) -> None:
    code, retryable = _failure_code(error)
    _post_json(
        config,
        f"/api/vouchspec/v1/internal/fulfillment/{job['order_id']}/fail",
        {"lease_token": job["lease_token"], "error_code": code, "retryable": retryable},
        expected_status=200,
    )


def _complete(
    config: HostedWorkerConfig,
    job: dict[str, Any],
    envelope_bytes: bytes,
    receipt: dict[str, Any],
    key_id: str,
) -> dict[str, Any]:
    if not envelope_bytes or len(envelope_bytes) > MAX_ENVELOPE_BYTES:
        raise HostedWorkerError("signed envelope is invalid", code="isolated_signer_failed")
    envelope_digest = f"sha256:{hashlib.sha256(envelope_bytes).hexdigest()}"
    value = _post_json(
        config,
        f"/api/vouchspec/v1/internal/fulfillment/{job['order_id']}/complete",
        {
            "lease_token": job["lease_token"],
            "envelope_base64": base64.b64encode(envelope_bytes).decode("ascii"),
        },
        expected_status=200,
    )
    response = _exact_object(
        value,
        {"fulfillment", "public_receipt_path", "public_status_path"},
        code="worker_completion_invalid",
    )
    fulfillment = _exact_object(
        response["fulfillment"],
        {
            "order_id", "order_status", "payment_status", "delivery_status",
            "result_digest", "receipt_id", "signing_key_id", "counts_for_goal",
        },
        code="worker_completion_invalid",
    )
    digest_hex = envelope_digest.removeprefix("sha256:")
    if (
        fulfillment["order_id"] != job["order_id"]
        or fulfillment["order_status"] != "delivered"
        or fulfillment["payment_status"] not in {"captured", "available"}
        or fulfillment["delivery_status"] != "ready"
        or fulfillment["result_digest"] != envelope_digest
        or fulfillment["receipt_id"] != receipt.get("receipt_id")
        or fulfillment["signing_key_id"] != key_id
        or not isinstance(fulfillment["counts_for_goal"], bool)
        or response["public_receipt_path"] != f"/api/vouchspec/v1/receipts/{digest_hex}"
        or response["public_status_path"] != f"/api/vouchspec/v1/receipts/{digest_hex}/status"
    ):
        raise HostedWorkerError("worker completion response is invalid", code="worker_completion_invalid")
    return response


def run_once(config: HostedWorkerConfig) -> dict[str, Any]:
    config.validate()
    config.work_root.mkdir(mode=0o700, parents=True)
    job = _load_preclaimed_job(config.preclaimed_job) if config.preclaimed_job else _claim(config)
    if job is None:
        return {"status": "idle"}
    completion_attempted = False
    try:
        request_path = config.work_root / "request.json"
        request_path.write_bytes(deterministic_json(job["request"]) + b"\n")
        frozen = freeze_public_source(job["request"], config.work_root / "frozen")
        if frozen.manifest["request_digest"] != job["request_digest"]:
            raise HostedWorkerError("frozen request digest changed", code="worker_claim_invalid")
        worker_output = config.work_root / "worker-output"
        DockerNoEgressWorker(config.image_reference).run(frozen.root, worker_output)
        envelope_path = _sign_no_egress(
            config,
            frozen,
            worker_output,
            config.work_root / "signed",
        )
        envelope_bytes = envelope_path.read_bytes()
        issuer_jwk = load_public_jwk(config.issuer_public_key)
        receipt, _ = verify_receipt_envelope(envelope_bytes, issuer_jwk)
        completion_attempted = True
        completed = _complete(config, job, envelope_bytes, receipt, jwk_thumbprint(issuer_jwk))
        return {
            "status": "delivered",
            "public_receipt_path": completed["public_receipt_path"],
            "public_status_path": completed["public_status_path"],
        }
    except Exception as exc:
        if not completion_attempted:
            try:
                _fail(config, job, exc)
            except Exception:
                pass
        raise


def main() -> int:
    try:
        result = run_once(HostedWorkerConfig.from_environment())
    except Exception as exc:
        code, _ = _failure_code(exc)
        print(json.dumps({"status": "failed", "error_code": code}, separators=(",", ":")), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
