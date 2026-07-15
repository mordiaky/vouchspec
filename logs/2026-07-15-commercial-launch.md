# Commercial launch checkpoint

Date: 2026-07-15 (America/Phoenix)

## Outcome

All non-financial commercial infrastructure was implemented, verified, merged, and provisioned.
Production remains deliberately fail-closed because the current Coinbase credential authenticates
to x402 but cannot access Wallet API accounts. No customer payment was accepted and no funds moved.

## Database isolation

- Snapshotted existing VouchSpec production row counts before migration.
- Applied missing migrations `20260715003000_vouchspec_environment_pricing.sql` and
  `20260715021500_vouchspec_onchain_remedies.sql`; existing tenant, order, payment, and job row
  counts did not change.
- Applied `20260715120000_vouchspec_scoped_live_rpc.sql` after a rollback-only dependency and
  privilege probe.
- Created non-login role `vouchspec_live_api` with 27 live-only RPC wrappers and no direct table or
  private-schema access.
- Issued a dedicated opaque Supabase secret key whose JWT template selects only that role, stored it
  directly in Vercel, and deleted every failed issuance attempt.
- External Data API probe results: live receipt wrapper 200; Plyrium client table 403; unscoped
  VouchSpec receipt RPC 403.

## Runtime identity and workers

- Generated distinct 256-bit live auth and delivery secrets, live fulfillment/remedy tokens, and a
  separate encrypted Ed25519 signing identity.
- Stored application material only in Vercel's encrypted production environment and the private
  signing material only in GitHub environment `vouchspec-mainnet`.
- Kept `VOUCHSPEC_COMMERCE_ENABLED=false` and
  `VOUCHSPEC_LIVE_FULFILLMENT_ENABLED=false` throughout provisioning.
- Merged fail-closed live fulfillment workflow in `mordiaky/vouchspec#15`, merge commit
  `dc97c83d04d6c2045460035bb3ee9e5e33015ea6`.

## Coinbase x402 credential

- Used the official CDP CLI in the protected mainnet-remedies environment; no browser or phone code
  was used.
- `cdp x402 supported` authenticated successfully and reported 24 payment kinds and 3 extensions.
- Copied the credential directly from the protected GitHub environment into Vercel encrypted
  variables `CDP_LIVE_API_KEY_ID` and `CDP_LIVE_API_KEY_SECRET` without revealing either value.
- Removed the temporary Vercel sync token, temporary deployment-branch allowlist, and temporary
  remote diagnostic branch immediately after successful run `29414686175`.
- The same credential's earlier read-only EVM account-list failure remains authoritative: it is a
  facilitator credential, not a Wallet-API-capable account credential.

## Application and deployment

- Merged scoped commercial access in `mordiaky/plyrium#39`, merge commit
  `d9afdcc079653f55c6a2115eade8133a6d2db33e`.
- Local gates: 180 application tests, TypeScript, private/public/release audits, zero production
  dependency vulnerabilities, and optimized production build passed.
- Hosted PR CI run `29414124330` passed, including its production build.
- Attached and verified `vouchspec.plyrium.com` on the Vercel production project. The disabled
  health and discovery surfaces return 503 as intended; the sandbox remains 200 and unchanged.
- The post-merge production deployment and CI were still building at this checkpoint.

## Remaining owner-only gate

Coinbase documents creation and permission changes for a CDP Secret API Key through the portal; no
documented non-interactive management endpoint can grant the current key Wallet API access. The
owner must create one Wallet-API-capable Secret API Key and Wallet Secret and place them in
`D:\Projects\plyrium.env` under the names in `HUMAN_ACTIONS.md`. Codex will not open the portal or
request SMS codes.

After that credential exists, Codex can create or verify the unfunded dedicated revenue and
policy-bound remedy accounts through the official CLI. Funding remedy USDC/Base gas remains a
separate explicit money-movement approval.

## Commercial accounting

- Genuine buyers: 0
- Settled commercial revenue: USD 0
- Owner-funded spend: USD 0
- Mainnet transactions in this checkpoint: 0
- Acceptance credit from tests, smoke, CI, controlled accounts, and monitoring: 0
