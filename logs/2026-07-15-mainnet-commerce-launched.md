# VouchSpec mainnet commerce launch — 2026-07-15

## Outcome

VouchSpec is publicly orderable by agents at 0.25 USDC per fresh static validation on Base
mainnet. Human checkout is disabled. Normal fulfillment is enabled; remedies remain disabled and
unfunded and do not block sales.

## Evidence

- Production deployment: `dpl_5M1DiVCyj7efCgqiBHDsG6QhbfLy`.
- Live database migration: `20260715121500`.
- Public health and discovery probes: HTTP 200, environment `live`, network `eip155:8453`,
  amount `0.25`, and mainnet settlement available.
- Unpaid valid purchase probe: HTTP 402 with x402 v2 exact requirements for `250000` atomic USDC.
- Dedicated live database role: live wrapper allowed; generic VouchSpec RPC denied.
- Fulfillment workflow: `https://github.com/mordiaky/vouchspec/actions/runs/29439885033` completed
  successfully with no queued order.
- Production build, focused security tests, migration audit, and zero-vulnerability dependency
  audit passed before deployment.

## Accounting and exclusions

- No funds were moved during launch.
- Genuine settled buyers: 0.
- Genuine settled gross revenue: USD $0.
- Owner, controlled-wallet, CI, smoke, monitor, testnet, related-party, reversed, and refunded
  activity remains excluded.

## Discovery state

The MCP Registry `0.3.0` live-endpoint update is prepared for publication. Coinbase Bazaar's
mainnet entry is pending the first successful external mainnet settlement; the existing sandbox
entry and controlled testnet settlement do not count as adoption or revenue.
