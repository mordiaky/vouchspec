# Stage B public-repository validation

Status: fulfillment and the authenticated order/result boundary are implemented and proven
end to end in a deliberately nonsettling loopback sandbox. No externally deployed order
endpoint, live payment rail, or commercial metric is enabled.

## Accepted request boundary

Stage B accepts only the strict `fresh_public_static_validation` JSON contract:

- host exactly `github.com`;
- repository owner/name in the bounded ASCII grammar;
- full lowercase 40-character commit;
- explicit portable Agent Skill subdirectory;
- the fixed public-static profile, maximum price, and opaque delivery ID.

It accepts no upload bytes, private repository, credential, branch, tag, mutable URL,
customer-confidential content, artifact command, or custom shell instruction.

## Fulfillment chain

1. `freeze-public-validation` initializes a credential-free Git repository with system and
   global configuration disabled, permits HTTPS only, fetches the exact commit with
   `--filter=tree:0`, and verifies `FETCH_HEAD`.
2. Git tree records are parsed before extraction. Only regular `100644` and `100755` blobs
   are accepted. Symlinks, submodules, special entries, traversal, control characters,
   non-NFC paths, reserved device names, and case collisions fail closed.
3. `git archive` output is size-bounded and manually extracted. Every file is compared to
   its Git blob SHA-1 and then SHA-256 hashed into a content-addressed freeze manifest.
4. `run-frozen-validation` rehashes the freeze and runs a pinned local Docker image with no
   network, read-only root and input filesystems, no capabilities, no new privileges, no IPC,
   non-root UID/GID 65532, 64 processes, 256 MiB memory, one CPU, bounded file descriptors,
   a 16 MiB no-exec temporary filesystem, and a 75-second host timeout.
5. The container has no writable host mount. Its only result is exact receipt bytes on a
   one-million-byte bounded stdout pipe. Artifact content is never executed.
6. `sign-frozen-validation` re-verifies the freeze, receipt, execution report, immutable
   allowlisted worker image, timing, source coordinates, content digest, evidence label, and
   no-execution claim before signing the exact receipt bytes in DSSE v1.0.2/Ed25519.
7. The SQLite commerce store records separate order/payment states, unique provider events,
   immutable quotes, idempotency keys, all ten direct-cost categories, fees, refunds,
   receipt/envelope identifiers, delivery, and contribution impact.
8. The access extension binds each API credential, quote, order, and result to one opaque
   tenant. It stores keyed token digests only. Reading an order or signed result requires both
   the tenant API key and its order-specific delivery capability.
9. Delivery capabilities are environment-specific, deterministic for retry safety, expire
   after 30 days, and can be rotated or revoked immediately. Result bytes are published only
   when their SHA-256 equals the envelope digest already committed to the delivered order.
10. The separate Stripe adapter verifies its SDK/API version and expected enabled account,
    creates an exact hosted Checkout Session, and reconciles only server-retrieved Session,
    PaymentIntent, Charge, and Balance Transaction state. It is not connected to this sandbox
    HTTP listener.
11. Delivered paid receipts enter a complete lifecycle draft that is signed by the offline
    recovery root. Publication is atomic, sequence-contiguous, exact-coverage, and terminal
    revocation/key-compromise states cannot be restored.

## Authenticated sandbox API

The sandbox server binds only to `127.0.0.1` and refuses live stores. Its supported routes are:

- `GET /health` — non-sensitive sandbox health only;
- `POST /v1/commerce/quotes` — bearer API key plus `Idempotency-Key`;
- `POST /v1/commerce/orders` — same tenant and a tenant-scoped idempotency key;
- `GET /v1/commerce/orders/{order_id}` — API key plus delivery capability;
- `GET /v1/commerce/orders/{order_id}/result` — the exact digest-bound DSSE envelope;
- `POST .../delivery-token/rotate` and `POST .../delivery-token/revoke`.

Requests use strict duplicate-key-rejecting JSON, exact body framing, a 16 KiB body ceiling,
connection deadlines, bounded concurrency, no query/path encoding, generic authorization
errors, no CORS allowance, and no-store security headers. Single-process global, direct-peer,
and tenant sliding-window limits apply. Each tenant also has a hard ceiling of 100 bound
quotes and 50 bound orders, with idempotent retries preserved. Security-state changes are
recorded without IP addresses, API keys, or delivery tokens.

Provisioning reads two distinct 32-byte hex secrets from environment-variable names, records
only their SHA-256 key identifiers, and prints a newly generated sandbox API key once:

```powershell
$env:VOUCHSPEC_AUTH_PEPPER_HEX = '<64 hex characters>'
$env:VOUCHSPEC_DELIVERY_SECRET_HEX = '<different 64 hex characters>'
vouchspec provision-commerce-tenant --database C:\vouchspec\sandbox-commerce.db
vouchspec serve-commerce-sandbox --database C:\vouchspec\sandbox-commerce.db --port 8789
```

Use an operating-system or platform secret manager for actual values. Persist both values
unchanged for the lifetime of this sandbox database; a mismatch fails at startup. The API key
and delivery capability are credentials and must never enter URLs, logs, source control, or
artifact input.

## Hard ceilings

- Git repository metadata after each networked phase: 64,000,000 bytes.
- Git command metadata output: 2,000,000 bytes.
- Artifact: 1,000 files, 2,000 entries, 256 directories, depth 32.
- Artifact bytes: 25,000,000 total; 2,000,000 per file; 1,000,000 for `SKILL.md`.
- Worker: 75 seconds, 256 MiB RAM, 1 CPU, 64 processes, 128 open files.
- Writable worker storage: 16 MiB `/tmp` only; no writable host mount.
- Worker receipt output: 1,000,000 bytes over bounded stdout.
- Commerce request body: 16,384 bytes; signed-result body: 1,000,000 bytes.
- Commerce API: 32 active connections, 60-second windows, 240 global / 60 direct-peer /
  30 tenant requests, 100 quotes and 50 orders per tenant.
- Delivery capability lifetime: 30 days unless rotated or revoked sooner.

These are evidence about the enforced implementation, not a universal safety guarantee.
Networked retrieval still trusts GitHub and HTTPS/DNS infrastructure; the worker performs
static parsing, not runtime behavior observation.

## Sandbox proof

The checked-in [sandbox proof](../fulfillment/stage-b-sandbox-proof.json) used the owned demo
at exact commit `344558d51ecae7929c50b7cff94e120bfca53807`. It completed quote, fake capture,
out-of-order-capable reconciliation, freeze, no-egress inspection, constrained signing,
complete cost recording, and delivery. It is marked `counts_for_goal: false` and
`sandbox_nonsettling`; it proves mechanics only.

## Operator commands

```powershell
vouchspec freeze-public-validation request.json --output-root C:\vouchspec\frozen
vouchspec run-frozen-validation C:\vouchspec\frozen\REQUEST_DIGEST `
  --image sha256:FULL_LOCAL_IMAGE_ID --output C:\vouchspec\worker-result
vouchspec sign-frozen-validation C:\vouchspec\frozen\REQUEST_DIGEST `
  --worker-output C:\vouchspec\worker-result `
  --allowed-worker-image sha256:FULL_LOCAL_IMAGE_ID `
  --private-key C:\secure\issuer.private.pem `
  --passphrase-file C:\secure\issuer.passphrase `
  --output C:\vouchspec\delivery\receipt.dsse.json
```

Signing keys and passphrases must remain outside the repository and worker. The signing
command is intended for a separate no-network role.

Paid receipt lifecycle publication keeps the root-signing step separate:

```powershell
vouchspec prepare-paid-lifecycle --database C:\vouchspec\commerce.db --environment sandbox `
  --issuer-records C:\secure\issuer-records.json `
  --generated-at 2026-07-14T12:00:00Z --expires-at 2026-07-21T12:00:00Z `
  --output C:\transfer\paid-lifecycle-draft.json
vouchspec sign-lifecycle C:\transfer\paid-lifecycle-draft.json `
  --private-key C:\offline\root.private.pem --output C:\transfer\paid-lifecycle.dsse.json
vouchspec publish-paid-lifecycle --database C:\vouchspec\commerce.db --environment sandbox `
  --envelope C:\transfer\paid-lifecycle.dsse.json --root-key C:\vouchspec\root.public.jwk.json
```

Run `sign-lifecycle` only in the offline root role. The online prepare/publish roles receive
public issuer/root JWKs and the signed envelope, never the root private key.

## Remaining live gates

- Deploy the implemented authenticated loopback service behind managed HTTPS, source-aware
  ingress limits, request-size limits, and redacted audit aggregation. Provision the two
  application secrets through a secret manager and restrict the database file to the service
  identity. The built-in direct-peer limiter must not trust forwarded client headers.
- Define automated credential issuance/recovery for a real buyer and expose the latest exact
  root-signed paid lifecycle envelope alongside each delivered result.
- Run the networked Git phase in an ephemeral deployment volume with a kernel-enforced disk
  quota; the local proof enforces its 64 MB ceiling after each Git phase but not mid-write.
- Connect the reviewed account-bound Stripe adapter to the authenticated HTTP order route and
  an exact-body Stripe webhook route behind managed ingress. Provision a mode-specific webhook
  endpoint and complete one unpaid-to-available test-card reconciliation.
- Provision an operational Stage B issuer key and allowlisted production image through the
  separate signing role.
- Preserve the already verified owner-controlled account identity/payout boundary; provision
  the production webhook endpoint/secret and complete any provider tax/terms steps only when
  the managed service is otherwise ready.
- Run a genuine unrelated-party paid request, then reconcile its balance transaction to
  `available`; test, pending, reversed, refunded, disputed, owner, and related-party activity
  remains excluded.

The detailed [Stage B security review](stage-b-security-review.md) records fixed findings and
the reason these remaining gates still block public order intake.
