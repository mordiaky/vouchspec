# OpenAI skill-creator receipt summary

This local sample demonstrates exact-byte non-executing evidence for the public
[`skill-creator` directory at commit `49f948f`](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator).

| Field | Value |
|---|---|
| Files / bytes | 7 / 56,734 |
| Artifact directory SHA-256 | `8145c5d9c0acc1926a17757a3ee68083ddcf813e9fc313894f8ae08b36a2efc4` |
| Receipt ID | `cpr_b37e70baa4bf79bb8cdb3425` |
| Evidence SHA-256 | `b37e70baa4bf79bb8cdb3425ae53bf944ee549f00cea76e264743f9887fc2fed` |
| Receipt-file SHA-256 | `F08EE57A1377C196557F1688A4FF7CC340A721A522580E1E4CABF749C775347C` |
| Structural result | Pass; 0 findings |
| Static risk-rule result | 0 findings |
| Highest contiguous evidence level | 3 |
| Integrity | Digest-only unauthenticated |

The analyzer inferred filesystem-read, filesystem-write, and process-spawn signals from
source text. It did not detect network or secret-access requirement signals under its listed
rules. These are static observations, not runtime behavior.

The checkout file set and every captured byte sequence matched raw blobs at the recorded Git
commit. A `LICENSE.txt` file was present; no license terms or publisher identity were
interpreted or verified. No artifact content was executed, imported, rendered, or fetched.

The receipt is bound to a non-atomic local snapshot with re-enumeration and opened-handle
checks. It uses a named deterministic JSON profile that is not RFC 8785 JCS, has no issuer
signature, and can be replaced and rehashed by an attacker. It is sample evidence, not a
safety approval, production attestation, or recommendation to install.
