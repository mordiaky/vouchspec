# Human actions

One owner-only action is required to finish mainnet activation. The newly supplied key was tested
without disclosure: it authenticates to x402 but cannot perform the first read-only Wallet API
account-list operation even when paired with the protected Wallet Secret. It is therefore the
wrong key type. The blank local Wallet Secret did not cause that read failure.

Create one new **Server Wallet API key** with Wallet API permission to list/create EVM accounts
and sign/send policy-limited transactions, and separately generate its **Wallet Secret**. Replace
the existing values and fill the blank third value in
`D:\Projects\plyrium.env` under these exact names:

```text
CDP_WALLET_API_KEY_ID=
CDP_WALLET_API_KEY_SECRET=
CDP_WALLET_SECRET=
```

Then tell Codex only `done`. Do not paste any credential into chat. Codex will not open the
Coinbase portal, request a phone code, or read values back into chat.

After that, Codex will use the official API/CLI to create or verify the unfunded dedicated revenue
and policy-bound remedy identities. Funding remains a separate explicit approval: no USDC, ETH,
or other money will move merely because the credentials exist.

Everything else is already autonomous and fail-closed: the production database, live-only API
role, app secrets, Ed25519 signer, fulfillment worker, x402 facilitator credential, commercial
hostname, and deployment configuration are provisioned. Stripe remains regression-only and is
not a customer purchase path.
