# Managed Stage B deployment boundary

This directory is preparation, not a deployment claim. The checked-in commerce listener remains
loopback-only and fake-provider-only. Do not expose it directly or set
`VOUCHSPEC_STRIPE_LIVE_CHECKOUT_ENABLED=true` from this repository.

The managed service must preserve these boundaries before the reviewed Stripe adapter is wired
to order creation:

1. Terminate HTTPS at a managed edge and forward only to `127.0.0.1`. Enforce source-aware and
   global request limits, body limits, timeouts, and connection limits at that edge. The
   application must continue ignoring untrusted forwarded-client headers.
2. Preserve Stripe webhook request bytes exactly. Route only the dedicated webhook path to the
   adapter, pass the single `Stripe-Signature` header unchanged, return non-2xx for retryable or
   already-processing reconciliation, and never use browser redirects to authorize work.
3. Inject API key, mode-specific webhook secret, authentication pepper, delivery secret, and
   signing-key reference from a secret manager. Do not place secret values in manifests, image
   layers, command arguments, source, logs, or the commerce database.
4. Configure and persist one expected Stripe account ID per environment. Test and live accounts
   use different databases, webhook endpoints/secrets, and service configuration. The adapter
   re-retrieves and verifies the enabled account at startup.
5. Restrict the SQLite database and backups to the service identity. Verify restore, integrity,
   retention, and redacted audit aggregation before taking orders. Never clone test state into
   live or reuse tenant/token hashing secrets between environments.
6. Run networked Git intake in a disposable volume with a kernel-enforced quota. Keep the
   existing exact-commit, logical-size, timeout, cleanup, and archive controls as defense in
   depth. The inspection worker remains no-egress with no writable host mount.
7. Provision the issuer key only in a separate no-network signing role with an immutable worker
   image allowlist. Keep the lifecycle recovery-root private key offline; the online role sees
   only unsigned drafts, public JWKs, and exact signed envelopes.
8. Publish the latest root-signed paid lifecycle envelope with every result and monitor feed
   expiry, sequence, signer status, disputes/refunds, backup health, worker failures, and webhook
   retry backlog without recording credentials or customer secrets.

Required non-secret configuration names are documented in [`.env.example`](../.env.example).
Leave live activation false while provisioning. The next verification is a complete
noncommercial test-card flow from authenticated order through signed delivery, paid lifecycle,
refund/dispute checks, and Balance Transaction availability. Only after that test and the
controls above pass may live Checkout receive a separate explicit activation acknowledgement.
