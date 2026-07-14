# CapabilityProof standards and working-name evidence

**Research date and access date:** 2026-07-13 (America/Phoenix)
**Scope:** Public, primary-source research for a USD $0 MVP that inspects exact Agent Skills directories containing `SKILL.md`. No artifact was downloaded or executed.
**Decision use:** Scope the first implementation and decide whether `CapabilityProof` can graduate from a working name.

## Decision summary

1. **Build against the Agent Skills file format now.** It is bounded enough for deterministic, non-executing inspection: a directory must contain `SKILL.md`; the file has required YAML frontmatter and unrestricted Markdown instructions; optional directories may include executable scripts. Structural conformance is therefore useful but cannot establish safety or effectiveness.
2. **Do not make the official `skills-ref` library a production dependency.** The official specification points to it for validation, but its own repository says it is for demonstration and not production. Implement the needed checks locally, record the upstream rule/source used, and maintain parity fixtures.
3. **Represent trigger and task evaluations in the receipt schema, but do not claim or run them in the zero-cost, non-executing MVP.** Official evaluation guidance is behavioral and model/client/environment dependent. Use an explicit `not_evaluated` state rather than treating structural validity as an evaluation pass.
4. **Treat MCP Registry, ARD, A2A, and x402 as later adapters, not the core data model.** The MCP Registry currently covers MCP servers and is in preview; ARD is available but remains v0.9 Draft; A2A discovers remote agents rather than `SKILL.md` packages; CDP Bazaar discovery is active but tied to x402 settlement and an evolving API.
5. **Keep `CapabilityProof` provisional and prefer renaming before public launch.** `SkillProof` already presents a tested Agent Skills registry, reports, validator, monitoring-style retesting, and paid products. An unrelated agent project also already uses the exact identifier `CapabilityProof` for evidence supporting a claimed agent capability. These are not legal conclusions, but they create immediate category, search, and semantic-confusion risk.

## Evidence-strength convention

- **High:** canonical specification, official project documentation/repository, or a product operator's own page for the limited fact that the product and its stated positioning exist.
- **Medium:** official provider documentation about a provider-operated, evolving service; reliable for the documented interface, not for independent performance or adoption.
- **Low / inference:** product conclusion drawn from the cited facts, or a limited scan that cannot establish absence, ownership, trademark rights, or market adoption.

## 1. Agent Skills: specification, validation, and evaluations

### Current primary-source evidence

| Fact | Direct primary source (accessed 2026-07-13) | Strength | Actionable implication |
|---|---|---|---|
| An Agent Skill is a directory containing at least `SKILL.md`; `scripts/`, `references/`, and `assets/` are optional. The specification describes `scripts/` as executable code. | [Agent Skills specification](https://agentskills.io/specification) | High | The MVP input boundary can be one exact directory snapshot. Inventory every file and hash bytes without importing or executing scripts. |
| `SKILL.md` requires YAML frontmatter plus Markdown. `name` and `description` are required; `license`, `compatibility`, `metadata`, and `allowed-tools` are optional. `allowed-tools` is explicitly experimental, and the Markdown body has no format restrictions. | [Agent Skills specification](https://agentskills.io/specification) | High | A conforming file may disclose neither complete permissions nor behavior. Report declared fields separately from inferred observations; never translate conformance into “safe,” “approved,” or “effective.” |
| The official documentation recommends `skills-ref validate`, which checks frontmatter and naming conventions. | [Agent Skills specification — Validation](https://agentskills.io/specification#validation) | High | A Level-1/structural result should be limited to deterministic format rules and should enumerate each rule checked. |
| The `skills-ref` repository calls itself a reference library but explicitly says it is for demonstration only and is not meant for production. | [Official `agentskills/agentskills` repository — `skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref) | High | Reimplement the narrow validator or vendor a reviewed, pinned snapshot only if later justified. Record the upstream source revision in test fixtures; do not silently track `main`. |
| Official trigger guidance says `description` is the primary activation mechanism; it recommends realistic positive and near-miss negative queries, repeated runs because model behavior is nondeterministic, and train/validation separation to reduce overfitting. | [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) | High source; non-normative guidance | A trigger result must identify client, model, query set/version, run count, threshold, and held-out results. It cannot be a universal property of the artifact. |
| Official output-evaluation guidance recommends realistic cases, clean contexts, with-skill versus without-skill (or prior-version) baselines, timing/token capture, evidence-backed assertions, aggregation, and human review for qualities that assertions miss. | [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills) | High source; non-normative guidance | A task-evaluation result must preserve environment and baseline provenance. Deterministic checks and model-judge/human judgments must be distinguishable in the receipt. |

### Product interpretation

**Fact:** The normative-looking file-format checks and the behavioral evaluation guidance solve different problems. The former can determine whether a snapshot follows selected format rules; the latter estimates behavior under named test conditions.

**Inference:** The zero-cost MVP should expose these separate states rather than one score:

- `format_validation`: `pass | fail | indeterminate`, with rule IDs, source URL, source revision/date, and findings.
- `artifact_identity`: source locator, resolved commit or immutable archive identity when available, canonical file manifest, and digest.
- `declared_requirements`: exact `compatibility`, `allowed-tools`, license text/reference, and other declared metadata; absence is `not_declared`, not `none`.
- `static_observations`: file types, references, scripts, URLs, likely commands, and unresolved/dynamic references, each tied to evidence locations. Do not execute.
- `trigger_evaluation` and `task_evaluation`: `not_evaluated` in the initial MVP, with reserved fields for harness, model/client, corpus digest, baseline, repetitions, assertions, evidence, cost, and timestamp.

**Scope decision:** Initial receipts should prove only what a deterministic static pass observed about one exact byte snapshot. Behavioral language should read “not evaluated” until an isolated, funded evaluation system exists.

## 2. MCP Registry: downstream-aggregator positioning

### Current primary-source evidence

| Fact | Direct primary source (accessed 2026-07-13) | Strength | Actionable implication |
|---|---|---|---|
| The official MCP Registry describes itself as the centralized metadata repository for publicly accessible MCP servers and says it is currently in preview, with possible breaking changes or data resets before general availability. | [The MCP Registry — About](https://modelcontextprotocol.io/registry/about) | High | Do not use the MCP Registry as the source of Agent Skills for this MVP, and do not hard-code a preview API into the core receipt schema. |
| The registry says it is intended primarily for **downstream aggregators**; its metadata is deliberately unopinionated, while aggregators may add curation or metadata such as ratings. | [MCP Registry — Relationship with Downstream Aggregators](https://modelcontextprotocol.io/registry/about#relationship-with-downstream-aggregators) | High | If CapabilityProof later covers MCP servers, position it as an evidence-enriching downstream aggregator. Use “subregistry” only as informal shorthand; the current official term is “downstream aggregator” (and, separately, “other MCP registry”). |
| The registry provides an OpenAPI interface that other registries can implement, and says MCP host applications should consume downstream registries rather than the official registry directly. | [MCP Registry — Other Registries and Host Applications](https://modelcontextprotocol.io/registry/about#relationship-with-other-mcp-registries) | High | A later MCP-facing catalog can implement the official interface at its boundary while keeping CapabilityProof-specific evidence in extensions or linked receipt documents. |
| Namespace authentication ties a publisher to a GitHub account/domain, but the registry delegates code security scanning to package registries and downstream aggregators. | [MCP Registry — Trust and Security](https://modelcontextprotocol.io/registry/about#trust-and-security) | High | Treat namespace ownership as provenance evidence, not a safety result. Independent, artifact-version evidence remains a legitimate downstream role. |

**Inference:** MCP Registry positioning validates the broader business thesis but not the first ingestion scope. Add MCP only after the `SKILL.md` receipt model works and after defining a separate live-server threat model; do not imply that an MCP namespace proves server behavior.

## 3. Agentic Resource Discovery (ARD): verified status and fit

### Current primary-source evidence

| Fact | Direct primary source (accessed 2026-07-13) | Strength | Actionable implication |
|---|---|---|---|
| Google announced ARD on 2026-06-17 as an open specification for publishing, discovering, and verifying metadata for capabilities across the web. The announcement describes domain-hosted catalogs, federated registries, `ai-catalog.json`, and resources including MCP servers, A2A agents, OpenAPI tools, and nested catalogs. | [Google Developers Blog — ARD announcement](https://developers.googleblog.com/announcing-the-agentic-resource-discovery-specification/) | High | The attached business brief's ARD claim is verified. ARD is a plausible future discovery input/output adapter for skills and services. |
| The canonical ARD repository labels its status **v0.9 (Draft)** and says the specification is open and evolving. Its GitHub page shows no published releases at the access date. | [Canonical `ards-project/ard-spec` repository](https://github.com/ards-project/ard-spec) | High for declared status; current snapshot | Do not base receipt semantics on ARD v0.9. Version-gate any adapter and pin the exact schema/revision used. |
| The official ARD site says ARD operates before invocation, is not an execution runtime or central catalog, and expects multiple discovery services with different trust, ranking, and access policies. | [AgenticResourceDiscovery.org](https://agenticresourcediscovery.org/) | High | CapabilityProof's evidence/ranking role is compatible with ARD's architecture; ARD discovery metadata must remain distinct from independently observed evidence. |
| The publication guide uses `https://<domain>/.well-known/ai-catalog.json` and warns that publishing makes a resource discoverable but does not guarantee that a discovery service will index it. | [ARD — How to publish](https://agenticresourcediscovery.org/how_to_publish/) | High | When a public domain exists, generate an optional catalog from canonical product metadata. Do not count publication or indexing as customer demand or verification. |

**Inference:** ARD is relevant but not mature enough to be an MVP dependency. The practical order is: canonical CapabilityProof receipt first, optional ARD import/export adapter later, then empirical interoperability tests against named ARD implementations.

## 4. A2A discovery: limited relevance

### Current primary-source evidence

| Fact | Direct primary source (accessed 2026-07-13) | Strength | Actionable implication |
|---|---|---|---|
| A2A standardizes remote-agent self-description through an Agent Card. Public agents may publish it at `/.well-known/agent-card.json`. Its `AgentSkill` objects describe remote-agent tasks, inputs, outputs, and examples. | [A2A Protocol — Agent Discovery](https://a2a-protocol.org/latest/topics/agent-discovery/) | High | Do not conflate an A2A `AgentSkill` description with an Agent Skills directory containing `SKILL.md`; they are different artifact/protocol layers. |
| A2A documents curated registries as a discovery strategy but says the current specification does not prescribe a standard API for those registries. | [A2A Protocol — Curated Registries](https://a2a-protocol.org/latest/topics/agent-discovery/#2-curated-registries-catalog-based-discovery) | High | A2A provides no required registry integration for the initial product. |

**Inference:** Defer A2A. Publish an Agent Card only if CapabilityProof later becomes a remotely delegable A2A agent with task lifecycle semantics. A REST or MCP verification endpoint alone does not require A2A for the exact-`SKILL.md` MVP.

## 5. x402 discovery: current primary-source-verified state

### Current primary-source evidence

| Fact | Direct primary source (accessed 2026-07-13) | Strength | Actionable implication |
|---|---|---|---|
| Coinbase documents CDP Bazaar as discovery for x402-enabled services cataloged through the CDP Facilitator, with a paginated HTTP catalog, hybrid/semantic search, and an MCP interface. The page labels Bazaar under active development and warns that the API surface may evolve. | [Coinbase Developer Documentation — x402 Bazaar](https://docs.cdp.coinbase.com/x402/bazaar) | Medium (official operator documentation) | x402 discovery is real and machine-readable, but keep it outside the core receipt model and behind a versioned adapter. |
| The documentation calls x402 v2 current and v1 deprecated. In v2, sellers declare Bazaar discovery metadata through an official extension; CDP indexes it after a successful settlement, not after verification alone. | [x402 Bazaar — How it works](https://docs.cdp.coinbase.com/x402/bazaar#how-it-works) | Medium | A seller cannot treat a static listing file as sufficient. A later integration needs a real paid route, v2 metadata, and a successful CDP settlement. |
| The documented seller flow requires CDP Facilitator integration and CDP API keys on the resource server. The read-only discovery endpoints do not require keys. | [x402 Bazaar — Seller integration and discovery endpoints](https://docs.cdp.coinbase.com/x402/bazaar#seller-integration) | Medium | Under the present USD $0/no-external-account constraint, do not create an x402 seller integration. Public discovery can be researched without onboarding, but listing/payment validation is a later owner-authorized step. |
| Search ranking combines retrieval relevance with facilitator-observed buyer reach, transaction volume, recency, and declared metadata quality; weights may change. | [x402 Bazaar — Quality ranking](https://docs.cdp.coinbase.com/x402/bazaar#quality-ranking) | Medium | Bazaar activity/ranking is not independent artifact verification. If ingested later, label it as provider-observed market/activity metadata, never CapabilityProof evidence. |

**Inference:** Reserve a payment/discovery adapter boundary, but omit wallets, settlements, paid endpoints, and Bazaar listing work from the initial MVP. Re-evaluate only after a useful free verification response exists and the owner separately authorizes accounts and financial rails.

## 6. Working-name evidence: `CapabilityProof`

This is a limited obvious-conflict scan, not a trademark, corporate-name, domain, or legal clearance search.

| Current public use | Direct primary page (accessed 2026-07-13) | Evidence and strength | Naming implication |
|---|---|---|---|
| **SkillProof** | [skillproof.dev](https://skillproof.dev/) | High for existence and operator-stated positioning. The site presents a tested directory for Claude/Agent Skills, test reports and scores, a `SKILL.md` validator, install guidance, paid bundles/subscription, and retesting. Its performance, counts, and independence were not audited here. | **High practical conflict.** It occupies the same initial artifact category and the same “noun + Proof” naming pattern. `CapabilityProof` could be mistaken for a broader edition, feature, or competitor clone even without exact spelling identity. |
| **Squaremind `CapabilityProof` identifier** | [Go package documentation for `square-mind/squaremind/pkg/identity`](https://pkg.go.dev/github.com/square-mind/squaremind/pkg/identity#CapabilityProof) | High for exact public technical use. The published type is named `CapabilityProof` and represents benchmark, peer-attestation, or task-history evidence for a claimed agent capability. It is not presented as a standalone product brand. | **Moderate semantic distinctiveness risk.** The exact compound already arises naturally in agent trust code, supporting the inference that the name is descriptive and hard to own conceptually. |
| **ProofPath** | [proofpath.com](https://proofpath.com/) | High for existence and operator-stated positioning. The beta product describes capability verification from work evidence for people/workforces and advertises API and MCP integration. | **Low-to-moderate adjacent naming risk.** The market and subject differ, but “proof” plus “capability verification” is already an active product theme. |

### Name decision

**Fact:** The closest obvious product, SkillProof, is already in the exact tested-Agent-Skills category. The exact `CapabilityProof` compound also has prior public technical use in an agent identity project.

**Inference / recommendation:** Keep `CapabilityProof` only as an internal codename and choose a more distinctive public name before publishing a domain, package, registry entry, badge, or receipt namespace. At minimum, a later human-approved naming step should include professional trademark/legal review, relevant jurisdiction databases, corporate-name checks, package/registry handles, social handles, and domain ownership. This memo makes no availability or legal-clearance claim.

## 7. Implementation scope decided by this evidence

### Build in the USD $0 initial MVP

- Exact local directory or already-resolved snapshot input; never execute submitted content.
- Canonical file inventory and content digests.
- Deterministic `SKILL.md` parsing and structural findings tied to cited Agent Skills rules.
- Declared-versus-observed separation and explicit unknown/not-declared/not-evaluated states.
- A machine-readable receipt whose claims identify artifact digest, checker version, rule source, timestamp, evidence locations, and limitations.
- Regression fixtures that compare local validation behavior with documented examples and, optionally in development only, a pinned `skills-ref` snapshot.

### Reserve in the schema but do not perform

- Trigger evaluations and task-performance evaluations.
- Dynamic execution, sandbox observations, live network checks, or universal permission claims.
- Signatures whose key custody and verification policy have not yet been designed.

### Defer as adapters

- MCP Registry ingestion/downstream-registry compatibility until the product covers MCP servers.
- ARD v0.9 import/export until the core receipt is stable; pin any later adapter revision.
- A2A Agent Card until CapabilityProof is genuinely an A2A task-serving agent.
- x402/Bazaar until account, wallet, payment, and successful-settlement work is separately authorized and funded.

## Bottom line

The standards evidence supports a narrow, static, exact-version `SKILL.md` verifier now. It does **not** support collapsing conformance, provenance, static observations, trigger behavior, task performance, or safety into one badge or score. Discovery protocols reinforce the long-term aggregator thesis but are all later boundaries for this MVP. The working name should remain provisional because SkillProof is already visibly established in the same product niche.
