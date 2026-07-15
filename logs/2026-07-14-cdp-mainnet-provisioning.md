# CDP mainnet provisioning checkpoint

Date: 2026-07-14 (America/Phoenix)

## Scope

Prepare a fail-closed, policy-bound CDP remedy identity without funding it, accepting a mainnet
order, or enabling transaction execution.

## Material external actions

- Inspected the signed-in CDP Live project and found the existing `vouchspec-revenue` and
  owner-controlled `vouchspec-owner-buyer` EVM accounts. The owner-controlled account remains
  excluded from every commercial metric.
- Created a first remedy API credential through the portal. Its secret appeared in the browser
  automation output, so the credential was immediately deleted before use and was never stored in
  GitHub, the repository, or the application. No funds, customer data, or transactions were
  involved.
- Created a replacement credential and rotated the CDP Wallet Secret without printing either
  value. Stored them as encrypted environment secrets named `CDP_API_KEY_ID`,
  `CDP_API_KEY_SECRET`, and `CDP_WALLET_SECRET` in GitHub environment
  `vouchspec-mainnet-remedies`.
- Created an account-scope policy described as `VouchSpec Base USDC remedies max 25 cents`. Its
  accepting rule is limited to `sendEvmTransaction` on Base, the canonical Base USDC contract
  `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, ERC-20 `transfer`, a maximum `value` of 250000
  atomic units, and maximum net USD change of 25 cents.
- An SDK account-creation attempt failed without creating or funding an account. A direct policy
  API attempt showed that the replacement credential lacks `policies#manage`; no permission
  change was completed.
- The protected GitHub environment is restricted by a custom `main` branch policy, contains
  `VOUCHSPEC_REMEDIES_ENABLED=false`, and the remedy workflow was manually disabled.

## Owner correction and permanent boundary

Changing API-key permissions through the web portal caused Coinbase to send repeated SMS
verification codes. The owner correctly required an API-only path. Portal automation was stopped,
the Coinbase tab was closed, and in-memory credential variables were cleared.

Do not resume Coinbase portal automation and do not request another SMS code. All remaining CDP
work must use documented APIs or the official CDP CLI. If the existing credential cannot perform
the required account-and-policy operation, leave mainnet disabled and continue other autonomous
work instead of retrying the portal.

The credential-free help surface of official package `@coinbase/cdp-cli@2.0.20` was then verified
locally. It supports headless policy listing and atomic account creation with both `name` and
`accountPolicy` fields. No CDP credential was loaded for that check and no authenticated request
was made.

## Commercial accounting

No production account was funded, no mainnet transaction occurred, no external buyer was created,
and this activity contributes zero requests, buyers, revenue, margin, repeat use, or autonomous
operating days.
