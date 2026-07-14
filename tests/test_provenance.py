from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from capabilityproof.errors import InputRejected
from capabilityproof.receipt import inspect_git_skill, verify_receipt_integrity


FIXTURE = Path(__file__).parent / "fixtures" / "valid-skill"
FIXED_TIME = "2026-07-14T03:00:00Z"


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path]:
    if shutil.which("git") is None:
        pytest.skip("git is unavailable")
    root = tmp_path / "repo"
    skill = root / "skills" / "valid-skill"
    skill.parent.mkdir(parents=True)
    shutil.copytree(FIXTURE, skill)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "CapabilityProof Test")
    _git(root, "remote", "add", "origin", "https://example.invalid/public/skills.git")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fixture")
    return root, skill


def test_clean_git_skill_reaches_level_three_with_exact_commit(tmp_path: Path) -> None:
    root, skill = _repository(tmp_path)
    receipt = inspect_git_skill(skill, root, generated_at=FIXED_TIME)

    assert receipt["provenance"]["source_commit"] == _git(root, "rev-parse", "HEAD")
    assert receipt["provenance"]["source_repository"] == "https://example.invalid/public/skills.git"
    assert receipt["provenance"]["artifact_path"] == "skills/valid-skill"
    assert receipt["evidence_levels"]["highest_contiguous_level"] == 3
    assert receipt["evidence_levels"]["completed_checks"] == [0, 1, 2, 3]
    assert verify_receipt_integrity(receipt)


def test_untracked_or_changed_skill_is_not_given_provenance(tmp_path: Path) -> None:
    root, skill = _repository(tmp_path)
    (skill / "untracked.txt").write_text("untracked", encoding="utf-8")

    with pytest.raises(InputRejected) as error:
        inspect_git_skill(skill, root, generated_at=FIXED_TIME)
    assert error.value.code in {"provenance_dirty", "provenance_scope_mismatch"}


def test_modified_tracked_bytes_are_not_given_provenance(tmp_path: Path) -> None:
    root, skill = _repository(tmp_path)
    (skill / "SKILL.md").write_text(
        (skill / "SKILL.md").read_text(encoding="utf-8") + "\nModified after commit.\n",
        encoding="utf-8",
    )

    with pytest.raises(InputRejected) as error:
        inspect_git_skill(skill, root, generated_at=FIXED_TIME)
    assert error.value.code == "provenance_blob_mismatch"


def test_remote_credentials_are_not_written_to_receipt(tmp_path: Path) -> None:
    root, skill = _repository(tmp_path)
    _git(root, "remote", "set-url", "origin", "https://user:secret@example.invalid/public/skills.git")
    receipt = inspect_git_skill(skill, root, generated_at=FIXED_TIME)
    serialized = json.dumps(receipt)

    assert "user:secret" not in serialized
    assert receipt["provenance"]["source_repository"] == "https://example.invalid/public/skills.git"


def test_remote_query_credentials_are_not_written_to_receipt(tmp_path: Path) -> None:
    root, skill = _repository(tmp_path)
    _git(
        root,
        "remote",
        "set-url",
        "origin",
        "https://example.invalid/public/skills.git?access_token=TOKEN_SHOULD_NOT_LEAK",
    )
    receipt = inspect_git_skill(skill, root, generated_at=FIXED_TIME)
    serialized = json.dumps(receipt)

    assert "TOKEN_SHOULD_NOT_LEAK" not in serialized
    assert receipt["provenance"]["source_repository"] == "https://example.invalid/public/skills.git"
