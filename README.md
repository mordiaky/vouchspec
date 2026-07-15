# VouchSpec

VouchSpec is the provisional public-beta name for an independent evidence index for exact
Agent Skill versions. The name passed a $0 obvious-conflict screen; it has not received
formal legal or trademark clearance.

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
- Managed agent API: <https://vouchspec-sandbox.plyrium.com/api/vouchspec/v1/health>
- Managed API discovery: <https://vouchspec-sandbox.plyrium.com/api/vouchspec/v1/discovery>
- Agent quickstart: <https://vouchspec-sandbox.plyrium.com/vouchspec>
- Signed index over managed TLS: <https://raw.githubusercontent.com/mordiaky/vouchspec/main/catalog/public/index.dsse.json>
- Root-signed lifecycle feed: <https://raw.githubusercontent.com/mordiaky/vouchspec/main/catalog/public/lifecycle.dsse.json>
- Out-of-band root/issuer key publication: <https://gist.github.com/mordiaky/794e30c1c33ba1663921718cc8d530e1>

The static distribution returns the exact checked-in signed bytes with CORS enabled and
rejects writes. Download the signed index, filter it locally, then retrieve a receipt by ID
from `catalog/public/receipts/`. For immutable retrieval, replace `main` with catalog snapshot
`4404b7a9a2d3dc45b621ea694d2ca7ad666b9898`. The out-of-band Gist is separate from the
repository but shares its GitHub account, so an account-level compromise still requires a
new trusted channel.

## Product stages

- **Stage A — public artifact index (live):** selected public artifacts only; signed
  receipts and read-only REST/MCP retrieval; no uploads, private repositories, or
  customer-confidential content.
- **Stage B — public repository validation (public testnet sandbox):** allowlisted public
  host, full commit, explicit subdirectory, bounded immutable retrieval, isolated no-egress
  worker, separate no-egress signing, durable tenant/order/payment state, an authenticated
  managed API, and exact x402 settlement using test USDC on Base Sepolia. Testnet orders are
  self-service and fully fulfilled; mainnet settlement remains disabled.
- **Stage C — private/arbitrary inputs (deferred):** private storage, authentication,
  tenant isolation, deletion policy, and expanded legal/incident controls only after
  demand and revenue justify them.

Stage C is not a prerequisite for Stage A or B. No arbitrary upload route exists in the
Stage A server or MCP tools.

## Publisher CI — complete self-service example

The public [publisher-CI demo](https://github.com/mordiaky/vouchspec-demo) shows the complete
trusted-workflow path: immutable action pins, exact-commit inspection, two GitHub artifact
attestations, downloadable evidence, and independent `gh attestation verify` commands. The
latest [verified matrix run](https://github.com/mordiaky/vouchspec-demo/actions/runs/29331787790)
passes both a structural-pass case and an intentional structural-failure case. Its four
downloaded evidence files independently verified with `gh attestation verify`. The demo is
operator-controlled and is not counted as external adoption.

Use the action at its immutable evidence-preserving snapshot:

```yaml
- id: vouchspec
  uses: mordiaky/vouchspec/distribution/github-action@ed812a14cbc62333d59bac319f79d897f14d1b64
  with:
    skill-path: path/to/skill
```

The action emits a receipt draft and publisher/workflow binding for both structural passes
and explicit structural failures. See the [full pinned workflow, permissions, verification,
and troubleshooting guide](distribution/github-action/README.md).

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

The local catalog price-card route reports the commercial price hypothesis without accepting
an order. For a strict request-specific local preview:

```powershell
vouchspec quote-fresh-validation docs\examples\fresh-validation-request.json
```

The preview validates the same request shape used by the managed API. The public sandbox price
is deliberately faucet-sized at **1.00 test USDC**. Full agent-market research rejected the
earlier $49 idea; the commercial mainnet launch cohort is an unvalidated **0.25 USDC** per fresh
validation, with the predeclared evidence gates in `PRICING.md`.

## Agent-only x402 sandbox

The public service at `https://vouchspec-sandbox.plyrium.com` has no card form, hosted checkout,
or human approval step. An agent:

1. accepts terms version `vouchspec-stage-b-2026-07-14` at
   `POST /api/vouchspec/v1/tenants` and stores the one-time tenant bearer key;
2. sends the strict fresh-validation request to `POST /api/vouchspec/v1/quotes` with
   `Authorization` and a unique `Idempotency-Key`;
3. creates an order at `POST /api/vouchspec/v1/orders` and stores the returned delivery token;
4. calls the order's `purchase_path`, reads the x402 v2 `PAYMENT-REQUIRED` challenge, signs the
   exact 1.00 test-USDC payment on Base Sepolia, and retries with `PAYMENT-SIGNATURE`;
5. polls the authenticated order, retrieves the exact DSSE result, and verifies it with the
   public issuer JWK.

Successful envelopes are also published at a content-addressed unauthenticated URL. Agents may
cache and share those immutable bytes. Invalidation is intentionally separate: check the
corresponding no-store `/status` URL each time the receipt is used for a new decision. The
[machine-readable discovery document](distribution/discovery.json) contains all route templates,
headers, network, price, trust, caching, and product-boundary fields.

The hosted proof is owner-controlled and testnet-only, so it demonstrates mechanics but counts
as no customer, request, buyer, or revenue. See the [Stage B operating boundary](docs/stage-b-operations.md),
[payment flow](docs/payment-flow.md), [managed deployment boundary](deploy/README.md), and
[refund policy](docs/refund-policy.md), and
[mainnet remedy operations](docs/mainnet-remedy-operations.md).

## Local commerce harness

The repository still includes a loopback harness for regression and security testing. It stores
keyed credential digests, never plaintext tokens, and binds each quote and order to one opaque
tenant. Generate two distinct 32-byte secrets with an approved secret manager, expose their hex
values only to the process, then provision one local sandbox credential:

```powershell
$env:VOUCHSPEC_AUTH_PEPPER_HEX = '<64 hex characters>'
$env:VOUCHSPEC_DELIVERY_SECRET_HEX = '<different 64 hex characters>'
vouchspec provision-commerce-tenant --database C:\vouchspec\sandbox-commerce.db
vouchspec serve-commerce-sandbox --database C:\vouchspec\sandbox-commerce.db --port 8789
```

The local API binds to `127.0.0.1`, has no CORS allowance, and exposes authenticated quote, order,
status, signed-result, capability-rotation, and capability-revocation routes. Its fake payment
rail never settles and every resulting order remains `counts_for_goal: false`.

An explicitly nonsettling Stripe-test adapter remains available for regression coverage only.
It is not the VouchSpec launch rail and is not exposed by the managed agent service:

```powershell
vouchspec serve-commerce-stripe-test `
  --database C:\vouchspec\stripe-test-commerce.db --port 8789
```

Do not expose that built-in listener directly. Mainnet activation uses x402, separate live state
and secrets, and the live gates in [the deployment boundary](deploy/README.md).

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
and named price-card operations only, not artifact content. This local read-only MCP does not
place paid orders; agents use the managed x402 API for fresh validation.

## Local inspector and builder

Development install:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

The compatibility command and Python package name `capabilityproof` remain available
alongside the public `vouchspec` command.

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
