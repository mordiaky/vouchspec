# 2026-07-13 E-001 verification record

## Outcome

E-001 passed for the bounded local-development profile after independent review found and
forced remediation of material defects. This does not authorize external artifact intake.

## Real public artifact

- Repository: `https://github.com/openai/skills.git`
- Commit: `49f948faa9258a0c61caceaf225e179651397431`
- Path: `skills/.system/skill-creator`
- Captured files: 7
- Captured bytes: 56,734
- Directory digest: `8145c5d9c0acc1926a17757a3ee68083ddcf813e9fc313894f8ae08b36a2efc4`
- Git evidence: exact tracked set plus raw blob equality for every captured file; origin query
  and user credentials are stripped; publisher identity remains not checked.

## Final receipt

- Path: `receipts/public/openai-skill-creator-49f948faa9258a0c61caceaf225e179651397431.json`
- Receipt ID: `cpr_b37e70baa4bf79bb8cdb3425`
- Evidence SHA-256: `b37e70baa4bf79bb8cdb3425ae53bf944ee549f00cea76e264743f9887fc2fed`
- File SHA-256: `F08EE57A1377C196557F1688A4FF7CC340A721A522580E1E4CABF749C775347C`
- File size: 16,618 bytes
- Fixed timestamp: `2026-07-14T03:20:53Z`
- Expiry: `2026-07-21T03:20:53Z`
- Integrity assurance: `digest-only-unauthenticated`
- Result: format pass; highest contiguous Level 3; 0 structural findings; 0 risk-rule findings.
- Inferred requirement signals: filesystem read, filesystem write, and process spawn.
- Static non-detections: network and secrets. These mean not detected, not absent.

Two independent fixed-time regenerations produced identical 16,618-byte files and the same
file SHA-256. The checked-in receipt passes Draft 2020-12 schema validation with format checks
and the semantic integrity verifier.

## Verification commands

```powershell
.venv\Scripts\capabilityproof.exe inspect-git <skill-path> `
  --repository-root <checkout-root> `
  --generated-at 2026-07-14T03:20:53Z `
  --expires-in-days 7 `
  --output <receipt-path>

.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m pip check
```

Final test result: `34 passed, 1 skipped`; dependency check: no broken requirements. The
skipped case requires Windows ordinary-symlink privilege. Native Windows junction/reparse and
hard-link escape regressions ran and passed. Full MCP stdio initialization negotiated protocol
revision `2025-11-25`, returned the receipt in `structuredContent`, and returned only fixed
server text in unstructured content.

A post-merge Windows checkout gate caught Git line-ending conversion changing the public
receipt file SHA-256 and the schema/lock bytes bound into receipts. Repository attributes now
force LF for all detected text and explicitly bind receipts, schemas, and `requirements.lock`;
the 34th regression checks those rules. After a clean checkout, the public receipt returned to
the recorded 16,618 bytes and `F08EE57A...347C` file SHA-256.

## Independent-review-driven changes

- Rejected Windows directory junctions/reparse points and hard links after a reproduced P0
  outside-root inclusion.
- Added path/entry/directory/depth/byte limits, opened-handle identity checks, and post-capture
  inventory comparison.
- Bounded references, findings, dependencies, hosts, and requirement evidence; surfaced every
  truncation or manifest-parse failure.
- Rejected deep/malformed YAML/JSON, duplicate/complex keys, anchors, aliases, merge keys,
  implicit timestamps, non-finite values, NUL, and malformed URI references.
- Made CLI stdout byte-identical UTF-8/LF, stripped Git URL credentials/query data, and bound
  provenance to raw commit blobs.
- Kept artifact-derived MCP data out of unstructured content and confined CI inputs through
  environment variables plus the workspace root.
- Replaced ambiguous canonical terminology with a named deterministic non-JCS profile.
- Made receipt integrity explicitly digest-only unauthenticated and bound schema, ruleset,
  policy limits, methodology, runtime, capture mode/times/source, and limitations.
- Forced stable LF checkout bytes and added a regression after Windows Git conversion was
  observed changing byte-addressed evidence.

## Residual boundary

No remaining P0-P2 finding exists for the reviewed local profile. External launch remains
blocked by the controls listed in `research/mvp-threat-model.md` and `COMPLIANCE_CHECKLIST.md`.
