# VouchSpec living business plan

## Executive summary

VouchSpec (provisional beta name; no formal legal/trademark clearance) is an independent,
registry-neutral evidence layer that machines can consult before acquiring or activating an
Agent Skill. The commercial wedge is a portable exact-byte receipt, not a generic scanner,
badge, directory, or manual security service.

The launch sequence is deliberately constrained: prove usage first with a read-only index
of selected public artifacts; add bounded public-repository validation only after its worker
profile passes; defer private and arbitrary inputs until demand and revenue justify them.

## Customer and problem

The first hypothesized users are Agent Skill publishers and automated agent/tooling systems.
Discovery and format validation alone do not establish exact-byte identity, immutable source
coordinates, inferred requirements, static findings, test scope, or lifecycle. Current
research supports the provenance/security problem but not willingness to pay.

## Product stages

### Stage A — public artifact index (current)

- Deliberately select public Agent Skills.
- Resolve a full immutable commit and exact subdirectory.
- Publish signed machine-readable receipts and a root-signed lifecycle feed.
- Expose read-only REST and MCP retrieval.
- Accept no uploads, private repositories, customer-confidential content, or artifact code
  execution.

The initial local catalog contains 25 skills across 12 GitHub repository owners. Nineteen pass the current
structural profile; six remain indexed with explicit structural failures. Every receipt is
signed, digest-bound, and labeled by the evidence actually produced.

### Stage B — public repository validation (later)

Accept only an allowlisted public host, full immutable commit, and explicit skill path;
enforce byte/file/depth/time bounds; freeze and hash bytes before analysis; run in an
isolated worker; return a signed receipt. Do not execute artifact scripts under this static
profile.

### Stage C — private and arbitrary inputs (deferred)

Private storage, tenant isolation, customer authentication, upload/deletion policies,
expanded legal terms, and incident response are justified only by external demand and
revenue. Stage C is not a dependency of Stage A or B.

## Differentiation and claims

Receipts contain source/blob evidence, a complete bounded file inventory, exact digest,
transparent issue counts, coverage, environment, method/policy versions, issuance/expiry,
explicit limitations, and lifecycle. Labels are factual: `DIGEST_PINNED`,
`STRUCTURE_VALIDATED`, `STATIC_INSPECTION_COMPLETED`, `INDEPENDENT_STATIC_SCAN`, and only
later when evidenced, `PUBLISHER_CI_ATTESTED`, `SANDBOX_BEHAVIOR_OBSERVED`, or
`TASK_EVALUATED`. VouchSpec never emits a generic `VERIFIED` status.

DSSE v1.0.2 authenticates the exact receipt bytes with Ed25519. The inner deterministic
JSON format remains explicitly non-JCS; cryptographic verification does not reconstruct
JSON. A separate recovery/root key signs receipt and issuer-key lifecycle state.

## Pricing hypotheses

- Public search: free.
- Existing receipt retrieval: free or near-free.
- Receipt comparison: USD $0.005–$0.01.
- Fresh public static validation plus signed receipt: USD $49.00 initial hypothesis.
- Signed receipt issuance: included in the first paid fresh-validation product.
- Continuous artifact monitoring: USD $2–$10 monthly.
- Independent sandbox analysis: later, priced from measured compute cost.

These are machine-transaction experiments, not validated prices. Payment never changes
findings or evidence ranking. A machine-readable quote precedes payment; a settlement or
signed paid-job token may authorize one job without a conventional customer account.

## External alpha acceptance

The commercial goal passes only when every one of the 30 current tests in
`GOAL_EVIDENCE.md` passes. Among them: three retained integrations under unrelated external
owners; 100 legitimate machine requests from ten sources, including 20 repeats from five;
three unrelated settled buyers; at least USD $500 settled gross; one repeat paid buyer;
positive fully costed contribution margin; and 14 autonomous days after first settlement.
Routine jobs require no owner call, meeting, demo, review, or manual delivery. Owned demo,
operator CI, monitoring, tests, related parties, and synthetic or reversed payments do not
count.

## Economics, compliance, and stop rules

Spend and revenue are both USD $0. No customer, contract, payment rail, recurring service,
or delivery obligation exists. Only deliberately selected public artifacts have been
processed. No original artifact file or executable payload is redistributed, but signed
receipts contain bounded artifact-derived metadata and redacted evidence excerpts.

Stop public alpha for any unresolved P0/P1 security defect, forged/stale lifecycle behavior,
artifact-content intake route, false evidence label, or inability to keep routine
fulfillment autonomous. Reject a price/offer only from real machine transaction evidence,
not clicks, stars, waitlists, or simulated payments.
