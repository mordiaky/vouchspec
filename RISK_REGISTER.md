# Risk register

| ID | Risk | Severity | Control | Status |
|---|---|---|---|---|
| R-001 | Evidence is mistaken for a safety guarantee. | High | Explicit labels, digest, method, tested/not-tested fields, limitations, expiry, and no generic verified/safe badge. | Active |
| R-002 | Static rules miss harmful behavior or flag benign material. | High | Rule IDs, bounded evidence, coverage, transparent issue counts, and no runtime claim. | Active |
| R-003 | A signed receipt or lifecycle document is forged, replaced, stale, rolled back, or equivocated. | Critical | Exact-byte DSSE/Ed25519, externally configured root JWK, distinct issuer/root keys, expiring root feed, startup sequence+digest persistence, process lock, conservative compromise revocation, mutation tests. | Implemented and independently reviewed; independent-channel root publication pending |
| R-004 | Signing secret reaches source, logs, or the public service. | Critical | Encrypted issuer/root PKCS#8 files outside repository, restrictive ACLs, no secret CLI arguments/output, separate root role. | Implemented locally; operational review pending |
| R-005 | `VouchSpec` conflicts with an existing name or mark. | High | Provisional low-obvious-conflict screen; no clearance claim or material brand spend. | Active |
| R-006 | Public metadata processing or publication infringes license/privacy interests. | High | Selected public sources; no original files/archives/executables redistributed; bounded metadata/excerpts disclosed; no license interpretation. | Active |
| R-007 | Catalog metadata is substituted even though receipt signatures remain valid. | High | Issuer-signed exact index bytes, root-authorized issuer, full index-to-receipt binding, immutable verified process snapshot, externally configured root, persistent sequence state, and managed TLS. | Implemented and independently reviewed; independent-channel root publication pending |
| R-008 | Stage A accidentally grows an artifact upload or confidential-data path. | Critical | GET-only catalog API, retrieval-only MCP identifiers/search, POST returns 405, boundary tests. | Controlled locally |
| R-009 | Git source binding is mistaken for publisher identity. | High | Receipt separates exact commit/blob evidence from publisher identity, which remains not checked. | Controlled by schema/limitations |
| R-010 | Six structurally failing artifacts are mistaken for passing. | High | Omit `STRUCTURE_VALIDATED`; keep findings and decision in signed receipt; disclose 19 pass/6 fail. | Controlled |
| R-011 | Built-in public HTTP server lacks TLS or production hardening. | High | Deploy behind managed TLS/proxy; expose only public immutable data; measure/rate-limit at platform boundary. | External deployment gate |
| R-012 | Free substitutes eliminate willingness to pay. | High | Free search/retrieval, micropriced fresh/comparison/issuance tests, real settlement gate. | Demand unvalidated |
| R-013 | Linux/cross-OS/archive security is assumed from Windows local tests. | Critical for Stage B | Stage B blocked on Linux-equivalent suite, adversarial fixture matrix, determinism, and explicit skipped-test accounting. | Stage B gate; not a Stage A retrieval gate |
| R-014 | Dependency lock does not prove the executing runtime. | Medium | Record runtime versions and describe lock hash as reference evidence only. | Active limitation |
| R-015 | LF conversion changes signed files. | High | Repository LF policy, catalog/schema/lock attributes, full-catalog verification tests. | Controlled |
