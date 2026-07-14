# VouchSpec payment and reconciliation flow

Status: provider-neutral fulfillment plus an account-bound Stripe adapter are implemented and
test-mode Checkout creation has been exercised against the authorized Stripe sandbox. The
authenticated HTTP boundary still uses the fake nonsettling rail; live/public orders remain
disabled.

## Provider decision

Stripe Checkout is the primary launch rail. It has no setup or monthly fee, supports hosted
checkout, webhooks, refunds and balance-transaction reconciliation, and is familiar to
developer buyers. x402 is the planned secondary machine-native rail after the conventional
path is proven. Paddle is the fallback if merchant-of-record tax handling later outweighs
its higher 5% + $0.50 fee.

Current official sources (accessed 2026-07-14):

- [Stripe pricing](https://stripe.com/pricing)
- [Stripe Checkout lifecycle](https://docs.stripe.com/payments/checkout/how-checkout-works)
- [Stripe account and sandbox behavior](https://docs.stripe.com/get-started/account)
- [Stripe webhook requirements](https://docs.stripe.com/webhooks)
- [Stripe refund API](https://docs.stripe.com/api/refunds/create)
- [Stripe balance transactions](https://docs.stripe.com/api/balance_transactions)
- [Stripe currency minimums](https://docs.stripe.com/currencies)
- [Coinbase x402 flow](https://docs.cdp.coinbase.com/x402/core-concepts/how-it-works)
- [Coinbase x402 facilitator](https://docs.cdp.coinbase.com/x402/core-concepts/facilitator)
- [Coinbase x402 refund limitation](https://docs.cdp.coinbase.com/x402/support/faq)
- [Paddle pricing](https://www.paddle.com/pricing)
- [Paddle sandbox](https://developer.paddle.com/sdks/sandbox/)

## Machine contract

1. A caller prepares the strict JSON request documented by
   `fresh-validation-request.schema.json`.
2. `vouchspec quote-fresh-validation REQUEST.json` validates the allowlisted public host,
   full immutable commit, explicit skill path, profile, maximum price and delivery ID.
3. The public preview returns USD 49.00, exact deliverable, limits, expiry, refund conditions,
   payment options and remaining live gates. It is explicitly `orderable: false` today.
4. The local HTTP sandbox uses only the deterministic fake provider. The separate reviewed
   adapter can persist a Stripe test-mode quote/order. Both remain nonsettling and
   `counts_for_goal: false`.
5. The adapter persists the immutable quote and order before creating a Stripe Checkout
   Session. The stored amount—not a client-returned amount—is authoritative.
6. The Checkout Session and PaymentIntent carry only opaque `order_id`, `quote_id`, and the
   configured Stripe account ID. Creation uses a deterministic SDK idempotency key.
7. The service fulfills only after an authenticated webhook and server-side retrieval of the
   Checkout Session and PaymentIntent confirm live mode, amount, currency, metadata and paid
   status. Browser redirects never authorize work.
8. Duplicate or out-of-order provider events are persisted, deduplicated by immutable event
   ID, and reconciled as predecessor states arrive.
9. The result endpoint returns the signed receipt and verification material. The service
   records direct compute, provider costs, processing fee, delivery and refund status.
10. A daily reconciliation pass reads the charge Balance Transaction. Revenue counts as
   settled only when provider funds are available and remain non-refunded/non-disputed.

## Independent state dimensions

Order state and payment state are separate. A captured card can authorize a bounded job,
while commercial revenue remains unsettled until provider availability.

Order: `checkout_pending -> payment_pending -> queued -> running -> delivered`, with explicit
`payment_failed`, `fulfillment_failed`, and `cancelled` terminals.

Payment: `pending -> captured -> available`, with explicit `failed`, `refund_pending ->
refunded`, and `disputed` terminals.

The implementation rejects every transition not explicitly listed in
`capabilityproof.commerce`. The durable SQLite implementation is in
`capabilityproof.commerce_store`; it refuses to open one database under a different
`sandbox`/`live` environment.

The sandbox HTTP boundary in `capabilityproof.commerce_api` uses
`capabilityproof.commerce_access` to authenticate keyed-digest API credentials, scope
idempotency and every quote/order to one tenant, require an expiring order capability for
status/result reads, and record rotation/revocation/result-publication audit events without
plaintext credentials. It still connects only to the fake nonsettling provider.

## Stripe adapter and webhook security

`StripePaymentAdapter` pins `stripe==15.3.0` and API version `2026-06-24.dahlia`, verifies the
credential against an expected enabled account ID, creates exact hosted Checkout Sessions, and
never persists the API key, webhook secret, or Checkout URL. Official SDK verification consumes
the exact raw webhook bytes. Signed events are allowlisted, content-bound to immutable event IDs,
deduplicated, and recovered through a bounded processing lease after a crash. Financial state is
derived only after server-side retrieval and cross-binding of the Checkout Session,
PaymentIntent, Charge, and Balance Transaction. Partial refunds, future-dated availability,
account/environment mismatches, and ambiguous objects fail closed.

On 2026-07-14 the authorized test credential passed account binding and created a USD $49.00
`livemode=false` Checkout Session. Reconciliation found no PaymentIntent before payment; the
session was then expired unpaid. The live credential was checked read-only and belongs to a
separate enabled account whose configured business URL is `www.plyrium.com`. No charge or
commercial metric resulted. No Stripe listener or public webhook route is exposed yet.

## Paid receipt lifecycle

Delivered Stage B receipts can be exactly covered by an unsigned online draft, transferred to
the existing offline `sign-lifecycle` root-signing command, and atomically imported with
`publish-paid-lifecycle`. Publication binds the recovery-root key, exact envelope, contiguous
sequence, delivered receipt/order IDs, and exact issuer-key set. Rollback, equal-sequence
equivocation, root replacement, signer removal, restoration of retired/compromised keys, and
reversal of terminal receipt states are rejected. `export-paid-lifecycle` returns the exact
latest signed envelope; the online database never receives root private material.

## Remaining live gates

- Managed-HTTPS deployment of the implemented authenticated quote/order/result boundary,
  including trusted-edge source limits, secret-manager provisioning, restricted database
  permissions, and automated real-buyer credential issuance/recovery.
- Connect the reviewed Stripe adapter to authenticated quote/order creation and an exact-body
  Stripe webhook route, provision a mode-specific webhook endpoint/secret, and complete one
  noncommercial test-card payment through Balance Transaction reconciliation.
- Operational no-network signing role with an owner-controlled production issuer key and
  allowlisted production image.
- Managed ephemeral fetch storage with a kernel-enforced quota.
- Only after those controls are deployed, enable live Checkout explicitly and process a genuine
  purchase. Test, owner, related-party, pending, reversed, refunded, and disputed activity must
  remain excluded from commercial counters.

The immutable fetcher, no-egress worker, constrained signing gate, durable event/cost store,
authenticated sandbox API, and sandbox end-to-end fulfillment are complete. Their limits and proof are documented in
[Stage B operations](stage-b-operations.md).
