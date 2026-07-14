# Graph Report - initial-mvp  (2026-07-13)

## Corpus Check
- 63 files · ~34,021 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 834 nodes · 1203 edges · 83 communities (57 shown, 26 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 111 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `05f0e139`
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
- [[_COMMUNITY_Community 47|Community 47]]
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
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]

## God Nodes (most connected - your core abstractions)
1. `ScanLimits` - 46 edges
2. `InputRejected` - 41 edges
3. `inspect_skill()` - 41 edges
4. `PathRejected` - 27 edges
5. `Snapshot` - 23 edges
6. `collect_snapshot()` - 23 edges
7. `inspect_git_skill()` - 18 edges
8. `ParsedSkill` - 18 edges
9. `CapabilityProofError` - 15 edges
10. `CapabilityProof hostile-input threat model and security acceptance checklist` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Path` --uses--> `InputRejected`  [INFERRED]
  tests/test_inspector.py → src/capabilityproof/errors.py
- `Path` --uses--> `InputRejected`  [INFERRED]
  tests/test_provenance.py → src/capabilityproof/errors.py
- `Path` --uses--> `LimitExceeded`  [INFERRED]
  tests/test_inspector.py → src/capabilityproof/errors.py
- `Path` --uses--> `PathRejected`  [INFERRED]
  tests/test_inspector.py → src/capabilityproof/errors.py
- `Path` --uses--> `ScanLimits`  [INFERRED]
  tests/test_inspector.py → src/capabilityproof/snapshot.py

## Import Cycles
- 1-file cycle: `src/capabilityproof/receipt.py -> src/capabilityproof/receipt.py`
- 1-file cycle: `src/capabilityproof/snapshot.py -> src/capabilityproof/snapshot.py`

## Communities (83 total, 26 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (58): ArgumentParser, BaseHTTPRequestHandler, create_server(), make_handler(), _no_duplicate_object(), Small loopback-only JSON API around the deterministic inspector., _validate_request(), _build_parser() (+50 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (44): 1. Input forms and immutable capture, 2. Central MVP limits, 3. ZIP, path, and filesystem rules, 4. Parser and rule-engine rules, 5. Worker containment and side-effect controls, 6. Output, evidence, logging, and privacy, A. Non-execution and containment, Assets to protect (+36 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (51): CapabilityProof exact-version Agent Skill evidence., ProvenanceEvidence, _decision(), deterministic_json(), inspect_git_skill(), inspect_skill(), _iso(), _levels() (+43 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (40): const, additionalProperties, properties, required, type, additionalProperties, properties, required (+32 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (44): const, maxLength, minLength, type, maxLength, minLength, type, additionalProperties (+36 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (18): maxItems, minItems, type, additionalProperties, properties, required, type, maximum (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (31): _construct_unique_mapping(), _extract_references(), _finding(), _normalize_link_target(), _parse_frontmatter(), parse_skill(), ParsedSkill, Strict, bounded parsing and structural checks for Agent Skills. (+23 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (29): const, format, type, maxLength, minLength, type, const, format (+21 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (21): maximum, minimum, type, maximum, minimum, type, maximum, minimum (+13 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (21): 1. Agent Skills: specification, validation, and evaluations, 2. MCP Registry: downstream-aggregator positioning, 3. Agentic Resource Discovery (ARD): verified status and fit, 4. A2A discovery: limited relevance, 5. x402 discovery: current primary-source-verified state, 6. Working-name evidence: `CapabilityProof`, 7. Implementation scope decided by this evidence, Bottom line (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (22): maxLength, type, additionalProperties, properties, required, type, maxLength, type (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (19): anyOf, const, artifact_path, content_digest_pinned, provenance, publisher_identity, source_commit, source_repository (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (18): additionalProperties, properties, required, type, coverage, maximum, minimum, type (+10 more)

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (16): const, minimum, type, maxLength, minLength, type, evidence_type, line (+8 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (14): Adjacent provenance, posture, and schema substitutes, Buyer pain and demand evidence, CapabilityProof market, competitor, and buyer evidence, Cheapest decisive demand experiment (not executed in this research cycle), Closest direct and partial substitutes, Decision, Defensible wedge after the competitor check, Differentiation and execution risks (+6 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (15): format, type, format, type, maxLength, minLength, type, expires_at (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (10): maxLength, type, const, additionalProperties, properties, required, type, declared_claim_untrusted (+2 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (14): const, properties, integrity_assurance, receipt_id, receipt_profile, schema_sha256, schema_uri, schema_version (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.15
Nodes (12): Acquisition experiment, Automation path, CapabilityProof living business plan, Competition and differentiation, Current product evidence, Customer and problem, Deliverables and exclusions, Economics and compliance (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (12): $defs, path, sha256, staticSummary, maxLength, minLength, type, pattern (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (7): skippedFile, $ref, path, additionalProperties, properties, required, type

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (12): maxItems, type, additionalProperties, properties, required, type, external_references_untrusted, format_validation (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.31
Nodes (10): items, items, maximum, maxLength, minimum, minLength, type, items (+2 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (14): $ref, const, coverage, engine, script_languages, static_analysis, summary, maxItems (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (9): $ref, properties, const, evidence_sha256, profile, replacement_warning, maxLength, minLength (+1 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (15): $ref, $ref, additionalProperties, properties, required, type, $ref, $ref (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.22
Nodes (9): $ref, additionalProperties, properties, required, type, $ref, limits, policy (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (13): items, maxItems, type, $ref, items, maxItems, type, dependencies (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (9): 2026-07-13 - Close independent audit findings before accepting E-001, 2026-07-13 - Do not grant a public code license autonomously, 2026-07-13 - First slice is non-executing Level 1-3 evidence, 2026-07-13 - Keep CapabilityProof as an internal codename, 2026-07-13 - Local proof is not an external service, 2026-07-13 - Position as a portable policy receipt, 2026-07-13 - Prices remain transaction experiments, 2026-07-13 - Select the Agent Skills exact-version wedge (+1 more)

### Community 29 - "Community 29"
Cohesion: 0.22
Nodes (8): Acceptance criteria, Current proof versus sellable delivery, Customer outcome, Defect remedy hypothesis, Excluded, For whom, Full-price transaction hypotheses, Offer hypothesis - portable exact-byte Agent Skill policy receipt

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
Cohesion: 0.09
Nodes (22): additionalProperties, properties, required, type, maxLength, minLength, type, decision (+14 more)

### Community 34 - "Community 34"
Cohesion: 0.29
Nodes (6): CapabilityProof v0.1 methodology, Checks, Explicit non-claims, Git provenance option, Integrity limits, Scope and security profile

### Community 35 - "Community 35"
Cohesion: 0.29
Nodes (6): CapabilityProof, Evidence semantics, Local developer HTTP, Local MCP stdio, Local use, What exists now

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (7): localReference, enum, additionalProperties, properties, required, type, kind

### Community 37 - "Community 37"
Cohesion: 0.50
Nodes (4): staticFinding, additionalProperties, required, type

### Community 38 - "Community 38"
Cohesion: 0.60
Nodes (5): HTTPConnection, _request(), test_health_is_non_sensitive(), test_http_inspect_and_path_confinement(), test_incomplete_request_does_not_block_other_loopback_clients()

### Community 39 - "Community 39"
Cohesion: 0.40
Nodes (4): Completed, Deferred, Next, Prioritized backlog

### Community 40 - "Community 40"
Cohesion: 0.40
Nodes (4): Authorized scope, Local validation and evidence-delivery SOP, Procedure, Stop conditions

### Community 41 - "Community 41"
Cohesion: 0.50
Nodes (3): Operating charter, Owner controls, Product-specific boundaries

### Community 42 - "Community 42"
Cohesion: 0.50
Nodes (3): Compliance and trust checklist, Current local proof, Required before any external/public artifact intake

### Community 43 - "Community 43"
Cohesion: 0.50
Nodes (3): Charter acceptance tests, Goal evidence, Product proof accepted for the current local scope

### Community 44 - "Community 44"
Cohesion: 0.50
Nodes (3): Final gate matrix, Independent local-MVP review record, Initial material findings

### Community 45 - "Community 45"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, category

### Community 46 - "Community 46"
Cohesion: 0.50
Nodes (4): items, maxItems, type, findings

### Community 47 - "Community 47"
Cohesion: 0.50
Nodes (4): maxLength, pattern, type, deterministic_json_profile

### Community 48 - "Community 48"
Cohesion: 0.50
Nodes (4): additionalProperties, required, type, integrity

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (4): items, maxItems, type, local_references

### Community 50 - "Community 50"
Cohesion: 0.50
Nodes (4): items, maxItems, type, license_files

### Community 51 - "Community 51"
Cohesion: 0.50
Nodes (3): Decision rules, E-002 full-price demand experiment SOP, Qualified units

### Community 52 - "Community 52"
Cohesion: 0.50
Nodes (4): maxItems, minItems, type, limitations

### Community 81 - "Community 81"
Cohesion: 0.67
Nodes (3): maxLength, type, evidence_excerpt

### Community 82 - "Community 82"
Cohesion: 0.67
Nodes (3): referenced_hosts, maxItems, type

## Knowledge Gaps
- **415 isolated node(s):** `$schema`, `$id`, `title`, `description`, `type` (+410 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `properties` connect `Community 17` to `Community 32`, `Community 33`, `Community 3`, `Community 4`, `Community 5`, `Community 11`, `Community 15`, `Community 48`, `Community 16`, `Community 52`, `Community 21`, `Community 23`, `Community 26`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **Why does `$defs` connect `Community 19` to `Community 32`, `Community 36`, `Community 37`, `Community 12`, `Community 20`, `Community 30`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `properties` connect `Community 3` to `Community 10`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `ScanLimits` (e.g. with `BaseHTTPRequestHandler` and `ParsedSkill`) actually correct?**
  _`ScanLimits` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `InputRejected` (e.g. with `BaseHTTPRequestHandler` and `ProvenanceEvidence`) actually correct?**
  _`InputRejected` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `PathRejected` (e.g. with `BaseHTTPRequestHandler` and `ProvenanceEvidence`) actually correct?**
  _`PathRejected` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Snapshot` (e.g. with `ProvenanceEvidence` and `ParsedSkill`) actually correct?**
  _`Snapshot` has 17 INFERRED edges - model-reasoned connections that need verification._