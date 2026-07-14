# Decision log

## 2026-07-13 — Select CapabilityProof and narrow the first scope

- **Decision:** Build exact-version evidence for Agent Skills containing `SKILL.md`.
- **Alternatives considered:** Broad AI artifact directory; MCP-first scanner; marketplace.
- **Evidence:** Owner-selected thesis; external evidence review is in progress.
- **Reason:** A bounded artifact format permits a zero-spend, deterministic proof quickly.
- **Constraint:** Do not pivot back to a conventional manual service business.

## 2026-07-13 — First slice is non-executing Level 1–3 analysis

- **Decision:** Parse bytes, hash the artifact, validate structure, extract requirements,
  and emit static findings without importing or running artifact content.
- **Reason:** This produces evidence without violating the host-isolation boundary.
- **Deferred:** Sandboxing, trigger/task evaluation, payment, monitoring, and broad discovery.

