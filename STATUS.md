# Operating status

- **Goal:** active and not achieved.
- **Public product:** Stage A catalog/retrieval/verification is live. Stage B is a public,
  self-service, agent-only x402 sandbox at `https://vouchspec-sandbox.plyrium.com`; it accepts
  immutable public GitHub coordinates and has no human checkout path. Agents can now purchase in
  one call at `POST /api/vouchspec/v1/validate` without registering or authenticating first.
- **Stage B payment:** exact x402 v2 payment using test USDC on Base Sepolia. The sandbox price
  is 1.00 test USDC so faucet-funded agents can exercise the complete flow. The one-call route
  verifies and settles through Coinbase's authenticated CDP facilitator and declares the official
  x402 Bazaar extension. The commercial price remains an unvalidated USD $49 hypothesis.
  Mainnet is fail-closed.
- **CDP/Bazaar launch:** reconciled deployment `fc26b09a5d391029c21d11f9cb8ee25b14aff2d7` is live. Hosted
  health reports Bazaar readiness; a valid anonymous request returns HTTP 402 with one exact
  Base-Sepolia requirement for 1.00 test USDC, the canonical sandbox URL, and `extensions.bazaar`.
  A syntactically valid but invalid-signature probe was rejected with HTTP 402 and did not settle.
  CDP's public Bazaar search does not list the endpoint yet because CDP catalogs a seller only
  after its first successful CDP-facilitated settlement. No registration claim is made yet.
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
- **Owner action:** none currently required. The next controlled CDP settlement, if used only to
  seed Bazaar indexing, remains owner/test traffic and must stay excluded from every goal counter.
- **Boundary:** public immutable GitHub coordinates only; no uploads, private repositories,
  confidential content, credentials, mutable refs, or artifact execution.
- **Verification:** the connected Plyrium repository passes typecheck, 176 tests, private-address,
  public-route, transaction, and migration audits, a production build, and a zero-vulnerability
  production dependency audit. VouchSpec launch PR `mordiaky/plyrium#31` and CI memory repair PR
  `#32` are merged; post-merge main CI run `29373305038` passed. The CapabilityProof suite still
  has 136 passes and one explicit Windows symlink-privilege skip. The latest hosted paid-flow
  workflow run succeeded at commit `13c65f3dc36a099c0d45aa36aa08b58b3d738371`.

Next: complete one explicitly excluded CDP testnet settlement to trigger Bazaar indexing, verify
the public listing, then acquire unrelated agent integrations that discover and exercise the
sandbox without owner involvement. Mainnet activation must preserve the same tenant,
settlement-recovery, no-egress, signing, receipt, invalidation, and honest-accounting boundaries.
