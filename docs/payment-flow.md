# VouchSpec agent-only payment and reconciliation flow

Status: the managed public sandbox accepts self-service agent registrations and exact x402 v2
payments using test USDC on Base Sepolia. A settled testnet payment autonomously queues the
immutable-source job, delivers a signed result, publishes cacheable receipt bytes, and exposes
separate live invalidation status. There is no card form, hosted checkout, human approval, or
manual delivery. Mainnet remains fail-closed.

## Payment decision

x402 is the only VouchSpec launch rail. It keeps the buyer and seller as software: an
authenticated agent requests a protected HTTP resource, receives `402 Payment Required`, signs
the exact payment, retries the same resource, and receives a settlement proof. The checked-in
Stripe adapter is retained for regression/research only and is not connected to the managed API.

Current protocol references:

- [Coinbase x402 flow](https://docs.cdp.coinbase.com/x402/core-concepts/how-it-works)
- [Coinbase x402 facilitator](https://docs.cdp.coinbase.com/x402/core-concepts/facilitator)
- [Coinbase x402 refund limitation](https://docs.cdp.coinbase.com/x402/support/faq)

## Public machine contract

Base URL: `https://vouchspec-sandbox.plyrium.com`

1. `POST /api/vouchspec/v1/tenants` with the current machine terms acceptance. The response
   returns an opaque tenant API key once; the service stores only a keyed digest.
2. `POST /api/vouchspec/v1/quotes` with `Authorization: Bearer ...`, a unique
   `Idempotency-Key`, and the strict `fresh_public_static_validation` request. The request pins
   `github.com`, repository owner/name, a full lowercase commit, exact portable skill path,
   fixed profile, maximum price, and opaque delivery ID.
3. The sandbox quote is exactly 1.00 test USDC and is explicitly non-revenue. The separate
   researched commercial launch experiment is 0.25 USDC; it is not mainnet-orderable today.
4. `POST /api/vouchspec/v1/orders` with the quote ID and a new tenant-scoped idempotency key.
   The response returns the order, a one-time order delivery token, and its purchase path.
5. `GET` the purchase path with the bearer key and `X-VouchSpec-Delivery-Token`. Without a
   payment it returns 402 and an x402 v2 `PAYMENT-REQUIRED` challenge for exact USDC on
   `eip155:84532`.
6. The agent signs that exact payment and retries the identical request with
   `PAYMENT-SIGNATURE`. A successful settlement returns `PAYMENT-RESPONSE` and 202 while the
   fulfillment lease is queued.
7. A private authenticated worker lease freezes the exact Git commit and subdirectory. Static
   inspection runs in a pinned no-egress, read-only container. A separate no-egress signer
   re-verifies the bounded evidence before producing the DSSE envelope.
8. The agent polls `GET /api/vouchspec/v1/orders/{order_id}` using both credentials, then reads
   `/result` when delivered. The authenticated result is `no-store`.
9. The same exact envelope bytes are published without credentials at the returned
   content-addressed `/receipts/{sha256_hex}` URL with a one-year immutable cache policy.
10. Every new reliance decision checks the separate `/receipts/{sha256_hex}/status` resource.
    Receipt bytes never change; the no-store status can report invalidation or lifecycle change.

The [machine discovery document](../distribution/discovery.json) contains the route templates,
headers, network, issuer key, caching semantics, prices, and trust boundary in JSON.

## Independent state dimensions

Order, payment, fulfillment, delivery, and commercial accounting remain separate. Testnet chain
settlement authorizes work but is never revenue and never starts the commercial 14-day clock.
The durable store uses tenant-bound idempotency, one settlement record per order, leased payment
processing, a pre-settlement recovery checkpoint, and exact settlement/order binding to prevent
replay or concurrent double fulfillment.

Delivery capabilities expire after 30 days and may be rotated or revoked. The order and result
endpoints require both the tenant API key and order capability. Content-addressed public receipt
bytes need neither credential because they are non-secret evidence; the separate status endpoint
is what carries live invalidation.

## Hosted proof

On 2026-07-14, owner-controlled order `ord_01b1e85f188649a6b68e2dd2` completed the public
flow. Base Sepolia transaction
`0xfe4b912ace571cd533d02e474de766d7dbe19d744d5cb35420cb71d7952aea11` settled exactly 1.00
test USDC. The leased worker and signer delivered receipt `cpr_2bb3259dd33d0cbadf7580dc` with
envelope digest `sha256:f76d3c36a611bf304e6d87ff02331e0298282ed449a335b5704d54bedb0c0c53`.
The signature verified with issuer key `PWGCY2HpACKhufnSBjbf2zwMzThqxyPTz_MAwCyJ0I0`; the
public bytes exactly matched the authenticated result and live status returned `CURRENT`.

This proof is deliberately marked `counts_for_goal: false`. It is not an external request,
customer, buyer, payment, revenue, or adoption event.

## Accounting and remedies

Every order records the immutable quote, chain/payment identifiers, fulfillment events, direct
cost fields, envelope/receipt identifiers, delivery state, remedy state, and contribution impact.
Only an unrelated buyer's Base mainnet settlement may become revenue, and only after exclusion
of owner/related/test funds and any refund, reversal, dispute, or unresolved remedy.

x402 does not supply a card-style refund object. VouchSpec therefore models a remedy as a new,
fixed USDC transfer from a separate balance-capped wallet to the payer proven by the original
authorization. The durable state machine covers duplicate settlement and terminal objective
fulfillment failure, uniquely binds settlement/remedy transactions, stops uncertain retries
before the provider idempotency window closes, and excludes returned funds from settled gross.
The wallet executor remains disabled until its live account policy and bounded float are verified.

## Remaining mainnet gates

- Configure a separate live receiving identity, mainnet facilitator/network allowlist, live
  secrets, and isolated live database. Test and live objects must never share state.
- Provision the separate CDP remedy account, attach its Base/USDC/amount/function policy, cap its
  float, and pass negative policy probes before enabling its protected scheduled workflow.
- Exercise settlement recovery against mainnet-compatible RPC/facilitator behavior without
  weakening the current fail-closed checkpoint and replay controls.
- Reconcile actual chain/facilitator, worker, storage, delivery, and remedy costs per order and
  refuse work that cannot retain positive contribution at the quoted price.
- Run a genuine unrelated agent purchase, preserve its attribution evidence, and count it only
  after the settlement and exclusion rules pass.

The worker, signer, immutable receipt publication, invalidation, and public self-service API are
already hosted and proven on testnet. Mainnet enablement must change payment environment and
accounting—not reintroduce humans or broaden accepted artifact inputs.
