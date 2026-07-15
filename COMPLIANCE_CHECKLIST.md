# Compliance and trust checklist

## Live Stage A

- [x] `VouchSpec` remains provisional; no legal/trademark-clearance claim.
- [x] Public catalog uses full immutable Git commits and explicit subdirectories.
- [x] No artifact content is installed, imported, rendered, or executed.
- [x] No upload, private-repository, or confidential-input route exists.
- [x] Exact receipt bytes use DSSE v1.0.2/Ed25519 and an independent verifier.
- [x] Root/issuer trust and lifecycle state are separately machine-readable.
- [x] Public HTTP and MCP surfaces are read-only; writes are rejected.
- [x] Structural failures remain visible and are not labeled validated.
- [x] Owned demo, operator CI, monitoring, smoke, load, related-party, and synthetic events
  are excluded from adoption, usage, and commercial metrics.

## External adoption

- [x] Complete immutable-pinned publisher workflow and attested owned demo exist.
- [x] Publisher action preserves evidence for structural pass and fail outcomes.
- [x] First qualified repository's contribution rules were read before tailored contact.
- [ ] Three unrelated external repositories retain and run the integration. Current: 0 / 3.

## Before Stage B orderability

- [x] Strict request contract requires allowlisted host, full lowercase commit, explicit safe
  POSIX skill path, profile, buyer maximum, and opaque delivery ID.
- [x] Quote states the exact 0.25-USDC launch price, deliverable, exclusions, limits, remedies,
  and disabled mainnet gates.
- [x] Order and payment states are separate; exact-body Stripe webhook authentication is tested.
- [x] Fetch only allowlisted public immutable sources with streamed limits.
- [x] Freeze/hash bytes before analysis in an isolated, no-egress, non-executing worker.
- [x] Enforce file/count/depth/size/time/queue/output limits and adversarial path/archive tests.
- [x] Use a separate constrained signing service with no worker access to private keys.
- [x] Persist immutable quotes, idempotent orders, unique provider events, costs, fees, refunds,
  disputes, receipts, and deliveries.
- [x] Authenticate keyed-digest sandbox API credentials; bind quotes/orders/results to one
  tenant; require an expiring, rotatable, revocable order capability; store no plaintext token.
- [x] Bound the loopback commerce API by body, connection, time, rate, tenant storage, and
  exact-result digest, with generic object errors and security-state audit events.
- [x] Reconcile payment server-side from the retrieved Session, PaymentIntent, Charge, and
  Balance Transaction chain; never fulfill from a browser redirect or webhook object alone.
- [x] Complete Linux CI and cross-OS deterministic/adversarial verification for the current
  sandbox boundary; one Windows symlink-creation test remains an explicit host-privilege skip.
- [ ] Deploy the sandbox-reviewed API behind managed TLS, source-aware ingress limits, secret
  management, restricted database permissions, and redacted audit aggregation.
- [ ] Publish monotonic signed lifecycle status/invalidation for newly paid Stage B receipts.
- [ ] Activate live payment only after the owner supplies legally controlled provider identity,
  payout, and secrets.

## Commercial evidence

- [ ] 100 legitimate requests from ten unrelated sources.
- [ ] 20 repeat requests from five sources after their initial real use.
- [ ] Three unrelated settled buyers, at least $500 settled gross, and one repeat buyer.
- [ ] Positive contribution margin with complete per-order variable costs.
- [ ] Fourteen consecutive autonomous days after first settlement.
- [ ] Repeated acquisition and paid fulfillment plus self-serve support.
- [ ] Independent final goal audit confirms every acceptance test.

## Deferred Stage C

Private repositories, arbitrary uploads, confidential customer content, broad user-profile or
organization-account storage, and artifact execution remain out of scope. Stage B uses only
the minimal opaque tenant binding needed to prevent cross-buyer quote/order/result access.
