# Stage B public-repository validation

Status: a managed public testnet service now completes authenticated registration, quote, order,
x402 settlement, kernel-quota immutable retrieval, no-egress inspection, separate no-egress
signing, signed delivery, content-addressed receipt publication, and live invalidation status
without a human step. Durable payer-derived onchain remedies are implemented but their separate
wallet executor is disabled until live policy and funding are provisioned. The stable base URL is
`https://vouchspec-sandbox.plyrium.com`. Base mainnet and commercial accounting remain
fail-closed.

## Accepted request boundary

Stage B accepts only the strict `fresh_public_static_validation` JSON contract:

- host exactly `github.com`;
- bounded repository owner/name grammar;
- full lowercase 40-character commit;
- explicit portable Agent Skill subdirectory;
- fixed `vouchspec-public-static-v1` profile;
- maximum price and opaque delivery ID.

It accepts coordinates, not customer-supplied ZIP bytes. It accepts no private repository,
credential, branch, tag, mutable URL, confidential content, artifact command, custom shell
instruction, or executable upload.

## Hosted architecture and trust boundaries

1. A public agent registers an opaque tenant. Only a keyed API-key digest is stored.
2. Quotes, idempotency keys, orders, payments, delivery capabilities, and results are tenant
   bound. Cross-tenant access returns a generic authorization failure.
3. The order exposes one protected x402 purchase resource. The public sandbox accepts only x402
   v2 `exact` payment of 1.00 test USDC on Base Sepolia (`eip155:84532`). There is no human or
   Stripe checkout route.
4. Payment verification and settlement is replay-resistant, lease-protected, and checkpointed
   for recovery before the external settlement call. Testnet orders are always
   `counts_for_goal: false`.
5. A private worker endpoint leases at most one paid job. The bearer worker credential is
   separate from buyer credentials, wallet material, delivery tokens, and signing material.
6. The networked fetch phase runs in a separate immutable, non-root container with a read-only
   root, no host mount, and a 64 MiB kernel-enforced `/scratch` tmpfs. It disables ambient Git
   configuration and credentials, permits HTTPS only, fetches the exact commit, materializes the
   requested tree inside the quota, verifies `FETCH_HEAD`, and removes its remote before export.
7. Git tree records are parsed before extraction. Only regular `100644` and `100755` blobs are
   accepted. Symlinks, submodules, special entries, traversal, control characters, non-NFC paths,
   reserved device names, and case collisions fail closed.
8. `git archive` output is bounded and manually extracted. Every file is compared to its Git
   blob SHA-1 and SHA-256 hashed into a content-addressed freeze manifest.
9. Static inspection runs in a pinned local Docker image with no network, read-only root/input
   filesystems, no capabilities, no new privileges, no IPC, non-root UID/GID 65532, bounded
   processes/memory/CPU/descriptors, a no-exec temporary filesystem, and a host timeout. Artifact
   content is parsed, never imported or executed.
10. The inspection container has no writable host mount. Its only result is bounded receipt and
    execution evidence.
11. A **separate no-egress signer container** re-verifies the freeze, receipt, execution report,
    allowlisted worker image, timing, source coordinates, content digest, evidence labels, and
    no-execution claim before signing exact receipt bytes in DSSE v1.0.2/Ed25519. It invokes a
    dependency-minimal signer entry point and receives no buyer API key, wallet key, worker API
    token, or delivery capability.
12. The service accepts completion only when order/source bindings, envelope digest, receipt ID,
    issuer key ID, and public receipt/status paths pass exact validation.
13. The authenticated result is `no-store`. The identical envelope is also published under its
    SHA-256 digest with `public, max-age=31536000, immutable` and CORS `*`.
14. Invalidation is not implemented by mutating receipt bytes. A separate no-store status
    resource reports the current lifecycle state; relying agents check it before each new use.

## Public agent API

- `GET /api/vouchspec/v1/health` — non-sensitive environment and x402 health.
- `GET /api/vouchspec/v1/discovery` — canonical machine contract.
- `POST /api/vouchspec/v1/tenants` — current terms acceptance and one-time bearer credential.
- `POST /api/vouchspec/v1/quotes` — authenticated strict request plus `Idempotency-Key`.
- `POST /api/vouchspec/v1/orders` — authenticated quote conversion and delivery capability.
- `GET /api/vouchspec/v1/orders/{order_id}/purchase` — x402 challenge/settlement resource.
- `GET /api/vouchspec/v1/orders/{order_id}` — authenticated order state.
- `GET /api/vouchspec/v1/orders/{order_id}/result` — authenticated exact DSSE bytes.
- `POST .../delivery-token/rotate` and `POST .../delivery-token/revoke` — capability control.
- `GET /api/vouchspec/v1/keys/issuer` — public Stage B issuer JWK.
- `GET /api/vouchspec/v1/receipts/{sha256_hex}` — immutable public envelope bytes.
- `GET /api/vouchspec/v1/receipts/{sha256_hex}/status` — live no-store invalidation state.

Strict JSON rejects duplicate keys and noncanonical framing, enforces a 16 KiB request ceiling,
and applies bounded public/tenant registration and commerce limits. Credentials never belong in
URLs, logs, source control, artifact input, or public receipt content.

## Hard ceilings

- Git repository metadata after each networked phase: 64,000,000 bytes.
- Fetcher writable storage: 64 MiB kernel-enforced tmpfs; no writable host mount.
- Fetcher metadata stream: 68,000,000 bytes maximum and 20,000 archive entries.
- Git command metadata output: 2,000,000 bytes.
- Artifact: 1,000 files, 2,000 entries, 256 directories, depth 32.
- Artifact bytes: 25,000,000 total; 2,000,000 per file; 1,000,000 for `SKILL.md`.
- Worker: 75 seconds, 256 MiB RAM, 1 CPU, 64 processes, 128 open files.
- Writable worker storage: 16 MiB `/tmp` only; no writable host mount.
- Worker receipt output: 1,000,000 bytes over bounded stdout.
- Commerce request body: 16,384 bytes; signed-result body: 1,000,000 bytes.
- Delivery capability lifetime: 30 days unless rotated or revoked sooner.

These limits are evidence about this implementation, not a universal safety guarantee. Networked
retrieval still trusts GitHub plus HTTPS/DNS infrastructure, and static parsing does not observe
runtime behavior.

## Payment recovery and remedy worker

An orchestration-only API token leases stale x402 reconciliation and fixed remedy jobs. Wallet
credentials are never deployed to the web application or fulfillment worker. A separate disabled
GitHub workflow holds the CDP credential only inside the `vouchspec-mainnet-remedies` environment.
It first terminalizes at most one paid fulfillment that remained unclaimed for 30 minutes,
recovers unknown settlement outcomes, then claims at most one remedy, scans from the durable
pre-send block checkpoint, and submits at most one fixed USDC transfer using the remedy UUID as
Coinbase's idempotency key.

The application, not the wallet executor, decides the destination and amount. It accepts
completion only after an independent Base RPC check proves the dedicated remedy account called
canonical USDC `transfer(payer, 250000)`, emitted exactly one matching Transfer log, succeeded,
and has a confirmation. A unique settlement-transaction index prevents one onchain payment from
being credited twice. A 23-hour retry cutoff stops sends before Coinbase's 24-hour idempotency
retention expires. See [mainnet remedy operations](mainnet-remedy-operations.md).

## Hosted owner-excluded proof

On 2026-07-14, owner-controlled buyer software completed order
`ord_01b1e85f188649a6b68e2dd2` through the stable API:

- exact Base Sepolia payment transaction:
  `0xfe4b912ace571cd533d02e474de766d7dbe19d744d5cb35420cb71d7952aea11`;
- result digest:
  `sha256:f76d3c36a611bf304e6d87ff02331e0298282ed449a335b5704d54bedb0c0c53`;
- receipt ID: `cpr_2bb3259dd33d0cbadf7580dc`;
- issuer key ID: `PWGCY2HpACKhufnSBjbf2zwMzThqxyPTz_MAwCyJ0I0`;
- signature verification: pass;
- public bytes equal authenticated result bytes: pass;
- live lifecycle status: `CURRENT`;
- goal/revenue credit: none (`counts_for_goal: false`).

The public receipt is
`https://vouchspec-sandbox.plyrium.com/api/vouchspec/v1/receipts/f76d3c36a611bf304e6d87ff02331e0298282ed449a335b5704d54bedb0c0c53`;
append `/status` for the live state.

## Signer incident and recovery

The first four hosted owner diagnostics produced GitHub failure emails. Safe, allowlisted error
classification isolated `isolated_signer_runtime_import`: the deliberately minimal signer image
was importing the broad compatibility CLI, which imported optional modules absent from the
image. The signer now invokes `stage_b_signer_cli.py`, which imports only signing dependencies.
The exact image passed local no-egress/read-only probing and hosted workflow run `29359911240`
completed successfully at commit `13c65f3dc36a099c0d45aa36aa08b58b3d738371`.

Those emails were correct operational alerts, not customer activity or an attack. Alerts remain
enabled so a future paid-job failure is visible.

## Local operator commands

The local freeze/worker/signer commands remain useful for deterministic regression:

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

Signing keys and passphrases remain outside the repository and worker. The worker receives no
wallet credentials; payment verification/settlement and fulfillment are separate roles.

## Remaining mainnet gates

- Separate live receiving wallet, facilitator/network allowlist, secrets, state, issuer policy,
  and accounting from every testnet object.
- Create and attach the dedicated CDP remedy-account policy, fund only the bounded operating
  float, configure the protected workflow environment, and verify policy rejection probes before
  enabling the schedule.
- Preserve the existing payment recovery checkpoint and prove mainnet-compatible recovery for
  unknown facilitator outcomes without double settlement or fulfillment.
- Reconcile actual chain/facilitator, worker, storage, delivery, and remedy costs per order and
  require positive contribution.
- Complete a genuine unrelated-agent mainnet purchase and independently preserve attribution,
  settlement, cost, receipt, delivery, and exclusion evidence.

These gates block commercial mainnet accounting, not public testnet use. They do not require a
human checkout, a call, or broader artifact intake.
