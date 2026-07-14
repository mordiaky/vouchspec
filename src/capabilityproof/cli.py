"""Command-line entry point."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import sys

from .api import create_server
from .catalog_api import create_catalog_server
from .catalog_builder import build_catalog_drafts, finalize_catalog_lifecycle, sign_catalog_drafts
from .catalog_mcp import run_catalog_mcp_server
from .commerce import build_fresh_validation_quote, load_strict_commerce_json
from .commerce_access import CommerceAccessStore
from .commerce_api import create_commerce_server
from .commerce_store import CommerceStore
from .errors import CapabilityProofError
from .lifecycle import LifecycleSequenceStore, evaluate_receipt_lifecycle_with_state, sign_lifecycle_feed
from .mcp_server import run_mcp_server
from .paid_lifecycle import PaidReceiptLifecycleStore
from .receipt import inspect_git_skill, inspect_skill
from .signing import (
    generate_encrypted_keypair,
    jwk_thumbprint,
    load_private_key,
    load_public_jwk,
    _require_safe_regular_file,
    sign_receipt_bytes,
    _strict_json,
    verify_receipt_envelope,
)
from .snapshot import resolve_allowed_path
from .stage_b import DockerNoEgressWorker, freeze_public_source
from .stage_b_signer import sign_verified_worker_result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vouchspec", description="Signed static-evidence receipts for exact public Agent Skills")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="inspect one exact local Agent Skill directory")
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.add_argument("--allow-root", type=Path, help="require path to be relative to this operator-owned root")
    inspect_parser.add_argument("--generated-at", help="timezone-aware ISO 8601 timestamp for reproducible output")
    inspect_parser.add_argument("--expires-in-days", type=int, default=7)
    inspect_parser.add_argument("--output", type=Path)
    inspect_parser.add_argument("--compact", action="store_true")

    inspect_git_parser = subparsers.add_parser(
        "inspect-git", help="inspect a skill and verify it exactly matches a clean local Git commit"
    )
    inspect_git_parser.add_argument("path", type=Path)
    inspect_git_parser.add_argument("--repository-root", type=Path, required=True)
    inspect_git_parser.add_argument("--generated-at", help="timezone-aware ISO 8601 timestamp for reproducible output")
    inspect_git_parser.add_argument("--expires-in-days", type=int, default=7)
    inspect_git_parser.add_argument("--output", type=Path)
    inspect_git_parser.add_argument("--compact", action="store_true")

    quote_parser = subparsers.add_parser(
        "quote-fresh-validation", help="validate a constrained Stage B request and print a non-orderable quote preview"
    )
    quote_parser.add_argument("request", type=Path, help="JSON request file")
    quote_parser.add_argument("--quote-id", help="deterministic q_<24 hex> identifier for testing")
    quote_parser.add_argument("--generated-at", help="timezone-aware ISO 8601 timestamp for reproducible output")

    freeze_parser = subparsers.add_parser(
        "freeze-public-validation",
        help="fetch and freeze one exact public GitHub skill without executing artifact content",
    )
    freeze_parser.add_argument("request", type=Path, help="strict Stage B JSON request file")
    freeze_parser.add_argument("--output-root", type=Path, required=True)

    worker_parser = subparsers.add_parser(
        "run-frozen-validation",
        help="inspect a verified frozen source in a pinned Docker worker with no network",
    )
    worker_parser.add_argument("frozen_root", type=Path)
    worker_parser.add_argument("--output", type=Path, required=True)
    worker_parser.add_argument(
        "--image",
        required=True,
        help="immutable sha256 image ID or registry reference with @sha256 digest",
    )
    worker_parser.add_argument("--generated-at", help="timezone-aware ISO 8601 timestamp")
    worker_parser.add_argument("--expires-in-days", type=int, default=7)

    stage_b_sign_parser = subparsers.add_parser(
        "sign-frozen-validation",
        help="sign exact worker receipt bytes after re-verifying freeze and isolation evidence",
    )
    stage_b_sign_parser.add_argument("frozen_root", type=Path)
    stage_b_sign_parser.add_argument("--worker-output", type=Path, required=True)
    stage_b_sign_parser.add_argument("--private-key", type=Path, required=True)
    stage_b_sign_parser.add_argument("--passphrase-file", type=Path)
    stage_b_sign_parser.add_argument("--allowed-worker-image", action="append", required=True)
    stage_b_sign_parser.add_argument("--output", type=Path, required=True)

    provision_commerce_parser = subparsers.add_parser(
        "provision-commerce-tenant",
        help="provision one sandbox tenant and print its API key exactly once",
    )
    provision_commerce_parser.add_argument("--database", type=Path, required=True)
    provision_commerce_parser.add_argument("--tenant-id")
    provision_commerce_parser.add_argument("--auth-pepper-env", default="VOUCHSPEC_AUTH_PEPPER_HEX")
    provision_commerce_parser.add_argument(
        "--delivery-secret-env", default="VOUCHSPEC_DELIVERY_SECRET_HEX"
    )

    commerce_server_parser = subparsers.add_parser(
        "serve-commerce-sandbox",
        help="run the authenticated nonsettling commerce API on loopback",
    )
    commerce_server_parser.add_argument("--database", type=Path, required=True)
    commerce_server_parser.add_argument("--port", type=int, default=8789)
    commerce_server_parser.add_argument("--auth-pepper-env", default="VOUCHSPEC_AUTH_PEPPER_HEX")
    commerce_server_parser.add_argument(
        "--delivery-secret-env", default="VOUCHSPEC_DELIVERY_SECRET_HEX"
    )

    serve_parser = subparsers.add_parser("serve", help="run the root-confined loopback JSON API")
    serve_parser.add_argument("--allow-root", type=Path, required=True)
    serve_parser.add_argument("--port", type=int, default=8787)

    mcp_parser = subparsers.add_parser("mcp", help="run the root-confined MCP stdio server")
    mcp_parser.add_argument("--allow-root", type=Path, required=True)

    catalog_parser = subparsers.add_parser("serve-catalog", help="serve the read-only Stage A public catalog")
    catalog_parser.add_argument("--catalog-root", type=Path, required=True)
    catalog_parser.add_argument("--port", type=int, default=8788)
    catalog_parser.add_argument("--trusted-root-key", type=Path, required=True, help="independently provisioned root JWK")
    catalog_parser.add_argument("--sequence-state", type=Path, default=Path.home() / ".vouchspec" / "lifecycle-sequences.json")

    catalog_mcp_parser = subparsers.add_parser("mcp-catalog", help="run the read-only Stage A catalog MCP server")
    catalog_mcp_parser.add_argument("--catalog-root", type=Path, required=True)
    catalog_mcp_parser.add_argument("--trusted-root-key", type=Path, required=True, help="independently provisioned root JWK")
    catalog_mcp_parser.add_argument("--sequence-state", type=Path, default=Path.home() / ".vouchspec" / "lifecycle-sequences.json")

    build_parser = subparsers.add_parser("build-catalog", help="networked/keyless collection of curated Stage A drafts")
    build_parser.add_argument("--manifest", type=Path, required=True)
    build_parser.add_argument("--cache-root", type=Path, required=True)
    build_parser.add_argument("--output-root", type=Path, required=True)
    build_parser.add_argument("--generated-at", help="timezone-aware ISO 8601 timestamp for a reproducible build")

    sign_catalog_parser = subparsers.add_parser("sign-catalog", help="no-network issuer signing of bounded catalog drafts")
    sign_catalog_parser.add_argument("--drafts-root", type=Path, required=True)
    sign_catalog_parser.add_argument("--output-root", type=Path, required=True)
    sign_catalog_parser.add_argument("--issuer-private-key", type=Path, required=True)
    sign_catalog_parser.add_argument("--issuer-passphrase-file", type=Path)

    finalize_parser = subparsers.add_parser("finalize-catalog", help="offline root signing of catalog lifecycle metadata")
    finalize_parser.add_argument("--catalog-root", type=Path, required=True)
    finalize_parser.add_argument("--root-private-key", type=Path, required=True)
    finalize_parser.add_argument("--root-passphrase-file", type=Path)
    finalize_parser.add_argument("--generated-at", help="timezone-aware ISO 8601 timestamp")
    finalize_parser.add_argument("--previous-lifecycle", type=Path, help="previous root-signed feed to increment")

    keygen_parser = subparsers.add_parser("keygen", help="create an encrypted Ed25519 signing key and public JWK")
    keygen_parser.add_argument("--private-key", type=Path, required=True)
    keygen_parser.add_argument("--public-key", type=Path, required=True)
    keygen_parser.add_argument("--passphrase-file", type=Path)

    sign_parser = subparsers.add_parser("sign", help="DSSE-sign the exact bytes of an existing receipt")
    sign_parser.add_argument("receipt", type=Path)
    sign_parser.add_argument("--private-key", type=Path, required=True)
    sign_parser.add_argument("--passphrase-file", type=Path)
    sign_parser.add_argument("--output", type=Path, required=True)

    sign_lifecycle_parser = subparsers.add_parser("sign-lifecycle", help="root-sign an exact lifecycle feed")
    sign_lifecycle_parser.add_argument("feed", type=Path)
    sign_lifecycle_parser.add_argument("--private-key", type=Path, required=True)
    sign_lifecycle_parser.add_argument("--passphrase-file", type=Path)
    sign_lifecycle_parser.add_argument("--output", type=Path, required=True)

    prepare_paid_lifecycle = subparsers.add_parser(
        "prepare-paid-lifecycle",
        help="build an exact unsigned lifecycle draft for delivered paid receipts",
    )
    prepare_paid_lifecycle.add_argument("--database", type=Path, required=True)
    prepare_paid_lifecycle.add_argument("--environment", choices=("sandbox", "live"), required=True)
    prepare_paid_lifecycle.add_argument(
        "--issuer-records",
        type=Path,
        required=True,
        help="strict JSON list of root-authorized issuer key records",
    )
    prepare_paid_lifecycle.add_argument("--changes", type=Path, help="strict JSON receipt-status changes")
    prepare_paid_lifecycle.add_argument("--generated-at", required=True)
    prepare_paid_lifecycle.add_argument("--expires-at", required=True)
    prepare_paid_lifecycle.add_argument("--output", type=Path, required=True)

    publish_paid_lifecycle = subparsers.add_parser(
        "publish-paid-lifecycle",
        help="verify and atomically import an offline-root-signed paid lifecycle envelope",
    )
    publish_paid_lifecycle.add_argument("--database", type=Path, required=True)
    publish_paid_lifecycle.add_argument("--environment", choices=("sandbox", "live"), required=True)
    publish_paid_lifecycle.add_argument("--envelope", type=Path, required=True)
    publish_paid_lifecycle.add_argument("--root-key", type=Path, required=True)

    export_paid_lifecycle = subparsers.add_parser(
        "export-paid-lifecycle",
        help="export the exact latest root-signed paid lifecycle envelope",
    )
    export_paid_lifecycle.add_argument("--database", type=Path, required=True)
    export_paid_lifecycle.add_argument("--environment", choices=("sandbox", "live"), required=True)
    export_paid_lifecycle.add_argument("--output", type=Path, required=True)

    verify_parser = subparsers.add_parser("verify", help="independently verify a signed receipt envelope")
    verify_parser.add_argument("envelope", type=Path)
    verify_parser.add_argument("--key", type=Path, required=True, help="pinned issuer public JWK")
    verify_parser.add_argument("--receipt-output", type=Path, help="write the exact verified receipt payload bytes")
    verify_parser.add_argument("--lifecycle", type=Path, help="root-signed lifecycle DSSE envelope")
    verify_parser.add_argument("--root-key", type=Path, help="pinned lifecycle root public JWK")
    verify_parser.add_argument("--sequence-state", type=Path, default=Path.home() / ".vouchspec" / "lifecycle-sequences.json")

    subparsers.add_parser("schema", help="print the Capability Receipt JSON Schema")
    return parser


def _write_receipt(receipt: dict, output: Path | None, compact: bool, artifact_root: Path) -> None:
    text = json.dumps(
        receipt,
        sort_keys=True,
        ensure_ascii=False,
        indent=None if compact else 2,
        separators=(",", ":") if compact else None,
    ) + "\n"
    if output is None:
        sys.stdout.buffer.write(text.encode("utf-8"))
        return
    target = output.expanduser().resolve(strict=False)
    root = artifact_root.expanduser().resolve(strict=True)
    try:
        target.relative_to(root)
    except ValueError:
        pass
    else:
        raise CapabilityProofError("output must be outside the inspected artifact root", code="output_inside_artifact")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def _passphrase(path: Path | None, *, confirm: bool = False) -> bytes:
    if path is not None:
        _require_safe_regular_file(path, "passphrase")
        raw = path.expanduser().resolve(strict=True).read_bytes()
        if len(raw) > 4_096:
            raise CapabilityProofError("passphrase file is too large", code="invalid_passphrase")
        value = raw.rstrip(b"\r\n")
    else:
        value = getpass.getpass("Signing-key passphrase: ").encode("utf-8")
        if confirm and value != getpass.getpass("Confirm passphrase: ").encode("utf-8"):
            raise CapabilityProofError("passphrases did not match", code="passphrase_mismatch")
    return value


def _write_json_file(path: Path, value: dict) -> None:
    target = path.expanduser().resolve(strict=False)
    if target.exists():
        raise CapabilityProofError("refusing to overwrite an existing output", code="output_exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))


def _write_exact_file(path: Path, value: bytes) -> Path:
    target = path.expanduser().resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(target, flags, 0o600)
    except FileExistsError as exc:
        raise CapabilityProofError(
            "refusing to overwrite an existing output",
            code="output_exists",
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def _timestamp_argument(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise CapabilityProofError(f"{field} is invalid", code="invalid_timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except (ValueError, OverflowError) as exc:
        raise CapabilityProofError(f"{field} is invalid", code="invalid_timestamp") from exc
    if parsed.tzinfo is None:
        raise CapabilityProofError(f"{field} requires a timezone", code="invalid_timestamp")
    return parsed.astimezone(timezone.utc)


def _strict_json_file(path: Path, field: str, *, maximum_bytes: int) -> object:
    target = path.expanduser().resolve(strict=True)
    _require_safe_regular_file(target, field)
    if target.stat().st_size > maximum_bytes:
        raise CapabilityProofError(f"{field} file is too large", code="invalid_arguments")
    return _strict_json(target.read_bytes(), code="invalid_arguments")


def _commerce_secret(environment_name: str) -> bytes:
    if not isinstance(environment_name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", environment_name):
        raise CapabilityProofError("commerce secret environment name is invalid", code="invalid_arguments")
    raw = os.environ.get(environment_name)
    if raw is None:
        raise CapabilityProofError(
            f"required commerce secret environment variable is not set: {environment_name}",
            code="missing_secret",
        )
    if not re.fullmatch(r"[0-9a-fA-F]{64}", raw):
        raise CapabilityProofError(
            f"commerce secret environment variable must contain exactly 32 bytes as hex: {environment_name}",
            code="invalid_secret",
        )
    return bytes.fromhex(raw)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            target = resolve_allowed_path(args.allow_root, str(args.path)) if args.allow_root else args.path
            receipt = inspect_skill(target, generated_at=args.generated_at, expires_in_days=args.expires_in_days)
            _write_receipt(receipt, args.output, args.compact, target)
            return 0 if receipt["format_validation"]["status"] == "pass" else 2
        if args.command == "inspect-git":
            receipt = inspect_git_skill(
                args.path,
                args.repository_root,
                generated_at=args.generated_at,
                expires_in_days=args.expires_in_days,
            )
            _write_receipt(receipt, args.output, args.compact, args.path)
            return 0 if receipt["format_validation"]["status"] == "pass" else 2
        if args.command == "quote-fresh-validation":
            request = load_strict_commerce_json(args.request.read_text(encoding="utf-8"))
            generated_at = None
            if args.generated_at:
                normalized = args.generated_at[:-1] + "+00:00" if args.generated_at.endswith("Z") else args.generated_at
                generated_at = datetime.fromisoformat(normalized)
            quote = build_fresh_validation_quote(request, generated_at=generated_at, quote_id=args.quote_id)
            print(json.dumps(quote, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "freeze-public-validation":
            request = load_strict_commerce_json(args.request.read_text(encoding="utf-8"))
            frozen = freeze_public_source(
                request,
                args.output_root.expanduser().resolve(strict=False),
            )
            print(json.dumps({
                "artifact_directory_sha256": frozen.manifest["artifact_directory_sha256"],
                "freeze_manifest_digest": frozen.manifest["manifest_digest"],
                "frozen_root": str(frozen.root),
                "request_digest": frozen.manifest["request_digest"],
            }, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "run-frozen-validation":
            result = DockerNoEgressWorker(args.image).run(
                args.frozen_root.expanduser().resolve(strict=True),
                args.output.expanduser().resolve(strict=False),
                generated_at=args.generated_at,
                expires_in_days=args.expires_in_days,
            )
            print(json.dumps({
                "execution": str(result.execution_path),
                "output_root": str(result.output_root),
                "receipt": str(result.receipt_path),
                "receipt_id": result.receipt["receipt_id"],
            }, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "sign-frozen-validation":
            private_key = load_private_key(
                args.private_key.expanduser().resolve(strict=True),
                _passphrase(args.passphrase_file),
            )
            report = sign_verified_worker_result(
                args.frozen_root.expanduser().resolve(strict=True),
                args.worker_output.expanduser().resolve(strict=True),
                args.output.expanduser().resolve(strict=False),
                private_key,
                allowed_image_references=set(args.allowed_worker_image),
            )
            print(json.dumps(report, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command in {"provision-commerce-tenant", "serve-commerce-sandbox"}:
            commerce_store = CommerceStore(
                args.database.expanduser().resolve(strict=False), environment="sandbox"
            )
            access_store = CommerceAccessStore(
                commerce_store.path,
                environment="sandbox",
                auth_pepper=_commerce_secret(args.auth_pepper_env),
                delivery_secret=_commerce_secret(args.delivery_secret_env),
            )
            if args.command == "provision-commerce-tenant":
                credential = access_store.provision_tenant(tenant_id=args.tenant_id)
                print(json.dumps(credential, sort_keys=True, separators=(",", ":")))
                print("Store this sandbox API key securely; it is not persisted in plaintext.", file=sys.stderr)
                return 0
            server = create_commerce_server(commerce_store, access_store, args.port)
            host, port = server.server_address
            print(
                f"VouchSpec nonsettling commerce sandbox listening on http://{host}:{port}",
                file=sys.stderr,
            )
            server.serve_forever()
            return 0
        if args.command == "prepare-paid-lifecycle":
            commerce_store = CommerceStore(
                args.database.expanduser().resolve(strict=True),
                environment=args.environment,
            )
            issuer_records = _strict_json_file(
                args.issuer_records,
                "issuer records",
                maximum_bytes=256_000,
            )
            changes = (
                _strict_json_file(args.changes, "lifecycle changes", maximum_bytes=1_000_000)
                if args.changes
                else None
            )
            draft = PaidReceiptLifecycleStore(commerce_store).build_draft(
                issuer_records,  # type: ignore[arg-type]
                generated_at=_timestamp_argument(args.generated_at, "--generated-at"),
                expires_at=_timestamp_argument(args.expires_at, "--expires-at"),
                changes=changes,  # type: ignore[arg-type]
            )
            output = _write_exact_file(args.output, draft)
            feed = json.loads(draft)
            print(json.dumps({
                "draft_sha256": hashlib.sha256(draft).hexdigest(),
                "expires_at": feed["expires_at"],
                "output": str(output),
                "receipt_count": len(feed["receipts"]),
                "sequence": feed["sequence"],
            }, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "publish-paid-lifecycle":
            commerce_store = CommerceStore(
                args.database.expanduser().resolve(strict=True),
                environment=args.environment,
            )
            envelope_path = args.envelope.expanduser().resolve(strict=True)
            _require_safe_regular_file(envelope_path, "paid lifecycle envelope")
            if envelope_path.stat().st_size > 1_100_000:
                raise CapabilityProofError(
                    "paid lifecycle envelope file is too large",
                    code="invalid_arguments",
                )
            root_jwk = load_public_jwk(args.root_key.expanduser().resolve(strict=True))
            publication = PaidReceiptLifecycleStore(commerce_store).publish(
                envelope_path.read_bytes(),
                root_jwk,
            )
            print(json.dumps(publication, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "export-paid-lifecycle":
            commerce_store = CommerceStore(
                args.database.expanduser().resolve(strict=True),
                environment=args.environment,
            )
            envelope = PaidReceiptLifecycleStore(commerce_store).latest_envelope()
            output = _write_exact_file(args.output, envelope)
            print(json.dumps({
                "envelope_sha256": hashlib.sha256(envelope).hexdigest(),
                "output": str(output),
            }, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "serve":
            server = create_server(args.allow_root, args.port)
            host, port = server.server_address
            print(f"VouchSpec listening on http://{host}:{port}", file=sys.stderr)
            server.serve_forever()
            return 0
        if args.command == "mcp":
            run_mcp_server(args.allow_root)
            return 0
        if args.command == "serve-catalog":
            server = create_catalog_server(args.catalog_root, args.port, args.trusted_root_key, args.sequence_state)
            host, port = server.server_address
            print(f"VouchSpec read-only catalog listening on http://{host}:{port}", file=sys.stderr)
            server.serve_forever()
            return 0
        if args.command == "mcp-catalog":
            run_catalog_mcp_server(args.catalog_root, args.trusted_root_key, args.sequence_state)
            return 0
        if args.command == "build-catalog":
            generated_at = None
            if args.generated_at:
                normalized = args.generated_at[:-1] + "+00:00" if args.generated_at.endswith("Z") else args.generated_at
                generated_at = datetime.fromisoformat(normalized)
                if generated_at.tzinfo is None:
                    raise CapabilityProofError("--generated-at requires a timezone", code="invalid_timestamp")
                generated_at = generated_at.astimezone(timezone.utc)
            report = build_catalog_drafts(
                args.manifest.expanduser().resolve(strict=True),
                args.cache_root.expanduser().resolve(strict=False),
                args.output_root.expanduser().resolve(strict=False),
                generated_at=generated_at,
            )
            print(json.dumps(report, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "sign-catalog":
            issuer_key = load_private_key(
                args.issuer_private_key.expanduser().resolve(strict=True),
                _passphrase(args.issuer_passphrase_file),
            )
            report = sign_catalog_drafts(
                args.drafts_root.expanduser().resolve(strict=True),
                args.output_root.expanduser().resolve(strict=False),
                issuer_key,
            )
            print(json.dumps(report, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "finalize-catalog":
            generated_at = None
            if args.generated_at:
                normalized = args.generated_at[:-1] + "+00:00" if args.generated_at.endswith("Z") else args.generated_at
                generated_at = datetime.fromisoformat(normalized)
                if generated_at.tzinfo is None:
                    raise CapabilityProofError("--generated-at requires a timezone", code="invalid_timestamp")
            root_key = load_private_key(
                args.root_private_key.expanduser().resolve(strict=True),
                _passphrase(args.root_passphrase_file),
            )
            report = finalize_catalog_lifecycle(
                args.catalog_root.expanduser().resolve(strict=True),
                root_key,
                generated_at=generated_at,
                previous_envelope=args.previous_lifecycle.expanduser().resolve(strict=True) if args.previous_lifecycle else None,
            )
            print(json.dumps(report, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "keygen":
            jwk = generate_encrypted_keypair(
                args.private_key.expanduser().resolve(strict=False),
                args.public_key.expanduser().resolve(strict=False),
                _passphrase(args.passphrase_file, confirm=True),
            )
            print(json.dumps({"created": True, "keyid": jwk_thumbprint(jwk), "public_key": str(args.public_key)}))
            return 0
        if args.command in {"sign", "sign-lifecycle"}:
            private_key = load_private_key(args.private_key.expanduser().resolve(strict=True), _passphrase(args.passphrase_file))
            payload = args.receipt.read_bytes() if args.command == "sign" else args.feed.read_bytes()
            envelope = sign_receipt_bytes(payload, private_key) if args.command == "sign" else sign_lifecycle_feed(payload, private_key)
            _write_json_file(args.output, envelope)
            return 0
        if args.command == "verify":
            issuer_jwk = load_public_jwk(args.key.expanduser().resolve(strict=True))
            receipt, payload = verify_receipt_envelope(args.envelope.read_bytes(), issuer_jwk)
            if args.receipt_output:
                output = args.receipt_output.expanduser().resolve(strict=False)
                if output.exists():
                    raise CapabilityProofError("refusing to overwrite receipt output", code="output_exists")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(payload)
            result = {
                "signature": "valid",
                "lifecycle": "not-evaluated",
                "receipt_id": receipt["receipt_id"],
                "artifact_sha256": receipt["artifact"]["digest"]["sha256"],
                "source_commit": receipt["provenance"]["source_commit"],
                "issuer_keyid": jwk_thumbprint(issuer_jwk),
                "expires_at": receipt["validity"]["expires_at"],
            }
            if (args.lifecycle is None) != (args.root_key is None):
                raise CapabilityProofError("--lifecycle and --root-key must be supplied together", code="invalid_arguments")
            if args.lifecycle is not None:
                root_jwk = load_public_jwk(args.root_key.expanduser().resolve(strict=True))
                result = evaluate_receipt_lifecycle_with_state(
                    args.envelope.read_bytes(),
                    args.lifecycle.read_bytes(),
                    root_jwk,
                    LifecycleSequenceStore(args.sequence_state),
                )
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "schema":
            schema = files("capabilityproof").joinpath("schemas/capability-receipt.schema.json").read_text(encoding="utf-8")
            text = schema if schema.endswith("\n") else schema + "\n"
            sys.stdout.buffer.write(text.encode("utf-8"))
            return 0
    except KeyboardInterrupt:
        return 130
    except (CapabilityProofError, OSError, ValueError) as exc:
        code = getattr(exc, "code", "operational_error")
        print(json.dumps({"error": {"code": code, "message": str(exc)}}), file=sys.stderr)
        return 1
    return 1
