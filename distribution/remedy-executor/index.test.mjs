import assert from "node:assert/strict";
import test from "node:test";
import { loadConfig, normalizeApiBaseUrl, parseClaim, RemedyExecutorError, runOnce } from "./index.mjs";

const TOKEN = `vsr_live_${"A".repeat(43)}`;
const ACCOUNT = "0x1111111111111111111111111111111111111111";
const DESTINATION = "0x2222222222222222222222222222222222222222";

test("executor configuration is HTTPS-only and requires isolated credentials", () => {
  assert.equal(normalizeApiBaseUrl("https://VOUCHSPEC.PLYRIUM.COM/"), "https://vouchspec.plyrium.com");
  for (const value of ["http://vouchspec.plyrium.com", "https://u@vouchspec.plyrium.com", "https://vouchspec.plyrium.com/x"])
    assert.throws(() => normalizeApiBaseUrl(value), RemedyExecutorError);
  const config = loadConfig({
    VOUCHSPEC_API_BASE_URL: "https://vouchspec.plyrium.com",
    VOUCHSPEC_REMEDY_TOKEN: TOKEN,
    CDP_REMEDY_ACCOUNT_ADDRESS: ACCOUNT,
    CDP_API_KEY_ID: "a".repeat(16),
    CDP_API_KEY_SECRET: "b".repeat(32),
    CDP_WALLET_SECRET: "c".repeat(32),
  });
  assert.equal(config.accountAddress, ACCOUNT);
});

test("claim parser binds mainnet USDC, amount, payer, and UUID idempotency", () => {
  const remedyId = "11111111-1111-4111-8111-111111111111";
  const value = {
    worker_version: "vouchspec-onchain-remedy-v1",
    lease_seconds: 1200,
    job: {
      remedy_id: remedyId,
      lease_token: "22222222-2222-4222-8222-222222222222",
      idempotency_key: remedyId,
      attempt: 1,
      network: "eip155:8453",
      asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      amount_atomic: "250000",
      destination: DESTINATION,
      reason: "objective_fulfillment_failure",
      source_transaction: `0x${"3".repeat(64)}`,
      checkpoint_block: "123",
    },
  };
  assert.equal(parseClaim(value).amount_atomic, "250000");
  value.job.amount_atomic = "250001";
  assert.throws(() => parseClaim(value), RemedyExecutorError);
});

test("executor sends one exact idempotent transfer and confirms it", async () => {
  const remedyId = "11111111-1111-4111-8111-111111111111";
  const responses = [
    new Response(null, { status: 204 }),
    Response.json({
      worker_version: "vouchspec-onchain-remedy-v1",
      lease_seconds: 1200,
      job: {
        remedy_id: remedyId,
        lease_token: "22222222-2222-4222-8222-222222222222",
        idempotency_key: remedyId,
        attempt: 1,
        network: "eip155:8453",
        asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        amount_atomic: "250000",
        destination: DESTINATION,
        reason: "duplicate_settlement",
        source_transaction: `0x${"3".repeat(64)}`,
        checkpoint_block: "123",
      },
    }),
    Response.json({ worker_version: "vouchspec-onchain-remedy-v1", action: "confirmed", remedy: {} }),
  ];
  const calls = [];
  const cdp = { evm: { sendTransaction: async options => {
    calls.push(options);
    return { transactionHash: `0x${"4".repeat(64)}` };
  } } };
  const result = await runOnce({
    config: { apiBaseUrl: "https://vouchspec.plyrium.com", remedyToken: TOKEN, workerId: "github-actions-remedy", accountAddress: ACCOUNT },
    cdp,
    fetchImpl: async () => responses.shift(),
    wait: async () => {},
  });
  assert.equal(result.status, "confirmed");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].idempotencyKey, remedyId);
  assert.equal(calls[0].network, "base");
  assert.equal(calls[0].transaction.to, "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913");
});

test("executor never sends after the provider idempotency window closes", async () => {
  const responses = [
    new Response(null, { status: 204 }),
    Response.json({
      worker_version: "vouchspec-onchain-remedy-v1",
      action: "idempotency_window_closed",
    }),
  ];
  const cdp = { evm: { sendTransaction: async () => {
    assert.fail("sendTransaction must not be called after the idempotency window");
  } } };
  const result = await runOnce({
    config: { apiBaseUrl: "https://vouchspec.plyrium.com", remedyToken: TOKEN, workerId: "github-actions-remedy", accountAddress: ACCOUNT },
    cdp,
    fetchImpl: async () => responses.shift(),
    wait: async () => {},
  });
  assert.equal(result.status, "held");
});
