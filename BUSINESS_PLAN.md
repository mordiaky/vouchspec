# CapabilityProof living business plan

## Executive summary

CapabilityProof is an independent, machine-readable evidence layer that agents consult
before acquiring or using an external Agent Skill. The initial scope is intentionally
limited to exact versions of directories containing `SKILL.md`.

## Target customer

Initial customers are Agent Skill publishers and small teams that operate coding or
document agents and need a reproducible installation gate. Autonomous agents are an API
interface and future per-call buyer, not the only early revenue source.

## Problem

Discovery and format validation do not establish provenance, requested permissions,
static risk indicators, compatibility, observed behavior, or task performance. Operators
need evidence tied to exact bytes rather than promotional descriptions.

## Existing alternatives

Official registries, specification validators, security scanners, and internal manual
review are upstream or partial alternatives. Current facts and prices are recorded in
`research/market-evidence.md`; no competitive claim is considered verified until cited there.

## Initial offer

Produce an exact-version Capability Receipt containing structural validation, SHA-256
provenance, normalized metadata, referenced-file closure, declared/runtime-relevant
requirements inferred from text, and transparent static findings. The initial product
does **not** execute the artifact or guarantee safety.

## Deliverables and exclusions

Deliverables: canonical JSON receipt, concise human summary, machine-readable findings,
and a reproducible command/API call. Excluded from the first offer: sandbox execution,
malware guarantees, legal advice, runtime certification, and task-performance benchmarking.

## Provisional pricing hypothesis

- Free: basic search and cached public metadata.
- USD $19 one-time: publisher-funded fresh Level 1–3 release receipt.
- USD $99 one-time pilot: small-team policy pack plus up to five fresh Level 1–3 receipts.

Pricing is a test hypothesis, not evidence of market willingness to pay.

## Acquisition

Start with a public, truthful sample receipt and a free verify-before-install skill.
Publisher CI and targeted permission-based outreach follow only after the sample and
fulfillment path pass QA. No bulk outreach or pay-to-rank.

## Sales and fulfillment

A customer submits a public repository URL or archive plus desired evidence level. The
system resolves immutable bytes, quotes the exact scope/price, produces the receipt,
runs QA, and returns JSON. Any unsupported or unsafe-to-process input is rejected without
execution.

## Tools and direct costs

The evidence MVP uses local Python and Git with no paid dependency. Direct cost is
currently USD $0 plus unmetered host/model time; paid infrastructure is deferred until
external usage requires it.

## Contribution margin estimate

Unknown until measured. The working hypothesis is positive margin for cached Level 1–3
receipts because validation is deterministic and non-executing. Time and compute will be
measured before accepting payment.

## Compliance and data handling

Only public artifacts or customer-authorized inputs are accepted. Store minimal request
metadata. Never execute submitted code on the host, never collect credentials, respect
licenses, bind claims to digests, publish limitations, and separate sponsorship.

## Validation evidence

Owner-provided business thesis is recorded as unsourced strategic input. Current external
evidence belongs in `research/`; executable product evidence belongs in `receipts/` and
test logs.

## Assumptions

See `ASSUMPTIONS.md`.

## 14-day execution plan

1. Produce and verify the real-artifact evidence MVP.
2. Publish the schema, methodology, sample receipt, and free local verifier.
3. Identify ten relevant publishers/teams and test the exact paid-release offer.
4. Measure qualified engagement and willingness to submit an artifact or pay.

## 30-day operating plan

Iterate only from observed use: improve parsers, add CI, add safe fetching, and add
payment after a real buyer path exists. Defer sandboxing and broad registries until the
Level 1–3 wedge converts.

## Pivot criteria

Modify or stop if 25 qualified publisher/team contacts produce no artifact submissions or
specific product feedback, 50 produce no paid-pilot signal, the evidence duplicates a
free incumbent without a defensible workflow advantage, or safe fulfillment cannot fit
the budget.

## First three-customer strategy

Sell one narrow release receipt to skill publishers and one small-team policy pilot to
agent operators. Target three unrelated buyers; never simulate revenue.

## Automation path

Local deterministic inspector → hosted queued validator → publisher CI → cached search →
restricted sandbox observation → performance evaluation → continuous monitoring.

