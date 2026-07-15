import assert from "node:assert/strict";
import test from "node:test";
import {
  createCliRunner,
  loadConfig,
  RemedyProvisionerError,
  runProvisioning,
} from "./index.mjs";

const POLICY_ID = "11111111-1111-4111-8111-111111111111";
const ADDRESS = "0x1111111111111111111111111111111111111111";

function policy(overrides = {}) {
  return {
    id: POLICY_ID,
    description: "VouchSpec Base USDC remedies max 25 cents",
    scope: "account",
    rules: [{
      action: "accept",
      operation: "sendEvmTransaction",
      criteria: [
        { type: "evmNetwork", networks: ["base"], operator: "in" },
        {
          type: "evmAddress",
          addresses: ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
          operator: "in",
        },
        {
          type: "evmData",
          abi: "erc20",
          conditions: [{
            function: "transfer",
            params: [{ name: "value", operator: "<=", value: "250000" }],
          }],
        },
        { type: "netUSDChange", changeCents: 25, operator: "<=" },
      ],
    }],
    ...overrides,
  };
}

function account(overrides = {}) {
  return {
    address: ADDRESS,
    name: "vouchspec-remedy",
    policies: [POLICY_ID],
    ...overrides,
  };
}

test("configuration requires all three headless credentials", () => {
  const valid = {
    CDP_KEY_ID: "a".repeat(16),
    CDP_KEY_SECRET: "b".repeat(32),
    CDP_WALLET_SECRET: "c".repeat(32),
  };
  assert.deepEqual(loadConfig(valid), valid);
  assert.deepEqual(loadConfig({
    CDP_KEY_ID: ` ${valid.CDP_KEY_ID}\r\n`,
    CDP_KEY_SECRET: `\t${valid.CDP_KEY_SECRET} `,
    CDP_WALLET_SECRET: `${valid.CDP_WALLET_SECRET}\n`,
  }), valid);
  for (const name of Object.keys(valid)) {
    const missing = { ...valid };
    delete missing[name];
    assert.throws(() => loadConfig(missing), RemedyProvisionerError);
  }
  assert.throws(
    () => loadConfig({ ...valid, CDP_WALLET_SECRET: `${valid.CDP_WALLET_SECRET}\0` }),
    RemedyProvisionerError,
  );
});

test("CLI runner uses headless live credentials without URL override or secret output", () => {
  const config = {
    CDP_KEY_ID: "a".repeat(16),
    CDP_KEY_SECRET: "b".repeat(32),
    CDP_WALLET_SECRET: "c".repeat(32),
  };
  const originalUrl = process.env.CDP_URL;
  process.env.CDP_URL = "https://attacker.invalid";
  let observed;
  try {
    const runner = createCliRunner(config, (executable, args, options) => {
      observed = { executable, args, options };
      return { status: 0, stdout: '{"accounts":[]}', stderr: "" };
    });
    assert.deepEqual(runner(["evm", "accounts", "list"]), { accounts: [] });
  } finally {
    if (originalUrl === undefined) delete process.env.CDP_URL;
    else process.env.CDP_URL = originalUrl;
  }
  assert.match(observed.executable, /node_modules[\\/]\.bin[\\/]cdp(?:\.cmd)?$/);
  assert.deepEqual(observed.args, ["evm", "accounts", "list"]);
  assert.equal(observed.options.shell, false);
  assert.equal(observed.options.env.CDP_ENV, "live");
  assert.equal(observed.options.env.CDP_NO_HISTORY, "1");
  assert.equal(observed.options.env.CDP_URL, undefined);
});

test("API failures identify only the failed operation", () => {
  const accountFailure = () => { throw new RemedyProvisionerError("provisioner_cdp_api_failed"); };
  assert.throws(
    () => runProvisioning(accountFailure),
    (error) => error.code === "provisioner_account_list_api_failed",
  );

  const policyFailure = (args) => {
    if (args[1] === "accounts") return { accounts: [] };
    throw new RemedyProvisionerError("provisioner_cdp_api_failed");
  };
  assert.throws(
    () => runProvisioning(policyFailure),
    (error) => error.code === "provisioner_policy_list_api_failed",
  );
});

test("an existing account must already carry the exact verified policy", () => {
  const calls = [];
  const cli = (args) => {
    calls.push(args);
    if (args[1] === "policies" && args[2] === "list") return { policies: [policy()] };
    if (args[1] === "policies" && args[2] === "get") return policy();
    return { accounts: [account()] };
  };
  assert.deepEqual(runProvisioning(cli), {
    status: "verified",
    created: false,
    address: ADDRESS,
    name: "vouchspec-remedy",
    policy_id: POLICY_ID,
  });
  assert.equal(calls.length, 3);

  const unbound = (args) => {
    if (args[1] === "policies" && args[2] === "list") return { policies: [policy()] };
    if (args[1] === "policies" && args[2] === "get") return policy();
    return { accounts: [account({ policies: [] })] };
  };
  assert.throws(() => runProvisioning(unbound), RemedyProvisionerError);
});

test("a missing account is created once with the policy attached atomically", () => {
  const calls = [];
  const cli = (args) => {
    calls.push(args);
    if (args[1] === "policies" && args[2] === "list") return { policies: [policy()] };
    if (args[1] === "policies" && args[2] === "get") return policy();
    if (args[1] === "accounts" && args[2] === "list") return { accounts: [] };
    return account();
  };
  assert.equal(runProvisioning(cli).created, true);
  assert.deepEqual(calls[3], [
    "evm", "accounts", "create",
    `accountPolicy=${POLICY_ID}`,
    "name=vouchspec-remedy",
  ]);
});

test("policy drift or ambiguity fails before account creation", () => {
  const drifted = policy();
  drifted.rules[0].criteria[2].conditions[0].params[0].value = "250001";
  const driftCli = (args) => {
    if (args[1] === "accounts") return { accounts: [] };
    if (args[1] === "policies" && args[2] === "list") return { policies: [policy()] };
    return drifted;
  };
  assert.throws(() => runProvisioning(driftCli), RemedyProvisionerError);

  const duplicateCli = (args) => (
    args[1] === "accounts" ? { accounts: [] } : { policies: [policy(), policy()] }
  );
  assert.throws(() => runProvisioning(duplicateCli), RemedyProvisionerError);
});
