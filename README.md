# CapabilityProof

CapabilityProof (an internal working name) turns an exact Agent Skill directory into a
machine-readable evidence receipt. Version `0.1.0` hashes files, validates `SKILL.md`,
checks local references, extracts dependencies and requirement signals, and runs
transparent text/code rules. It does **not** install, import, render, or execute the
artifact, and it does not claim that an artifact is safe.

This is a **local-development evidence prototype** for controlled public or synthetic
artifacts. It is not an external intake service and must not receive customer/private or
otherwise untrusted third-party inputs. External launch remains blocked on immutable
raw-byte upload, isolated no-egress workers, authentication/TLS, tenant controls, RFC 8785
JCS, signatures, authenticated keys, rotation/revocation, and invalidation.

## What exists now

- Bounded, re-enumerated local directory snapshot and SHA-256 digest.
- Rejection of symbolic links, Windows reparse points/junctions, hard links, and special files.
- Agent Skills frontmatter validation for the published fields and duplicate-key rejection.
- Referenced-file containment and existence checks.
- Static risk-rule findings, inferred requirements, dependency evidence, and explicit coverage limits.
- Versioned deterministic-JSON evidence hash with digest-only, unauthenticated status.
- Local CLI, loopback developer HTTP API, and official-SDK MCP stdio tool.
- Windows junction/hard-link regressions, hostile parser fixtures, and contract tests.

## Local use

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\capabilityproof inspect C:\path\to\skill --output receipt.json
```

For Level 2 source/commit evidence, use a controlled local Git checkout. This command
does not fetch. It verifies that the complete inspected file set is tracked and that every
captured file exactly equals its raw blob at `HEAD`:

```powershell
.venv\Scripts\capabilityproof inspect-git C:\checkout\skills\example `
  --repository-root C:\checkout --output receipt.json
```

For a byte-reproducible receipt, supply a fixed timezone-aware timestamp. The receipt
labels capture times as a caller-supplied reproducibility override in this mode.

```powershell
.venv\Scripts\capabilityproof inspect C:\path\to\skill `
  --generated-at 2026-07-14T03:00:00Z --compact
```

## Local developer HTTP

The developer HTTP server binds only to loopback, uses bounded threaded requests, and
requires an explicit allowed root. Client paths must be relative to that root. This is a
local integration surface, not a remote service.

```powershell
.venv\Scripts\capabilityproof serve --allow-root C:\approved\skills --port 8787
```

```http
POST /v1/inspect
Content-Type: application/json

{"path":"pdf-processing","generated_at":"2026-07-14T03:00:00Z","expires_in_days":7}
```

## Local MCP stdio

```powershell
.venv\Scripts\capabilityproof mcp --allow-root C:\approved\skills
```

The stdio server exposes `inspect_skill` and `get_methodology`. Artifact-derived strings
appear only in structured receipt content and remain untrusted data. The current SDK
surface has no external-service authentication or tenant boundary.

## Evidence semantics

`highest_contiguous_level` is conservative. A local scan can complete Level 1 structural
validation and Level 3 static review while Level 2 publisher/source identity remains
unchecked; in that case the highest contiguous level remains 1. "Not detected" never means
"absent," and static review never means "safe."

The local snapshot is non-atomic but re-enumerated and checked against opened file handles.
The receipt is unsigned: its digest detects standalone payload changes, but an attacker
replacing the receipt can recompute the digest and receipt ID. Its named JSON profile is
fully specified and explicitly **not** RFC 8785 JCS.

See [methodology](docs/methodology.md), the
[receipt schema](src/capabilityproof/schemas/capability-receipt.schema.json), and the
[threat model](research/mvp-threat-model.md).
