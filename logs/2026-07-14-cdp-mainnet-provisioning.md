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

## API-only implementation and final result

- PR `mordiaky/vouchspec#10` merged the main-only protected-environment provisioner and Node CI as
  merge commit `30c9fc31c192eed7d9e974cca875fd8921f0675d`.
- The first dispatch, run `29384979666`, was skipped before any step because environment-scoped
  variables are not available in a job-level condition. No CDP request occurred.
- PR `#11` moved the exact-false assertion into the first protected-environment step and merged as
  `c32f0127c5bce06d9e397d097d13fb0b88155953`.
- Run `29385077682` loaded the encrypted credentials and failed closed with a deliberately generic
  CDP API error. No account or transaction operation was confirmed.
- PR `#12` added safe operation-level diagnostics without logging provider response text or secret
  material and merged as `82463543668b0abd92712004110a294aae8b0bf6`.
- Final API-only run `29385202893` passed the protected-environment false-flag gate, installed the
  integrity-locked official CLI, and failed on its first read-only EVM account-list call with
  `provisioner_account_list_api_failed`. It stopped before policy lookup or account creation.
- Post-merge main CI run `29385199415` passed 140 Python tests with one explicit host
  symlink-privilege skip, plus both Node suites and zero-vulnerability production audits.

This exhausts the current credential safely. Do not retry it, resume portal automation, or request
SMS verification. Revisit CDP provisioning only if a credential with account and policy access
becomes available through a documented non-interactive API path.

## Commercial accounting

No production account was funded, no mainnet transaction occurred, no external buyer was created,
and this activity contributes zero requests, buyers, revenue, margin, repeat use, or autonomous
operating days.
