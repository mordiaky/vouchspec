# Assumptions ledger

| ID | Assumption | Current status | Decisive test |
|---|---|---|---|
| A-001 | Machines will use a free public exact-version receipt index. | Untested externally; 25-entry signed catalog exists locally. | 10 legitimate external machine requests, including three repeat requests. |
| A-002 | A caller will pay a microprice for comparison, fresh static evidence, or signed issuance. | Untested; no payment rail. | One genuine machine-initiated settled request at a quoted nonzero price. |
| A-003 | Static evidence can be produced without artifact execution. | Supported by 25 public catalog runs, zero skips, local tests, and explicit non-execution. | Reopen on any execution, containment escape, hidden skip, or digest/source mismatch. |
| A-004 | `VouchSpec` has acceptably low obvious public-beta conflict risk. | Provisional screen supports; no legal/trademark clearance. | Re-screen before material brand spend; obtain professional review only when justified. |
| A-005 | Exact-byte portable evidence is more useful than another score/badge. | Plausible; usage and transaction evidence absent. | Repeat machine retrieval, external CI adoption, and paid requests. |
| A-006 | Stage A can launch safely without Stage C upload/auth/tenant infrastructure. | Supported by retrieval-only public data, no submission route, and closed P0-P2 Stage A review. | Reopen on any live boundary-probe failure or route expansion. |
| A-007 | Stage B public-repository validation can fit budget. | Untested. | Linux-equivalent isolation, adversarial fixtures, cross-OS determinism, and measured unit cost. |
