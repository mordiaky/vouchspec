# Next action

Publish the live VouchSpec endpoint as MCP Registry version `0.3.0`, then acquire and monitor the
first unrelated agent buyer.

Agents can buy now by sending a valid request to:

`POST https://vouchspec.plyrium.com/api/vouchspec/v1/validate`

The unpaid response supplies the x402 v2 payment requirements for exactly 0.25 USDC on Base
mainnet. After settlement, the isolated fulfillment worker creates and signs the receipt and
returns delivery credentials. No registration or human checkout is required before payment.

Coinbase Bazaar mainnet discovery is expected only after the first successful mainnet settlement.
Do not self-pay, use an owner-controlled wallet, or move remedy funds to manufacture discovery or
revenue. Direct API and MCP discovery remain valid sales channels while Bazaar is pending.
