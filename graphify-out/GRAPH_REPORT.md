# Graph Report - capabilityproof  (2026-07-14)

## Corpus Check
- 118 files · ~48,614 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1223 nodes · 1965 edges · 105 communities (78 shown, 27 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 172 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1315682a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 106|Community 106]]

## God Nodes (most connected - your core abstractions)
1. `InputRejected` - 115 edges
2. `ScanLimits` - 44 edges
3. `inspect_skill()` - 39 edges
4. `PathRejected` - 31 edges
5. `main()` - 29 edges
6. `VerifiedCatalog` - 23 edges
7. `LifecycleSequenceStore` - 23 edges
8. `Snapshot` - 23 edges
9. `CatalogStore` - 22 edges
10. `collect_snapshot()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Path` --uses--> `VerifiedCatalog`  [INFERRED]
  tests/test_catalog.py → src/capabilityproof/catalog_runtime.py
- `test_quote_cli_emits_machine_readable_preview()` --calls--> `main()`  [EXTRACTED]
  tests/test_commerce.py → src/capabilityproof/cli.py
- `test_quote_cli_rejects_duplicate_request_keys()` --calls--> `main()`  [EXTRACTED]
  tests/test_commerce.py → src/capabilityproof/cli.py
- `Path` --uses--> `InputRejected`  [INFERRED]
  tests/test_catalog.py → src/capabilityproof/errors.py
- `Path` --uses--> `InputRejected`  [INFERRED]
  tests/test_inspector.py → src/capabilityproof/errors.py

## Import Cycles
- 1-file cycle: `src/capabilityproof/receipt.py -> src/capabilityproof/receipt.py`
- 1-file cycle: `src/capabilityproof/catalog_builder.py -> src/capabilityproof/catalog_builder.py`
- 1-file cycle: `src/capabilityproof/lifecycle.py -> src/capabilityproof/lifecycle.py`
- 1-file cycle: `src/capabilityproof/commerce.py -> src/capabilityproof/commerce.py`
- 1-file cycle: `src/capabilityproof/snapshot.py -> src/capabilityproof/snapshot.py`

## Communities (105 total, 27 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (77): create_server(), make_handler(), _no_duplicate_object(), Small loopback-only JSON API around the deterministic inspector., _validate_request(), LimitExceeded, PathRejected, Public error types with stable machine-readable codes. (+69 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (44): 1. Input forms and immutable capture, 2. Central MVP limits, 3. ZIP, path, and filesystem rules, 4. Parser and rule-engine rules, 5. Worker containment and side-effect controls, 6. Output, evidence, logging, and privacy, A. Non-execution and containment, Assets to protect (+36 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (99): create_catalog_server(), make_catalog_handler(), Bounded loopback HTTP retrieval API for the Stage A catalog., build_catalog_drafts(), _checkout(), finalize_catalog_lifecycle(), _iso(), load_source_manifest() (+91 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (42): const, additionalProperties, properties, required, type, additionalProperties, properties, required (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (44): const, maxLength, minLength, type, maxLength, minLength, type, additionalProperties (+36 more)

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (13): additionalProperties, properties, required, type, maximum, minimum, type, maxItems (+5 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (52): VouchSpec exact-version Agent Skill evidence engine., ProvenanceEvidence, _decision(), deterministic_json(), inspect_git_skill(), inspect_skill(), _iso(), _levels() (+44 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (29): const, format, type, maxLength, minLength, type, const, format (+21 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (25): maximum, minimum, type, staticSummary, maximum, minimum, type, maximum (+17 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (21): 1. Agent Skills: specification, validation, and evaluations, 2. MCP Registry: downstream-aggregator positioning, 3. Agentic Resource Discovery (ARD): verified status and fit, 4. A2A discovery: limited relevance, 5. x402 discovery: current primary-source-verified state, 6. Working-name evidence: `CapabilityProof`, 7. Implementation scope decided by this evidence, Bottom line (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (22): maxLength, type, additionalProperties, properties, required, type, maxLength, type (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (15): anyOf, const, artifact_path, content_digest_pinned, publisher_identity, source_commit, source_repository, source_verification (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (47): additionalProperties, maximum, minimum, type, pattern, type, const, pattern (+39 more)

### Community 13 - "Community 13"
Cohesion: 0.16
Nodes (14): maxLength, type, maxLength, minLength, type, evidence_excerpt, message, rule_id (+6 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (14): Adjacent provenance, posture, and schema substitutes, Buyer pain and demand evidence, CapabilityProof market, competitor, and buyer evidence, Cheapest decisive demand experiment (not executed in this research cycle), Closest direct and partial substitutes, Decision, Defensible wedge after the competitor check, Differentiation and execution risks (+6 more)

### Community 15 - "Community 15"
Cohesion: 0.18
Nodes (11): format, type, format, type, maxLength, minLength, type, expires_at (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (10): maxLength, type, const, additionalProperties, properties, required, type, declared_claim_untrusted (+2 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (13): additionalProperties, properties, required, type, authentication, public_distribution_requirement, signature_verification, maxLength (+5 more)

### Community 18 - "Community 18"
Cohesion: 0.05
Nodes (41): pattern, type, additionalProperties, properties, required, type, pattern, type (+33 more)

### Community 19 - "Community 19"
Cohesion: 0.25
Nodes (8): $defs, path, sha256, maxLength, minLength, type, pattern, type

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (21): CatalogStore, filter_catalog_entries(), Read-only Stage A catalog storage and validation., Filter an already validated catalog snapshot without rereading disk., validate_catalog_index(), validate_receipt_id(), HTTPConnection, Any (+13 more)

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (12): maxItems, type, additionalProperties, properties, required, type, external_references_untrusted, format_validation (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.20
Nodes (14): items, maxLength, minLength, type, items, maxItems, minItems, type (+6 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (14): $ref, const, coverage, engine, script_languages, static_analysis, summary, maxItems (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.11
Nodes (31): build_fresh_validation_quote(), _canonical_bytes(), _exact_object(), load_strict_commerce_json(), OrderStatus, parse_fresh_validation_request(), PaymentStatus, Provider-neutral commerce contracts for the constrained Stage B product.  This m (+23 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (15): $ref, $ref, additionalProperties, properties, required, type, $ref, $ref (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (14): const, properties, integrity_assurance, receipt_id, receipt_profile, schema_sha256, schema_uri, schema_version (+6 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (14): items, maxItems, type, $ref, items, items, maxItems, type (+6 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (10): localReference, enum, minimum, type, additionalProperties, properties, required, type (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (22): const, const, const, const, format, type, const, const (+14 more)

### Community 30 - "Community 30"
Cohesion: 0.50
Nodes (4): structuralFinding, additionalProperties, required, type

### Community 31 - "Community 31"
Cohesion: 0.25
Nodes (7): 2026-07-13 E-001 verification record, Final receipt, Independent-review-driven changes, Outcome, Real public artifact, Residual boundary, Verification commands

### Community 32 - "Community 32"
Cohesion: 0.25
Nodes (7): additionalProperties, description, $id, required, $schema, title, type

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (12): additionalProperties, properties, required, type, maxLength, minLength, type, decision (+4 more)

### Community 34 - "Community 34"
Cohesion: 0.29
Nodes (6): Authentication and lifecycle, Checks, Evidence labels, Explicit non-claims and publication content, Profiles and scope, VouchSpec static evidence methodology v0.2

### Community 35 - "Community 35"
Cohesion: 0.20
Nodes (9): Evidence labels, Local inspector and builder, Product stages, Public Stage A distribution, Publisher CI — complete self-service example, Read-only catalog API, Read-only catalog MCP, Verify a public receipt independently (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.16
Nodes (13): ArgumentParser, BoundedCatalogServer, _build_parser(), _passphrase(), Command-line entry point., _write_json_file(), _write_receipt(), CapabilityProofError (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.50
Nodes (4): staticFinding, additionalProperties, required, type

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (17): 2026-07-13 - Authenticate exact receipt bytes with DSSE and Ed25519, 2026-07-13 - Close independent audit findings before accepting E-001, 2026-07-13 - Correct launch sequencing to Stage A, B, and C, 2026-07-13 - Do not grant a public code license autonomously, 2026-07-13 - First slice is non-executing Level 1-3 evidence, 2026-07-13 - Keep CapabilityProof as an internal codename, 2026-07-13 - Local proof is not an external service, 2026-07-13 - Make repository checkout bytes deterministic (+9 more)

### Community 39 - "Community 39"
Cohesion: 0.17
Nodes (11): Customer and problem, Differentiation and claims, Economics, compliance, and stop rules, Executive summary, External alpha acceptance, Pricing hypotheses, Product stages, Stage A — public artifact index (current) (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.40
Nodes (4): Authorized scope, Procedure, Stage A catalog build and evidence-delivery SOP, Stop conditions

### Community 41 - "Community 41"
Cohesion: 0.18
Nodes (11): maxLength, pattern, type, $ref, properties, deterministic_json_profile, evidence_sha256, replacement_warning (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (10): const, const, const, command, payload_type, profile, verification_order, properties (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (6): Before Stage B orderability, Commercial evidence, Compliance and trust checklist, Deferred Stage C, External adoption, Live Stage A

### Community 44 - "Community 44"
Cohesion: 0.50
Nodes (3): Final gate matrix, Independent local-MVP review record, Initial material findings

### Community 45 - "Community 45"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, category

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (5): Completed foundations, Deferred Stage C, Evidence-driven operation, Now — external adoption and safe orderability, Prioritized backlog

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (9): $ref, additionalProperties, properties, required, type, $ref, limits, policy (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.29
Nodes (7): items, maxItems, minItems, type, uniqueItems, enum, evidence_labels

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (5): Automatic remedy, Exclusions, First paid product — fresh public static validation, Free Stage A, VouchSpec exact-version evidence offer

### Community 51 - "Community 51"
Cohesion: 0.40
Nodes (4): Acceptance, Boundary, E-003 machine-native external alpha SOP, Qualified events

### Community 52 - "Community 52"
Cohesion: 0.29
Nodes (7): items, maxItems, minItems, type, maximum, minimum, completed_checks

### Community 54 - "Community 54"
Cohesion: 0.50
Nodes (3): 0.2.0 - 2026-07-13, Changelog, Unreleased

### Community 56 - "Community 56"
Cohesion: 0.13
Nodes (15): const, const, const, additionalProperties, properties, required, type, const (+7 more)

### Community 58 - "Community 58"
Cohesion: 0.29
Nodes (6): Independent state dimensions, Machine contract, Provider decision, Remaining live gates, VouchSpec payment and reconciliation flow, Webhook security prepared locally

### Community 59 - "Community 59"
Cohesion: 0.50
Nodes (3): Operating charter, Owner controls, Product-specific boundaries

### Community 61 - "Community 61"
Cohesion: 0.50
Nodes (3): Complete trusted-workflow example, Verify and troubleshoot, VouchSpec publisher CI profile

### Community 62 - "Community 62"
Cohesion: 0.33
Nodes (5): additionalProperties, $id, required, $schema, type

### Community 63 - "Community 63"
Cohesion: 0.50
Nodes (4): items, maxItems, type, findings

### Community 67 - "Community 67"
Cohesion: 0.50
Nodes (4): additionalProperties, required, type, integrity

### Community 68 - "Community 68"
Cohesion: 0.33
Nodes (6): items, maxItems, minItems, prefixItems, type, live_gates

### Community 70 - "Community 70"
Cohesion: 0.50
Nodes (4): items, maxItems, type, license_files

### Community 73 - "Community 73"
Cohesion: 0.50
Nodes (4): items, maxItems, type, manifest_parse_failures

### Community 76 - "Community 76"
Cohesion: 0.50
Nodes (4): provenance, additionalProperties, required, type

### Community 80 - "Community 80"
Cohesion: 0.33
Nodes (6): items, maxItems, minItems, prefixItems, type, payment_options

### Community 81 - "Community 81"
Cohesion: 0.50
Nodes (4): signature, additionalProperties, required, type

### Community 83 - "Community 83"
Cohesion: 0.33
Nodes (6): refund_conditions, items, maxItems, minItems, prefixItems, type

### Community 85 - "Community 85"
Cohesion: 0.40
Nodes (4): Decision, Discovery and registry decision — 2026-07-14, Official sources checked, Valid next preparation

### Community 86 - "Community 86"
Cohesion: 0.40
Nodes (4): Decision, Evidence, Payment provider decision — 2026-07-14, Pricing implication

### Community 89 - "Community 89"
Cohesion: 0.50
Nodes (3): Automatic refund, Fresh-validation refund policy, Not a refund condition

### Community 92 - "Community 92"
Cohesion: 0.50
Nodes (4): validity, additionalProperties, required, type

### Community 96 - "Community 96"
Cohesion: 0.67
Nodes (3): format, type, generated_at

### Community 97 - "Community 97"
Cohesion: 0.67
Nodes (3): quote_digest, pattern, type

### Community 98 - "Community 98"
Cohesion: 0.67
Nodes (3): quote_id, pattern, type

### Community 99 - "Community 99"
Cohesion: 0.67
Nodes (3): request_digest, pattern, type

## Knowledge Gaps
- **545 isolated node(s):** `$schema`, `$id`, `title`, `description`, `type` (+540 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `properties` connect `Community 26` to `Community 32`, `Community 33`, `Community 3`, `Community 67`, `Community 5`, `Community 4`, `Community 76`, `Community 16`, `Community 17`, `Community 49`, `Community 48`, `Community 21`, `Community 22`, `Community 23`, `Community 92`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `InputRejected` connect `Community 2` to `Community 0`, `Community 36`, `Community 6`, `Community 20`, `Community 24`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `properties` connect `Community 3` to `Community 10`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `InputRejected` (e.g. with `BoundedCatalogServer` and `CatalogStore`) actually correct?**
  _`InputRejected` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `ScanLimits` (e.g. with `ParsedSkill` and `UniqueKeySafeLoader`) actually correct?**
  _`ScanLimits` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `PathRejected` (e.g. with `CatalogStore` and `ProvenanceEvidence`) actually correct?**
  _`PathRejected` has 19 INFERRED edges - model-reasoned connections that need verification._
- **What connects `VouchSpec exact-version Agent Skill evidence engine.`, `Run the VouchSpec CLI from an immutable source checkout.`, `Small loopback-only JSON API around the deterministic inspector.` to the rest of the system?**
  _588 weakly-connected nodes found - possible documentation gaps or missing edges._