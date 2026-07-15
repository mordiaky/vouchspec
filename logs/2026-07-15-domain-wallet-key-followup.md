# Domain isolation and Wallet key follow-up

Date: 2026-07-15 (America/Phoenix)

## Live hostname outcome

- Merged `mordiaky/plyrium#41` at commit
  `d54196fe33e3bdde075f5c44c6ed68edbab0c957`.
- Production deployment `dpl_54nF5zD3eJGVShz7EqPpj8vb6Lcr` reached READY.
- Main CI run `29418546016` passed 185 application tests, all audits, and the optimized build.
- `https://vouchspec.plyrium.com/` returns 308 to
  `/api/vouchspec/v1/discovery`.
- Stray human-product paths such as `/pricing` return the same machine-contract redirect.
- Following the live root ends at a 503 JSON response because commerce remains deliberately
  disabled.
- `https://www.plyrium.com/` remains 200 and unchanged.

The sandbox discovery API remains healthy at 200. Its root is still attached to the older
preview deployment and returns the staging 401. A replacement preview was not attached: the
remote Preview builder stalled, while the local Vercel prebuilt path failed on the unrelated
existing `/api/voice/voices` lambda packaging defect. Never point the sandbox alias at the live
deployment merely to hide this cosmetic root issue.

## Owner-supplied Coinbase credential outcome

- Confirmed `CDP_WALLET_API_KEY_ID` and `CDP_WALLET_API_KEY_SECRET` were nonblank and structurally
  plausible in `D:\Projects\plyrium.env`; no value was printed.
- Confirmed the local `CDP_WALLET_SECRET` entry is blank.
- Replaced the protected GitHub environment's encrypted CDP API key values while preserving the
  already-encrypted Wallet Secret.
- API-only workflow run `29417171632` failed on its first read-only EVM account-list operation,
  before policy lookup, account creation, funding, signing, or transaction submission.
- The same owner-supplied key successfully authenticated to the official `cdp x402 supported`
  command locally.

Conclusion: the key is valid for CDP x402 but is not a Server Wallet API key. The blank local
Wallet Secret did not cause the read-only account-list failure because the protected Wallet Secret
was present during that test. Do not retry the same key or use portal/SMS automation.

## Financial and acceptance accounting

- Customer payments accepted: 0
- Mainnet transactions: 0
- Funds moved: USD 0
- Owner-funded spend: USD 0
- Acceptance credit from owner/CI/smoke traffic: 0
