# VouchSpec static evidence methodology v0.2

## Profiles and scope

The scanner accepts one local directory containing `SKILL.md`. It inventories bounded
regular files; rejects symlinks, Windows reparse points/junctions, hard links, and special
files; and excludes only version-control metadata from artifact scope. It never installs,
imports, renders, or executes artifact content.

The local `inspect`/`inspect-git` commands and developer HTTP/MCP surfaces are not a remote
customer-input boundary. Stage A uses a separate builder that deliberately clones only
manifest-selected public HTTPS GitHub repositories at full 40-character commits. The
scanner never follows artifact-declared URLs or references.

Stage A receipt generation runs in three separate processes:

1. a networked **keyless collector** checks out public commits and emits bounded receipt
   drafts;
2. a no-network **issuer signer** validates draft schema/integrity and signs receipt and
   catalog-index bytes;
3. an offline **recovery root** authorizes the issuer and signs only lifecycle metadata.

Private repositories, uploads, customer-confidential content, and artifact execution are
outside Stage A.

## Checks

1. **Snapshot:** opened-handle identity checks, post-capture re-enumeration, sorted paths,
   per-file SHA-256, and a length-prefixed directory digest bind analysis to one byte set.
2. **Structure:** duplicate-key-rejecting restricted YAML plus bounded Agent Skills field,
   name, and reference rules. Failures remain signed evidence; they are not silently hidden.
3. **References:** local references are resolved only against the captured inventory.
   External references have credentials/query strings removed and are never fetched.
4. **Static review:** fixed rule IDs scan bounded UTF-8 text. Excerpts are length-limited and
   secret-redacted. Findings are indicators, not observed behavior.
5. **Receipt:** exact digest/commit, profiles, runtime, issue counts, coverage, environment,
   limitations, issuance/expiry, and tested/not-tested fields are machine-readable.

The inner receipt serialization is sorted compact UTF-8 JSON with `ensure_ascii=false` and
`allow_nan=false`. It is explicitly not RFC 8785 JCS. DSSE signs the exact bytes, so
signature verification never reconstructs JSON.

## Evidence labels

- `DIGEST_PINNED`: an exact directory digest is present.
- `STRUCTURE_VALIDATED`: the current structural profile passed; absent on a failure.
- `STATIC_INSPECTION_COMPLETED`: bounded static analysis completed with coverage recorded.
- `INDEPENDENT_STATIC_SCAN`: VouchSpec's curated operator-run Git profile produced it.
- `PUBLISHER_CI_ATTESTED`: reserved for a separately verified publisher CI attestation.
- `SANDBOX_BEHAVIOR_OBSERVED` and `TASK_EVALUATED`: reserved for later profiles.

No generic `VERIFIED` status is emitted. Git byte/commit equality does not verify publisher
identity or repository ownership.

## Authentication and lifecycle

Public receipts are DSSE v1.0.2 envelopes signed with Ed25519. Public keys use RFC 8037 JWK;
`keyid` is an RFC 7638 thumbprint and only a lookup hint. A client must pin the recovery-root
thumbprint through an independent trusted channel; the key bundled with the catalog is
discovery material only.

The root-signed feed has an expiring validity window and monotonically increasing sequence.
Verifiers persist the highest accepted sequence outside mutable catalog storage. State is
max-merged under a cross-process file lock and records the signed feed payload digest so an
equal-sequence conflicting feed is rejected. Catalog services persist the sequence during
startup, verify every index-to-receipt binding, and serve one immutable in-memory snapshot;
a new catalog generation requires a process restart.
The verifier reports `CURRENT`, `SUPERSEDED`, `EXPIRED`, `REVOKED_EVALUATOR_DEFECT`,
`REVOKED_KEY_COMPROMISE`, or `SIGNATURE_VALID_LIFECYCLE_UNKNOWN` for a valid receipt whose
feed is missing, stale, or rolled back. A compromised issuer revokes every receipt from that
key because issuance timestamps are signer-asserted, not trusted timestamps.

An immutable receipt remains evidence only about its exact digest. Any artifact byte/path
change requires a new receipt.

## Explicit non-claims and publication content

VouchSpec does not verify publisher identity, absence of malware, runtime compatibility,
task performance, trigger quality, network behavior, license meaning, or safety. A clean
static result means only that listed checks did not find listed indicators within recorded
coverage.

The catalog distributes no original artifact files, archives, or executable payloads.
Receipts do contain bounded artifact-derived metadata, paths, hashes, references, and
redacted static-analysis excerpts.
