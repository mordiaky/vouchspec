# x402 Bazaar launch checkpoint — 2026-07-14

## Outcome

The agent-native one-call VouchSpec intake is deployed at
`POST https://vouchspec-sandbox.plyrium.com/api/vouchspec/v1/validate` from reconciled Plyrium
commit `fc26b09a5d391029c21d11f9cb8ee25b14aff2d7`.

An agent submits one strict public immutable GitHub request. Before payment, the route returns the
official x402 v2 HTTP 402 challenge. After a valid CDP-facilitated settlement, the same call creates
the tenant, quote, and order and returns deterministic tenant and delivery bearer capabilities.
Exact payment retries recover the same capabilities. No human checkout exists.

## Hosted probes

- Health: HTTP 200; Bazaar readiness true; Base Sepolia; 1.00 test USDC; human checkout false.
- Discovery: HTTP 200; `agent_paid_validation` points to `/api/vouchspec/v1/validate`;
  acquisition channel is `coinbase_x402_bazaar`; authentication before payment is false.
- Valid unpaid request: HTTP 402; `PAYMENT-REQUIRED` present; x402 v2; one `exact` requirement;
  network `eip155:84532`; amount `1000000`; canonical resource URL; `extensions.bazaar` present;
  response is no-store.
- Invalid signed authorization: HTTP 402; payment requirement returned; no payment response and no
  settlement.
- CDP Bazaar public hybrid search: HTTP 200; zero VouchSpec matches. CDP indexes after successful
  settlement, so no listing is claimed yet.

## Security and deployment

- Supabase migration `20260714224500_vouchspec_bazaar_intake.sql` applied successfully.
- Vercel variables `CDP_API_KEY_ID` and `CDP_API_KEY_SECRET` are encrypted and restricted to the
  `codex/vouchspec-staging` preview branch.
- The CDP key is read-only. The server has no wallet seed, private key, transfer authority, or
  `CDP_WALLET_SECRET`.
- Deterministic payment-derived identities are domain-separated. Durable lookup binds payment,
  tenant, order, delivery-token digest, request digest, and exact stored payload.
- Public daily rate limits run before parsing. Cross-site browser mutations are rejected. Responses
  containing capabilities are no-store.
- `npm run check`, `npm run build`, the 13 focused VouchSpec security tests, TypeScript typecheck,
  and `npm audit --omit=dev` passed. The full connected repository reports 176 passing tests and
  zero known production dependency vulnerabilities.
- Launch PR `mordiaky/plyrium#31` merged the agent-native sandbox. PR `#32` raised the GitHub CI
  check-step Node heap from the default approximately 2 GB to 4 GB after an observed runner OOM;
  post-merge main run `29373305038` passed check and production build.

## Accounting

Every probe in this checkpoint is owner/test/health/smoke traffic. It contributes zero external
requests, sources, buyers, integrations, revenue, repeat use, margin evidence, or autonomy days.
The first controlled CDP settlement used only to trigger Bazaar indexing must also remain
`counts_for_goal: false`.

## Next gate

Complete one controlled Base-Sepolia payment through this CDP route, verify the resulting signed
receipt and separate invalidation status, then verify that CDP public Bazaar search returns the
canonical endpoint. Only unrelated, independently attributable agent use after that may advance
commercial acceptance counters.

## Completed excluded settlement and indexing checkpoint

At `2026-07-14T23:50:30Z`, Coinbase Agentic Wallet authorized exactly 1.00 test USDC from
`0x5AbA743d6e6Dc22584D9e175D0b39E972AB9918d`. CDP settled transaction
`0xb8e841903c0b948a639a47c33dbcf5eb63ed09ee5f727004e876005bc9e23a17`
successfully on Base Sepolia. No wallet credential entered the VouchSpec application.

Workflow run `29377467330` claimed the paid request, completed the isolated no-egress worker and
separate no-egress signing stages, and published immutable receipt digest
`sha256:da6d3b8f6d6e99390efc98c050f83e45a7a8121d736759f32400309263470bd3`.
Independent verification confirmed the signature, source commit, receipt ID, artifact digest,
byte hash, immutable cache headers, and separate `current` lifecycle status.

Coinbase's public semantic search for `VouchSpec` and public merchant lookup for the exact
receiver now both return the canonical endpoint with the expected description, 1.00-test-USDC
amount, exact scheme, Base-Sepolia network, and settlement timestamp. Agentic Wallet's earlier
local CLI search miss was a pre-index cached result; the authoritative CDP catalog is positive.

Plyrium PRs `#33` and `#34` added bounded Agentic Wallet discovery/paid-request transport
compatibility. PR `#34` merged as `d93deb4647506892f88549aab4c2167d8087d01e`; post-merge main CI
run `29377469580` passed.

This entire checkpoint is owner/controlled-wallet/testnet activity and is `counts_for_goal:
false`. External requests, sources, integrations, buyers, settled gross revenue, repeat use,
margin proof, and autonomy days all remain zero.
