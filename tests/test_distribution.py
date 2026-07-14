from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def test_composite_action_passes_inputs_only_through_environment() -> None:
    action_path = ROOT / "distribution" / "github-action" / "action.yml"
    action = yaml.safe_load(action_path.read_text(encoding="utf-8"))

    runs = [step.get("run", "") for step in action["runs"]["steps"]]
    assert all("${{ inputs." not in script for script in runs)
    generate_step = action["runs"]["steps"][1]
    assert generate_step["env"]["CAPABILITYPROOF_SKILL_PATH"] == "${{ inputs.skill-path }}"
    assert "--allow-root" in generate_step["run"]
    assert "GITHUB_WORKSPACE" in generate_step["run"]
