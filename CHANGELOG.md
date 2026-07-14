# Changelog

## Unreleased

- Preserve publisher receipt/binding evidence for both structural passes and explicit
  structural failures, with separate structure/decision outputs.
- Install the publisher action runtime from a fully resolved hash-locked Linux/Python 3.11
  dependency set instead of dynamically resolving an unhashed tree.
- Publish a complete attested owned demo and self-serve publisher workflow; owned evidence
  remains excluded from external adoption.
- Add a strict $49 fresh public static validation request contract and non-orderable quote
  preview, exact nested schemas, duplicate-key rejection, separate order/payment states, and
  Stripe exact-body webhook authentication.
- Add GitHub-only exact-commit/subdirectory freezing with Git blob verification, hostile path
  and archive rejection, bounded repository/artifact intake, and content-addressed manifests.
- Add a pinned Docker static worker with no network or writable host mount, read-only filesystems,
  non-root execution, capability/resource limits, and bounded stdout-only receipt delivery.
- Add a constrained exact-byte Stage B signing gate, environment-bound SQLite commerce ledger,
  out-of-order/duplicate provider-event reconciliation, complete direct-cost accounting, and
  a fully delivered fake-provider sandbox proof that is permanently excluded from revenue.
- Replace the old external-alpha counters with the authoritative 30-test autonomous
  commercial goal and explicit exclusion accounting.

## 0.2.0 - 2026-07-13

Stage A alpha candidate under the provisional public name `VouchSpec`.

- Added 25 issuer-signed, exact-version Agent Skill receipts from 12 GitHub
  repository-owner namespaces, plus an issuer-signed catalog index.
- Added a separate recovery-root-signed lifecycle feed with expiry, revocation, monotonic
  sequence persistence, rollback detection, and equal-sequence equivocation rejection.
- Added read-only loopback REST and stdio MCP catalog retrieval with independently supplied
  root trust, bounded HTTP handling, immutable verified runtime snapshots, and no artifact
  submission route.
- Added explicit factual evidence labels, Ed25519/DSSE verification, encrypted signing-key
  tooling, and separated collection, issuer-signing, and recovery-root phases.
- Added a machine-readable public price/availability response; paid orders and settlement
  remain disabled.
- Published exact signed catalog resources through GitHub-managed TLS/CORS, an installable
  stdio MCP source, a commit-pinned publisher CI action, and a separate public root/issuer
  JWK fingerprint Gist. Operator-owned smoke traffic is not counted as external demand.
- Deferred private repositories, arbitrary uploads, authentication, tenant storage, and
  executable sandboxing beyond Stage A.

Verification: 53 tests passed; one Windows symlink test was skipped because the host lacks
the required symlink privilege. Native Windows junction and hard-link regressions passed.
