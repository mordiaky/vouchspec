# Operating status

- **Launch:** VouchSpec commercial mainnet sales are live and agent-only at
  `https://vouchspec.plyrium.com`.
- **Product:** a fresh, static, non-executing validation of an immutable public GitHub commit or
  explicitly selected skill subdirectory, delivered as an exact-byte signed receipt.
- **Price and payment:** 0.25 USDC per validation through x402 v2 on Base mainnet
  (`eip155:8453`); there is no human or card checkout path.
- **Public contract:** health and discovery return HTTP 200. An unpaid valid request to
  `POST /api/vouchspec/v1/validate` returns HTTP 402 for exactly `250000` atomic USDC.
- **Fulfillment:** enabled. The protected no-egress worker and separate signer are scheduled;
  manual no-order probe `29439885033` completed successfully.
- **Production isolation:** the live application uses a dedicated opaque database key and
  live-only RPC wrappers. Generic VouchSpec RPC access is denied. Migration
  `20260715121500` is applied and verified.
- **Remedies:** disabled and unfunded by owner direction. This does not block ordinary paid
  validation, settlement, receipt delivery, or revenue.
- **Discovery:** official MCP Registry version `0.3.0` is active and latest, pointing to the live
  endpoint. Coinbase Bazaar mainnet indexing will begin after the first genuine
  successful mainnet settlement; no owner-funded or controlled payment will be used to force it.
- **Revenue:** 0 unrelated buyers, 0 repeat buyers, and USD $0 settled gross. The business is
  launched, but no external agent has purchased yet.
- **Owner action:** none required for launch. Do not create more wallet keys, send money, or
  fund the optional remedy wallet.
- **Boundary:** public immutable GitHub coordinates only; no uploads, private repositories,
  confidential content, mutable refs, or artifact execution.

Next: expose the live contract through additional agent discovery channels, acquire the first
unrelated agent buyer, and monitor genuine settlement, fulfillment, delivery, and repeat use. Exclude owner, CI,
monitor, demo, controlled-wallet, related-party, reversed, refunded, and testnet activity.
