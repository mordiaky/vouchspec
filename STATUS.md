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
  returns only the exact digest-bound signed envelope. The proof and all API traffic are
  explicitly nonsettling and excluded. Public checkout remains disabled pending managed
  deployment, paid-receipt lifecycle, the real Stripe adapter, production signing role, and
  owner-controlled payment account.
- **Revenue:** 0 / 3 unrelated settled buyers; USD $0 / $500 settled gross; 0 repeat buyers.
- **Economics:** USD $0 spend; USD $100 lifetime owner-funded budget remaining. No paid-order
  margin exists yet.
- **Autonomous run:** not started; it begins only after the first genuine settled payment.
- **Owner action:** none currently required. Live payment activation will eventually require
  owner-controlled identity, business, payout, and provider credentials.
- **Boundary:** public immutable sources only; no uploads, private repositories, confidential
  content, or artifact execution.
- **Verification:** local isolated verification passes 114 tests with one explicit Windows
  symlink-privilege skip. Public CI refresh for this change is pending; prior run
  `29335330180` passed at commit `6c73742efafb314a1d1b6ba2e98ef66d4912f2a1`.

Next: follow all three unrelated adoption proposals without an unsolicited same-day follow-up,
resume the rules-limited publisher channel after its daily cap resets,
and implement the real Stripe adapter plus paid-receipt lifecycle and managed deployment
preparation before requesting payment activation.
