# Initial offer — exact-version Agent Skill evidence

## For whom

Agent Skill publishers and small teams operating coding or document agents.

## Problem solved

A discovered `SKILL.md` package may be correctly formatted while still hiding broad
requirements, mutable downloads, dangerous instructions, or unclear provenance.

## Customer receives

- One canonical JSON Capability Receipt for exact submitted bytes.
- SHA-256 digest and file inventory.
- Structural/specification findings.
- Extracted dependencies, commands, file/network/secrets indicators, and referenced files.
- Transparent static-risk findings with locations and evidence excerpts.
- Test timestamp, methodology version, evidence level, limitations, and expiry.

## Customer provides

A public, licensed repository/version or an artifact they are authorized to submit.
No credentials, private owner files, or production access.

## Delivery

Provisional: machine-readable response after deterministic validation. Delivery time will
be published only after E-001 measures it.

## Price

Provisional validation hypothesis: USD $19 for a publisher-funded Level 1–3 release receipt.

## Included

Non-executing structural, provenance, requirement, and static-risk evidence for one exact version.

## Excluded

Sandbox execution, runtime guarantee, penetration testing, legal/license advice, universal
safety certification, custom consulting, calls, and unlimited support.

## Acceptance criteria

The receipt parses against the published schema, identifies exact input bytes, lists every
checked file, exposes findings with locations, and reproduces byte-for-byte when volatile
timestamps are fixed by the test harness.

## Remediation and refund hypothesis

If the delivered JSON is malformed or references the wrong artifact digest, rerun once at
no charge; if still defective, refund the validation charge. Findings are evidence under
stated conditions, not a promise that no defect or malicious behavior exists.

