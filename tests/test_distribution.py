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


def test_machine_discovery_is_read_only_and_does_not_offer_stage_b_or_paid_intake() -> None:
    discovery = json.loads((ROOT / "distribution" / "discovery.json").read_text(encoding="utf-8"))
    assert discovery["service"] == "VouchSpec"
    assert discovery["stage"] == "A_PUBLIC_ARTIFACT_INDEX"
    assert discovery["trust"]["root_keyid"] == "zccWAwcnMzkQQUn8MXQDnpfUeGF0oavBZgYDoYfKgs4"
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
    assert discovery["boundary"] == {
        "artifact_submissions_accepted": False,
        "private_content_accepted": False,
        "artifact_code_executed": False,
        "paid_orders_accepted": False,
        "human_call_required": False,
    }
    assert discovery["pricing"]["fresh_validation_availability"] == "stage_b_not_orderable"
    assert discovery["pricing"]["settlement_available"] is False


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
