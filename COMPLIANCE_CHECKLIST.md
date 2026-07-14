# Compliance and trust checklist

## Stage A local implementation

- [x] `VouchSpec` is recorded as provisional and not legally/trademark cleared.
- [x] Catalog contains 25 deliberately selected public skills across 12 GitHub repository owners; publisher identity is not claimed.
- [x] Every source uses a full immutable Git commit and exact artifact subdirectory.
- [x] No original artifact files, archives, or executable payloads are redistributed;
  receipts contain bounded artifact-derived metadata and static-analysis excerpts.
- [x] Artifact content was not installed, imported, rendered, or executed.
- [x] No upload, private-repository, or customer-confidential input route exists.
- [x] Receipts use explicit factual labels and never a generic `VERIFIED` status.
- [x] Six structural failures remain visible and lack `STRUCTURE_VALIDATED`.
- [x] DSSE v1.0.2 signs exact receipt bytes with Ed25519 before JSON parsing.
- [x] RFC 8037 public JWKs and an independent CLI verifier are included.
- [x] Encrypted issuer/root private keys and passphrases are outside source and normal logs.
- [x] Separate root-signed lifecycle feed supports current, superseded, expired,
  evaluator-defect revocation, key-compromise revocation, staleness, and rollback handling.
- [x] REST and MCP catalog surfaces are read-only; POST is rejected.
- [x] Paid placement cannot change evidence labels, ranking, or severity.
- [x] No spend, payment, contract, account, recurring infrastructure, or customer obligation.
- [x] Independent P0-P2 signing/catalog/claims review closed; no remaining finding after
  distinct-key, startup-persistence, immutable-snapshot, and process-safe sequence fixes.

## Before live Stage A acceptance

- [x] Exact signed read-only catalog resources are live through GitHub-managed TLS/CORS;
  writes are rejected and dynamic search is performed locally from the signed index.
- [x] Read-only stdio MCP retrieval is publicly installable and passed a public-clone smoke.
- [x] Public root/issuer JWKs and fingerprints are published in a separate public Gist;
  same-account compromise remains an explicit limitation.
- [ ] One external publisher repository emits a commit/workflow-bound CI attestation.
- [ ] Ten legitimate external machine requests occur, including three repeats.
- [ ] One genuine machine-initiated paid request settles after a machine-readable quote.
- [ ] Compute, infrastructure, fees, and contribution margin are recorded.
- [ ] No owner call, customer meeting, or routine manual fulfillment is required.

## Before Stage B public-repository validation

- [ ] Allowlist public source hosts; require full commit and explicit subdirectory.
- [ ] Enforce streamed byte, individual file, count, depth, time, queue, and output limits.
- [ ] Freeze/hash all retrieved bytes before static analysis in an isolated non-executing worker.
- [ ] Run the full production-equivalent Linux suite across 20–50 public skills and at least
  10 repository-owner namespaces; do not infer publisher identity or independence.
- [ ] Cover traversal, absolute paths, symlinks, hard links, duplicate paths, case/Unicode
  collisions, archive bombs, excessive counts/sizes, malformed metadata, recursive
  references, hidden executables, credential requests, downloads, and permissions.
- [ ] Verify supported cross-OS determinism and record every skipped test.

## Deferred Stage C

Private storage, general authentication, tenant isolation, secure arbitrary uploads,
deletion/retention policy, expanded terms/privacy, and incident response remain deferred
until external demand and revenue justify them.
