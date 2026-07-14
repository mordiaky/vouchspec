# Stage A catalog build and evidence-delivery SOP

## Authorized scope

Use only deliberately selected public Agent Skill repositories from the checked-in manifest,
at full commits and explicit subdirectories. Do not accept uploads, private repositories,
customer-confidential inputs, or artifact-provided source URLs.

## Procedure

1. Run the networked keyless collector; never make issuer or root private keys available to
   that process.
2. Require exact Git remote, full commit, clean checkout, raw-blob equality, and zero hidden
   source skips. Never execute artifact content.
3. Review the keyless build report and retain real structural failures as evidence.
4. In a separate no-network process, validate and issuer-sign every exact receipt payload
   and the exact catalog index.
5. In a separate offline process, verify all issuer signatures, increment the previous
   trusted lifecycle sequence, authorize issuer status, and root-sign the lifecycle feed.
6. Run the full test suite and whole-catalog verification with an independently pinned root
   thumbprint and external sequence-state file.
7. Record pass/fail counts, every skip, key IDs, feed/receipt expiry, build cost, and limits.
8. Publish signed evidence only. No original artifact files, archives, or executable payloads
   are distributed; receipts may include bounded redacted metadata and evidence excerpts.

## Stop conditions

Stop on any path/link/blob mismatch, parser crash, hidden partial coverage, signature/schema/
integrity failure, stale or non-incrementing lifecycle feed, key-role co-location, unpinned
root, or unresolved P0/P1 review finding. Never describe output as safe, malware-free,
publisher-verified, or behavior-tested unless that specific evidence exists.
