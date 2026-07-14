# Operating status

- **Goal:** active and not achieved.
- **Public product:** Stage A catalog/retrieval/verification is live. Stage B is a public,
  self-service, agent-only x402 sandbox at `https://vouchspec-sandbox.plyrium.com`; it accepts
  immutable public GitHub coordinates and has no human checkout path.
- **Stage B payment:** exact x402 v2 payment using test USDC on Base Sepolia. The sandbox price
  is 1.00 test USDC so faucet-funded agents can exercise the complete flow. The commercial
  price remains an unvalidated USD $49 hypothesis. Mainnet is fail-closed.
- **Hosted fulfillment proof:** owner-controlled order `ord_01b1e85f188649a6b68e2dd2` settled
  on Base Sepolia in transaction
  `0xfe4b912ace571cd533d02e474de766d7dbe19d744d5cb35420cb71d7952aea11`, traversed the leased
  no-egress worker and separate no-egress signer, and produced a signature-verified public
  content-addressed receipt. It is explicitly `counts_for_goal: false`.
- **Receipt reuse:** exact DSSE envelope bytes are public, immutable, cacheable, and shareable.
  The live invalidation/lifecycle status is a separate no-store resource that agents must check
  when making a new reliance decision.
- **Fulfillment alerts:** four owner diagnostic runs failed while isolating a minimal-container
  signer import defect. The signer was reduced to a dependency-minimal entry point and workflow
  run `29359911240` then completed successfully. Failure email alerts remain enabled for genuine
  operational failures.
- **Publisher route:** the public GitHub Action and owned demo prove integration mechanics.
  The owned demo does not count as external adoption.
- **External adoption:** 0 / 3 retained unrelated integrations. Supabase issue `136` and K-Dense
  issue `211` remain proposals only. `michtio/craftcms-claude-skills#10` was declined and is useful
  ICP feedback, not adoption.
- **External machine use:** 0 / 100 legitimate requests; 0 / 10 sources; 0 / 20 repeat requests;
  0 / 5 repeat sources. Owner, CI, smoke, monitoring, and controlled-account traffic is excluded.
- **Revenue:** 0 / 3 unrelated settled buyers; USD $0 / $500 settled gross; 0 repeat buyers.
  Testnet USDC is never revenue.
- **Economics:** USD $0 owner-funded spend recorded; USD $100 lifetime budget remains. Positive
  contribution margin is not yet proven by a genuine paid order.
- **Autonomous run:** not started; the 14-day clock starts only after the first genuine settled
  commercial payment.
- **Owner action:** none currently required.
- **Boundary:** public immutable GitHub coordinates only; no uploads, private repositories,
  confidential content, credentials, mutable refs, or artifact execution.
- **Verification:** 136 tests pass with one explicit Windows symlink-privilege skip. The latest
  hosted paid-flow workflow run succeeded at commit `13c65f3dc36a099c0d45aa36aa08b58b3d738371`.

Next: acquire unrelated agent integrations that can discover and exercise the public sandbox
without owner involvement. Mainnet activation must preserve the same tenant,
settlement-recovery, no-egress, signing, receipt, invalidation, and honest-accounting boundaries.
