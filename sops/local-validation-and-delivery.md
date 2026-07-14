# Local validation and evidence-delivery SOP

## Authorized scope

Use only controlled public or synthetic Agent Skill directories. Do not accept customer,
private, remotely submitted, or otherwise untrusted third-party artifacts under this SOP.

## Procedure

1. Confirm the source is public/synthetic and record the exact commit or controlled origin.
2. Use a credential-free, hook-disabled local checkout; never execute artifact content.
3. Run `inspect-git` with a fixed UTC timestamp for reproducible evidence.
4. Regenerate to a second output and require byte equality plus equal SHA-256.
5. Validate the receipt against the Draft 2020-12 schema with format checking.
6. Run semantic integrity verification and verify the recorded artifact/file digests.
7. Run the full test suite, dependency check, and MCP stdio smoke.
8. Record structural findings, risk-rule findings, inferred requirements, coverage, skipped
   areas, capture mode, expiry, integrity assurance, and every explicit limitation.
9. Deliver receipt evidence only; never redistribute artifact bytes unless separately licensed.

## Stop conditions

Issue no successful receipt after any path/link/identity mismatch, parser crash, hidden partial
coverage, non-determinism, schema/integrity failure, or unresolved P0/P1 review finding. Do not
describe any output as safe, certified, malware-free, publisher-verified, or production-ready.
