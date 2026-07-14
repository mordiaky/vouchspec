# Goal evidence

The charter goal is **not achieved**: USD $0 spend, USD $0 settled revenue, zero customers,
zero legitimate external machine requests, no genuine external publisher CI integration,
and no payment rail or customer delivery. Public retrieval is live, but operator-owned smoke
traffic is not demand evidence.

## Stage A product evidence

- Provisional beta name: `VouchSpec`; $0 obvious-conflict screen complete; no formal legal or
  trademark clearance.
- Corpus: 25 deliberately selected public Agent Skill artifacts at full Git commits across
  12 GitHub repository owners; 251 listed files and 2,044,855 source bytes were independently
  reproduced in the first audit.
- Outcomes: 19 structural passes, six signed structural failures, zero skipped artifacts.
- Claims: all 25 carry `DIGEST_PINNED`, `STATIC_INSPECTION_COMPLETED`, and
  `INDEPENDENT_STATIC_SCAN`; only the 19 passes carry `STRUCTURE_VALIDATED`.
- Authentication: every exact receipt payload is in a DSSE v1.0.2 Ed25519 envelope; the
  catalog index is issuer-signed; a separate recovery root signs issuer authorization and
  lifecycle state.
- Isolation: collection is networked and keyless; issuer signing is a separate no-network
  phase; recovery-root signing is a separate offline lifecycle-only phase. Rotated keys were
  generated after the original combined-process review finding.
- Trust: root and issuer JWKs/thumbprints are pinned in regression tests and published in a
  separate public Gist. Bundled keys remain discovery material; the Gist shares the GitHub
  account and therefore does not survive account-level compromise.
- Lifecycle: current/superseded/expired/evaluator-defect/key-compromise plus conservative
  stale/rollback unknown; highest accepted sequence persists outside catalog storage.
- Interfaces: exact signed files are live through GitHub-managed TLS/CORS; remote byte-parity
  probes pass and POST is rejected. The stdio MCP is publicly installable and passed a clean
  public-clone tool-discovery smoke. Dynamic query serving remains a local/self-host option.
- Boundary: no uploads/private artifacts/customer content; no artifact code execution. The
  catalog distributes no original artifact files or executable payloads, but receipts contain
  bounded artifact-derived metadata and redacted excerpts.
- Current main verification suite: 54 tests pass; one ordinary Windows symlink test skips because the host
  lacks symlink privilege, while Windows junction and hard-link regressions pass. Stage B
  remains blocked on Linux-equivalent and full adversarial/cross-OS coverage.

Evidence: `catalog/public/`, `catalog/sources.json`, `tests/test_public_receipt.py`,
`tests/test_signing.py`, `tests/test_lifecycle.py`, and `tests/test_catalog.py`.

## External alpha acceptance

| # | Test | Status |
|---:|---|---|
| 1 | Provisional public name selected | Pass locally |
| 2 | At least 25 public skills indexed | Pass: 25 |
| 3 | At least 10 repository-owner namespaces | Pass: 12; publisher identity and corporate independence remain unverified |
| 4 | Exact commits and content digests | Pass locally |
| 5 | Receipts cryptographically signed | Pass locally: 25 |
| 6 | Public verification method works | Pass: public source/catalog plus out-of-band JWK Gist |
| 7 | REST retrieval live | Pass: static exact-byte GET over managed TLS/CORS; write probe rejected |
| 8 | MCP retrieval live | Pass: public installable stdio MCP; clean-clone tool discovery succeeded |
| 9 | One external repository uses publisher CI route | Pending |
| 10 | Ten legitimate external machine requests | Pending: 0 |
| 11 | Three repeat external requests | Pending: 0 |
| 12 | One genuine machine-paid settlement | Pending: USD $0 |
| 13 | Actual compute/infrastructure cost recorded | Pass for current launch: $0 local spend and $0 GitHub free-tier hosting |
| 14 | No arbitrary upload/private artifact | Pass locally |
| 15 | No owner call/meeting/routine manual fulfillment | Pass locally; external operation unproven |

## Charter acceptance

The segment/problem and offer are documented, public Stage A retrieval is automated, and
records/budget controls are current. Acquisition, payment, three unaffiliated customers,
USD $500 settled gross, customer delivery, positive margin, repeatability, and final
independent goal audit all remain pending. No completion, demand, revenue, safety, or
commercial-validation claim follows from the public product proof.
