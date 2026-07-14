# Stage B API and service-boundary security review

Reviewed 2026-07-14 against the local CLI, GitHub intake, Docker worker, signing gate,
commerce store, provider-event path, and planned public order/result boundary.

## Fixed findings

### High — worker could write without a host disk quota

- **Affected boundary:** `run-frozen-validation` Docker command.
- **Exploit scenario:** a parser/dependency compromise could fill the host directory through
  the receipt output bind even though CPU, memory, and temporary storage were bounded.
- **Evidence:** the initial command mounted `/output` read-write.
- **Fix:** removed every writable host mount. The container now emits only a receipt through a
  one-million-byte host-bounded stdout pipe; root/input are read-only and `/tmp` is a 16 MiB
  no-exec tmpfs.

### High — Stage B provenance change would break historical signed-schema identity

- **Affected boundary:** constrained signer and public receipt verification.
- **Exploit scenario:** broadening the existing schema changed its SHA-256, making all 25
  historical signed receipts disagree with the checked-in schema they identify.
- **Evidence:** the full suite detected a schema-hash mismatch.
- **Fix:** preserved the immutable receipt schema and existing exact-Git-blob provenance
  method. The stronger remote freeze procedure remains separately bound in the freeze manifest
  and worker execution report. No historical receipt was rewritten.

### Medium — checkout/event replay and reordering could duplicate financial effects

- **Affected boundary:** commerce provider events.
- **Exploit scenario:** duplicate IDs, ID reuse with changed content, or an `available` event
  arriving before `captured` could double-count or incorrectly advance an order.
- **Evidence:** provider delivery is explicitly unordered and retryable.
- **Fix:** environment-bound SQLite store, immutable payload digest per unique event ID,
  pending-event reconciliation, explicit transition tables, idempotent financial entries,
  and conflict rejection. Fake events are accepted only by sandbox stores.

### Medium — arbitrary immutable worker image could obtain a receipt signature

- **Affected boundary:** `sign-frozen-validation`.
- **Exploit scenario:** an attacker substitutes a different image digest and fabricates a
  structurally valid receipt/execution report.
- **Fix:** signing now requires an explicit non-empty allowlist of immutable image references
  and re-verifies isolation fields, source/freeze/receipt digests, timing, provenance,
  no-execution claim, and exact signed payload bytes.

### High — unauthenticated order/result boundary would expose cross-customer objects

- **Affected boundary:** Stage B quote, order, status, and signed-result HTTP routes.
- **Exploit scenario:** anonymous queue exhaustion, credential replay, quote/order enumeration,
  cross-tenant result disclosure, token leakage through URLs/logs, or indefinite reuse of a
  stolen delivery token.
- **Fix:** added a loopback-only sandbox server that refuses live stores. API credentials and
  delivery capabilities are stored only as HMAC-SHA-256 digests under distinct 32-byte
  secrets whose non-secret key identifiers are environment-bound in SQLite. Quotes and orders
  are bound to one opaque tenant; order/result access requires both credentials. Delivery
  capabilities are environment-specific, retry-safe, expire after 30 days, and support
  immediate rotation/revocation with old-token rejection.
- **Additional controls:** exact duplicate-key-rejecting JSON and framing, 16 KiB body limit,
  bounded connections/deadlines, global/direct-peer/tenant rate limits, per-tenant hard storage
  ceilings, no CORS, no-store headers, generic object errors, sanitized order output, exact
  envelope-digest result publication, and credential-free security-state audit events. Slow
  bodies, duplicate auth headers, cross-tenant access, expiry, rotation, revocation, result
  rebinding, quota exhaustion, and live-store startup are covered by tests.

## Open launch gates

### High — authenticated API is not externally deployed or operationally provisioned

- **Current exposure:** the new server is sandbox-only, loopback-only, fake-provider-only, and
  absent from the public Stage A distribution.
- **Exploit if exposed directly:** plaintext transport, proxy/client-IP confusion, unaggregated
  auth abuse, weak filesystem secret permissions, or multi-instance limit bypass.
- **Required live fix:** managed TLS and ingress request limits, source-aware rate limiting at
  the trusted edge, redacted audit aggregation, secret-manager injection, service-identity-only
  database permissions, backup/restore verification, and automated buyer credential issuance/
  recovery. The application intentionally ignores forwarded client-IP headers; the edge must
  enforce source limits before forwarding to loopback.

### High — no authenticated real Stripe adapter or server-side object retrieval

- **Current exposure:** none; live stores refuse quote/order creation and only fake sandbox
  events are connected.
- **Exploit if exposed prematurely:** forged redirect/webhook, amount or environment confusion,
  test-mode payments counted as live, or fulfillment before provider confirmation.
- **Required fix:** official Stripe API client, fixed API version, secret isolation, exact raw
  webhook verification, event allowlist, server-side Checkout Session/PaymentIntent retrieval,
  stored amount/currency/metadata comparison, and balance-transaction availability
  reconciliation. Browser redirects never authorize work.

### High — production signing role/key is not provisioned

- **Current exposure:** sandbox used a deterministic test key and is marked noncommercial.
- **Required fix:** encrypted owner-controlled issuer key outside source/logs, separate
  no-network signing role, immutable worker-image allowlist, rotation/revocation runbook, and
  public trust publication before any live receipt is returned.

### High — paid Stage B receipt lifecycle invalidation is not published

- **Current control:** order delivery capabilities can expire, rotate, or revoke immediately;
  Stage A receipts already use the root-signed lifecycle feed.
- **Residual scenario:** revoking result access does not tell a buyer that a previously
  downloaded paid receipt was superseded or invalidated because of evaluator defect or key
  compromise.
- **Required fix:** bind paid Stage B receipt IDs to a root-authorized monotonic lifecycle
  publication, reuse the conservative Stage A status vocabulary, and test rollback,
  equivocation, expiry, key-compromise, and evaluator-defect invalidation before live delivery.

### Medium — networked Git scratch disk lacks a kernel quota in local proof

- **Current control:** GitHub-only HTTPS URL, `tree:0` partial fetch, 90-second process timeout,
  64 MB logical repository check after each networked/materialization phase, and complete
  cleanup. Artifact/archive bytes have independent hard limits.
- **Residual scenario:** an unusually large or fast Git pack could transiently exceed 64 MB
  before the post-command check runs.
- **Required live fix:** run the networked fetch phase in an ephemeral scratch volume with a
  deployment-enforced disk quota; preserve the existing post-phase checks as defense in depth.

## Secrets and privacy conclusion

No customer secret, repository credential, signing key, payment key, API key, delivery token,
or webhook secret is passed to the worker. Plaintext API keys and delivery capabilities are
not stored in SQLite or application audit events. The accepted artifact is public and the
store holds only bounded public source coordinates, keyed credential digests, opaque tenant
identifiers, immutable signed-result bytes, and non-secret audit metadata. Private
repositories, uploads, credentials, and customer-confidential content remain rejected.
