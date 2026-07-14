# Operating status

- **Goal:** active and not achieved.
- **Public product:** Stage A catalog, exact-byte HTTP retrieval, installable stdio MCP,
  independent verification, and lifecycle metadata are live.
- **Publisher route:** the action now preserves and exposes signed evidence for both structural
  passes and structural failures; a complete public demo is available at
  `https://github.com/mordiaky/vouchspec-demo`. Run `29331787790` passed both cases and all
  four downloaded files passed independent GitHub attestation verification.
- **External adoption:** 0 / 3 retained unrelated integrations. Three tailored proposals are
  open at `https://github.com/supabase/agent-skills/issues/136`,
  `https://github.com/K-Dense-AI/scientific-agent-skills/issues/211`, and
  `https://github.com/michtio/craftcms-claude-skills/issues/10`; issues are outreach, not
  adoption. None has a maintainer response yet. The three-new-contact daily cap is reached.
- **External machine use:** 0 / 100 legitimate requests; 0 / 10 sources; 0 / 20 repeat
  requests; 0 / 5 repeat sources.
- **Commerce:** the first product is a USD $49 exact-version public static validation. Its
  strict request schema and non-orderable public quote preview are implemented. Immutable
  intake, no-egress inspection, constrained signing, idempotent event/cost accounting, and
  signed delivery completed in a fake-provider sandbox. A loopback-only authenticated API now
  tenant-binds quotes/orders/results, stores keyed credential digests, scopes idempotency,
  expires/rotates/revokes delivery capabilities, enforces framing/rate/storage limits, and
  returns only the exact digest-bound signed envelope. A pinned, expected-account-bound Stripe
  adapter now creates authenticated tenant-bound Checkout Sessions and reconciles only
  server-retrieved Session, PaymentIntent, Charge, and Balance Transaction state. The loopback
  API has a dedicated exact-body webhook route, separate webhook rate-limit capacity, strict
  signature-header handling, and non-2xx retry signaling. A real USD $49 Stripe test Session
  was created through this HTTP path and immediately expired unpaid; all sandbox/test activity
  remains excluded. Offline-root paid-receipt lifecycle publication provides exact coverage and
  irreversible invalidation. Public checkout remains disabled pending managed deployment, a
  public test webhook endpoint, kernel fetch quota, and a production signing role.
- **Revenue:** 0 / 3 unrelated settled buyers; USD $0 / $500 settled gross; 0 repeat buyers.
- **Economics:** USD $0 spend; USD $100 lifetime owner-funded budget remaining. No paid-order
  margin exists yet.
- **Autonomous run:** not started; it begins only after the first genuine settled payment.
- **Owner action:** none currently required. Existing external Stripe credentials were
  authorized and both test/live identities were verified without persisting secret values; the
  live account reports charges and payouts enabled.
- **Boundary:** public immutable sources only; no uploads, private repositories, confidential
  content, or artifact execution.
- **Verification:** local isolated verification passes 130 tests with one explicit Windows
  symlink-privilege skip. Public Linux CI run `29342266720` passed at commit
  `ff78ba5fda4290cf824d4d708fecf27a882df9e4`, including package installation, the full test
  suite, and a CLI receipt smoke test.

Next: follow all three unrelated adoption proposals without an unsolicited same-day follow-up,
resume the rules-limited publisher channel after its daily cap resets, and deploy the connected
Stripe-test boundary behind managed TLS with a mode-specific public webhook endpoint and
restricted durable state. Live Checkout remains off until that deployment, the production
signer, and kernel fetch quota are verified.
