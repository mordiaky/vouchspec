# Goal evidence

The goal is **not achieved**. Public catalog and testnet commerce mechanics work, but there are
no qualifying external integrations, requests, buyers, payments, repeat buyers, contribution
margin, or autonomous paid-operation days. Owner, controlled-wallet, demo, CI, smoke, monitoring,
and test traffic is explicitly excluded.

| # | Acceptance test | Verified status |
|---:|---|---|
| 1 | Stage A public catalog operational | Pass: public index and receipt resources return exact signed bytes |
| 2 | Documented HTTP and MCP retrieval | Pass: static HTTP, verifier, and installable stdio MCP |
| 3 | Current machine-readable discovery | Pass: repository contract, stable managed discovery endpoint, and official x402 Bazaar metadata are public and consistent |
| 4 | Independent public signature verification | Pass: public JWKs, exact-byte verifier, and mutation tests |
| 5 | Machine-readable lifecycle/invalidation | Pass: root-signed catalog lifecycle plus separate live hosted receipt status |
| 6 | Material public-service failure monitoring | Pass operationally: GitHub fulfillment failures alert the owner; no uptime-SLA claim |
| 7 | Three retained integrations in unrelated repositories | Pending: 0 / 3 |
| 8 | Integrations are genuine, external, verifiable, retained/release-used | Pending; owned demo and proposals do not count |
| 9 | 100 legitimate external machine requests | Pending: 0 / 100 |
| 10 | Requests from ten unrelated external sources | Pending: 0 / 10 |
| 11 | Twenty repeat requests | Pending: 0 / 20 |
| 12 | Repeat requests from five sources | Pending: 0 / 5 |
| 13 | Exclude controlled/fake traffic | Pass as accounting policy; owner E2E remains excluded |
| 14 | One genuine machine-readable paid request completes | Pending: 0; owner Base Sepolia payment proves mechanics only |
| 15 | Software quotes, explains, pays, delivers, verifies, and continues autonomously | Pass on the public one-call testnet flow, including Agentic Wallet payment, CDP settlement, scheduled fulfillment, signature verification, caching, and lifecycle status; commercial mainnet remains disabled |
| 16 | Three unrelated external buyers settle | Pending: 0 / 3 |
| 17 | At least USD $500 settled gross external revenue | Pending: USD $0 / $500 |
| 18 | Exclude owner/test/pending/reversed/refunded/simulated revenue | Pass as policy and stored `counts_for_goal`; no revenue recorded |
| 19 | One paid buyer repeats or buys a second service | Pending: 0 |
| 20 | Positive contribution margin after variable cost | Pending: no genuine paid operation |
| 21 | Complete quote/payment/cost/receipt/delivery/remedy fields | Pass on owner testnet proof; pending for a genuine paid operation |
| 22 | Owner-funded spending within USD $100 lifetime limit | Pass: USD $0 recorded; USD $100 remains |
| 23 | Fourteen autonomous days after first settled payment | Pending: clock not started |
| 24 | Monitoring, recovery, support, and financial logging during that period | Pending |
| 25 | No ordinary order requires human labor | Pass on testnet mechanics; unproven with genuine commercial demand |
| 26 | One acquisition channel produces multiple qualified users/integrations | Pending: current issues are outreach only |
| 27 | One fulfillment process completes multiple real orders | Pending: 0 genuine orders |
| 28 | Self-serve discovery, integration, quote, purchase, verify, troubleshooting | Pass for the public testnet sandbox: the canonical endpoint is indexed in Coinbase Bazaar, accepts anonymous-before-payment one-call intake, and publishes independently verifiable receipts; mainnet remains disabled |
| 29 | Independent goal auditor inspects complete evidence | Pending until tests 1-28 are eligible |
| 30 | Auditor confirms every required claim | Pending |

## Hosted owner-excluded proof

- Stable base URL: `https://vouchspec-sandbox.plyrium.com`.
- Agent-only payment: x402 v2, `exact`, Base Sepolia (`eip155:84532`), 1.00 test USDC, no
  human checkout.
- Order: `ord_01b1e85f188649a6b68e2dd2`.
- Settlement transaction:
  `0xfe4b912ace571cd533d02e474de766d7dbe19d744d5cb35420cb71d7952aea11`.
- Result digest: `sha256:f76d3c36a611bf304e6d87ff02331e0298282ed449a335b5704d54bedb0c0c53`.
- Receipt ID: `cpr_2bb3259dd33d0cbadf7580dc`.
- Issuer key ID: `PWGCY2HpACKhufnSBjbf2zwMzThqxyPTz_MAwCyJ0I0`.
- Independent signature check passed; public content-addressed bytes exactly matched the
  authenticated result; separate live status returned `CURRENT`.
- Public receipt:
  `https://vouchspec-sandbox.plyrium.com/api/vouchspec/v1/receipts/f76d3c36a611bf304e6d87ff02331e0298282ed449a335b5704d54bedb0c0c53`.
- Public status: the receipt URL plus `/status`.
- Accounting: `counts_for_goal: false`; no buyer, request, adoption, or revenue credit.

## CDP Bazaar one-call launch evidence

- Connected deployment commit:
  `fc26b09a5d391029c21d11f9cb8ee25b14aff2d7`.
- Launch implementation merged through `mordiaky/plyrium#31`; CI runner-memory repair merged
  through `#32`. Post-merge main CI run `29373305038` passed.
- Direct route:
  `POST https://vouchspec-sandbox.plyrium.com/api/vouchspec/v1/validate`.
- No tenant registration or authentication is required before payment. A successful payment
  deterministically returns a tenant API key and delivery capability bound to that exact payment.
- Hosted health returned HTTP 200 with Bazaar readiness enabled.
- A valid anonymous request returned HTTP 402 with x402 v2, `exact`, Base Sepolia
  (`eip155:84532`), amount `1000000` atomic test USDC, one accepted requirement, the canonical
  route URL, and the official `bazaar` extension.
- A syntactically valid invalid-signature request returned HTTP 402, with no payment-response
  header and no settlement.
- CDP public search initially returned zero matches before settlement. After the excluded
  successful settlement below, both semantic search for `VouchSpec` and merchant lookup by the
  exact `payTo` address returned the canonical endpoint, description, price, network, scheme,
  asset, and last-updated settlement timestamp.
- The dedicated CDP server key is read-only and encrypted only in the branch-scoped Vercel
  environment. No wallet secret or private key is configured in the application.
- Repository gates: TypeScript typecheck, 176 tests, security/release audits, production build,
  and production dependency audit with zero known vulnerabilities all passed.
- Accounting: health, unpaid, invalid-signature, owner, and controlled settlement probes are
  excluded from all request, buyer, adoption, and revenue counters.

## Agentic Wallet settlement, fulfillment, and Bazaar indexing evidence

- Agentic Wallet payer: `0x5AbA743d6e6Dc22584D9e175D0b39E972AB9918d`.
- Base-Sepolia USDC transfer: exactly `1000000` atomic test USDC in successful transaction
  `0xb8e841903c0b948a639a47c33dbcf5eb63ed09ee5f727004e876005bc9e23a17`,
  block `44152371`, timestamp `2026-07-14T23:50:30Z`.
- Fulfillment workflow:
  `https://github.com/mordiaky/vouchspec/actions/runs/29377467330`; it claimed the paid request,
  ran the immutable no-egress worker, ran the separate no-egress signer, and delivered successfully.
- Public envelope digest:
  `sha256:da6d3b8f6d6e99390efc98c050f83e45a7a8121d736759f32400309263470bd3`;
  receipt ID `cpr_00ce786d643f31303c0f6363`.
- Two independent fetches returned identical 10,856-byte envelope bytes. Their SHA-256 matched
  the content-addressed path, `Cache-Control` was `public, max-age=31536000, immutable`, and the
  ETag carried the same digest.
- The local verifier authenticated the Ed25519 DSSE signature with the public issuer JWK, exact
  source commit `344558d51ecae7929c50b7cff94e120bfca53807`, and artifact digest
  `b0b3fa6662dc6f673dc4fe274fc9a8e5d04923cbce8fc4e5f1a976c7f83163fe`.
  The separate no-store status reports the receipt `current` with no replacement or invalidation.
- Coinbase public semantic search and merchant discovery both list
  `https://vouchspec-sandbox.plyrium.com/api/vouchspec/v1/validate`, last updated at
  `2026-07-14T23:50:30.595Z`, with exact 1.00 test USDC on `eip155:84532`.
- Agentic Wallet request-body/header compatibility fixes were merged through Plyrium PRs `#33`
  and `#34`; post-merge main CI run `29377469580` passed.
- Accounting: this owner-controlled faucet-funded test is `counts_for_goal: false`. Genuine
  requests remain 0, buyers remain 0, settled gross revenue remains USD $0, and the 14-day clock
  remains unstarted.

## Operational recovery evidence

Four owner-triggered workflow runs failed while diagnosing the separate signer container. Safe,
allowlisted diagnostics reduced the fault to `isolated_signer_runtime_import`: the minimal image
was invoking a broad CLI module whose optional imports were intentionally absent. The signer now
invokes dependency-minimal `stage_b_signer_cli.py`. Exact-image no-egress/read-only probing passed,
the full suite passed, and hosted workflow run
`https://github.com/mordiaky/vouchspec/actions/runs/29359911240` completed successfully at commit
`13c65f3dc36a099c0d45aa36aa08b58b3d738371`. The emails were valid failure alerts and remain
enabled for future genuine incidents.

Other evidence sources include `catalog/public/`, `distribution/discovery.json`, `analytics/`,
`CRM.csv`, `EXPERIMENTS.csv`, `BUDGET.csv`, `REVENUE.csv`, hosted API/workflow records, public
CI/attestation URLs, and the final independent audit when eligible.

## Mainnet fail-closed safety evidence

- Hosted remedy/state PR `mordiaky/plyrium#37` merged as
  `d10c9efca88b73ab057ec47759ca86e4f36d5521`; main CI run `29382823021` passed typecheck,
  178 tests/audits, and the optimized production build.
- Public fetcher/executor PR `mordiaky/vouchspec#9` merged as
  `82ad5fbf526f2b2f01397899f692045ce659870d`; main CI run `29382833205` passed 139 tests with
  one explicit Windows symlink-privilege skip.
- The fetcher is a separate immutable image running non-root, read-only, capability-dropped, with
  no host mount, kernel-backed bounded scratch, bounded output/resources, remote removal, and
  offline finalization.
- The hosted store now persists reconciliation checkpoints and remedy attempts, prevents double
  settlement credit, converts terminal paid fulfillment failures into zero contribution and a
  queued payer-derived remedy, and permits only one remedy per payment.
- Remedy confirmation independently verifies the exact Base ERC-20 transfer, sender, canonical
  USDC contract, calldata amount, transaction receipt, and Transfer log through Base RPC.
- The CDP executor is exact-version pinned, stops before the provider's 24-hour idempotency window,
  is guarded by a protected main-only environment, and remains disabled because
  `VOUCHSPEC_REMEDIES_ENABLED` is not true.
- No production wallet was funded, no mainnet order was accepted, and these controls add no buyer,
  request, revenue, margin, repeat-use, or autonomous-day credit.
