# Decision log

## 2026-07-13 - Select the Agent Skills exact-version wedge

- **Decision:** Build machine-readable evidence for one exact Agent Skill directory containing `SKILL.md`.
- **Reason:** The owner selected a machine-native evidence business; a bounded artifact permits a zero-spend proof.
- **Constraint:** Do not pivot to a conventional manual service.

## 2026-07-13 - First slice is non-executing Level 1-3 evidence

- **Decision:** Snapshot and hash bytes, validate structure, close references, extract
  requirements/dependencies, and emit transparent static findings without importing,
  rendering, fetching, or executing artifact content.
- **Deferred:** Sandboxing, trigger/task evaluation, monitoring, broad discovery, and live payment.

## 2026-07-13 - Position as a portable policy receipt

- **Decision:** Test an independent, registry-neutral exact-byte policy record rather than
  another scanner, badge, catalog, or single vendor score.
- **Evidence:** Strong free substitutes and no direct willingness-to-pay evidence in the
  market/competitor memo.

## 2026-07-13 - Prices remain transaction experiments

- **Decision:** Reject USD $19 as a validated generic-scan offer; retain USD $19 public
  receipt and USD $99 policy pack only as full-price experiments with explicit 2/25 and 1/15
  success gates.

## 2026-07-13 - Keep CapabilityProof as an internal codename

- **Decision:** Choose a distinctive name before any public package, domain, badge, namespace,
  or marketplace listing.
- **Evidence:** SkillProof occupies the same Agent Skills category and the exact compound has
  prior agent-identity use. This is practical conflict evidence, not legal clearance.

## 2026-07-13 - Local proof is not an external service

- **Decision:** Permit only controlled public/synthetic local artifacts in v0.1. Loopback HTTP,
  MCP stdio, CI, and the sample receipt are developer evidence.
- **Launch block:** No public/paid artifact intake until raw immutable ZIP capture, isolated
  no-egress workers, auth/TLS/tenant controls, RFC 8785 JCS, isolated signing/authenticated
  verification key, rotation/revocation/invalidation, and hostile regression evidence pass.

## 2026-07-13 - Close independent audit findings before accepting E-001

- **Decision:** Treat the Windows junction escape as P0 and the stdout, remote-query,
  parser-bound, MCP isolation, CI interpolation, and schema/claim defects as release blockers.
- **Result:** Reparse/junction and hard-link rejection, parser restrictions, derived-output
  caps, MCP structured-only artifact output, deterministic UTF-8 output, strict schema,
  digest-only disclosure, raw Git blob binding, and corresponding regressions now pass.

## 2026-07-13 - Do not grant a public code license autonomously

- **Decision:** Remove the draft Apache-2.0 declarations from the internal package and
  bundled skill. No public license, package publication, or distribution is authorized.
- **Reason:** Selecting distribution terms is a material legal commitment reserved for
  owner approval by the operating charter.

## 2026-07-13 - Make repository checkout bytes deterministic

- **Decision:** Force LF for every detected text file and retain explicit LF rules for public
  receipts, receipt schemas, and the reference dependency lock.
- **Reason:** A Windows checkout converted those files to CRLF after merge, changing the
  receipt file hash and methodology input digests. The checked-in file-hash contract must
  survive a fresh checkout on every supported host.

## 2026-07-13 - Correct launch sequencing to Stage A, B, and C

- **Decision:** Launch first as a read-only index of deliberately selected public artifacts;
  place allowlisted public-repository validation in Stage B; defer private and arbitrary
  uploads to Stage C until demand and revenue justify them.
- **Reason:** Public arbitrary upload remains unsafe, but its controls are not prerequisites
  for serving signed evidence about operator-selected public artifacts.

## 2026-07-13 - Select VouchSpec as the provisional beta name

- **Decision:** Use `VouchSpec` for the constrained public beta and retain `CapabilityProof`
  only as the internal engine/package compatibility name.
- **Evidence:** A $0 obvious-conflict screen found no exact indexed product, GitHub repository,
  account, PyPI package, npm package, or DNS record in the checked set.
- **Qualification:** This is not legal, trademark, entity-name, handle, or domain clearance.

## 2026-07-13 - Authenticate exact receipt bytes with DSSE and Ed25519

- **Decision:** Put the exact receipt payload bytes in a DSSE v1.0.2 envelope and sign DSSE
  PAE with Ed25519; publish RFC 8037 JWKs using RFC 7638 thumbprints.
- **Reason:** Verification authenticates bytes before JSON parsing and never reconstructs
  ambiguous JSON. RFC 8785 JCS is not a cryptographic prerequisite for this profile.
- **Lifecycle:** A separate recovery/root key signs issuer-key and receipt state. A compromised
  issuer key revokes every receipt from that key because issuance timestamps are not trusted.

## 2026-07-13 - Preserve failed public artifacts as evidence

- **Decision:** Index all 25 selected public skills even when a current structural rule fails;
  omit `STRUCTURE_VALIDATED` and publish the signed findings rather than silently replacing
  or hiding the artifact.
- **Result:** 25 signed receipts across 12 source organizations: 19 structural passes, six
  explicit failures, and zero skipped artifacts.

## 2026-07-14 - Select Stripe first and correct fresh-validation pricing

- **Decision:** Use Stripe Checkout as the primary conventional payment rail, retain x402 as
  a later machine-native secondary rail, and test fresh public static validation at USD $49.
- **Reason:** The prior USD $0.10 hypothesis is below Stripe's USD $0.50 minimum and cannot
  absorb the fixed USD $0.30 fee. The revised hypothesis leaves room for a USD $5 direct-cost
  ceiling while remaining a real market test, not a validated price.
- **Current gate:** The worker, store, account-bound Stripe adapter, real unpaid test Checkout,
  and paid lifecycle now pass. Public/live Checkout remains disabled until the adapter is wired
  to the managed authenticated HTTP/webhook boundary, kernel fetch quota exists, and the
  production signing role is provisioned.

## 2026-07-14 - Hash-lock the publisher action runtime

- **Decision:** Run the composite action only on Linux x86-64 with Python 3.11 and install its
  complete dependency graph from a hash-locked binary-only file before using the immutable
  VouchSpec source checkout.
- **Reason:** An unhashed runtime dependency resolution in a workflow holding OIDC and
  attestation permissions could undermine the evidence it produces.

## 2026-07-14 - Prepare discovery listings without accepting owner-bound terms

- **Decision:** Keep GitHub discovery live; defer official MCP Registry publication until a
  supported public package exists, and defer GitHub Marketplace publication until a dedicated
  root-action repository is eligible.
- **Authority boundary:** The owner, not the autonomous agent, will authenticate or accept new
  platform agreements only after all technical eligibility work is complete.

## 2026-07-14 - Use minimal tenant isolation and two-part delivery authorization

- **Decision:** Keep Stage B public-source-only, but bind every sandbox quote/order/result to
  one opaque tenant. Require both an API key and a separate order capability for status/result
  reads; store each only as a keyed digest under distinct environment-bound secrets.
- **Reason:** Object-level authorization is necessary even though private repositories and
  general user accounts remain out of scope. Tenant-scoped idempotency prevents one buyer's
  common retry key from colliding with another's.
- **Capability lifecycle:** order capabilities are retry-safe, environment-specific, valid for
  30 days, and immediately rotatable/revocable. Security-state changes are audited without
  recording tokens or IP addresses.
- **Boundary:** the server is loopback and sandbox only. This does not authorize public
  exposure or live settlement; managed TLS/ingress, exact-body Stripe HTTP/webhook wiring,
  secret operations, kernel fetch quota, and production signing remain launch gates.

## 2026-07-14 - Bind Stripe credentials to explicit accounts and keep root signing offline

- **Decision:** Every Stripe adapter instance must retrieve and match an expected enabled
  account ID before creating Checkout state. Test and live accounts use separate IDs,
  environments, and databases; live Checkout also requires an explicit activation flag.
- **Evidence:** The owner-authorized test and live credentials authenticated to distinct enabled
  accounts. A USD $49 test Session was created, reconciled unpaid, and expired without a charge;
  neither secret nor Checkout URL entered SQLite.
- **Lifecycle:** The online role may build a complete paid-receipt draft and verify/publish an
  exact envelope, but only the offline recovery-root role signs it. Root replacement, rollback,
  equivocation, incomplete receipt/signer coverage, and terminal-state restoration fail closed.
- **Boundary:** This verifies the payment/lifecycle core, not a public service or settled sale.

## 2026-07-14 - Connect Stripe only in explicit loopback test mode

- **Decision:** Inject the reviewed Stripe adapter into the existing authenticated commerce
  server only when the operator selects `serve-commerce-stripe-test`. Keep the fake provider as
  the default and continue refusing every live store.
- **Security shape:** create quotes and orders only after tenant authentication; derive Stripe
  idempotency solely from the immutable stored account/order/quote binding; preserve webhook
  bytes exactly; require one signature header; separate webhook rate capacity from API traffic;
  and return non-2xx for retryable or already-processing reconciliation.
- **Evidence:** 130 local tests pass. One real USD $49 test Checkout traversed the HTTP quote and
  order routes, reported non-live/nonsettling, and was immediately expired unpaid. The secret
  and Checkout URL were absent from the disposable database.
- **Boundary:** This is not a deployment or sale. Managed TLS, a mode-specific public test
  endpoint, restricted durable state, kernel fetch quota, and production signing remain gates.

## 2026-07-14 - Reject $49 for the agent-only market and set a 0.25 USDC launch cohort

- **Decision:** Supersede the Stripe-era $49 hypothesis. Launch Base-mainnet agent-only fresh
  validation at exactly 0.25 USDC only after the remaining safety gates pass.
- **Evidence:** A complete Coinbase CDP Bazaar catalog observation found 12,360 unique
  Base-mainnet USDC resource/scheme/price entries: median $0.01, 95th percentile $0.30, and 99th
  percentile $2.10. Closest code/security operations were $0.10-$1.00. Only 0.15% of observed
  entries cost $20 or more. Free Cisco, NVIDIA, GitHub, Tessl, Snyk, and Socket substitutes
  compress the value of a generic scan. Coinbase wallet spending controls further penalize a
  $49 autonomous call.
- **Economics:** The completed isolated fulfillment used 34 seconds of a Linux runner; the
  published one-minute floor is about $0.006. A conservative $0.05 variable-cost reserve leaves
  $0.20 contribution, or 80%, at 0.25 USDC.
- **Experiment:** Fall to 0.10 USDC only after zero settlements with qualified exposure; test
  0.50 USDC only after three unrelated buyers, one repeat buyer, positive contribution, and a
  low remedy rate. Never personalize price by wallet or buyer.
- **Research:** `research/agent-only-pricing-analysis-2026-07-14.md`.
- **Boundary:** This changes only the unvalidated launch cohort. Mainnet stays fail-closed until
  the separate production payment, worker, signer, remedy, monitoring, and ledger gates pass.

## 2026-07-14 - Treat Bazaar indexing proof as infrastructure, not adoption

- **Decision:** Use one faucet-funded Agentic Wallet settlement to validate the public x402/CDP
  path and seed Coinbase Bazaar, but permanently exclude it from request, buyer, revenue, repeat,
  margin, and autonomy counters.
- **Evidence:** Exactly 1.00 test USDC settled on Base Sepolia; the no-egress worker and separate
  signer delivered an independently verified immutable receipt; Coinbase semantic and merchant
  discovery then listed the canonical endpoint.
- **Boundary:** The public listing proves self-service discoverability and transport compatibility.
  Only unrelated, independently attributable agents and commercial funds may prove adoption or
  revenue. Testnet USDC is never revenue.

## 2026-07-14 - Add remote MCP discovery through GitHub OIDC

- **Decision:** Supersede the package-only Registry deferral. Publish a remote-only
  `io.github.mordiaky/vouchspec` manifest after the canonical endpoint passes a hosted MCP client
  smoke test. Keep the existing locally pinned stdio catalog available.
- **Evidence:** The official 2025-12-11 Registry schema supports public Streamable HTTP remotes
  without an npm or PyPI package. The official publisher supports GitHub OIDC from Actions with no
  dedicated Registry secret or interactive account login. The manifest validates against the
  exact schema, and publisher v1.8.0 plus both download checksums are pinned.
- **Security shape:** The hosted server is stateless JSON with one anonymous read-only discovery
  tool, canonical-origin controls, strict bounded JSON, exact protocol negotiation, and durable
  global/peer limits. It cannot submit artifacts, fetch repositories, settle payments, spend
  funds, open sessions, or access private data; paid validation remains on the x402 REST route.
- **Boundary:** Registry publication is distribution infrastructure, not an external integration,
  legitimate request, buyer, revenue, repeat use, margin, or autonomy evidence. Mainnet remains
  disabled, and Coinbase portal/SMS access remains prohibited.
