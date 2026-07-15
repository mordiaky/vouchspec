# Next action

Acquire and monitor the first unrelated agent buyer through the active official MCP Registry
`0.3.0`, the auto-verified Agent Tools x402 listing, its healthy MCP entry, the searchable A2A
agent listing, and direct machine discovery.

An A2A-capable agent can discover the purchase contract at
`https://vouchspec.plyrium.com/.well-known/agent-card.json` and call the read-only
`discover_vouchspec_validation` skill at
`POST https://vouchspec.plyrium.com/api/vouchspec/v1/a2a`. That discovery call never pays,
validates, or issues a receipt; it returns the exact existing x402 purchase instructions.

Agents can buy now by sending a valid request to:

`POST https://vouchspec.plyrium.com/api/vouchspec/v1/validate`

The unpaid response supplies the x402 v2 payment requirements for exactly 0.25 USDC on Base
mainnet. After settlement, the isolated fulfillment worker creates and signs the receipt and
returns delivery credentials. No registration or human checkout is required before payment.

Coinbase Bazaar mainnet discovery is expected only after the first successful mainnet settlement.
Do not self-pay, use an owner-controlled wallet, or move remedy funds to manufacture discovery or
revenue. Direct API, Agent Tools, and MCP discovery remain valid sales channels while Bazaar is
pending. Expand only through agent-readable channels that require neither human checkout nor a new
owner contract.
