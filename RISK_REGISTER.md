# Risk register

| ID | Risk | Severity | Control | Status |
|---|---|---|---|---|
| R-001 | Evidence is mistaken for a safety guarantee. | High | Explicit factual labels, limitations, tested/not-tested fields, expiry; no generic safe badge. | Active |
| R-002 | Static inspection misses harm or flags benign content. | High | Rule IDs, bounded evidence/coverage, transparent findings, no runtime claim. | Active |
| R-003 | Signed evidence is forged, stale, rolled back, or equivocated. | Critical | Exact-byte DSSE/Ed25519, distinct root/issuer roles, expiring signed lifecycle, persistent sequence/digest, mutation tests. | Implemented/reviewed |
| R-004 | Signing secret reaches source, logs, worker, or public service. | Critical | Encrypted keys outside repository; no-network signing role; planned constrained signing service. | Stage A implemented; Stage B gate |
| R-005 | Provisional name conflicts with an existing mark. | High | Low-cost obvious-conflict screen; no clearance claim or material brand spend. | Active |
| R-006 | Public metadata publication creates license/privacy risk. | High | Selected public immutable sources; no original artifact/archive/executable redistribution; bounded metadata/excerpts. | Active |
| R-007 | Catalog metadata is substituted around valid receipts. | High | Signed exact index, full index/receipt binding, immutable verified snapshot, separate trust material, managed TLS. | Implemented/reviewed |
| R-008 | Stage A grows an upload/private/confidential-data path. | Critical | Read-only identifiers/search, write rejection, boundary tests. | Controlled |
| R-009 | Git source binding is mistaken for publisher identity. | High | Schema and copy separate exact commit evidence from unverified identity. | Controlled |
| R-010 | Structural failures are mistaken for passes or lost by CI. | High | Failure receipts remain attested; `structure-status` and `decision-status` are explicit; only pass receives validation label. | Corrected; demo verification pending |
| R-011 | Built-in server is treated as production hardened. | High | Public Stage A uses managed TLS/static hosting; dynamic worker requires bounded deployment controls. | Active gate |
| R-012 | Free substitutes eliminate willingness to pay. | High | Free retrieval plus $49 fresh exact-version test; genuine settlement/repeat gates. | Demand unvalidated |
| R-013 | Windows tests are generalized to Linux/cross-OS/archive safety. | Critical for Stage B | Production-equivalent Linux, adversarial path/archive matrix, deterministic checks, explicit skips. | Stage B gate |
| R-014 | Dependency lock is mistaken for executing-runtime proof. | Medium | Record runtime versions; describe lock hash as reference evidence only. | Active limitation |
| R-015 | Owned/demo/monitor traffic inflates commercial evidence. | Critical | Source classification, immutable exclusions, raw event ledger, acceptance queries exclude controlled sources. | Policy implemented; telemetry expansion pending |
| R-016 | Webhook replay, duplicates, reordering, or forged redirects trigger fulfillment. | Critical | Exact raw-body HMAC/timestamp verification, event-ID uniqueness, state machine, server retrieval/reconciliation, no redirect fulfillment. | Signature/state prepared; store/provider pending |
| R-017 | Payment, refund, fee, or cost records overstate settled revenue/margin. | Critical | Separate order/payment states; count only available unrelated funds; reconcile fees/refunds/disputes; complete per-order ledger. | Design documented; no live orders |
| R-018 | Immutable-source retrieval causes SSRF, traversal, resource abuse, or artifact execution. | Critical | GitHub-only full commit/path contract; byte/file/depth/time limits; isolated no-egress non-executing worker. | Request validation prepared; worker gate |
| R-019 | Marketplace/registry publication accepts owner-binding terms or publishes invalid metadata. | High | Use official requirements; prepare locally; owner authenticates/accepts terms only when eligible. | Controlled |
