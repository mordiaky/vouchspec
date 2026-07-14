"""Entrypoint logic executed only inside the Stage B no-egress worker container."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .provenance import ProvenanceEvidence
from .receipt import deterministic_json, inspect_skill
from .stage_b import FROZEN_SOURCE_PROFILE, verify_frozen_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vouchspec-stage-b-worker")
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--expires-in-days", type=int, default=7)
    args = parser.parse_args(argv)

    frozen = verify_frozen_source(args.frozen_root)
    manifest = frozen.manifest
    if manifest["profile"] != FROZEN_SOURCE_PROFILE:
        raise ValueError("unsupported frozen source profile")
    provenance = ProvenanceEvidence(
        repository_url=manifest["repository_url"],
        commit=manifest["fetched_commit"],
        artifact_path=manifest["source"]["skill_path"],
        method="exact-local-git-blob-match-v1",
    )
    receipt = inspect_skill(
        frozen.artifact_root,
        generated_at=args.generated_at,
        expires_in_days=args.expires_in_days,
        provenance=provenance,
        independent_static_scan=True,
    )
    if receipt["artifact"]["digest"]["sha256"] != manifest["artifact_directory_sha256"]:
        raise ValueError("receipt digest does not match the frozen source")
    sys.stdout.buffer.write(deterministic_json(receipt) + b"\n")
    sys.stdout.buffer.flush()
    return 0
