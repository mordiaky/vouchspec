# Operating status

- **Goal:** active and not achieved.
- **Public product:** Stage A catalog/retrieval/verification is live. Stage B is a public,
  self-service, agent-only x402 sandbox at `https://vouchspec-sandbox.plyrium.com`; it accepts
  immutable public GitHub coordinates and has no human checkout path. Agents can now purchase in
  one call at `POST /api/vouchspec/v1/validate` without registering or authenticating first.
- **Stage B payment:** exact x402 v2 payment using test USDC on Base Sepolia. The sandbox price
  is 1.00 test USDC so faucet-funded agents can exercise the complete flow. The one-call route
  verifies and settles through Coinbase's authenticated CDP facilitator and declares the official
  x402 Bazaar extension. Full live-catalog and substitute research rejected the prior $49
  hypothesis; the predeclared commercial launch experiment is 0.25 USDC per fresh validation,
  with evidence-triggered $0.10/$0.50 follow-on cohorts. Plyrium PR `#36` merged the
  environment-derived price/network migration and dedicated mode-separated mainnet configuration
  at `fed83d6f63c1b1d6ac49f4499077590b04545ad5` after 177 tests, release/security audits, an
  optimized build, Vercel preview, and zero-vulnerability production audit passed. Mainnet remains
  fail-closed and unprovisioned. Plyrium PR `#37` and VouchSpec PR `#9` have now merged the
  durable reconciliation/remedy state machine, bounded no-root network fetcher, independent Base
  RPC remedy verification, and disabled protected-environment executor. No mainnet funds can move
  because the executor flag remains false and the separate remedy identity is not provisioned.
  VouchSpec PRs `#10`-`#12` added a manual, main-only, API-only official-CLI provisioner with exact
  policy validation and no funding/send commands. Final run `29385202893` failed on its first
  read-only EVM account-list call, before policy lookup or account creation, so the current
  credential is exhausted and Coinbase work is paused without a portal fallback.
- **CDP/Bazaar launch:** Agentic Wallet compatibility deployment
  `d30577721f800a93748a2a4c55fd26972662e675` is live; PR `mordiaky/plyrium#34` merged it to main
  as `d93deb4647506892f88549aab4c2167d8087d01e`. Coinbase's public semantic search and merchant
  catalog now list the canonical validation endpoint with the exact 1.00-test-USDC Base-Sepolia
  requirement and agent-only metadata. The listing was indexed at the successful excluded
  settlement timestamp; no separate registration or human action was required.
- **Remote MCP discovery:** Plyrium PR `#38` is merged at
  `ba91715c8ea028ebedca56a85c614c73464bc083`; the canonical sandbox alias now serves a stateless
  Streamable HTTP endpoint at `/api/vouchspec/v1/mcp`. The official MCP client negotiated version
  `0.2.0`, listed only `get_vouchspec_discovery`, and returned the exact testnet-only public
  contract. Hosted method/origin probes returned 405/403 as designed. VouchSpec PR `#13` merged
  the validated manifest and main-only OIDC workflow; publication run `29388372800` passed, and
  the official Registry API returns one active `io.github.mordiaky/vouchspec` version `0.2.0`
  record pointing to the canonical Streamable HTTP endpoint.
- **Hosted fulfillment proof:** owner-controlled order `ord_01b1e85f188649a6b68e2dd2` settled
  on Base Sepolia in transaction
  `0xfe4b912ace571cd533d02e474de766d7dbe19d744d5cb35420cb71d7952aea11`, traversed the leased
  no-egress worker and separate no-egress signer, and produced a signature-verified public
  content-addressed receipt. It is explicitly `counts_for_goal: false`.
- **Agentic Wallet/CDP proof:** wallet `0x5AbA743d6e6Dc22584D9e175D0b39E972AB9918d`
  authorized exactly 1.00 test USDC. CDP settlement transaction
  `0xb8e841903c0b948a639a47c33dbcf5eb63ed09ee5f727004e876005bc9e23a17`
  succeeded at `2026-07-14T23:50:30Z`; workflow run `29377467330` then claimed, isolated,
  signed, and delivered the request. Public receipt digest
  `sha256:da6d3b8f6d6e99390efc98c050f83e45a7a8121d736759f32400309263470bd3`
  independently verifies under the published issuer JWK and is current. This controlled test is
  `counts_for_goal: false` and contributes no buyer, request, revenue, margin, or autonomy credit.
- **Receipt reuse:** exact DSSE envelope bytes are public, immutable, cacheable, and shareable.
  The live invalidation/lifecycle status is a separate no-store resource that agents must check
  when making a new reliance decision.
- **Fulfillment alerts:** four owner diagnostic runs failed while isolating a minimal-container
  signer import defect. The signer was reduced to a dependency-minimal entry point and workflow
  run `29359911240` then completed successfully. Failure email alerts remain enabled for genuine
  operational failures.
- **Publisher route:** the public GitHub Action and owned demo prove integration mechanics.
  The owned demo and the controlled remote MCP smoke do not count as external adoption.
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
- **Owner action:** none currently requested. Coinbase portal automation is stopped; no more SMS
  codes will be requested. The current credential failed the documented API-only account-list
  probe and will not be retried. Mainnet remains disabled while other autonomous work continues.
- **Boundary:** public immutable GitHub coordinates only; no uploads, private repositories,
  confidential content, credentials, mutable refs, or artifact execution.
- **Verification:** the connected Plyrium repository passes typecheck, 179 tests, private-address,
  public-route, transaction, and migration audits, a production build, and a zero-vulnerability
  production dependency audit. The public VouchSpec repository's 142-test suite passes 141 with
  one explicit Windows symlink-privilege skip. VouchSpec launch PR `mordiaky/plyrium#31`, CI memory repair PR
  `#32`, Agentic Wallet compatibility PRs `#33` and `#34`, remedy PR `#37`, and remote MCP PR
  `#38` are merged;
  post-merge main CI run `29382823021` passed. Public remedy/fetcher PR `#9` is merged and main CI
  run `29382833205` passed. API-only provisioning PRs `#10`-`#12` are merged at
  `82463543668b0abd92712004110a294aae8b0bf6`; main CI run `29385199415` passed both Python and
  Node suites with zero production dependency vulnerabilities. The latest hosted paid-flow
  workflow run `29377467330` succeeded at commit `f79dc9602849c04a482c840233933d3a701fae7b`.

Next: use the active official MCP Registry and indexed Bazaar entries to reach unrelated agent
integrations and genuine machine buyers. Continue isolated production state, signing, monitoring,
and deployment work without funding or enabling mainnet. Count only independently attributable
external activity; revisit the CDP identity only if an account-and-policy-capable credential becomes
available through a documented non-interactive API path.
