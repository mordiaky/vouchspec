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
