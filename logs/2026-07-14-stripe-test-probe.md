# Stripe account and test Checkout probe

Date: 2026-07-14 UTC

The owner authorized use of Stripe credentials already stored in an environment file outside
the repository. Secret values were loaded only in process memory and were never
printed, copied into this repository, or persisted in the temporary commerce database.

Observed evidence:

- The configured test secret authenticated successfully to a Stripe test/sandbox account named
  `Plyrium`; charges, payouts, and submitted account details were enabled.
- The configured live secret was used only for a read-only account retrieval. It authenticated
  to a distinct enabled U.S. account whose Stripe business URL is `www.plyrium.com`.
- The reviewed adapter used `stripe==15.3.0` with API version `2026-06-24.dahlia`, verified the
  expected test account ID, and created one USD $49.00 hosted Checkout Session.
- The Session reported `livemode=false`, `currency=usd`, `amount_total=4900`, `status=open`, and
  no PaymentIntent before payment. Adapter reconciliation returned the corresponding pending
  state.
- The Session was immediately expired and confirmed `status=expired`, `payment_status=unpaid`.
- A byte scan of the temporary SQLite database found neither the API key nor webhook secret.

This was owner-authorized internal test activity. It records no buyer, settled revenue,
external request, integration, or autonomous-operation day.
