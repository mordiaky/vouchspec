# CapabilityProof market, competitor, and buyer evidence

**Research date / access date:** 2026-07-13
**Scope:** exact-version Level 1-3 structural, provenance, requirement/permission,
and static-risk evidence for Agent Skills (`SKILL.md` packages); initial buyers are
publishers and small agent teams.
**Evidence rule:** a vendor page proves what that vendor offers or claims, not that
customers buy it or that its scanner is accurate. Prices below are public list prices
in USD as displayed on the access date. "No public price" means none was found on the
reviewed official page; it does not mean free.

## Decision

Public evidence strongly validates the **problem**, but it does not validate either
willingness-to-pay hypothesis.

| Hypothesis | Decision from desk research | Why | Confidence |
|---|---|---|---|
| **USD $19 publisher-funded Level 1-3 public release receipt** | **Reject as the default offer in its current "one more scan" framing. Retain only as a full-price experiment for a portable, independent, exact-byte release record.** | Publishers can obtain specification validation, several skill-native static scanners, registry security ratings, and even an independent install/trigger/task test for $0. NVIDIA also publishes an open scanning + skill-card + whole-directory signing pipeline. No reviewed primary source shows a publisher paying per release for a receipt. | **High** on competitive pressure; **low** on willingness to pay because there is no transaction evidence. |
| **USD $99 small-team pilot for up to five receipts** | **Do not accept as a demand claim. Retain $99 as a reasonable test price only if the pilot is a policy-ready decision pack, supports private/authorized inputs, and is registry-neutral.** | Tessl lists a broader Team plan at $100/month, while Snyk and Socket list adjacent team security plans from $25/developer/month. Those are price anchors, not proof that a small team will buy five CapabilityProof receipts. Public-only scans would be too easy to substitute. | **High** on public prices; **low** on segment-specific willingness to pay. |

**Research stopping condition:** reached. There is enough evidence to reject both
prices as *validated demand claims*. There is also enough evidence to justify one
zero-upfront-cost, full-price transaction test. Do not infer demand from waitlists,
clicks, replies, vendor launches, GitHub stars, or security-study prevalence.

## What the market already provides

### Closest direct and partial substitutes

| Provider / product | Observed offer | Public price | Overlap with CapabilityProof | Remaining gap or differentiation opportunity | Evidence type / confidence |
|---|---|---:|---|---|---|
| [Agent Skills specification and `skills-ref`](https://agentskills.io/specification) | The official specification defines required frontmatter and optional `license`, `compatibility`, `metadata`, and experimental `allowed-tools`. `skills-ref validate` checks frontmatter and naming conventions. The reference repository is [Apache-2.0](https://github.com/agentskills/agentskills). | **$0** to use the open-source reference implementation; no hosted verification product is offered on these pages. | Most of Level 1. | It does not establish publisher identity, immutable provenance, file closure, inferred requirements, or static-risk evidence. Because permission-related fields are optional/experimental, CapabilityProof must label its output as **declared** or **inferred requirements**, not permissions actually enforced at runtime. | **Fact / High** (official specification and repository). |
| [GitHub CLI `gh skill publish`](https://cli.github.com/manual/gh_skill_publish) and [`gh skill search`](https://cli.github.com/manual/gh_skill_search) | GitHub validates spec fields, can create a version-tagged GitHub release, and searches public repositories for `SKILL.md` files with JSON output. | **No separate public price stated** in the CLI manuals. | Level 1, discovery, and a release/version workflow. | The documented publish checks do not perform skill-native static risk analysis, permission inference, or issue a portable evidence receipt tied to the complete directory digest. | **Fact / High** (official GitHub CLI manual). |
| [Cisco AI Defense Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner) | Apache-2.0 scanner for Agent Skills. It combines static/YARA rules, behavioral data-flow analysis, optional LLM and cloud analyzers, policies, CI/pre-commit support, and terminal/JSON/SARIF/HTML output. Cisco explicitly calls it best-effort and says a clean result is not a guarantee. | **$0** for the open-source core. Optional model/cloud services can create external costs. [Cisco AI Defense](https://www.cisco.com/site/us/en/products/security/ai-defense/index.html) is request-a-demo with no reviewed public list price. | A large part of Level 3, plus policy and CI workflows. | CapabilityProof could add a stable independent record, exact-byte inventory/provenance, canonical output, methodology/version/expiry, and cross-scanner evidence. Detection rules alone are not a moat. | **Fact / High** (official Cisco repository and product page). |
| [Snyk Agent Scan](https://github.com/snyk/agent-scan) | Apache-2.0 CLI discovers and scans installed agent components, including skills, for prompt injection, malware payloads, untrusted content, credential handling, and secrets. JSON output is explicitly experimental. Skill content is sent to Snyk for API analysis; large-scale registry use requires a designated API and permission. | No separate Agent Scan fee is stated. A Snyk token/account is required. [Snyk platform plans](https://snyk.io/plans/) list **Free $0**, **Team from $25/month per contributing developer**, **Ignite from $1,260/year per contributing developer**, and Enterprise contact-sales. The page does not establish which Agent Security/Evo capabilities are included in those tiers. | Level 3 and local/team inventory. | Experimental output creates an opening for a stable schema. Snyk's terms make its standard API unsuitable as an unapproved wholesale backend. CapabilityProof cannot claim independence if it merely republishes a vendor score. | **Fact / High** on features/prices; **Inference / Medium** on the stable-schema opportunity. |
| [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) and [NVIDIA-Verified Agent Skills trust pipeline](https://docs.nvidia.com/skills/agent-skill-trust-pipeline) | Apache-2.0, non-executing static scanner with optional LLM analysis, dependency/CVE checks, permission mismatch rules, and JSON/Markdown/SARIF reports. NVIDIA's release process combines a scan, skill card, evaluation artifacts, and a detached OMS signature covering the whole directory; [consumers can verify the directory signature](https://docs.nvidia.com/skills/signing-agent-skills). | **$0** for the open-source scanner, documentation, and public catalog. Optional hosted LLM calls may cost money. | Levels 1-3, permission evidence, provenance/integrity, report artifacts, and a signed release gate. This is the nearest technical substitute. | NVIDIA verifies NVIDIA-owned releases; it is not an independent, registry-neutral service for arbitrary publishers. CapabilityProof would need to win on third-party independence, canonical exact-byte receipts, reproducibility, and policy consumption—not on having another risk score. | **Fact / High**; differentiation statement is **Inference / High**. |
| [Vercel skills.sh security audits](https://vercel.com/changelog/automated-security-audits-now-available-for-skills-sh) | skills.sh displays public security audits from Gen, Socket, and Snyk. As of 2026-02-17, Vercel said the integration covered 60,000+ skills; malicious skills are hidden from search/leaderboards, and the `skills` CLI shows audit results before install. | **No separate public price stated** for browsing or the audit display on the reviewed page. | Public discovery, third-party ratings, and an install-time risk signal. | The cited page does not document a portable signed receipt, canonical whole-directory digest, stable public API contract, detailed permission manifest, or reproducibility guarantee. Verify these gaps before claiming them in marketing. | **Fact / High** on the offer; **Unknown / Low** on undocumented gaps. |
| [Tessl Registry with Snyk scores](https://tessl.io/blog/the-tessl-registry-now-has-security-scores-powered-by-snyk/) | Every submitted public skill is sent to Snyk's Batch Skill Analysis API; the registry shows security, quality, and impact signals, warns at install, and installs the exact version associated with the scan. Public best-practice reviews and publish/install are included in its free tier. | [Free **$0/month** with 1,000 credits; Team **$100/month** with 5,000 credits; Enterprise **custom**](https://tessl.io/pricing/). The price page says public reviews and publishing/installing are free. Enterprise adds install/publish policies, audit logs, inventory, and analytics. | Levels 1-3, exact-version install, security signal, performance evaluation, and team governance. This is the strongest registry/team substitute. | CapabilityProof may still differentiate as an independent portable decision record usable outside Tessl, especially for private or mixed-source artifacts. A public-only five-scan pack is not enough differentiation. | **Fact / High**; portability opportunity is **Inference / Medium**. |
| [SkillProof](https://skillproof.dev/) | Independent directory that installs skills, checks triggering, runs real tasks, compares against a no-skill baseline, publishes verdicts, and offers a [browser-only free `SKILL.md` validator](https://skillproof.dev/tools/skill-validator). For authors, [a full test and permanent listing are $0](https://skillproof.dev/submit). | Author test/listing **$0**; user Pro **$19.90/month**; role packs **$10 one-time**; publisher featured placement **$50-$150/month**. | Independent third-party testing beyond Level 3, including install/trigger/outcome evidence. It directly undercuts a generic $19 publisher review. | The reviewed pages do not document exact whole-directory hashing, signed canonical JSON, stable machine API, permission manifests, or reproducibility. SkillProof monetizes users and placement rather than verdicts, which is an important alternative business model. | **Fact / High** on offer/prices; **Unknown / Low** on undocumented machine/provenance features. |
| [OpenClaw / ClawHub](https://github.com/openclaw/clawhub) | Public versioned skill registry with CLI-friendly API, pinned installs, moderation, and security analysis. [OpenClaw docs](https://github.com/openclaw/openclaw/blob/main/docs/tools/skills.md) say skill pages expose VirusTotal, ClawScan, and static-analysis states before install. [ClawHub's format docs](https://github.com/openclaw/clawhub/blob/main/docs/skill-format.md) say declared environment/binary requirements are compared with observed content and that ClawHub does not support paid skills. | No separate public registry price found; repository is MIT-licensed; paid skills are explicitly unsupported. | Versioning/pinning, requirements declarations, risk scans, discovery, and machine access for the OpenClaw ecosystem. | Ecosystem-specific rather than registry-neutral. CapabilityProof would need portable exact-byte evidence and policy semantics, not another ClawHub badge. | **Fact / High**. |
| [Socket skill scanning for skills.sh](https://socket.dev/blog/socket-brings-supply-chain-security-to-skills) | Socket says Vercel uploads installed skill source to its APIs; Socket analyzes markdown and referenced multi-language files, continuously rescans updates, and returns findings to skills.sh. Socket reports benchmark results, but those are vendor-reported and were not independently reproduced here. | The skills.sh integration page states no end-user audit fee. [Socket's general platform](https://socket.dev/pricing) lists **Free $0/month** (1,000 scans), **Team $25/month/developer**, **Business $50/month/developer**, and custom Enterprise. The pricing page does not say whether standalone Agent Skill scanning is included. | Level 3 code/supply-chain analysis and continuous rescanning. | Another strong free/public substitute; also an adjacent team-price anchor. CapabilityProof must not treat Socket's self-reported accuracy as proof of performance or sales. | **Fact / High** on offer/prices; **Vendor claim / Medium** on accuracy. |

### Adjacent provenance, posture, and schema substitutes

| Product / project | What it supplies | Price / access | Relevance | Evidence type / confidence |
|---|---|---:|---|---|
| [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations) | Sigstore-backed build provenance, subject digest verification, repository/workflow/commit identity, and optional SBOM attestations. | Available for public repositories on GitHub Free, Pro, and Team; private/internal use requires Enterprise Cloud. [Standard Actions usage is free for public repositories](https://docs.github.com/en/billing/concepts/product-billing/github-actions). | A publisher can already create verifiable provenance for release artifacts. It does not interpret skill instructions or permissions. CapabilityProof should consume or cross-reference attestations where present rather than reinvent signing infrastructure. | **Fact / High**. |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard-action) | Repository security-posture checks, JSON/SARIF results, badge, and public API. | Official action is **free for all public repositories**; private use depends on GitHub security entitlements or local CLI use. | Free evidence for repository hygiene, signed releases, dependency pinning, review practice, and license posture. It is repo-level, not exact-skill semantic analysis. | **Fact / High**. |
| [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/) and [Universal Skill Format](https://owasp.org/www-project-agentic-skills-top-10/universal-skill-format.html) | Public guidance calls for verified publishers, signing, content hashes, version pinning, permission review, scan status, inventory, approval, and audit logging. Its proposed universal manifest includes `permissions`, `risk_tier`, `scan_status`, `signature`, and `content_hash`. | **$0** public guidance/specification proposal. | Validates the shape of the problem, but also commoditizes the proposed receipt schema. The value must be trustworthy evidence generation and policy integration, not merely defining fields. This OWASP project is guidance, not proof of broad adoption or payment. | **Fact / High** on published guidance; **Inference / High** on commoditization risk. |

## Buyer pain and demand evidence

### Observed problem and adoption signals

| Evidence | What it supports | What it does **not** support | Confidence |
|---|---|---|---|
| [Snyk ToxicSkills study](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) reports that, as of 2026-02-05, it scanned 3,984 skills, found at least one critical issue in 13.4%, at least one issue of any severity in 36.82%, and human-confirmed 76 malicious payloads. | There is a measurable skill supply-chain risk worth screening. | Snyk authored the study and scanner; it does not prove independent accuracy, buyer urgency, or willingness to pay CapabilityProof. | **Vendor research / Medium-High**. |
| [Vercel integrated three independent audit providers](https://vercel.com/changelog/automated-security-audits-now-available-for-skills-sh) and changed search/install behavior for flagged skills. | A large registry considers pre-install evidence important enough to productize. | It is supply-side investment, not evidence that publishers or users paid for the audits. | **Fact / High** for the integration; **Demand inference / Low**. |
| [K-Dense Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) says it scans every skill with Cisco's scanner, reviews contributions, and rescans about weekly because skills can run code, access networks, and modify files. | A real skill publisher has adopted recurring scanning and describes limited review capacity. | K-Dense uses a free scanner; this is evidence of pain and adoption, not payment. | **Fact / High**. |
| [NVIDIA's verified-skill program](https://docs.nvidia.com/skills) requires cataloging, scanning, signing, and a skill card, and publishes whole-directory verification instructions. | A large publisher sees provenance, change detection, requirements, ownership, and risk documentation as release controls. | NVIDIA built the controls internally/openly; this may favor self-service rather than outsourced receipts. It does not show external purchase demand. | **Fact / High**; commercial implication **Inference / Medium**. |
| [Agent Skills discussion #210](https://github.com/agentskills/agentskills/discussions/210) proposes a lockfile with exact commits and SHA-256 integrity for skill directories because the base specification does not define distribution/dependency locking. | Builders are actively trying to solve exact-version integrity and reproducibility. | A community RFC is not an adopted standard, a buying commitment, or proof that a third-party receipt is preferred over a lockfile. | **User-generated primary evidence / Medium**. |
| [ClawHub issue #1253](https://github.com/openclaw/clawhub/issues/1253) shows a publisher asking for review after a security score flagged undeclared environment/API usage. | Findings must be explainable, location-specific, correctable, and tied to declarations. A no-human-support model still needs a deterministic rescan/appeal path. | One issue cannot quantify market size or willingness to pay. | **User-generated primary evidence / Medium**. |
| [OWASP's assessment checklist](https://owasp.org/www-project-agentic-skills-top-10/checklist.html) asks reviewers for verified publisher identity, signature/hash verification, behavioral analysis, explicit permissions, and exact version pinning. | CapabilityProof's evidence categories correspond to a published security-review workflow. | OWASP guidance is normative; it does not establish implementation prevalence, procurement budget, or sales. | **Fact / High** on guidance; **Demand inference / Low**. |

### Direct willingness-to-pay evidence

**None identified in the reviewed primary sources.** Specifically:

- No reviewed official case study, invoice, procurement record, or customer quote says an
  Agent Skill publisher paid a per-release verification fee.
- No reviewed official case study says a small agent team paid about $99 for up to five
  exact-version receipts.
- SkillProof's $19.90/month, Tessl's $100/month, and Snyk/Socket's $25/developer/month
  are **listed offers**, not proof of transactions or retention.
- A security study, product launch, GitHub star, installed-skill count, or "used by" logo
  must not be entered as customer demand in CapabilityProof records.

This absence is not proof that no demand exists. It means desk research cannot accept
the revenue hypotheses; only a real full-price buying decision can.

## Defensible wedge after the competitor check

CapabilityProof should not describe the initial product as "a skill scanner" or "a
verified badge." Those categories are already crowded and often free.

The narrow offer worth testing is:

> **A registry-neutral, independent, exact-byte policy receipt for one Agent Skill
> version: canonical file inventory and digest, source/ref resolution, declared versus
> inferred requirements, deterministic static findings with locations, methodology
> version, limitations, and expiry—returned under a stable machine-readable contract.**

Potential differentiation, in priority order:

1. **Portable evidence, not a platform score.** The same receipt should be consumable by
   CI, Codex, Claude Code, Cursor, a local policy gate, and any registry.
2. **Exact input identity.** Bind every statement to a canonical directory digest, file
   inventory, source commit/ref, and retrieval time. Record whether a tag/ref was mutable.
3. **Stable, reproducible contract.** Canonical JSON, schema version, methodology version,
   evidence locations, and deterministic reruns. Snyk explicitly labels its CLI JSON
   experimental; other tools emphasize scores rather than a cross-vendor receipt contract.
4. **Decision-ready requirements.** Separate `declared`, `observed-in-content`, and
   `inferred` filesystem, shell, network, secret, binary, package, and external-content
   needs. Never claim inferred requirements are enforced runtime permissions.
5. **Independent issuance.** Publisher self-signing proves origin/integrity, not independent
   review. CapabilityProof can verify existing signatures/attestations and issue its own
   time-bounded evidence about the exact bytes.
6. **Private/local team path.** A $99 team offer is more defensible for authorized private
   inputs, local execution, organization policy rules, and a consolidated allow/review/block
   decision pack than for five already-public registry scans.

## Differentiation and execution risks

| Risk | Evidence and implication | Required response |
|---|---|---|
| **Free-tool compression** | Cisco, Snyk, NVIDIA, Agent Skills, OpenSSF, GitHub, skills.sh, Tessl public reviews, and SkillProof author testing all provide substantial evidence for $0. | Sell independent evidence packaging and policy consumption, not detection rules. Show a side-by-side field-level gap against the free stack before charging. |
| **Near-exact NVIDIA precedent** | NVIDIA already combines scan + card + evaluation artifacts + whole-directory signature. | Interoperate with OMS/Sigstore and position CapabilityProof as the independent issuer for arbitrary publishers. Do not claim the workflow is novel. |
| **Registry distribution disadvantage** | skills.sh, Tessl, and ClawHub place trust signals directly at discovery/install, where decisions occur. | Make the receipt embeddable and queryable by registries/agents; a standalone web report has weak distribution. |
| **Schema commoditization** | OWASP's proposed format already includes permissions, hashes, signatures, and scan status. | Treat schemas as open interoperability infrastructure. The product value is fresh evidence, reproducibility, issuer trust, history, and policy automation. |
| **False positives and support load** | ClawHub publisher issues show legitimate credential/network behaviors can be flagged. LLM/regex scanners also state limitations. | Include file/line evidence, rule IDs, confidence, suppression rationale, deterministic rescan, and a bounded correction process. Avoid opaque scores as the primary output. |
| **Reproducibility versus semantic coverage** | Deterministic static rules reproduce well; optional LLM analyzers can catch contextual attacks but vary and cost money. | Keep Level 1-3 deterministic and disclose its narrower coverage. Offer semantic analysis only as a separately versioned, non-deterministic evidence layer later. |
| **Permission overclaim** | The official Agent Skills format does not mandate a comprehensive permission manifest; `allowed-tools` is experimental. | Use "requirements/indicators inferred from content," list evidence, and state that runtime behavior was not observed. Never emit a universal `safe` or `certified` verdict. |
| **Backend license/terms risk** | Snyk forbids unapproved large-scale use of its standard Agent Scan API for registries; cloud/LLM analyzers have separate costs and terms. | Use code and services only under compatible licenses/terms. Keep the core receipt reproducible with owned or permissively licensed deterministic checks. |
| **Pay-to-rank confusion** | SkillProof sells placement while testing for free; registries mix discovery and trust. | Keep payment, sponsorship, and evidence severity separate. A buyer pays for processing/issuance, never a better result. |

## Cheapest decisive demand experiment (not executed in this research cycle)

### Experiment: two-SKU, full-price receipt checkout

Run only after E-001 proves the exact deliverable can be fulfilled safely and
reproducibly. Use one static sample receipt and one no-upfront-cost payment/order page;
do not build accounts, dashboards, a marketplace, or automated billing first.

**Offer A — publisher, $19 one-time**

- Independent exact-byte Level 1-3 release receipt for one public or authorized skill.
- Canonical JSON, digest/file inventory, source/ref, declared vs inferred requirements,
  static findings with locations, methodology/limitations/expiry.
- No badge promises, ranking benefit, runtime execution, safety guarantee, or consulting.

**Offer B — small team, $99 one-time**

- Up to five exact-version receipts plus one explicit organization policy result per
  artifact (`allow`, `review`, or `block`, with the customer's predeclared rule set).
- Prefer private/authorized or mixed-source artifacts; local/private handling must be
  described accurately before accepting payment.
- No calls, custom security review, runtime execution, or ongoing monitoring.

**Qualified exposure**

- 25 unrelated publishers with a public Agent Skill updated in the prior 90 days and at
  least one executable script, external dependency, network instruction, or credential
  requirement.
- 15 unrelated small teams with public evidence that they operate coding/document agents
  and manage at least three third-party or internal skills.
- Give each prospect one written, self-service invitation and the same sample/methodology.
  No calls. Do not change price or bundle mid-cohort.
- Count an exposure only when the qualified prospect actually views the order page. If
  25 publisher views or 15 team views cannot be obtained, the channel test is
  **inconclusive**, not an offer failure.

**What counts**

- Only a settled, full-price payment by a genuine, unaffiliated buyer counts as demand.
- A buyer must submit an authorized artifact and accept the delivered receipt. Refunds,
  test transactions, owner-funded purchases, free submissions, waitlist entries, clicks,
  replies, compliments, and "interested" messages do not count.

**Decision rules (management thresholds, not industry benchmarks)**

| Result after 7 days from the last qualified view | Decision |
|---|---|
| **Publisher success:** at least **2 of 25** buy at $19, both are fulfilled, and neither is refunded for a defective deliverable. | Accept the publisher offer as an initial positive demand signal; repeat with a second cohort before forecasting conversion. |
| **Publisher weak:** exactly **1 of 25** buys and is fulfilled. | Do not accept or reject. Repeat once unchanged; one transaction proves a buyer exists but not a repeatable channel. |
| **Publisher failure:** **0 of 25** buy. | Reject the $19 publisher-paid public receipt. Do not discount immediately; test team-paid policy receipts instead. |
| **Team success:** at least **1 of 15** buys at $99, submits at least three artifacts, the pack is fulfilled, and it is not refunded for a defective deliverable. | Accept the $99 pilot as an initial positive demand signal; repeat with a second unrelated team. |
| **Team failure:** **0 of 15** buy. | Reject the $99 small-team pilot in this scope. Interview evidence may guide a new offer, but does not retroactively count as demand. |
| Any cohort misses its required number of qualified page views. | Inconclusive channel test; do not label the price or offer rejected. |

**Why this is decisive and cheapest:** it uses the existing product proof and one sample,
requires no paid traffic or platform build, preserves the self-service/no-call model, and
tests the exact prices with irreversible buyer behavior. A survey or "would you pay?"
form would be cheaper in effort but would not test willingness to pay.

## Recommended commercial sequence

1. Finish E-001 and publish internally reviewable sample/methodology evidence.
2. Ensure the receipt visibly distinguishes itself from Cisco/NVIDIA/Snyk output and
   Tessl/skills.sh scores at the field level.
3. Run the two-SKU full-price test unchanged.
4. If publishers fail and a team buys, make operators/policy gates the primary customer
   and keep publisher receipts as free acquisition or team-funded evidence.
5. If both fail, do not expand to sandboxing, MCP servers, monitoring, or a marketplace.
   Revisit the buyer/problem before adding product scope.

## Research limitations

- Research used official specifications, vendor/project pages, repositories, pricing
  pages, and public first-party issue/discussion records. No access-controlled data,
  outreach, account creation, or purchases were used.
- Vendor benchmark and prevalence claims were not independently reproduced.
- Public list prices can change and may exclude usage, model, hosting, support, tax, or
  enterprise-contract costs.
- Product pages do not reveal conversion, revenue, retention, or the number of paying
  customers. This memo therefore makes no willingness-to-pay claim.
- Dynamic directory counts were not used to decide pricing because crawled pages can be
  stale or internally inconsistent.
