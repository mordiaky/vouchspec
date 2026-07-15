# Mainnet remedy operations

Status: implemented, tested, and disabled. Do not set `VOUCHSPEC_REMEDIES_ENABLED=true` until
every provisioning and rejection check below passes. The main web service never receives a CDP
Wallet Secret or wallet-capable API key.

## Separation boundary

- Create a dedicated CDP project/API key/account for VouchSpec remedies. Do not reuse the x402
  receiving address, facilitator credential, sandbox account, or fulfillment/signing workflow.
- Attach an account-scope policy to the exact remedy account. Coinbase evaluates project policy
  first and account policy second; unmatched operations fail closed.
- Keep only the bounded refund float in this account. Initial ceiling: 5 USDC plus the minimum
  Base ETH required for transaction fees. Replenishment is a separate owner-authorized treasury
  action, not an executor capability.
- Store `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET`, and `CDP_WALLET_SECRET` only in the protected
  GitHub environment `vouchspec-mainnet-remedies`. The Vercel service receives only the public
  remedy address and a distinct orchestration token.
- Restrict that GitHub environment to the protected `main` branch. The workflow also rejects any
  non-`main` ref before the job can receive environment credentials.
- Leave the scheduled workflow disabled if the policy ID, account binding, balance ceiling,
  receiving/remedy separation, or negative probes cannot be verified.

## Required account policy

Create this as an **account-scope** policy and attach its returned policy ID to the dedicated
remedy EVM account. The criteria are a logical AND: Base mainnet only, the canonical Base USDC
contract only, ERC-20 `transfer` only, no more than 250,000 USDC atomic units, and no more than
25 USD cents of net asset change. No rule authorizes message/hash signing or any other operation,
so those calls fail closed.

```json
{
  "scope": "account",
  "description": "VouchSpec remedy account",
  "rules": [
    {
      "action": "accept",
      "operation": "sendEvmTransaction",
      "criteria": [
        { "type": "evmNetwork", "networks": ["base"], "operator": "in" },
        {
          "type": "evmAddress",
          "addresses": ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
          "operator": "in"
        },
        {
          "type": "evmData",
          "abi": "erc20",
          "conditions": [
            {
              "function": "transfer",
              "params": [
                { "name": "value", "operator": "<=", "value": "250000" }
              ]
            }
          ]
        },
        { "type": "netUSDChange", "changeCents": 25, "operator": "<=" }
      ]
    }
  ]
}
```

This policy is a second boundary, not the source of the refund destination. The application
derives that address from the verified payer and the executor validates the strict claim before
encoding the transfer.

## Activation checks

1. Confirm the attached account policy ID and that the remedy address differs from live receiver
   and sandbox remedy addresses.
2. With a disposable unfunded probe account governed by the same policy shape, prove rejection
   for Ethereum, Base Sepolia, native ETH, a non-USDC contract, `approve`, `transferFrom`, and an
   amount of 250,001 atomic units. Do not intentionally send mainnet funds for a negative probe.
3. Confirm a valid encoded intent is accepted by policy evaluation without enabling the VouchSpec
   schedule. Record no controlled transfer as revenue, buyer activity, or remedy evidence.
4. Set the public account address, distinct live orchestration token, API base URL, and CDP secrets
   in their prescribed server/workflow locations. Verify repository logs redact all credential
   values.
5. Fund no more than the operating ceiling, enable the environment-scoped workflow variable, and
   watch the first genuine settlement through reconciliation, fulfillment, receipt delivery, and
   accounting. Controlled probes remain excluded from commercial counters.

## Retry and accounting behavior

The database checkpoints before exposing a transfer intent. Every later claim scans Base for an
already-confirmed exact transfer. The executor uses the remedy UUID as `X-Idempotency-Key`; sends
are suppressed after 23 hours because Coinbase documents exact replay responses for 24 hours.
The application independently verifies the transaction and one confirmation before completing the
remedy. Objective failures set the order to refunded/revoked and zero contribution; duplicate
settlements refund only the duplicate payment and preserve the valid fulfilled order.

## Primary references

- Coinbase Policy Engine evaluation and fail-secure default:
  https://docs.cdp.coinbase.com/wallets/security-and-policies/policy-engine/overview
- Coinbase EVM policy criteria and USDC example:
  https://docs.cdp.coinbase.com/api-reference/v2/rest-api/policy-engine/policy-engine
- Coinbase request idempotency window:
  https://docs.cdp.coinbase.com/api-reference/v2/idempotency
- Coinbase x402 refund limitation:
  https://docs.cdp.coinbase.com/x402/support/faq
