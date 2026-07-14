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
| 15 | Software quotes, explains, pays, delivers, verifies, and continues autonomously | Pass on the registered public testnet flow; the new one-call CDP route awaits its first excluded settlement and commercial mainnet remains disabled |
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
| 28 | Self-serve discovery, integration, quote, purchase, verify, troubleshooting | Pass for the public testnet sandbox, including anonymous-before-payment one-call intake; public Bazaar indexing awaits the first CDP settlement; mainnet remains disabled |
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
  `f84449fbf2b825b46a08582666ea1a09f7bd1654`.
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
- CDP public hybrid search returned HTTP 200 with zero VouchSpec matches. This is expected and is
  not counted as a listing: CDP documents that indexing begins only after the first successful
  CDP-facilitated settlement.
- The dedicated CDP server key is read-only and encrypted only in the branch-scoped Vercel
  environment. No wallet secret or private key is configured in the application.
- Repository gates: TypeScript typecheck, 169 tests, security/release audits, production build,
  and production dependency audit with zero known vulnerabilities all passed.
- Accounting: health, unpaid, invalid-signature, owner, and controlled settlement probes are
  excluded from all request, buyer, adoption, and revenue counters.

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
