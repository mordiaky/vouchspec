# Risk register

| ID | Risk | Severity | Control | Status |
|---|---|---|---|---|
| R-001 | Evidence is mistaken for a safety guarantee. | High | Explicit factual labels, limitations, tested/not-tested fields, expiry; no generic safe badge. | Active |
| R-002 | Static inspection misses harm or flags benign content. | High | Rule IDs, bounded evidence/coverage, transparent findings, no runtime claim. | Active |
| R-003 | Signed evidence is forged, stale, rolled back, or equivocated. | Critical | Exact-byte DSSE/Ed25519, distinct root/issuer roles, expiring signed lifecycle, persistent sequence/digest, mutation tests. | Implemented/reviewed |
| R-004 | Signing secret reaches source, logs, worker, or public service. | Critical | Encrypted keys outside repository/worker; exact-byte constrained gate; separate no-network role. | Stage B gate tested; production key/role pending |
| R-005 | Provisional name conflicts with an existing mark. | High | Low-cost obvious-conflict screen; no clearance claim or material brand spend. | Active |
| R-006 | Public metadata publication creates license/privacy risk. | High | Selected public immutable sources; no original artifact/archive/executable redistribution; bounded metadata/excerpts. | Active |
| R-007 | Catalog metadata is substituted around valid receipts. | High | Signed exact index, full index/receipt binding, immutable verified snapshot, separate trust material, managed TLS. | Implemented/reviewed |
| R-008 | Stage A grows an upload/private/confidential-data path. | Critical | Read-only identifiers/search, write rejection, boundary tests. | Controlled |
| R-009 | Git source binding is mistaken for publisher identity. | High | Schema and copy separate exact commit evidence from unverified identity. | Controlled |
| R-010 | Structural failures are mistaken for passes or lost by CI. | High | Failure receipts remain attested; `structure-status` and `decision-status` are explicit; only pass receives validation label. | Corrected; demo independently verified |
| R-011 | Built-in server is treated as production hardened. | High | Public Stage A uses managed TLS/static hosting; dynamic worker requires bounded deployment controls. | Active gate |
| R-012 | Free substitutes eliminate willingness to pay. | High | Free retrieval plus $49 fresh exact-version test; genuine settlement/repeat gates. | Demand unvalidated |
| R-013 | Windows tests are generalized to Linux/cross-OS/archive safety. | Critical for Stage B | Linux container proof, adversarial tree/archive/path matrix, deterministic checks, explicit skip. | 114 pass; 1 Windows symlink-privilege skip; public CI refresh pending |
| R-014 | Dependency lock is mistaken for executing-runtime proof. | Medium | Record runtime versions; describe lock hash as reference evidence only. | Active limitation |
| R-015 | Owned/demo/monitor traffic inflates commercial evidence. | Critical | Source classification, immutable exclusions, raw event ledger, acceptance queries exclude controlled sources. | Policy implemented; telemetry expansion pending |
| R-016 | Webhook replay, duplicates, reordering, or forged redirects trigger fulfillment. | Critical | Exact raw-body HMAC/timestamp verification, event-ID uniqueness, pending-event reconciliation, no redirect fulfillment. | Fake sandbox passes; real Stripe adapter pending |
| R-017 | Payment, refund, fee, or cost records overstate settled revenue/margin. | Critical | Environment-bound store; separate order/payment states; complete fee/refund/direct-cost ledger; goal-exclusion flag. | Sandbox implemented; no live orders |
| R-018 | Immutable-source retrieval causes SSRF, traversal, resource abuse, or artifact execution. | Critical | GitHub-only exact commit/path, tree/blob/archive verification, disk/byte/file/depth/time limits, zero-egress non-executing worker. | Sandbox-proven; live scratch-volume kernel quota pending |
| R-019 | Marketplace/registry publication accepts owner-binding terms or publishes invalid metadata. | High | Use official requirements; prepare locally; owner authenticates/accepts terms only when eligible. | Controlled |
| R-020 | API credential abuse or object-level authorization failure discloses another buyer's order/result. | Critical | HMAC-digest API keys; tenant-scoped idempotency and bindings; second expiring order capability; constant-time comparison; generic errors; rotation/revocation; cross-tenant tests. | Sandbox implemented; managed-TLS deployment pending |
| R-021 | Revoking result access is mistaken for invalidating an already downloaded paid receipt. | Critical | Separate capability status from evidence lifecycle; require root-authorized monotonic Stage B receipt status before live delivery. | Open launch gate |
| R-022 | Dynamic API is exposed without source limits, secret isolation, or restricted database permissions. | Critical | Loopback-only sandbox; direct-peer/global/tenant limits; secret key-ID binding; no forwarded-header trust; explicit managed-edge/secret-manager/service-identity gate. | No external exposure; deployment pending |
