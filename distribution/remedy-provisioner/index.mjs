import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const MAX_CLI_OUTPUT_BYTES = 1_000_000;
const MODULE_DIR = dirname(fileURLToPath(import.meta.url));
const ACCOUNT_NAME = "vouchspec-remedy";
const POLICY_DESCRIPTION = "VouchSpec Base USDC remedies max 25 cents";
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const POLICY_ID_RE = /^[A-Za-z0-9_-]{8,128}$/;
const ADDRESS_RE = /^0x[0-9a-f]{40}$/i;

export class RemedyProvisionerError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

function fail(code) {
  throw new RemedyProvisionerError(code);
}

function exactKeys(value, keys, code) {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(code);
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    fail(code);
  }
  return value;
}

export function loadConfig(environment = process.env) {
  const values = {};
  for (const name of ["CDP_KEY_ID", "CDP_KEY_SECRET", "CDP_WALLET_SECRET"]) {
    const value = environment[name];
    if (typeof value !== "string" || value.length < 16 || value.length > 16_384 || value.includes("\0")) {
      fail("provisioner_configuration_invalid");
    }
    values[name] = value;
  }
  return values;
}

function validatePolicy(policy) {
  if (
    !policy || typeof policy !== "object" || Array.isArray(policy)
    || !POLICY_ID_RE.test(policy.id ?? "")
    || policy.scope !== "account"
    || policy.description !== POLICY_DESCRIPTION
    || !Array.isArray(policy.rules) || policy.rules.length !== 1
  ) fail("provisioner_policy_invalid");

  const rule = exactKeys(
    policy.rules[0],
    ["action", "operation", "criteria"],
    "provisioner_policy_invalid",
  );
  if (
    rule.action !== "accept"
    || rule.operation !== "sendEvmTransaction"
    || !Array.isArray(rule.criteria) || rule.criteria.length !== 4
  ) fail("provisioner_policy_invalid");

  const criteriaByType = new Map();
  for (const criterion of rule.criteria) {
    if (!criterion || typeof criterion.type !== "string" || criteriaByType.has(criterion.type)) {
      fail("provisioner_policy_invalid");
    }
    criteriaByType.set(criterion.type, criterion);
  }

  const network = exactKeys(
    criteriaByType.get("evmNetwork"),
    ["type", "networks", "operator"],
    "provisioner_policy_invalid",
  );
  if (network.operator !== "in" || JSON.stringify(network.networks) !== '["base"]') {
    fail("provisioner_policy_invalid");
  }

  const address = exactKeys(
    criteriaByType.get("evmAddress"),
    ["type", "addresses", "operator"],
    "provisioner_policy_invalid",
  );
  if (
    address.operator !== "in" || !Array.isArray(address.addresses) || address.addresses.length !== 1
    || address.addresses[0].toLowerCase() !== BASE_USDC.toLowerCase()
  ) fail("provisioner_policy_invalid");

  const data = exactKeys(
    criteriaByType.get("evmData"),
    ["type", "abi", "conditions"],
    "provisioner_policy_invalid",
  );
  if (data.abi !== "erc20" || !Array.isArray(data.conditions) || data.conditions.length !== 1) {
    fail("provisioner_policy_invalid");
  }
  const condition = exactKeys(
    data.conditions[0],
    ["function", "params"],
    "provisioner_policy_invalid",
  );
  if (condition.function !== "transfer" || !Array.isArray(condition.params) || condition.params.length !== 1) {
    fail("provisioner_policy_invalid");
  }
  const parameter = exactKeys(
    condition.params[0],
    ["name", "operator", "value"],
    "provisioner_policy_invalid",
  );
  if (parameter.name !== "value" || parameter.operator !== "<=" || String(parameter.value) !== "250000") {
    fail("provisioner_policy_invalid");
  }

  const usd = exactKeys(
    criteriaByType.get("netUSDChange"),
    ["type", "changeCents", "operator"],
    "provisioner_policy_invalid",
  );
  if (usd.operator !== "<=" || usd.changeCents !== 25) fail("provisioner_policy_invalid");
  return policy.id;
}

function validateAccount(account, policyId) {
  if (
    !account || typeof account !== "object" || Array.isArray(account)
    || account.name !== ACCOUNT_NAME
    || !ADDRESS_RE.test(account.address ?? "")
    || !Array.isArray(account.policies)
    || !account.policies.every((value) => typeof value === "string")
    || !account.policies.includes(policyId)
  ) fail("provisioner_account_invalid");
  return {
    address: account.address,
    name: account.name,
    policy_id: policyId,
  };
}

export function runProvisioning(cli) {
  const listedPolicies = cli([
    "policy-engine", "policies", "list", "scope==account", "--paginate",
  ]);
  if (!listedPolicies || !Array.isArray(listedPolicies.policies)) fail("provisioner_policy_list_invalid");
  const matches = listedPolicies.policies.filter(
    (policy) => policy?.scope === "account" && policy?.description === POLICY_DESCRIPTION,
  );
  if (matches.length !== 1 || !POLICY_ID_RE.test(matches[0].id ?? "")) {
    fail("provisioner_policy_not_unique");
  }

  const policy = cli(["policy-engine", "policies", "get", matches[0].id]);
  const policyId = validatePolicy(policy);
  const listedAccounts = cli(["evm", "accounts", "list", "--paginate"]);
  if (!listedAccounts || !Array.isArray(listedAccounts.accounts)) fail("provisioner_account_list_invalid");
  const namedAccounts = listedAccounts.accounts.filter((account) => account?.name === ACCOUNT_NAME);
  if (namedAccounts.length > 1) fail("provisioner_account_not_unique");
  if (namedAccounts.length === 1) {
    return { status: "verified", created: false, ...validateAccount(namedAccounts[0], policyId) };
  }

  const created = cli([
    "evm", "accounts", "create", `accountPolicy=${policyId}`, `name=${ACCOUNT_NAME}`,
  ]);
  return { status: "verified", created: true, ...validateAccount(created, policyId) };
}

export function createCliRunner(config, spawn = spawnSync) {
  const executable = join(MODULE_DIR, "node_modules", ".bin", process.platform === "win32" ? "cdp.cmd" : "cdp");
  return (args) => {
    const childEnvironment = {
      ...process.env,
      CDP_ENV: "live",
      CDP_KEY_ID: config.CDP_KEY_ID,
      CDP_KEY_SECRET: config.CDP_KEY_SECRET,
      CDP_WALLET_SECRET: config.CDP_WALLET_SECRET,
      CDP_NO_HISTORY: "1",
      FORCE_COLOR: "0",
      NO_COLOR: "1",
    };
    delete childEnvironment.CDP_URL;
    const result = spawn(executable, args, {
      cwd: MODULE_DIR,
      env: childEnvironment,
      encoding: "utf8",
      maxBuffer: MAX_CLI_OUTPUT_BYTES,
      shell: false,
      timeout: 60_000,
      windowsHide: true,
    });
    if (result.error || result.status !== 0 || typeof result.stdout !== "string") {
      fail("provisioner_cdp_api_failed");
    }
    if (Buffer.byteLength(result.stdout, "utf8") > MAX_CLI_OUTPUT_BYTES) {
      fail("provisioner_cdp_response_invalid");
    }
    try {
      return JSON.parse(result.stdout);
    } catch {
      fail("provisioner_cdp_response_invalid");
    }
  };
}

async function main() {
  try {
    const config = loadConfig();
    const result = runProvisioning(createCliRunner(config));
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    const code = error instanceof RemedyProvisionerError ? error.code : "provisioner_failed";
    process.stderr.write(`${JSON.stringify({ status: "failed", error_code: code })}\n`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
