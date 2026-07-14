"""Command-line entry point."""

from __future__ import annotations

import argparse
from importlib.resources import files
import json
from pathlib import Path
import sys

from .api import create_server
from .errors import CapabilityProofError
from .mcp_server import run_mcp_server
from .receipt import inspect_git_skill, inspect_skill
from .snapshot import resolve_allowed_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="capabilityproof", description="Non-executing evidence receipts for exact Agent Skill directories")
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
            print(f"CapabilityProof listening on http://{host}:{port}", file=sys.stderr)
            server.serve_forever()
            return 0
        if args.command == "mcp":
            run_mcp_server(args.allow_root)
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
