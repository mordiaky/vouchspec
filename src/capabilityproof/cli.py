"""Command-line entry point."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
from importlib.resources import files
import json
from pathlib import Path
import sys

from .api import create_server
from .catalog_api import create_catalog_server
from .catalog_builder import build_catalog_drafts, finalize_catalog_lifecycle, sign_catalog_drafts
from .catalog_mcp import run_catalog_mcp_server
from .errors import CapabilityProofError
from .lifecycle import LifecycleSequenceStore, evaluate_receipt_lifecycle_with_state, sign_lifecycle_feed
from .mcp_server import run_mcp_server
from .receipt import inspect_git_skill, inspect_skill
from .signing import (
    generate_encrypted_keypair,
    jwk_thumbprint,
    load_private_key,
    load_public_jwk,
    _require_safe_regular_file,
    sign_receipt_bytes,
    verify_receipt_envelope,
)
from .snapshot import resolve_allowed_path


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
