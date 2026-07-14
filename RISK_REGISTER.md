# Risk register

| ID | Risk | Severity | Control | Status |
|---|---|---|---|---|
| R-001 | Evidence is mistaken for a safety guarantee. | High | Exact digest, method, coverage, limitations, expiry, and no safe/certified label. | Active |
| R-002 | Hostile artifacts exploit the validator or escape the root. | High | Non-execution, bounded parsing, no-follow/reparse/hard-link rejection, opened-handle checks, re-enumeration, hostile regressions. | Local profile reviewed; external blocked |
| R-003 | Static rules produce false positives or false negatives. | High | Rule IDs, locations, bounded redacted evidence, coverage signals, and explicit not-detected semantics. | Active |
| R-004 | Working name conflicts with an existing product/category. | High | Internal codename only; distinctive-name screen before public use; no legal-clearance claim. | Confirmed practical conflict |
| R-005 | Free scanners/registries make the offer noncommercial. | High | Portable policy-receipt wedge and strict full-price 2/25, 1/15 transaction gates. | Competitive pressure confirmed; demand unvalidated |
| R-006 | License or privacy constraints prohibit processing/redistribution. | High | Public/synthetic or authorized inputs only; return evidence rather than artifact bytes; no license interpretation. | Active; external private intake blocked |
| R-007 | Receipt is replaced, forged, or stale. | High | Current receipt explicitly digest-only unauthenticated; external issuance blocked until JCS signing, authenticated key, rotation/revocation, and invalidation. | Local disclosure complete; external control absent |
| R-008 | Scope consumes budget before demand. | Medium | USD $0 local proof, one artifact format, explicit deferrals and stop rules. | Controlled |
| R-009 | Deterministic JSON is misrepresented as RFC 8785 canonicalization. | High | Versioned profile string explicitly says not JCS; docs use deterministic terminology. | Controlled locally |
| R-010 | External HTTP/MCP exposes host paths, tenants, or resources. | Critical | No external service; require immutable uploads, auth/TLS/object authorization, isolation, rate/queue limits, and remote MCP profile. | Launch blocker |
| R-011 | Git provenance is mistaken for publisher identity. | High | Raw commit-blob equality is separate from publisher/ownership, which remains not checked. | Controlled by schema/limitations |
| R-012 | Reference dependency lock does not describe actual runtime. | Medium | Record runtime package versions and state that lock digest is reference evidence, not installation proof. | Active limitation |
| R-013 | Git line-ending conversion changes byte-addressed receipts or methodology inputs. | High | Repository-wide LF checkout policy, explicit receipt/schema/lock attributes, fixed file hashes, and regression coverage. | Controlled |
