# Goal evidence

The goal is **not achieved**. Public Stage A is live and three tailored external adoption
proposals have been made, but there are no qualifying external integrations, requests, buyers,
payments, or autonomous paid-operation days. The owned demo and all operator/CI/monitoring
traffic are explicitly excluded.

| # | Acceptance test | Verified status |
|---:|---|---|
| 1 | Stage A public catalog operational | Pass: public index and receipt resources return successfully |
| 2 | Documented HTTP and existing MCP retrieval | Pass: exact-byte static HTTP and installable stdio MCP |
| 3 | Current machine-readable discovery | Pass: `distribution/discovery.json`; updated action/demo/price metadata |
| 4 | Independent public signature verification | Pass: public verifier, root/issuer JWKs, and mutation tests |
| 5 | Machine-readable lifecycle status | Pass: root-signed lifecycle feed |
| 6 | Material public-service failure monitoring | Pass locally: active daily external monitor; no uptime-SLA claim |
| 7 | Three retained integrations in three unrelated external repositories | Pending: 0 / 3 |
| 8 | Each integration is genuine, external, verifiable, and retained/release-used | Pending; the owned demo and open proposal do not count |
| 9 | 100 legitimate external machine requests | Pending: 0 / 100 |
| 10 | Requests from ten unrelated external sources | Pending: 0 / 10 |
| 11 | Twenty repeat requests | Pending: 0 / 20 |
| 12 | Repeat requests from five sources after their first real use | Pending: 0 / 5 |
| 13 | Exclude owner, CI, monitor, tests, controlled accounts, related parties, fake repeats | Pass as accounting policy; external operation unproven |
| 14 | One genuine machine-readable paid request completes | Pending: 0 |
| 15 | Software can quote, price, explain, pay, receive, verify, and continue autonomously | Partial: authenticated quote/order/status/result and complete signed sandbox delivery work; public/live payment remains disabled |
| 16 | Three unrelated external buyers settle | Pending: 0 / 3 |
| 17 | At least USD $500 settled gross external revenue | Pending: USD $0 / $500 |
| 18 | Exclude owner/related/test/pending/reversed/refunded/simulated revenue | Pass as accounting policy; no revenue recorded |
| 19 | One paid buyer repeats or buys a second service | Pending: 0 |
| 20 | Positive contribution margin after every variable cost | Pending: no paid operation |
| 21 | Every paid operation has complete quote/payment/cost/receipt/delivery/refund fields | Partial: tenant-bound environment ledger and signed-result delivery pass sandbox reconciliation; no genuine paid operation |
| 22 | Owner-funded spending within USD $100 lifetime limit | Pass: USD $0 spent; USD $100 remains |
| 23 | Fourteen consecutive autonomous days after first settled payment | Pending: clock not started |
| 24 | Monitoring through recovery/support/financial logging runs during that period | Pending |
| 25 | No ordinary order requires a call, review, meeting, or manual delivery | Partial: authenticated sandbox order and result delivery were fully autonomous; no genuine order yet |
| 26 | One acquisition channel produces more than one qualified external user/integration | Pending: repository-specific publisher outreach has two contacts but no response/integration |
| 27 | One paid fulfillment process completes more than one real order | Pending: 0 |
| 28 | Self-serve discovery, evidence, integration, quote, purchase, verify, troubleshooting | Partial: authenticated sandbox quote/order/result plus discovery/integration/verify/operations are documented; public payment and credential issuance remain disabled |
| 29 | Independent goal-auditor inspects complete evidence | Pending until tests 1-28 have evidence |
| 30 | Auditor confirms every genuineness, financial, operational, security, and claims test | Pending |

## Current non-commercial product evidence

- 25 signed receipts across 12 GitHub repository-owner namespaces: 19 structural passes, six
  explicit structural failures, and no hidden catalog skips.
- DSSE v1.0.2/Ed25519 exact-byte receipt envelopes, signed index, root-signed lifecycle, and
  separate public trust material.
- Public GitHub-managed TLS/CORS distribution and a public installable read-only stdio MCP.
- Public owned demo run `29331787790` with pass/failure matrix assertions and four independently
  verified workflow-bound attestations. It proves integration mechanics only.
- Three public, repository-specific proposals to unrelated publishers: Supabase issue `136`,
  K-Dense issue `211`, and michtio issue `10`. They prove outreach only; all are open without
  maintainer response.
- One complete Stage B sandbox order: exact GitHub commit freeze, no-egress/no-host-write
  Docker worker, constrained DSSE signing, all direct-cost fields, event reconciliation, and
  delivery. `fulfillment/stage-b-sandbox-proof.json` marks it operator-owned,
  nonsettling, and excluded; it proves mechanics only.
- Authenticated sandbox API tests cover plaintext-token exclusion, tenant-scoped idempotency,
  cross-tenant denial, capability expiry/rotation/revocation, strict HTTP framing, slow-client
  isolation, quotas, audit events, exact signed-result delivery, and live-store refusal.
- 114 tests pass in an isolated environment. One Windows symlink-creation test is explicitly
  skipped for missing host privilege; Linux-container and hostile tree/archive/path tests pass.
- Public Linux CI run `29338263172` passed at commit
  `d5ed89f2630648a58531aff84006432dfd0ef5e7`, including package installation, the full test
  suite, and a CLI receipt smoke test.

Evidence sources include `catalog/public/`, `distribution/discovery.json`, `analytics/`,
`CRM.csv`, `EXPERIMENTS.csv`, `BUDGET.csv`, `REVENUE.csv`, public CI/attestation URLs, and the
final independent audit when eligible. Current public engineering/adoption references include
`https://github.com/mordiaky/vouchspec/actions/runs/29338263172`,
`https://github.com/supabase/agent-skills/issues/136`, and
`https://github.com/K-Dense-AI/scientific-agent-skills/issues/211`, and
`https://github.com/michtio/craftcms-claude-skills/issues/10`.
