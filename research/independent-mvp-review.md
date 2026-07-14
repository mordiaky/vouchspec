# Independent local-MVP review record

**Review date:** 2026-07-13
**Scope:** read-only code, API/MCP, receipt, claim, and regression review of the controlled
local-development profile. External production readiness was explicitly out of scope except
for preserving documented launch blockers.

## Initial material findings

| Severity | Finding | Disposition |
|---|---|---|
| P0 | NTFS directory junction traversed outside the artifact root and included external bytes in a receipt. | Fixed with Windows reparse rejection and native regression. |
| P1 | Deep/malformed parser shapes could raise uncaught exceptions. | Fixed with restricted grammar, typed failures, and hostile parser tests. |
| P1 | Derived references and requirement evidence could grow without output bounds. | Fixed with hard caps and machine-readable coverage/truncation. |
| P1 | MCP duplicated the full artifact-derived receipt into unstructured text. | Fixed with a constant TextContent result and receipt-only structuredContent. |
| P1 | Composite action interpolated inputs into a shell script and lacked root confinement. | Fixed with quoted environment variables and `GITHUB_WORKSPACE` allow-root. |
| P1 | Windows CLI stdout was locale/newline transformed rather than deterministic UTF-8/LF. | Fixed and byte-equivalence regression added. |
| P1 | Git URL query credentials survived sanitization. | Fixed; userinfo, query, and fragment no longer enter receipts. |
| P2 | Receipt said zero indicators despite inferred requirement indicators. | Wording now says zero risk-rule findings. |
| P2 | Schema left important evidence objects unconstrained. | Full object contracts and mutation regressions added. |
| P2 | Digest assurance, capture mode, rules/policy/lock binding, and non-JCS semantics were incomplete. | Explicit digest-only assurance, capture data, profiles/digests, and replacement warning added. |
| P2 | Manifest parse failures could look complete; loopback stalled client could block service. | Coverage failure records plus threaded/timeout loopback server and regressions added. |

## Final gate matrix

| Gate | Final result |
|---|---|
| Windows junction/reparse and hard-link containment | Pass |
| Restricted YAML/JSON and malformed-link handling | Pass |
| Derived-output bounds and partial-coverage reporting | Pass |
| MCP artifact-text isolation | Pass |
| CI input confinement | Pass |
| UTF-8/LF stdout determinism | Pass |
| Git credential/query redaction and raw-blob equality | Pass |
| Strict receipt schema and semantic integrity | Pass |
| Digest-only/capture/methodology disclosure | Pass |
| Loopback stalled-client isolation | Pass |
| Checked-in public receipt current and reproducible | Pass |

Final independent result: **PASS**. Receipt/schema/integrity/file hashes are valid; restricted
YAML and terminology checks pass; suite result is `34 passed, 1 skipped`. The single skip is
ordinary Windows symlink creation due host privilege; real Windows junction/reparse and
hard-link tests ran successfully.

A focused post-merge review also passed the Git checkout portability correction. An
independent `core.autocrlf=true` clean-room checkout retained LF-only bytes and the exact
receipt, schema, and lock SHA-256 values bound by the receipt. The added regression asserts
the repository rules and the current schema/lock byte bindings. No P0-P2 finding remained.

Remaining local-profile P0/P1/P2 findings: **none**.

This pass is not a safety certification and does not apply to external uploads, remote MCP,
multi-tenant service, signing, or hostile execution. Those remain explicit launch blockers.
