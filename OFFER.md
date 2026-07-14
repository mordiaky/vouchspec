# VouchSpec exact-version evidence offer

## Free evidence layer

Agents, Agent Skill publishers, runtimes, registries, and CI systems can search and retrieve
signed receipts for selected public skills. Each receipt binds a full source commit, artifact
path and digest, scanner/profile versions, checks, limitations, validity, lifecycle state, and
verification method. Exact receipt bytes may be cached and shared; a relying agent separately
checks the current invalidation status. No account, call, or human approval is required.

## Fresh public static validation

- **Buyer:** an autonomous agent, Agent Skill publisher, registry, runtime, or CI/release system.
- **Input:** `github.com`, repository owner/name, full lowercase 40-character commit, exact skill
  directory, `vouchspec-public-static-v1`, maximum price, and opaque delivery ID.
- **Deliverable:** one signed exact-version static DSSE receipt plus verification material and
  public content-addressed receipt/status URLs.
- **Public sandbox:** 1.00 test USDC through x402 v2 on Base Sepolia; self-service and
  `counts_for_goal: false`.
- **Commercial hypothesis:** USD $49.00-equivalent USDC per accepted mainnet request; not yet
  enabled or validated.
- **Delivery objective:** within 10 minutes of verified payment for an in-policy request;
  objective service failures follow the automatic remedy below.
- **Acceptance:** the signature verifies, the receipt binds the requested repository, commit,
  directory and digest, and the receipt states findings, skipped checks, and limitations. An
  accurately reported structural/static failure is an accepted deliverable.
- **Support:** machine-readable status/errors and asynchronous public documentation; no calls,
  demos, meetings, custom onboarding, card forms, or hosted checkout.

The agent-only sandbox is live at `https://vouchspec-sandbox.plyrium.com`. It authenticates an
opaque tenant, binds each quote/order/payment to that tenant, settles x402 test USDC, leases work
to a no-egress inspection worker, signs in a separate no-egress role, and publishes immutable
receipt bytes with separate invalidation status. A complete owner-controlled testnet order has
passed this chain; it proves mechanics only and is excluded from every commercial counter.

## Exclusions

No private repositories, arbitrary ZIP uploads, unpinned branches, mutable URLs, credentials,
customer-confidential content, artifact script execution, unrestricted network, general shell
execution, malware-free claim, universal-safety claim, publisher-identity claim, legal advice,
consulting, meetings, or unlimited support.

## Automatic remedy

Automatically remedy a duplicate settlement; a settled payment whose job never begins because
of a VouchSpec failure; a job that fails before producing a signed receipt; an unsupported request
accepted because of a VouchSpec validation defect; or a delivered receipt that still has an
invalid signature or wrong source/commit/path/digest after one automatic rerun. Mainnet refund
mechanics must be enabled before commercial settlement. Do not refund merely because the artifact
receives a failure or finding accurately produced under the disclosed profile.
