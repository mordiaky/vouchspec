import { pathToFileURL } from "node:url";
import { CdpClient } from "@coinbase/cdp-sdk";
import { encodeFunctionData, getAddress } from "viem";

const MAX_RESPONSE_BYTES = 1_000_000;
const REMEDY_VERSION = "vouchspec-onchain-remedy-v1";
const RECONCILIATION_VERSION = "vouchspec-payment-reconciliation-v1";
const TOKEN_RE = /^vsr_(test|live)_[A-Za-z0-9_-]{43}$/;
const WORKER_ID_RE = /^[a-z0-9][a-z0-9._-]{7,63}$/;
const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const LEASE_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TX_RE = /^0x[0-9a-f]{64}$/i;
const USDC_BY_NETWORK = {
  "eip155:84532": { cdp: "base-sepolia", asset: "0x036CbD53842c5426634e7929541eC2318f3dCF7e", amount: "1000000" },
  "eip155:8453": { cdp: "base", asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", amount: "250000" },
};
const TRANSFER_ABI = [{
  type: "function",
  name: "transfer",
  stateMutability: "nonpayable",
  inputs: [{ name: "to", type: "address" }, { name: "value", type: "uint256" }],
  outputs: [{ name: "", type: "bool" }],
}];

export class RemedyExecutorError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

function exactKeys(value, keys, code) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new RemedyExecutorError(code);
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new RemedyExecutorError(code);
  }
  return value;
}

export function normalizeApiBaseUrl(value) {
  let parsed;
  try { parsed = new URL(value); } catch { throw new RemedyExecutorError("executor_configuration_invalid"); }
  if (
    parsed.protocol !== "https:"
    || parsed.username || parsed.password || parsed.port
    || parsed.pathname !== "/" || parsed.search || parsed.hash
  ) throw new RemedyExecutorError("executor_configuration_invalid");
  return parsed.origin;
}

export function loadConfig(environment = process.env) {
  const apiBaseUrl = normalizeApiBaseUrl(environment.VOUCHSPEC_API_BASE_URL ?? "");
  const remedyToken = (environment.VOUCHSPEC_REMEDY_TOKEN ?? "").trim();
  const workerId = (environment.VOUCHSPEC_REMEDY_WORKER_ID ?? "github-actions-remedy").trim();
  const accountAddress = environment.CDP_REMEDY_ACCOUNT_ADDRESS ?? "";
  if (!TOKEN_RE.test(remedyToken) || !WORKER_ID_RE.test(workerId)) {
    throw new RemedyExecutorError("executor_configuration_invalid");
  }
  let account;
  try { account = getAddress(accountAddress); } catch { throw new RemedyExecutorError("executor_configuration_invalid"); }
  for (const name of ["CDP_API_KEY_ID", "CDP_API_KEY_SECRET", "CDP_WALLET_SECRET"]) {
    const value = environment[name] ?? "";
    if (value.length < 16 || value.length > 16_384) {
      throw new RemedyExecutorError("executor_configuration_invalid");
    }
  }
  return { apiBaseUrl, remedyToken, workerId, accountAddress: account };
}

async function readBoundedJson(response) {
  const length = response.headers.get("content-length");
  if (length !== null && (!/^\d+$/.test(length) || Number(length) > MAX_RESPONSE_BYTES)) {
    throw new RemedyExecutorError("executor_api_response_invalid");
  }
  if (!response.body) return null;
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_RESPONSE_BYTES) {
      await reader.cancel();
      throw new RemedyExecutorError("executor_api_response_invalid");
    }
    chunks.push(value);
  }
  if (total === 0) return null;
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  try { return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)); }
  catch { throw new RemedyExecutorError("executor_api_response_invalid"); }
}

export async function callVouchSpec(config, path, body, fetchImpl = fetch) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);
  let response;
  try {
    response = await fetchImpl(`${config.apiBaseUrl}${path}`, {
      method: "POST",
      redirect: "manual",
      signal: controller.signal,
      headers: {
        authorization: `Bearer ${config.remedyToken}`,
        "content-type": "application/json",
        accept: "application/json",
        "x-vouchspec-worker-id": config.workerId,
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new RemedyExecutorError("executor_api_unavailable");
  } finally {
    clearTimeout(timeout);
  }
  const value = await readBoundedJson(response);
  if (response.status === 204) return { status: 204, value: null };
  if (response.status < 200 || response.status >= 300) {
    throw new RemedyExecutorError(response.status >= 500 ? "executor_api_unavailable" : "executor_api_rejected");
  }
  return { status: response.status, value };
}

export function parseClaim(value) {
  exactKeys(value, ["worker_version", "lease_seconds", "job"], "executor_claim_invalid");
  if (value.worker_version !== REMEDY_VERSION || value.lease_seconds !== 1_200) {
    throw new RemedyExecutorError("executor_claim_invalid");
  }
  const job = exactKeys(value.job, [
    "remedy_id", "lease_token", "idempotency_key", "attempt", "network", "asset",
    "amount_atomic", "destination", "reason", "source_transaction", "checkpoint_block",
  ], "executor_claim_invalid");
  const network = USDC_BY_NETWORK[job.network];
  let asset;
  let destination;
  try {
    asset = getAddress(job.asset);
    destination = getAddress(job.destination);
  } catch { throw new RemedyExecutorError("executor_claim_invalid"); }
  if (
    !UUID_V4_RE.test(job.remedy_id)
    || job.idempotency_key.toLowerCase() !== job.remedy_id.toLowerCase()
    || !LEASE_RE.test(job.lease_token)
    || !Number.isInteger(job.attempt) || job.attempt < 1 || job.attempt > 20
    || !network || asset !== getAddress(network.asset)
    || job.amount_atomic !== network.amount
    || !["duplicate_settlement", "objective_fulfillment_failure"].includes(job.reason)
    || !TX_RE.test(job.source_transaction)
    || !/^\d+$/.test(job.checkpoint_block)
  ) throw new RemedyExecutorError("executor_claim_invalid");
  return { ...job, asset, destination, cdpNetwork: network.cdp };
}

export async function runOnce({ config, cdp = new CdpClient(), fetchImpl = fetch, wait = ms => new Promise(r => setTimeout(r, ms)) }) {
  const reconciliation = await callVouchSpec(config, "/api/vouchspec/v1/internal/payments/reconcile", {
    worker_version: RECONCILIATION_VERSION,
  }, fetchImpl);
  if (reconciliation.status !== 204) {
    const value = reconciliation.value;
    if (
      !value || typeof value !== "object" || Array.isArray(value)
      || value.worker_version !== RECONCILIATION_VERSION
      || !["no_settlement_found", "settlement_recovered", "duplicate_settlement_remedy_queued"].includes(value.action)
    ) throw new RemedyExecutorError("executor_reconciliation_invalid");
  }

  const claim = await callVouchSpec(config, "/api/vouchspec/v1/internal/remedies/claim", {
    worker_version: REMEDY_VERSION,
  }, fetchImpl);
  if (claim.status === 204) return { status: "idle" };
  if (claim.value?.action === "recovered_and_confirmed") {
    exactKeys(claim.value, ["worker_version", "action", "remedy"], "executor_claim_invalid");
    if (claim.value.worker_version !== REMEDY_VERSION) throw new RemedyExecutorError("executor_claim_invalid");
    return { status: "recovered" };
  }
  if (claim.value?.action === "idempotency_window_closed") {
    exactKeys(claim.value, ["worker_version", "action"], "executor_claim_invalid");
    if (claim.value.worker_version !== REMEDY_VERSION) throw new RemedyExecutorError("executor_claim_invalid");
    return { status: "held" };
  }
  const job = parseClaim(claim.value);
  const data = encodeFunctionData({
    abi: TRANSFER_ABI,
    functionName: "transfer",
    args: [job.destination, BigInt(job.amount_atomic)],
  });
  let sent;
  try {
    sent = await cdp.evm.sendTransaction({
      address: config.accountAddress,
      network: job.cdpNetwork,
      idempotencyKey: job.idempotency_key,
      transaction: { to: job.asset, data, value: 0n },
    });
  } catch {
    throw new RemedyExecutorError("executor_cdp_send_failed");
  }
  if (!sent || !TX_RE.test(sent.transactionHash ?? "")) {
    throw new RemedyExecutorError("executor_cdp_response_invalid");
  }
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const confirmation = await callVouchSpec(
      config,
      `/api/vouchspec/v1/internal/remedies/${job.remedy_id}/confirm`,
      { lease_token: job.lease_token, transaction: sent.transactionHash.toLowerCase() },
      fetchImpl,
    );
    if (confirmation.status === 200 && confirmation.value?.action === "confirmed") {
      return { status: "confirmed" };
    }
    if (confirmation.status !== 202 || confirmation.value?.action !== "confirmation_pending") {
      throw new RemedyExecutorError("executor_confirmation_invalid");
    }
    await wait(5_000);
  }
  throw new RemedyExecutorError("executor_confirmation_pending");
}

async function main() {
  try {
    const result = await runOnce({ config: loadConfig() });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    const code = error instanceof RemedyExecutorError ? error.code : "executor_failed";
    process.stderr.write(`${JSON.stringify({ status: "failed", error_code: code })}\n`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
