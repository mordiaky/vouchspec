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
    generate_step = action["runs"]["steps"][2]
    assert generate_step["env"]["VOUCHSPEC_SKILL_PATH"] == "${{ inputs.skill-path }}"
    binding_step = action["runs"]["steps"][3]
    assert binding_step["env"]["VOUCHSPEC_COMMIT"] == "${{ github.sha }}"
    assert binding_step["env"]["VOUCHSPEC_WORKFLOW_REF"] == "${{ github.workflow_ref }}"
    assert "receipt_sha256" in binding_step["run"]
    assert "PUBLISHER_CI_ATTESTED" not in action_path.read_text(encoding="utf-8")
