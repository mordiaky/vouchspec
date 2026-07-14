# CapabilityProof living business plan

## Executive summary

`CapabilityProof` is an internal codename for an independent, registry-neutral evidence
layer that agents and teams can consult before acquiring or activating an Agent Skill. The
initial artifact scope is one exact directory containing `SKILL.md`.

The commercial wedge is a **portable exact-byte policy receipt**, not another scanner,
directory, score, badge, or manual security service.

## Customer and problem

The first hypothesized buyers are Agent Skill publishers and small teams operating coding
or document agents. Discovery and format validation alone do not establish exact-byte
identity, source provenance, inferred requirements, static risk evidence, compatibility,
runtime behavior, or task performance. Current primary-source research supports the
security/provenance problem but supplies no direct willingness-to-pay evidence.

## Competition and differentiation

Official validation, GitHub release workflows, Cisco, Snyk, NVIDIA SkillSpector, skills.sh,
Tessl, SkillProof, ClawHub, Socket, GitHub attestations, and OpenSSF provide strong free or
bundled substitutes. Evidence and pricing are recorded in
`research/market-and-competitor-evidence.md` and
`research/standards-and-name-evidence.md`.

The testable gap is a stable, independent, registry-neutral record containing a complete
file inventory, exact digests, source/blob evidence, declared-versus-inferred requirements,
deterministic rule findings, coverage, methodology/policy versions, limitations, expiry,
and machine policy semantics.

## Current product evidence

The local v0.1 prototype accepts a controlled public or synthetic directory. It creates an
immutable in-memory byte snapshot, validates selected Agent Skills rules, closes local
references, extracts requirements/dependencies, runs transparent static rules, and emits a
strict-schema receipt. Git mode compares every file with its raw blob at the recorded
commit. It never fetches or executes artifact content.

The receipt uses a documented deterministic JSON profile, not RFC 8785 JCS. It is explicitly
digest-only and unauthenticated. The loopback HTTP, MCP stdio, CI action, and verify-before-
install skill are local developer integrations only.

## Deliverables and exclusions

Proposed deliverables are a JSON receipt, short human summary, reproducible invocation,
and exact policy decision inputs. Exclusions: sandbox execution, malware guarantees,
publisher identity, legal advice, penetration testing, runtime certification, task/trigger
evaluation, custom consulting, calls, and unlimited support.

## Pricing experiments, not claims

- USD $19 one-time: retained only as a full-price experiment for a portable public release
  receipt. Desk research rejected a generic paid scan as the default offer.
- USD $99 one-time: retained only as a full-price policy-ready small-team experiment after
  private/authorized external intake is safe.

No price is validated. Only settled purchases by unaffiliated buyers count.

## Acquisition experiment

After a distinctive public name and external-safe delivery path exist, expose a truthful
self-service page and run capped qualified-visitor tests:

- Publisher receipt succeeds at 2 or more full-price USD $19 purchases from 25 qualified
  publisher page viewers. Zero purchases at 25 rejects that offer; fewer than 25 views are
  inconclusive.
- Team policy pack succeeds at 1 or more full-price USD $99 purchase from 15 qualified team
  page viewers. Zero at 15 rejects that offer; fewer than 15 views are inconclusive.

Clicks, replies, waitlists, GitHub stars, security-study prevalence, and vendor launches do
not count as payment evidence.

## Fulfillment boundary

Current fulfillment is an audited local proof for controlled public/synthetic artifacts,
not a customer service. An external service must accept one bounded immutable raw ZIP byte
stream, parse it in a killable isolated no-egress worker, authenticate and authorize every
operation, sign JCS payloads with an isolated key, and support key/receipt invalidation.
Remote paths, URLs, repositories, base64 artifacts, and mutable fetch targets remain banned.

## Economics and compliance

Spend is USD $0 and measured revenue is USD $0. Contribution margin is unknown until a real
delivery occurs. No customer, payment, contract, account, recurring service, or financial
rail exists. Only public/synthetic inputs have been used; artifact code was never executed;
the sample receipt redistributes no artifact bytes and makes no license interpretation.

## Stop and pivot rules

Reject the respective offer at 0/25 qualified publisher views or 0/15 qualified team views.
Stop external launch if any P0/P1 security finding remains, safe fulfillment cannot fit the
budget, or the portable-policy wedge is indistinguishable from a free incumbent workflow.

## Automation path

Local deterministic evidence -> immutable upload intake -> isolated worker -> signed receipt
verification -> publisher CI -> policy consumption -> cached public search. Sandboxed runtime
observation, task evaluation, continuous monitoring, ARD/MCP Registry adapters, and x402 are
deferred until demand and safety evidence justify them.
