"""Minimal CLI for the no-egress Stage B receipt signer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .errors import CapabilityProofError
from .signing import _require_safe_regular_file, load_private_key
from .stage_b_signer import sign_verified_worker_result


def _passphrase(path: Path) -> bytes:
    _require_safe_regular_file(path, "passphrase")
    raw = path.expanduser().resolve(strict=True).read_bytes()
    if len(raw) > 4_096:
        raise CapabilityProofError("passphrase file is too large", code="invalid_passphrase")
    return raw.rstrip(b"\r\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vouchspec-stage-b-signer")
    parser.add_argument("frozen_root", type=Path)
    parser.add_argument("--worker-output", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--passphrase-file", type=Path, required=True)
    parser.add_argument("--allowed-worker-image", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
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
    except (CapabilityProofError, OSError, ValueError) as exc:
        code = getattr(exc, "code", "operational_error")
        print(json.dumps({"error": {"code": code, "message": str(exc)}}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
