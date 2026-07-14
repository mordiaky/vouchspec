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

## Open launch gates

### High — no authenticated public quote/order/result API

- **Current exposure:** none; Stage B commands are local and public Stage A rejects writes.
- **Exploit if exposed prematurely:** order enumeration, result disclosure, object-level access
  bypass, anonymous queue exhaustion, or cross-customer delivery.
- **Required fix:** managed TLS, strict request schemas, per-source and global rate limits,
  hashed high-entropy one-time delivery tokens, constant-time token checks, object-level order
  authorization, generic errors, bounded request bodies, audit events, and expiration. The
  public-only first product does not need a general tenant/account system.

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

### Medium — networked Git scratch disk lacks a kernel quota in local proof

- **Current control:** GitHub-only HTTPS URL, `tree:0` partial fetch, 90-second process timeout,
  64 MB logical repository check after each networked/materialization phase, and complete
  cleanup. Artifact/archive bytes have independent hard limits.
- **Residual scenario:** an unusually large or fast Git pack could transiently exceed 64 MB
  before the post-command check runs.
- **Required live fix:** run the networked fetch phase in an ephemeral scratch volume with a
  deployment-enforced disk quota; preserve the existing post-phase checks as defense in depth.

## Secrets and privacy conclusion

No customer secret, repository credential, signing key, payment key, or webhook secret is
passed to the worker. The accepted artifact is public and the store holds only bounded public
source coordinates plus opaque buyer/delivery identifiers. Private repositories, uploads,
credentials, and customer-confidential content remain rejected.
