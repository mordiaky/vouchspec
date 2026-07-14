# VouchSpec exact-version evidence offer

## Free Stage A

Agent Skill publishers, agent runtimes, and developer tools can search and retrieve signed
receipts for deliberately selected public Agent Skills. Each receipt identifies the full
source commit, artifact path and digest, scanner/profile versions, environment, issue counts,
tested and untested areas, validity window, limitations, lifecycle state, and verification
method. HTTP and MCP retrieval are read-only and require no account or call.

## First paid product — fresh public static validation

- **Buyer:** an Agent Skill publisher, registry, agent runtime, or CI/release system.
- **Input:** `github.com`, repository owner/name, full lowercase 40-character commit, exact
  skill directory, `vouchspec-public-static-v1`, maximum price, and opaque delivery ID.
- **Deliverable:** one signed exact-version static receipt and verification material.
- **Price hypothesis:** USD $49.00 per accepted request.
- **Expected delivery after launch:** within 10 minutes of verified payment for an in-policy
  request; objective failures follow the automatic remedy below.
- **Acceptance:** the DSSE signature verifies, the receipt binds the requested repository,
  full commit, directory and digest, and the receipt states findings, skipped checks and
  limitations. A correctly reported structural/static failure is an accepted deliverable.
- **Support:** machine-readable status/errors, documentation, and asynchronous GitHub issues;
  no calls or custom onboarding.

The current implementation exposes a strict request validator and non-orderable public quote
preview. The immutable fetcher, isolated no-egress worker, constrained signing gate,
idempotent order/event/cost store, full fake-provider sandbox delivery, and authenticated
tenant/order/result API pass locally. Checkout remains disabled until managed deployment,
the real Stripe adapter, paid-receipt lifecycle, operational signing role, Stripe account,
payout connection, webhook secret, and live reconciliation pass their gates.

## Exclusions

No private repositories, arbitrary ZIPs, unpinned branches, mutable URLs, credentials,
customer-confidential content, artifact script execution, unrestricted network, general
shell execution, malware-free claim, universal-safety claim, publisher-identity claim,
legal advice, consulting, or unlimited support.

## Automatic remedy

Automatically refund a duplicate charge, a settled payment whose job never begins because
of a VouchSpec failure, a job that fails before producing a signed receipt, an unsupported
request accepted because of a VouchSpec validation defect, or a delivered receipt that still
has an invalid signature or wrong source/commit/path/digest after one automatic rerun. Do not
refund merely because the artifact receives a failure or finding that was accurately
produced under the disclosed profile.
