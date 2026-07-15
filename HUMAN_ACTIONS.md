# Human actions

The mainnet receiving address is complete. Codex validated the owner Agentic Wallet Base address
without disclosure and stored it encrypted in Vercel production. Do not replace that address or
the working x402 facilitator key.

One owner-only action remains because Coinbase does not expose Wallet Secret generation through
an already authenticated API. In the CDP Portal, create one new **Server Wallet API key** with
Wallet API permission to list/create EVM accounts and sign/send policy-limited transactions, and
separately generate its **Wallet Secret**. Store the three new values in
`D:\Projects\plyrium.env` under these exact new names:

```text
CDP_REMEDY_API_KEY_ID=
CDP_REMEDY_API_KEY_SECRET=
CDP_REMEDY_WALLET_SECRET=
```

Then tell Codex only `done`. Do not paste any credential into chat. Codex will not open the
Coinbase portal, request a phone code, or read values back into chat.

After that, Codex will use the official API/CLI to create or verify one unfunded policy-bound
remedy identity. Funding remains a separate explicit approval: no USDC, ETH, or other money will
move merely because the credentials exist.

Everything else is already autonomous and fail-closed: the production database, live-only API
role, app secrets, Ed25519 signer, fulfillment worker, x402 facilitator credential, commercial
hostname, and deployment configuration are provisioned. Stripe remains regression-only and is
not a customer purchase path.
