# CapabilityProof v0.1 methodology

## Scope and security profile

The scanner accepts one local directory containing `SKILL.md`. This mode is limited to
controlled public or synthetic artifacts. It inventories regular files; rejects symbolic
links, Windows reparse points/junctions, hard links, and special files; enforces bounded
entry, directory, depth, path, byte, reference, finding, dependency, and evidence limits;
and excludes only version-control metadata directories from the artifact scope.

The loopback HTTP and MCP stdio surfaces are local developer integrations. They are not an
external intake, customer-data, or production security boundary.

## Checks

1. **Snapshot:** opened-handle identity checks, post-capture re-enumeration, sorted relative
   paths, per-file SHA-256, and a length-prefixed directory digest bind analysis to immutable
   in-memory bytes. Local directory capture remains non-atomic and says so in the receipt.
2. **Structure:** YAML is parsed with a duplicate-key-rejecting `SafeLoader` after
   frontmatter, alias, depth, and node limits. Published Agent Skills field constraints are
   checked deterministically. Parser/coverage limits fail closed or force review.
3. **References:** local Markdown and common skill-resource references must remain inside
   the inventory. URI-like local references fail; external references lose credentials and
   query strings and are never fetched.
4. **Static review:** fixed rule IDs scan bounded UTF-8 text. Matches are indicators, not
   observed runtime behavior. Evidence excerpts are length-limited and secret-redacted.
   Dependency-manifest parse failures and all truncation states are machine-readable.
5. **Receipt:** artifact-derived strings are labeled untrusted. Results list limitations,
   expiry, completed/not-run levels, coverage, capture timing source, policy/methodology
   digests, runtime versions, and a deterministic evidence SHA-256.

The receipt serialization profile is sorted compact UTF-8 JSON with `ensure_ascii=false`
and `allow_nan=false`. The exact profile string is carried in every receipt. It is not RFC
8785 JCS.

## Git provenance option

The optional local Git path verifies that the artifact is inside the repository top level,
the snapshot file set exactly equals tracked files, every captured byte sequence equals its
raw `HEAD` blob, no submodule is in scope, and `HEAD` plus a credential/query-redacted origin
identify the source. It never fetches.

The Git subprocess environment disables hooks, external diff, fsmonitor, untracked cache,
global/system config, credentials, pagers, and prompts. Only controlled plumbing commands
are used. This does not verify publisher identity or repository ownership.

## Integrity limits

The receipt binds the complete scan-limit profile, structural/static profile identifiers,
static ruleset digest, runtime versions, schema digest, and reference dependency-lock
digest. The lock digest identifies the tested reference environment but cannot prove that
a runtime was installed from that lock.

Receipts are `digest-only-unauthenticated`. Anyone replacing a receipt can recompute its
hash and ID. External/public issuance requires a different immutable-envelope, isolated
worker, JCS, signature, authenticated-key, authentication, tenant-isolation, rotation,
revocation, and invalidation profile.

## Explicit non-claims

The MVP does not verify publisher identity, signatures, runtime compatibility, absence of
malware, task performance, trigger quality, network behavior, or safety in other
environments. It does not execute content. A clean result means only that listed rules did
not detect a listed pattern in files that were actually scanned.
