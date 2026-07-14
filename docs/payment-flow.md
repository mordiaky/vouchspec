# VouchSpec payment and reconciliation flow

Status: implementation preparation; live checkout and orders remain disabled.

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
3. The preview returns USD 49.00, exact deliverable, limits, expiry, refund conditions,
   payment options and remaining live gates. It is explicitly `orderable: false` today.
4. Once live, the service persists the immutable quote before creating a Stripe Checkout
   Session. The stored amount—not a client-returned amount—is authoritative.
5. The Checkout Session carries only opaque `order_id`, `quote_id` and `request_digest`
   metadata. Creation uses idempotency key `checkout:{order_id}`.
6. The service fulfills only after an authenticated webhook and server-side retrieval of the
   Checkout Session and PaymentIntent confirm live mode, amount, currency, metadata and paid
   status. Browser redirects never authorize work.
7. Duplicate or out-of-order provider events are deduplicated by immutable `event.id`.
8. The result endpoint returns the signed receipt and verification material. The service
   records direct compute, provider costs, processing fee, delivery and refund status.
9. A daily reconciliation pass reads the charge Balance Transaction. Revenue counts as
   settled only when provider funds are available and remain non-refunded/non-disputed.

## Independent state dimensions

Order state and payment state are separate. A captured card can authorize a bounded job,
while commercial revenue remains unsettled until provider availability.

Order: `checkout_pending -> payment_pending -> queued -> running -> delivered`, with explicit
`payment_failed`, `fulfillment_failed`, and `cancelled` terminals.

Payment: `pending -> captured -> available`, with explicit `failed`, `refund_pending ->
refunded`, and `disputed` terminals.

The implementation rejects every transition not explicitly listed in
`capabilityproof.commerce`.

## Webhook security prepared locally

`verify_stripe_webhook_signature` authenticates the exact raw request bytes, accepts key
rotation through multiple `v1` signatures, compares in constant time, and rejects timestamps
outside a five-minute replay window. A live listener, secret and provider event store do not
exist yet, so no webhook route is exposed.

## Remaining live gates

- Allowlisted immutable public-source fetcher with redirect/DNS/size controls.
- Isolated no-egress, no-secret, non-executing worker with hard resource limits.
- Separate constrained signing service.
- Persistent idempotent quote/order/event/cost store and reconciliation job.
- Owner-controlled Stripe account activation, payout connection and secret provisioning.
- End-to-end Stripe sandbox tests, then a live unrelated-party transaction.
