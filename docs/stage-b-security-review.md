# Stage B managed x402 security review

Reviewed 2026-07-14 against the managed tenant/quote/order/payment API, durable x402 state,
private fulfillment lease, immutable Git intake, no-egress worker, separate no-egress signer,
public receipt cache, and live invalidation resource. This supersedes the earlier local
Stripe/loopback launch assessment; the Stripe adapter remains regression-only.

## Closed launch findings

### Anonymous Bazaar intake and deterministic credential bootstrap

- **Risk:** removing tenant registration before payment could create an unauthenticated resource
  allocation surface, let one authorization adopt another request, or disclose a settled buyer's
  tenant and delivery capabilities.
- **Control:** the route rate-limits before parsing; accepts only bounded strict JSON and immutable
  public GitHub coordinates; allocates durable objects only after CDP verification; derives tenant,
  quote, order, API-key, and delivery-token identities from a domain-separated HMAC of the signed
  payment authorization; binds retries to the exact stored request digest and payment payload; and
  returns capabilities only to the same payment proof. Capabilities are no-store bearer values,
  stored only as keyed digests, expiring, rotatable, revocable, and tenant-bound.

### CDP facilitator credential and wallet separation

- **Risk:** a Coinbase credential with wallet custody or transfer rights in the web application
  could turn an endpoint compromise into a funds compromise.
- **Control:** the branch-scoped Vercel deployment contains only a dedicated CDP API key ID and
  secret used to authenticate facilitator `verify` and `settle`. The key is read-only. No wallet
  seed, private key, or `CDP_WALLET_SECRET` is configured, documented as acceptable, or passed to
  fulfillment. The application fails closed when the CDP credentials are absent or malformed.

### Cross-tenant order or result access

- **Risk:** enumeration or credential reuse could disclose another tenant's request or result.
- **Control:** opaque bearer keys and order delivery capabilities are stored only as keyed
  digests; every quote/order/result/payment RPC binds the authenticated tenant and capability.
  Generic authorization failures, expiration, rotation, revocation, and replay tests pass.

### Forged, replayed, or ambiguous x402 settlement

- **Risk:** a client could replay a signature, substitute payment requirements, race settlement,
  or exploit a facilitator timeout to double charge or double fulfill.
- **Control:** x402 v2 only; exact scheme/network/asset/amount/receiver; validated payment
  requirements; canonical payment digest; one settlement row per order; tenant/order/capability
  binding; a processing lease; a pre-settlement checkpoint; bounded recovery proof; and atomic
  completion. Conflicts and unknown states fail closed.

### Payment credentials reaching artifact processing

- **Risk:** artifact-controlled input or a compromised parser could exfiltrate wallet/buyer
  credentials.
- **Control:** the networked fetch role receives public coordinates only. The no-egress worker
  receives frozen public bytes. The signer receives bounded evidence and signing material only.
  Wallet/CDP credentials, tenant keys, delivery tokens, and the private worker API token are not
  supplied to artifact or signer containers.

### Artifact escape or host modification

- **Risk:** a parser/dependency defect could execute content, reach the network, or modify host
  state.
- **Control:** only regular Git blobs survive the freeze; exact hashes are checked; artifact
  content is never imported or executed; the inspection container has no network, read-only
  root/input filesystems, no capabilities, no new privileges, bounded resources, no writable host
  mount, and bounded stdout-only results.

### Arbitrary worker evidence obtaining a signature

- **Risk:** a substituted worker image or fabricated report could obtain a trusted envelope.
- **Control:** the separate signer rehashes the freeze, validates source/receipt/execution/image/
  timing/isolation bindings against an immutable image allowlist, signs exact bytes, and
  self-verifies. Its dependency-minimal entry point passed the hosted no-egress flow.

### Downloaded receipts becoming silently stale

- **Risk:** caching could hide evaluator defect, key compromise, supersession, or revocation.
- **Control:** the DSSE envelope is content-addressed and immutable. Agents cache/share exact
  bytes, verify the signature/key, and fetch a separate no-store status resource for every new
  reliance decision. Lifecycle changes never rewrite historical evidence.

### Failure alerts creating noise or hiding incidents

- **Risk:** frequent expected failures could train the operator to ignore real paid-job failure.
- **Control:** empty queue exits successfully before expensive work; safe diagnostic categories
  distinguish infrastructure faults without exposing stderr/secrets; the signer import defect was
  fixed; run `29359911240` completed successfully. Alerts remain enabled only for failed runs.

### Bazaar listing and one-call compatibility

- **Risk:** a formally valid 402 route could remain undiscoverable or reject an agent wallet's
  header/body transport before payment, making the advertised self-service path unusable.
- **Control and evidence:** bounded route-specific compatibility accepts Agentic Wallet's
  headerless discovery and chunked paid retry while retaining strict media, length, schema, and
  paid-body checks. One owner-controlled Base-Sepolia payment settled through CDP, fulfilled and
  signed successfully, and both CDP semantic search and merchant discovery now return the
  canonical endpoint. The test remains excluded from all commercial counters.

## Residual mainnet gates

### Onchain remedies are not yet executable

The policy promises automatic remedies for duplicate settlement and objective VouchSpec failures.
Before mainnet, implement and test the return transaction, destination binding, idempotency,
accounting exclusion, and recovery behavior. Testnet proof alone is not a refund mechanism.

### Networked Git scratch storage lacks a mid-write kernel quota

The fetch phase uses exact Git coordinates, partial fetch, process timeout, post-phase metadata
ceilings, bounded archive/extraction, and cleanup. A maliciously large pack could transiently
exceed the logical ceiling before the post-command check. Mainnet deployment must use disposable
storage with a kernel-enforced quota.

### Live environment separation is unproven

Mainnet requires distinct receiver policy, network/facilitator allowlist, secrets, database,
issuer policy, credentials, monitoring, and financial ledger. Any test/live cross-binding must
fail closed and no test object may be promoted into commercial evidence.

### Positive contribution is unproven

The durable cost fields exist, but no genuine buyer has paid. Commercial fulfillment must record
actual chain/facilitator, worker, storage, delivery, and remedy cost and reject a quote that cannot
retain positive contribution.

## Privacy and claims conclusion

The accepted input is public immutable source coordinates. Private repositories, uploads,
credentials, confidential content, mutable refs, and artifact execution remain rejected.
Public receipts disclose evidence about public source and are intentionally shareable. VouchSpec
claims only the checks and limits stated in the signed receipt; it does not claim malware-free,
universal safety, publisher identity, or observed runtime behavior.
