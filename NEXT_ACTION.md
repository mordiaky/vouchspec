# Next action

Acquire and monitor the first unrelated agent buyer through the active official MCP Registry
`0.3.0`, the auto-verified Agent Tools x402 listing, its healthy MCP entry, the searchable A2A
agent listing, standard OpenAPI and `llms.txt` contracts, the draft/proposal ARD catalog, and
public repository metadata. Add the installable `vouchspec-verify-before-install` Agent Skill as
the primary verify-before-install acquisition path:

- repository discovery: `DISABLE_TELEMETRY=1 npx skills@latest add mordiaky/vouchspec --list`
- well-known index: `https://vouchspec.plyrium.com/.well-known/skills/index.json`
- skill file: `https://vouchspec.plyrium.com/.well-known/skills/vouchspec-verify-before-install/SKILL.md`

The Agent Tools direct-service badge currently reflects an older scheduled check and conflicts
with VouchSpec's live JSON health. A bodyless paid-endpoint POST returns the required 402, but do
not claim the directory itself is healthy until its JSON refreshes and the independent checker
accepts agreement. Its published health timer runs every six hours.

An A2A-capable agent can discover the purchase contract at
`https://vouchspec.plyrium.com/.well-known/agent-card.json` and call the read-only
`discover_vouchspec_validation` skill at
`POST https://vouchspec.plyrium.com/api/vouchspec/v1/a2a`. That discovery call never pays,
validates, or issues a receipt; it returns the exact existing x402 purchase instructions.

Agents can buy now by sending a valid request to:

`POST https://vouchspec.plyrium.com/api/vouchspec/v1/validate`

Agents that start from a general API or web-capability crawler can discover the same purchase
contract at:

- `https://vouchspec.plyrium.com/openapi.json`
- `https://vouchspec.plyrium.com/llms.txt`
- `https://vouchspec.plyrium.com/.well-known/ai-catalog.json`

The unpaid response supplies the x402 v2 payment requirements for exactly 0.25 USDC on Base
mainnet. After settlement, the isolated fulfillment worker creates and signs the receipt and
returns delivery credentials. No registration or human checkout is required before payment.

Coinbase Bazaar mainnet discovery is expected only after the first successful mainnet settlement.
Do not self-pay, use an owner-controlled wallet, or move remedy funds to manufacture discovery or
revenue. Direct API, Agent Tools, MCP, A2A, OpenAPI, `llms.txt`, ARD, and GitHub discovery remain
valid sales channels while Bazaar is pending. The existing daily autonomous monitor now includes
the Agent Skill paths and the directory recheck. Expand only through agent-readable channels that
require neither human checkout nor a new owner contract. At `2026-07-16T02:17:02Z`, live orders,
settled payments, distinct/repeat payers, paid minor units, and goal-qualified orders all remained
zero; do not overstate this launch work as a sale.
