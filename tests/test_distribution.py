import json
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def test_publisher_ci_action_binds_exact_git_and_workflow_context_without_expression_in_shell() -> None:
    action_path = ROOT / "distribution" / "github-action" / "action.yml"
    action = yaml.safe_load(action_path.read_text(encoding="utf-8"))

    runs = [step.get("run", "") for step in action["runs"]["steps"]]
    assert all("${{ inputs." not in script and "${{ github." not in script for script in runs)
    assert any("inspect-git" in script and "--repository-root" in script for script in runs)
    assert any("rev-parse HEAD" in script and "status --porcelain" in script for script in runs)
    install_step = action["runs"]["steps"][0]
    assert "--require-hashes" in install_step["run"]
    assert "--only-binary=:all:" in install_step["run"]
    assert "requirements-linux-x86_64-py311.lock" in install_step["run"]
    assert "pip install \"$VOUCHSPEC_ACTION_PATH/../..\"" not in install_step["run"]
    lock = (ROOT / "distribution" / "github-action" / "requirements-linux-x86_64-py311.lock").read_text(
        encoding="utf-8"
    )
    assert "--hash=sha256:" in lock
    generate_step = action["runs"]["steps"][2]
    assert generate_step["env"]["VOUCHSPEC_SKILL_PATH"] == "${{ inputs.skill-path }}"
    assert 'case "$inspection_status"' in generate_step["run"]
    assert "0|2" in generate_step["run"]
    assert "exit \"$inspection_status\"" in generate_step["run"]
    binding_step = action["runs"]["steps"][3]
    assert binding_step["env"]["VOUCHSPEC_COMMIT"] == "${{ github.sha }}"
    assert binding_step["env"]["VOUCHSPEC_WORKFLOW_REF"] == "${{ github.workflow_ref }}"
    assert "receipt_sha256" in binding_step["run"]
    assert "structure-status=" in binding_step["run"]
    assert "decision-status=" in binding_step["run"]
    assert action["outputs"]["structure-status"]["value"] == "${{ steps.paths.outputs.structure-status }}"
    assert action["outputs"]["decision-status"]["value"] == "${{ steps.paths.outputs.decision-status }}"
    assert "PUBLISHER_CI_ATTESTED" not in action_path.read_text(encoding="utf-8")


def test_machine_discovery_exposes_agent_only_x402_sandbox_and_cache_contract() -> None:
    discovery = json.loads((ROOT / "distribution" / "discovery.json").read_text(encoding="utf-8"))
    assert discovery["service"] == "VouchSpec"
    assert discovery["stage"] == "B_PUBLIC_X402_SANDBOX"
    assert discovery["internal_codename_replaced"] is True
    assert discovery["trust"]["root_keyid"] == "zccWAwcnMzkQQUn8MXQDnpfUeGF0oavBZgYDoYfKgs4"
    assert discovery["trust"]["sandbox_issuer_keyid"] == "PWGCY2HpACKhufnSBjbf2zwMzThqxyPTz_MAwCyJ0I0"
    assert discovery["mcp"]["transport"] == "stdio"
    assert discovery["publisher_ci_action"].endswith("@ed812a14cbc62333d59bac319f79d897f14d1b64")
    assert discovery["publisher_ci_demo"] == "https://github.com/mordiaky/vouchspec-demo"
    assert set(discovery["mcp"]["tools"]) == {
        "search_receipts",
        "get_receipt",
        "get_receipt_status",
        "get_verification_material",
        "get_price_quote",
    }
    assert discovery["api"]["base_url"] == "https://vouchspec-sandbox.plyrium.com"
    assert discovery["api"]["agent_only"] is True
    assert discovery["api"]["self_service_registration"] is True
    assert discovery["api"]["authentication"]["delivery_header"] == "X-VouchSpec-Delivery-Token"
    assert discovery["x402"] == {
        "version": 2,
        "scheme": "exact",
        "network": "eip155:84532",
        "asset": "USDC",
        "sandbox_amount": "1.00",
        "sandbox_atomic_amount": "1000000",
        "payment_required_header": "PAYMENT-REQUIRED",
        "payment_signature_header": "PAYMENT-SIGNATURE",
        "payment_response_header": "PAYMENT-RESPONSE",
        "testnet_settlement_available": True,
        "mainnet_settlement_available": False,
        "human_checkout": False,
        "sandbox_activity_counts_for_goal": False,
    }
    assert discovery["boundary"]["artifact_submissions_accepted"] is False
    assert discovery["boundary"]["public_github_coordinates_accepted"] is True
    assert discovery["boundary"]["paid_testnet_orders_accepted"] is True
    assert discovery["boundary"]["paid_mainnet_orders_accepted"] is False
    assert discovery["boundary"]["human_call_required"] is False
    assert discovery["receipts"]["cacheable"] is True
    assert discovery["receipts"]["shareable"] is True
    assert discovery["receipts"]["invalidation_status_is_separate"] is True
    assert discovery["pricing"]["sandbox_fresh_validation_test_usdc"] == "1.00"
    assert discovery["pricing"]["commercial_fresh_validation_hypothesis_usd"] == "49.00"


def test_hosted_fulfillment_workflow_keeps_secrets_out_of_networked_artifact_commands() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "vouchspec-fulfillment.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    assert "pull_request" not in workflow
    assert "environment: vouchspec-testnet" in workflow
    assert 'cron: "*/5 * * * *"' in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "--require-hashes" in workflow
    assert "python -I -m capabilityproof.hosted_worker" in workflow
    assert "Claim one paid job before allocating build work" in workflow
    assert "steps.claim.outputs.has_job == 'true'" in workflow
    assert workflow.index("Claim one paid job before allocating build work") < workflow.index("actions/checkout")
    assert "--max-redirs 0" in workflow
    assert "--max-filesize 1000000" in workflow
    assert "VOUCHSPEC_PRECLAIMED_JOB" in workflow
    assert "VouchSpec claim HTTP status: $status" in workflow
    assert '[[ "$status" == "204" ]]' in workflow
    assert "VOUCHSPEC_ISSUER_PRIVATE_KEY_B64" in workflow
    assert "VOUCHSPEC_WORKER_TOKEN" in workflow
    assert "--network host" not in workflow
    assert "wallet" not in workflow.lower()
