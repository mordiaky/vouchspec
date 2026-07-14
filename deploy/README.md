# Managed Stage B deployment boundary

The managed **testnet** service is deployed at `https://vouchspec-sandbox.plyrium.com`. It uses
the Plyrium web edge for the public tenant/quote/order/x402/result/receipt/status API and a private
leased GitHub Actions fulfillment worker. The Python loopback and Stripe-test commands in this
repository remain local regression harnesses; they are not the production architecture or
VouchSpec launch rail.

## Deployed testnet invariants

1. The edge terminates managed HTTPS, rejects cross-site mutation, enforces strict body/framing
   rules and public/tenant rate limits, and returns redacted errors.
2. Tenant API keys and delivery capabilities are shown once and stored only as keyed digests.
   Quotes, orders, x402 payments, results, rotation, and revocation are tenant bound.
3. The public payment route accepts only x402 v2 `exact`, Base Sepolia, 1.00 test USDC, and the
   configured receiver. Testnet activity is always excluded from commercial counters.
4. Settlement uses a durable processing lease and a recorded recovery checkpoint. Replays,
   conflicting payloads, concurrent settlement, and ambiguous recovery fail closed.
5. The networked fetch role receives only public immutable GitHub coordinates. The inspection
   container has no egress and no writable host mount.
6. The separate signer container receives encrypted signing material and bounded evidence but no
   buyer credential, delivery capability, payment/wallet key, or worker API token. It re-verifies
   the exact freeze/worker/source/image bindings before signing.
7. Authenticated result bytes are published verbatim under a content-addressed public receipt
   URL. Receipt bytes are immutable; current invalidation state is a separate no-store URL.
8. GitHub workflow failure alerts remain enabled. Empty-queue polling claims first and skips
   checkout, dependency installation, Docker build, and secret materialization when no job exists.

## Mainnet activation boundary

Mainnet is a separate environment, not a flag applied to testnet state:

1. Use separate live receiver/wallet policy, facilitator/network allowlist, application secrets,
   tenant credentials, database, signing policy, and monitoring. Never copy test objects into live.
2. Keep payment/wallet credentials out of the worker and signer. Only the public payment boundary
   talks to the x402 facilitator; fulfillment starts from a durable paid-order lease.
3. Preserve the settlement recovery checkpoint and prove retry after facilitator timeout/unknown
   outcomes without double settlement or double fulfillment.
4. Implement the disclosed automatic onchain remedy/refund operation, record its transaction and
   cost, and remove returned/reversed/disputed amounts from settled gross.
5. Run networked Git intake in disposable storage with a kernel-enforced quota while preserving
   exact-commit, logical-size, timeout, extraction, and cleanup controls.
6. Reconcile chain/facilitator, worker, storage, delivery, and remedy costs for every order and
   refuse fulfillment that cannot retain positive contribution at the signed quote.
7. Publish the issuer key and content-addressed receipt/invalidation contract before accepting
   value, then monitor receipt status, settlement recovery, worker failures, delivery, and
   accounting without recording credentials.

The launch strategy remains agent-to-agent only. Mainnet activation must not add a card form,
hosted checkout, call, meeting, manual review, or manual delivery.
