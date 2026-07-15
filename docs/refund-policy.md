# Fresh-validation refund policy

VouchSpec automatically remedies objective service failures. No call or manual approval is
required for an ordinary qualifying case.

## Automatic refund

- Duplicate charge.
- Payment settles but the job never starts because of a VouchSpec failure.
- The job fails before a signed receipt is produced.
- VouchSpec accepts a request that its published validator should have rejected.
- The delivered receipt has an invalid signature or is bound to the wrong source, commit,
  path, or digest, and one automatic rerun does not correct it.

## Not a refund condition

A structural failure, static finding, skipped check disclosed by the profile, or other
accurately reported unfavorable evidence is the purchased result. Payment does not buy a
passing label and never changes the receipt's findings or severity.

Refunds reverse counted revenue immediately. Provider processing fees and direct work costs
remain expenses even when the provider does not return them.

## Agent-only execution

x402 payments cannot be reversed in place. A qualifying remedy is a new USDC transfer to the
verified payer address from the original signed authorization. VouchSpec fixes the Base network,
canonical USDC contract, and exact original amount; the executor cannot select a destination or
amount. Completion requires an independent onchain verification and removes the order from gross
revenue and goal counters.

The remedy UUID is reused as the wallet-provider idempotency key. Before every retry VouchSpec
scans from a durable pre-send block checkpoint. If certainty is not restored before the provider's
documented idempotency window closes, VouchSpec holds rather than risking a second transfer.
