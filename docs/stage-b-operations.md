# Stage B public-repository validation

Status: implemented and proven end to end in a deliberately nonsettling sandbox. No public
order endpoint, live payment rail, or commercial metric is enabled.

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

## Hard ceilings

- Git repository metadata after each networked phase: 64,000,000 bytes.
- Git command metadata output: 2,000,000 bytes.
- Artifact: 1,000 files, 2,000 entries, 256 directories, depth 32.
- Artifact bytes: 25,000,000 total; 2,000,000 per file; 1,000,000 for `SKILL.md`.
- Worker: 75 seconds, 256 MiB RAM, 1 CPU, 64 processes, 128 open files.
- Writable worker storage: 16 MiB `/tmp` only; no writable host mount.
- Worker receipt output: 1,000,000 bytes over bounded stdout.

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

## Remaining live gates

- Deploy an authenticated, rate-limited HTTPS quote/order/result service with hashed opaque
  delivery tokens and object-level access checks. No general tenant system is required for
  the first public-only product.
- Run the networked Git phase in an ephemeral deployment volume with a kernel-enforced disk
  quota; the local proof enforces its 64 MB ceiling after each Git phase but not mid-write.
- Add and test the real Stripe Checkout/session retrieval and authenticated webhook adapter;
  the fake provider is sandbox-only and rejected by live stores.
- Provision an operational Stage B issuer key and allowlisted production image through the
  separate signing role.
- Complete provider account identity, payout, webhook-secret, tax/terms, and live-mode setup
  using owner-controlled credentials only after all non-credential work is ready.
- Run a genuine unrelated-party paid request, then reconcile its balance transaction to
  `available`; test, pending, reversed, refunded, disputed, owner, and related-party activity
  remains excluded.

The detailed [Stage B security review](stage-b-security-review.md) records fixed findings and
the reason these remaining gates still block public order intake.
