# VouchSpec

VouchSpec is the provisional public-beta name for an independent evidence index for exact
Agent Skill versions. `CapabilityProof` remains the internal package/codename during the
transition. The name passed a $0 obvious-conflict screen; it has not received legal or
trademark clearance.

The current Stage A catalog contains **25 deliberately selected public Agent Skills across
12 GitHub repository owners**. Every entry is pinned to a full Git commit and exact directory digest,
statically inspected without executing artifact code, wrapped in a DSSE v1.0.2 envelope,
and signed with Ed25519. A separate root key signs the machine-readable lifecycle feed.

This is evidence, not a safety certification. Six of the 25 real-world skills fail at least
one current structural rule; they remain indexed with the failure evidence and are not
labeled `STRUCTURE_VALIDATED`.

## Public Stage A distribution

- Repository and install source: <https://github.com/mordiaky/vouchspec>
- Machine-readable discovery: <https://raw.githubusercontent.com/mordiaky/vouchspec/main/distribution/discovery.json>
- Signed index over managed TLS: <https://raw.githubusercontent.com/mordiaky/vouchspec/main/catalog/public/index.dsse.json>
- Root-signed lifecycle feed: <https://raw.githubusercontent.com/mordiaky/vouchspec/main/catalog/public/lifecycle.dsse.json>
- Out-of-band root/issuer key publication: <https://gist.github.com/mordiaky/794e30c1c33ba1663921718cc8d530e1>

The static distribution returns the exact checked-in signed bytes with CORS enabled and
rejects writes. Download the signed index, filter it locally, then retrieve a receipt by ID
from `catalog/public/receipts/`. For immutable retrieval, replace `main` with release commit
`4404b7a9a2d3dc45b621ea694d2ca7ad666b9898`. The out-of-band Gist is separate from the
repository but shares its GitHub account, so an account-level compromise still requires a
new trusted channel.

## Product stages

- **Stage A — public artifact index (current):** selected public artifacts only; signed
  receipts and read-only REST/MCP retrieval; no uploads, private repositories, or
  customer-confidential content.
- **Stage B — public repository validation (later):** allowlisted public host, full commit,
  explicit subdirectory, bounded immutable retrieval, isolated worker, and signed result.
- **Stage C — private/arbitrary inputs (deferred):** private storage, authentication,
  tenant isolation, deletion policy, and expanded legal/incident controls only after
  demand and revenue justify them.

Stage C is not a prerequisite for Stage A or B. No arbitrary upload route exists in the
Stage A server or MCP tools.

## Evidence labels

Receipts use explicit labels, never a generic `VERIFIED` badge:

- `DIGEST_PINNED`
- `STRUCTURE_VALIDATED` (only when the structural profile passes)
- `STATIC_INSPECTION_COMPLETED`
- `INDEPENDENT_STATIC_SCAN` (only for the curated operator-run profile)

`PUBLISHER_CI_ATTESTED`, `SANDBOX_BEHAVIOR_OBSERVED`, and `TASK_EVALUATED` are reserved for
separate evidence that has actually been produced. Static inspection never implies them.

## Verify a public receipt independently

The verifier authenticates the exact decoded receipt bytes before parsing JSON, validates
the receipt schema and inner consistency digest, then optionally applies the root-signed
lifecycle feed.

```powershell
vouchspec verify catalog\public\receipts\RECEIPT_ID.dsse.json `
  --key catalog\public\keys\issuer.jwk.json `
  --lifecycle catalog\public\lifecycle.dsse.json `
  --root-key catalog\public\keys\root.jwk.json
```

Lifecycle results are `CURRENT`, `SUPERSEDED`, `EXPIRED`,
`REVOKED_EVALUATOR_DEFECT`, `REVOKED_KEY_COMPROMISE`, or the conservative
`SIGNATURE_VALID_LIFECYCLE_UNKNOWN`. The signing key ID is only a lookup hint; the public
JWK must be obtained or pinned through an independently trusted path.

## Read-only catalog API

```powershell
vouchspec serve-catalog --catalog-root catalog\public --port 8788 `
  --trusted-root-key C:\independently-provisioned\root.jwk.json
```

Available `GET` routes:

- `/health`
- `/v1/index` (issuer-signed DSSE index envelope)
- `/v1/quote?operation=...` (price/availability response; paid orders remain disabled)
- `/v1/receipts?q=...&repository_owner=...&limit=...`
- `/v1/receipts/{receipt_id}`
- `/v1/receipts/{receipt_id}/status`
- `/v1/lifecycle`
- `/v1/keys/root`
- `/v1/keys/issuer`

All `POST` requests receive `405 read_only`. The built-in server is connection-bounded,
deadline-enforced, and loopback-only; a public deployment must place it behind a managed TLS
proxy with platform ingress limits. Each process serves one fully verified immutable catalog
snapshot; deploy a new lifecycle/index generation by restarting the process. The highest
observed root-feed sequence and its payload digest are persisted with a cross-process lock.

## Read-only catalog MCP

Public install:

```powershell
git clone https://github.com/mordiaky/vouchspec.git
cd vouchspec
python -m venv .venv
.venv\Scripts\python -m pip install .
.venv\Scripts\vouchspec mcp-catalog --catalog-root catalog\public `
  --trusted-root-key C:\independently-provisioned\root.jwk.json
```

```powershell
vouchspec mcp-catalog --catalog-root catalog\public `
  --trusted-root-key C:\independently-provisioned\root.jwk.json
```

Tools are `search_receipts`, `get_receipt`, `get_receipt_status`,
`get_verification_material`, and `get_price_quote`. They accept identifiers, search text,
and named price-card operations only, not artifact content. Paid operations are reported as
not orderable until their separate safety and settlement gates exist.

## Local inspector and builder

Development install:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

The compatibility command `capabilityproof` remains available alongside `vouchspec`.

```powershell
vouchspec inspect C:\path\to\skill --output receipt.json
vouchspec inspect-git C:\checkout\skills\example `
  --repository-root C:\checkout --output receipt.json
```

Local inspection never installs, imports, renders, or executes artifact content. The
checked-in catalog builder accepts only the curated manifest and public HTTPS GitHub
repositories at full 40-character commits. Collection is keyless, issuer signing is a
separate no-network phase, and recovery-root lifecycle signing is a separate offline phase.
Encrypted private keys stay outside this repository; only RFC 8037 public JWKs are published.

See [methodology](docs/methodology.md), the
[receipt schema](src/capabilityproof/schemas/capability-receipt.schema.json), and the
[threat model](research/mvp-threat-model.md).
