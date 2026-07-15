# VouchSpec agent-only pricing analysis

**Decision date:** 2026-07-14 (America/Phoenix)

**Live catalog sample time:** 2026-07-15T00:28:22Z
**Scope:** one fresh, isolated, deterministic static validation of one exact public Agent Skill
commit, followed by a signed, public, content-addressed receipt and separate live invalidation
status. Payment is agent-to-agent x402 exact USDC; there is no human checkout, subscription,
meeting, or custom review.

## Decision

Reject USD **$49.00** as the launch price. It was a Stripe-era transaction hypothesis, not an
agent-market result, and it is incompatible with the observed x402 price distribution and common
agent wallet spending controls.

Launch the first genuine Base-mainnet experiment at **0.25 USDC per fresh validation**. This is a
test price, not a validated price or a permanent list price.

Keep existing receipt retrieval, signature verification material, and invalidation status free.
Agents pay for new independent work and freshness, not for re-downloading immutable bytes that
already exist.

## Evidence hierarchy

1. **Live market supply:** Coinbase CDP Bazaar's public discovery catalog and semantic search.
2. **Direct operating cost:** the completed VouchSpec isolated fulfillment run and current
   GitHub/CDP published rates.
3. **Competitive substitutes:** first-party vendor/project documentation and current public
   price pages.
4. **Autonomous buyer constraints:** Coinbase Agentic Wallet spending-limit documentation.
5. **Actual VouchSpec willingness to pay:** none yet. No desk evidence is allowed to substitute for
   genuine unrelated settlements and repeat use.

## Live x402 market distribution

The documented, unauthenticated Coinbase catalog endpoint was paged completely:

`GET https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?type=http&limit=1000&offset=...`

At the sample time it reported **26,623 catalog items**. After selecting Base mainnet
(`eip155:8453`), the canonical Base USDC asset, numeric amounts, and de-duplicating exact
`resource + scheme + price` tuples, the analysis retained **12,360 payable entries**.

| Statistic | USD/USDC per call |
|---|---:|
| Minimum | $0.00 |
| 25th percentile | $0.003 |
| Median | $0.01 |
| 75th percentile | $0.07 |
| 90th percentile | $0.15 |
| 95th percentile | $0.30 |
| 99th percentile | $2.10 |
| Maximum | $3,208.88 |

| Price band | Entries | Share |
|---|---:|---:|
| Below $0.01 | 4,709 | 38.10% |
| $0.01 to below $0.10 | 5,102 | 41.28% |
| $0.10 to below $1.00 | 2,233 | 18.07% |
| $1.00 to below $5.00 | 228 | 1.84% |
| $5.00 to below $20.00 | 69 | 0.56% |
| $20.00 to below $50.00 | 6 | 0.05% |
| $50.00 and above | 13 | 0.11% |

Consequences:

- **79.38%** of observed Base-mainnet USDC entries were below $0.10.
- **97.45%** were below $1.00.
- Only **19 of 12,360 (0.15%)** were $20 or more.
- A $49 single call would sit far beyond the 99th percentile and would need direct willingness-to-pay
  evidence that VouchSpec does not have.

These figures describe listed supply, not transaction conversion or buyer demand. Bazaar ranking
uses distinct-buyer reach, transaction volume, recency, and metadata quality, so a launch price
that permits genuine use also helps the endpoint accumulate the objective signals used in discovery.

## Closest live agent-native price anchors

Coinbase semantic-search results at the sample time included:

| Comparable paid operation | Observed price |
|---|---:|
| Signed receipt for one agent action | $0.05 |
| Agent Skill / untrusted-content injection scan | $0.10 |
| Deterministic ephemeral verification gate | $0.10 |
| AI code review with security/performance/architecture feedback | $0.40 |
| Dependency risk audit with live advisories and recommendation | $0.50 |
| Comprehensive code/security audit | $1.00 |
| Data-freshness signed attestation | $1.00 |
| Broad 22-check web quality/security audit | $5.00 |

VouchSpec is more durable and independently verifiable than a disposable content score, but its
current deterministic static profile is narrower than a comprehensive code/security audit. That
places a defensible unvalidated starting point between **$0.10 and $0.50**, not near $49.

## Autonomous wallet constraint

Coinbase Agentic Wallet lets the human owner configure a maximum per call and a maximum per
session; agents must respect those values and cannot change them. Coinbase's documentation uses
examples such as **$0.05 maximum per call** and **$5.00 per session**, and its CLI example shows a
**$0.10 maximum payment**. These examples are not universal defaults, but they demonstrate the
expected scale of unattended agent purchases. A $49 request is likely to require a human spending
limit change and therefore conflicts with the agent-only acquisition strategy.

## Free-substitute pressure

The buyer can already obtain substantial adjacent evidence at no marginal price:

- Cisco's Apache-2.0 Agent Skill scanner provides static, YARA, behavioral, optional semantic,
  policy, CI, and SARIF paths.
- NVIDIA publishes a scan + skill card + whole-directory OMS signature trust pipeline.
- GitHub artifact attestations provide public-repository provenance under current GitHub plans.
- Tessl lists free public plugin reviews and unlimited publishing/installing on its free tier.
- Snyk and Socket both offer free developer-security tiers.

VouchSpec therefore cannot price as though it owns unique detection capability. Its paid wedge is
fresh independent issuance, exact input identity, stable canonical receipt bytes, registry-neutral
portability, isolated processing, and a live invalidation decision.

## Unit economics

The completed VouchSpec fulfillment job ran for **34 seconds**. GitHub rounds partial hosted-runner
minutes up and currently lists a standard two-core Linux runner at **$0.006/minute**, so the measured
worker compute floor is one billed minute or about **$0.006** outside included allowances.

CDP currently includes the first **1,000 facilitator transactions/month**, then charges
**$0.001/transaction**. The facilitator sponsors settlement gas. Receipt bytes are small and no
GitHub artifact upload is required.

For launch decisions, use a deliberately conservative **$0.05 variable-cost reserve per accepted
order** covering worker rounding, database/egress allocation, settlement above the free tier,
monitoring, and remedy transaction overhead. Replace the reserve with actual recorded cost after
each genuine order.

| Candidate price | Contribution after $0.05 reserve | Contribution margin | Market/autonomy assessment |
|---|---:|---:|---|
| $0.10 | $0.05 | 50% | Low-friction fallback; weak revenue per receipt |
| **$0.25** | **$0.20** | **80%** | Near Bazaar's 95th percentile; justified premium over disposable skill scan |
| $0.50 | $0.45 | 90% | Strong comparable anchor; test only after buyer evidence |
| $1.00 | $0.95 | 95% | Comprehensive-audit territory; premature for current static profile |
| $49.00 | $48.95 | 99.9% | Extreme catalog outlier; likely blocked by wallet budgets; reject |

The $0.05 reserve is a management guardrail, not an observed average. Refunded principal is a
revenue reversal rather than contribution; remedy transaction costs remain direct costs.

## Predeclared price experiment

### Phase 1 — launch at 0.25 USDC

Run until the later of 14 mainnet days and enough opportunity for three unrelated CI integrations
to encounter the paid endpoint, or until 30 genuine accepted orders arrive. Exclude owner,
controlled-wallet, testnet, demo, monitoring, refunded, reversed, and simulated transactions.

Measure:

- genuine paid validations, distinct unrelated buyer wallets, and repeat buyers;
- eligible 402 challenges and settlements without storing raw IPs or creating cross-tenant leakage;
- fulfilled, remedied, refunded, and invalidated orders;
- actual variable cost and contribution per order;
- time to signed receipt and receipt verification failures;
- repeat calls for different commits, which are the best evidence that the price fits CI use.

### Decision rules

| Observed result | Next price action |
|---|---|
| Zero genuine settlements after 14 days **and** three unrelated integrations have produced qualified paid opportunities | Test **$0.10** for the next 14-day cohort; do not call $0.25 rejected if qualified exposure was absent. |
| One or two unrelated buyers, no repeat buyer, positive contribution | Hold **$0.25** for one more cohort. |
| At least three unrelated buyers, at least one repeat buyer, positive contribution, defect-remedy rate below 5% | Test **$0.50** on the next cohort. |
| A $0.50 cohort loses more than half the settlement rate per eligible 402 challenge, without a reliability/channel explanation | Revert to **$0.25**. |
| Actual variable cost reaches or exceeds 80% of price | Stop orderability and correct cost or scope before accepting more payments. |

Do not vary price per buyer, wallet, or inferred willingness to pay. Publish one exact price at a
time so agents can cache discovery safely and the experiment remains auditable.

## What the price does not prove

- $0.25 is not validated willingness to pay.
- A settlement proves one buyer at one moment, not a market.
- Bazaar listing counts and competitor list prices do not prove conversion or revenue.
- The owner's $500 acceptance target must not be used to inflate the per-call price. The product
  must earn that revenue through genuine demand, repeat use, and later evidence-based offers.

## Sources

- Coinbase CDP Bazaar documentation and public catalog/search:
  https://docs.cdp.coinbase.com/x402/bazaar
- Coinbase Agentic Wallet FAQ and payment tools:
  https://docs.cdp.coinbase.com/agentic-wallet/mcp/faq
  https://docs.cdp.coinbase.com/agentic-wallet/cli/skills/pay-for-service
- Coinbase x402 facilitator fees and refunds:
  https://docs.cdp.coinbase.com/x402/core-concepts/facilitator
  https://docs.cdp.coinbase.com/x402/support/faq
- GitHub Actions runner pricing:
  https://docs.github.com/en/billing/reference/actions-runner-pricing
- GitHub artifact attestations:
  https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- NVIDIA Agent Skill trust pipeline:
  https://docs.nvidia.com/skills/agent-skill-trust-pipeline
- Cisco Agent Skill scanner:
  https://github.com/cisco-ai-defense/skill-scanner
- Tessl pricing:
  https://tessl.io/pricing/
- Snyk plans:
  https://snyk.io/plans/
- Socket pricing:
  https://socket.dev/pricing

## Research limits

- The Bazaar catalog is changing continuously. The counts are a timestamped full-catalog
  observation, not a permanent benchmark.
- Listed prices do not reveal settlement conversion, revenue, refund rate, buyer concentration,
  quality, uptime, or fulfillment cost.
- Semantic-search comparables are seller descriptions and prices, not independently verified
  performance claims.
- VouchSpec still has zero genuine buyers and zero genuine revenue. Only actual unrelated
  settlements and repeat use can validate or reject the launch price.
