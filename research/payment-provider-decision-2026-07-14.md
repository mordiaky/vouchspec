# Payment provider decision — 2026-07-14

## Decision

Use Stripe Checkout as the primary conventional rail. Preserve x402 as a secondary
machine-native option after the first conventional paid flow is proven. Retain Paddle as a
fallback if merchant-of-record tax handling becomes a measured commercial requirement.

This is a product/engineering decision, not legal, tax, or jurisdiction advice.

## Evidence

| Provider | Current public price | Test preparation | Live gate | Decision |
|---|---:|---|---|---|
| Stripe Checkout | 2.9% + $0.30 for standard US cards; no setup/monthly fee | Sandboxes, webhooks, refunds and reconciliation documented | Activated account, identity/business/payout data, live secrets | Primary |
| Coinbase CDP/x402 | First 1,000 facilitator transactions/month free, then $0.001 each | Signup-free testnet facilitator documented | Production facilitator credentials and owner-authorized receiving wallet | Secondary later |
| Paddle | 5% + $0.50; no monthly fee | Separate sandbox and simulated webhooks/refunds | Business/identity/domain verification and live credentials | MoR fallback |

Official sources:

- https://stripe.com/pricing
- https://docs.stripe.com/payments/checkout/how-checkout-works
- https://docs.stripe.com/get-started/account
- https://docs.stripe.com/webhooks
- https://docs.stripe.com/api/refunds/create
- https://docs.stripe.com/api/balance_transactions
- https://docs.stripe.com/currencies
- https://docs.cdp.coinbase.com/x402/core-concepts/facilitator
- https://docs.cdp.coinbase.com/x402/core-concepts/how-it-works
- https://docs.cdp.coinbase.com/x402/quickstart-for-sellers
- https://docs.cdp.coinbase.com/x402/support/faq
- https://www.paddle.com/pricing
- https://developer.paddle.com/sdks/sandbox/
- https://www.paddle.com/help/start/account-verification

## Pricing implication

The previous USD $0.10 fresh-validation hypothesis is incompatible with a conventional card
rail. It is below Stripe's USD $0.50 minimum and below the fixed USD $0.30 component. The
initial USD $49 hypothesis preserves room for processor fees, a USD $5 hard direct-cost
ceiling, refunds, and positive contribution. It remains unvalidated until genuine buyers
pay it.
