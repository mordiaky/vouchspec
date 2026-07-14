# Changelog

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
- Deferred private repositories, arbitrary uploads, authentication, tenant storage, and
  executable sandboxing beyond Stage A.

Verification: 53 tests passed; one Windows symlink test was skipped because the host lacks
the required symlink privilege. Native Windows junction and hard-link regressions passed.
