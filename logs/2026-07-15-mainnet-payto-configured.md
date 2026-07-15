# Mainnet receiving address configured

Date: 2026-07-15 (America/Phoenix)

## Evidence

- Parsed `D:\Projects\plyrium.env` without printing values.
- `VOUCHSPEC_X402_MAINNET_PAY_TO` had exactly one definition and matched the Base/EVM
  `0x` plus 40-hex-character address contract.
- Its normalized SHA-256 prefix was recorded operationally as `7a6a913d62b5`; this is a
  non-reversible comparison fingerprint, not the address.
- It did not equal the configured sandbox receiver.
- Wrote the value as encrypted production environment metadata in the existing Vercel project.
- Re-read the individual Vercel environment value through the authenticated API and confirmed an
  exact match without emitting it.
- Confirmed production `VOUCHSPEC_COMMERCE_ENABLED=false` and public discovery HTTP 503 with
  `commerce_not_enabled`; no order or payment became possible.

## Remaining gate

Every other mainnet application configuration shape and allowlist check passed. The one missing
production identity is `VOUCHSPEC_X402_MAINNET_REMEDY_FROM`, which must be a distinct controlled
automation wallet. The existing CDP key authenticates to x402 but cannot use the Server Wallet
account API. Current official Coinbase documentation requires a Server Wallet API key plus a
separately generated Wallet Secret for programmatic account creation and signing. The Agentic
Wallet receive address is fixed to the authenticated email and does not supply a second address.

No funds moved. The bounded remedy float and any Base gas movement remain subject to separate
explicit owner approval after the remedy identity is provisioned and verified.
