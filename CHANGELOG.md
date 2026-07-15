# Changelog

## Unreleased

- Launch the agent-only commercial endpoint at 0.25 USDC on Base mainnet, activate the isolated
  fulfillment worker, and move the official MCP Registry remote from sandbox to the live service.
- Replace the unsupported $49/Stripe-era price card with the researched 0.25-USDC agent-only
  x402 launch cohort, timestamped full-Bazaar evidence, and predeclared $0.10/$0.50 cohort gates.
- Preserve publisher receipt/binding evidence for both structural passes and explicit
  structural failures, with separate structure/decision outputs.
- Install the publisher action runtime from a fully resolved hash-locked Linux/Python 3.11
  dependency set instead of dynamically resolving an unhashed tree.
- Publish a complete attested owned demo and self-serve publisher workflow; owned evidence
  remains excluded from external adoption.
- Add the original, now-superseded $49 fresh public static validation request contract and non-orderable quote
  preview, exact nested schemas, duplicate-key rejection, separate order/payment states, and
  Stripe exact-body webhook authentication.
- Add GitHub-only exact-commit/subdirectory freezing with Git blob verification, hostile path
  and archive rejection, bounded repository/artifact intake, and content-addressed manifests.
- Add a pinned Docker static worker with no network or writable host mount, read-only filesystems,
  non-root execution, capability/resource limits, and bounded stdout-only receipt delivery.
- Add a constrained exact-byte Stage B signing gate, environment-bound SQLite commerce ledger,
  out-of-order/duplicate provider-event reconciliation, complete direct-cost accounting, and
  a fully delivered fake-provider sandbox proof that is permanently excluded from revenue.
- Add a sandbox-only authenticated commerce API with HMAC-digest API credentials, minimal
  tenant isolation, tenant-scoped idempotency, expiring/rotatable/revocable order capabilities,
  exact signed-result retrieval, bounded concurrency/body/rate/storage controls, generic
  object errors, and credential-free security-state audit events.
- Add retry-safe automatic publication of the exact signed envelope from the sandbox
  fulfillment coordinator and secret-environment CLI commands for local tenant provisioning
  and loopback service operation. Live stores and real settlement remain fail-closed.
- Add an account-bound Stripe Checkout adapter pinned to SDK `15.3.0` and API
  `2026-06-24.dahlia`, with hosted-session idempotency, official exact-body webhook
  verification, crash-recoverable event deduplication, server-retrieved payment-chain
  reconciliation, and strict refund/dispute/availability handling. A real unpaid test-mode
  Session was created and expired; live HTTP intake remains disabled.
- Connect Stripe test mode to authenticated tenant quote/order creation and a dedicated
  exact-body webhook route, with immutable-order-derived Checkout idempotency, separate webhook
  rate-limit capacity, retry-safe non-2xx responses, and a real HTTP-path Checkout probe that
  was expired unpaid. The loopback server still refuses live stores.
- Add offline-root paid-receipt lifecycle draft, publication, evaluation, and export commands
  with exact delivered-receipt/signer coverage, root/sequence binding, historical state, and
  irreversible supersession/revocation/key-compromise controls.
- Preserve the historical catalog dependency lock byte-for-byte and record Stripe's additive
  resolved dependencies separately in `requirements-commerce.lock`.
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
