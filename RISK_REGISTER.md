# Risk register

| ID | Risk | Severity | Control | Status |
|---|---|---|---|---|
| R-001 | Customers interpret evidence as a safety guarantee. | High | Exact digest, methods, limitations, timestamps, expiry, and no “safe/certified” label. | Active |
| R-002 | Hostile artifacts exploit the validator. | High | Treat bytes as data; no import/exec/render; size/file limits; path containment; adversarial tests. | In implementation |
| R-003 | Static findings create false positives/negatives. | High | Evidence snippets, rule IDs, severity rationale, and explicit unknowns. | Active |
| R-004 | Working name conflicts with another product or mark. | Medium | Current search before public use; no legal-clearance claim. | Researching |
| R-005 | Free scanners/registries make the wedge noncommercial. | High | Test willingness to pay for exact-version receipts/workflow; stop rules. | Unvalidated |
| R-006 | Licenses prohibit redistribution. | High | Analyze public/customer-authorized inputs; return evidence, not artifact bytes; record license uncertainty. | Active |
| R-007 | Receipt tampering or stale evidence. | High | Canonical JSON digest now; public-key signing and invalidation before production. | Partial |
| R-008 | Broad scope consumes budget before demand. | Medium | Level 1–3 `SKILL.md` only; USD $0 MVP; explicit deferrals. | Controlled |

