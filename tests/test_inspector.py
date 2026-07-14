from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest

from capabilityproof.errors import InputRejected, LimitExceeded, PathRejected
from capabilityproof.receipt import REFERENCE_DEPENDENCY_LOCK_SHA256, inspect_skill, verify_receipt_integrity
from capabilityproof.snapshot import ScanLimits, collect_snapshot


FIXTURES = Path(__file__).parent / "fixtures"
FIXED_TIME = "2026-07-14T03:00:00Z"


def _schema() -> dict:
    path = Path(__file__).parents[1] / "src" / "capabilityproof" / "schemas" / "capability-receipt.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_skill_receipt_is_deterministic_schema_valid_and_path_private() -> None:
    first = inspect_skill(FIXTURES / "valid-skill", generated_at=FIXED_TIME)
    second = inspect_skill(FIXTURES / "valid-skill", generated_at=FIXED_TIME)

    assert first == second
    assert first["format_validation"]["status"] == "pass"
    assert first["evidence_levels"]["highest_contiguous_level"] == 1
    assert first["evidence_levels"]["completed_checks"] == [0, 1, 3]
    assert first["decision"]["status"] == "eligible-for-policy-evaluation"
    assert first["artifact"]["scope"]["capture_started_at"] == FIXED_TIME
    assert first["artifact"]["scope"]["capture_completed_at"] == FIXED_TIME
    assert first["artifact"]["scope"]["capture_timestamp_source"] == "caller-supplied-reproducibility-override"
    assert verify_receipt_integrity(first)
    assert "C:\\" not in json.dumps(first)
    jsonschema.Draft202012Validator(_schema()).validate(first)


def test_cli_stdout_matches_utf8_lf_output_bytes(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    base_command = [
        sys.executable,
        "-m",
        "capabilityproof",
        "inspect",
        str(FIXTURES / "valid-skill"),
        "--generated-at",
        FIXED_TIME,
    ]
    stdout_result = subprocess.run(
        [*base_command, "--compact"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        timeout=20,
    )
    subprocess.run(
        [*base_command, "--compact", "--output", str(output)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        timeout=20,
    )

    assert stdout_result.stdout == output.read_bytes()
    json.loads(stdout_result.stdout.decode("utf-8"))
    assert b"\r\n" not in stdout_result.stdout


def test_valid_skill_records_dependencies_references_and_requirement_signals() -> None:
    receipt = inspect_skill(FIXTURES / "valid-skill", generated_at=FIXED_TIME)
    references = receipt["format_validation"]["local_references"]
    assert {item["path"] for item in references} == {"references/guide.md", "scripts/normalize.py"}
    requirements = receipt["static_analysis"]["inferred_requirements"]
    assert requirements["filesystem_read"]["status"] == "indicated"
    assert requirements["filesystem_write"]["status"] == "indicated"
    assert requirements["network"]["status"] == "not-detected"


def test_risky_skill_surfaces_seeded_rules_without_leaking_seeded_secret() -> None:
    receipt = inspect_skill(FIXTURES / "risky-skill", generated_at=FIXED_TIME)
    rule_ids = {item["rule_id"] for item in receipt["static_analysis"]["findings"]}

    assert {"CP001", "CP002", "CP003", "CP004", "CP010", "CP012"}.issubset(rule_ids)
    assert receipt["decision"]["status"] == "review-required"
    serialized = json.dumps(receipt)
    assert "sk-this-is-a-seeded-secret-value" not in serialized
    assert "<redacted>" in serialized
    assert verify_receipt_integrity(receipt)


def test_invalid_structure_is_a_receipt_not_an_exception() -> None:
    receipt = inspect_skill(FIXTURES / "invalid-skill", generated_at=FIXED_TIME)
    rule_ids = {item["rule_id"] for item in receipt["format_validation"]["findings"]}

    assert receipt["format_validation"]["status"] == "fail"
    assert receipt["decision"]["status"] == "reject-structural"
    assert receipt["evidence_levels"]["highest_contiguous_level"] == 0
    assert {"AS102", "AS103", "AS104", "AS110", "AS201"}.issubset(rule_ids)


def test_snapshot_rejects_size_limit(tmp_path: Path) -> None:
    root = tmp_path / "large-skill"
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: large-skill\ndescription: Valid fixture.\n---\nBody\n", encoding="utf-8")
    (root / "large.bin").write_bytes(b"x" * 128)

    with pytest.raises(LimitExceeded):
        collect_snapshot(root, ScanLimits(max_total_bytes=100))


def test_snapshot_rejects_symlink_when_platform_allows_it(tmp_path: Path) -> None:
    root = tmp_path / "linked-skill"
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: linked-skill\ndescription: Valid fixture.\n---\nBody\n", encoding="utf-8")
    target = tmp_path / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(PathRejected):
        collect_snapshot(root)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction regression")
def test_snapshot_rejects_windows_directory_junction(tmp_path: Path) -> None:
    root = tmp_path / "junction-skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: junction-skill\ndescription: Valid fixture.\n---\nBody\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "requirements.txt").write_text("outside-root-secret\n", encoding="utf-8")
    junction = root / "vendor"
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        pytest.skip("NTFS junction creation is unavailable on this host")
    try:
        with pytest.raises(PathRejected, match="reparse"):
            collect_snapshot(root)
        with pytest.raises(PathRejected, match="reparse"):
            collect_snapshot(junction)
    finally:
        junction.rmdir()


def test_snapshot_rejects_hard_link_to_outside_file(tmp_path: Path) -> None:
    root = tmp_path / "hardlink-skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: hardlink-skill\ndescription: Valid fixture.\n---\nBody\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside.txt"
    outside.write_text("outside-root-secret\n", encoding="utf-8")
    link = root / "linked.txt"
    try:
        os.link(outside, link)
    except OSError:
        pytest.skip("hard-link creation is unavailable on this host")

    with pytest.raises(PathRejected, match="hard-linked"):
        collect_snapshot(root)


def test_integrity_verification_detects_tampering() -> None:
    receipt = inspect_skill(FIXTURES / "valid-skill", generated_at=FIXED_TIME)
    receipt["decision"]["status"] = "review-required"
    assert not verify_receipt_integrity(receipt)

    receipt = inspect_skill(FIXTURES / "valid-skill", generated_at=FIXED_TIME)
    receipt["integrity"]["signature"]["status"] = "configured"
    assert not verify_receipt_integrity(receipt)


def test_example_paths_are_candidates_not_broken_reference_findings(tmp_path: Path) -> None:
    root = tmp_path / "example-skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\n"
        "name: example-skill\n"
        "description: Demonstrates example references. Use while authoring skills.\n"
        "---\n\n"
        "Example: `scripts/not-created.py` could be useful.\n\n"
        "```markdown\n"
        "See [EXAMPLE.md](EXAMPLE.md).\n"
        "```\n",
        encoding="utf-8",
    )
    receipt = inspect_skill(root, generated_at=FIXED_TIME)
    statuses = {item["status"] for item in receipt["format_validation"]["local_references"]}
    rule_ids = {item["rule_id"] for item in receipt["format_validation"]["findings"]}

    assert {"unresolved-candidate", "unresolved-example"}.issubset(statuses)
    assert "AS202" not in rule_ids


def test_external_references_strip_credentials_and_file_uris_fail(tmp_path: Path) -> None:
    root = tmp_path / "external-links"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: external-links\ndescription: External link fixture.\n---\n"
        "[web](https://user:secret@example.invalid/path?access_token=TOKEN_SHOULD_NOT_LEAK)\n"
        "[local](file:///etc/passwd)\n",
        encoding="utf-8",
    )

    receipt = inspect_skill(root, generated_at=FIXED_TIME)
    serialized = json.dumps(receipt)
    assert "TOKEN_SHOULD_NOT_LEAK" not in serialized
    assert "user:secret" not in serialized
    assert receipt["format_validation"]["external_references_untrusted"] == ["https://example.invalid/path"]
    assert "AS201" in {item["rule_id"] for item in receipt["format_validation"]["findings"]}


def test_hostile_parser_shapes_fail_closed_without_crashing(tmp_path: Path) -> None:
    deep_yaml = tmp_path / "deep-yaml"
    deep_yaml.mkdir()
    (deep_yaml / "SKILL.md").write_text(
        "---\nvalue: " + "[" * 1_200 + "0" + "]" * 1_200 + "\n---\nBody\n",
        encoding="utf-8",
    )
    yaml_receipt = inspect_skill(deep_yaml, generated_at=FIXED_TIME)
    assert yaml_receipt["format_validation"]["status"] == "fail"
    assert "AS005" in {item["rule_id"] for item in yaml_receipt["format_validation"]["findings"]}

    deep_json = tmp_path / "deep-json"
    deep_json.mkdir()
    (deep_json / "SKILL.md").write_text(
        "---\nname: deep-json\ndescription: Parser bound fixture.\n---\nBody\n",
        encoding="utf-8",
    )
    (deep_json / "package.json").write_text("[" * 1_200 + "0" + "]" * 1_200, encoding="utf-8")
    json_receipt = inspect_skill(deep_json, generated_at=FIXED_TIME)
    assert json_receipt["static_analysis"]["status"] == "completed"
    assert json_receipt["static_analysis"]["manifest_parse_failures"] == [
        {"path": "package.json", "manifest": "package.json", "reason": "parse-failed"}
    ]
    assert json_receipt["decision"]["status"] == "review-required"

    malformed_url = tmp_path / "malformed-url"
    malformed_url.mkdir()
    (malformed_url / "SKILL.md").write_text(
        "---\nname: malformed-url\ndescription: URL parser fixture.\n---\n[broken](http://[)\n",
        encoding="utf-8",
    )
    url_receipt = inspect_skill(malformed_url, generated_at=FIXED_TIME)
    assert url_receipt["static_analysis"]["coverage"]["malformed_url_count"] == 1
    assert url_receipt["decision"]["status"] == "reject-structural"
    assert "AS201" in {item["rule_id"] for item in url_receipt["format_validation"]["findings"]}

    mixed_keys = tmp_path / "mixed-keys"
    mixed_keys.mkdir()
    (mixed_keys / "SKILL.md").write_text(
        "---\nname: mixed-keys\ndescription: Key type fixture.\n1: value\nz-field: value\n---\nBody\n",
        encoding="utf-8",
    )
    mixed_receipt = inspect_skill(mixed_keys, generated_at=FIXED_TIME)
    assert "AS115" in {item["rule_id"] for item in mixed_receipt["format_validation"]["findings"]}

    duplicate_keys = tmp_path / "duplicate-keys"
    duplicate_keys.mkdir()
    (duplicate_keys / "SKILL.md").write_text(
        "---\nname: duplicate-keys\nname: substituted\ndescription: Duplicate key fixture.\n---\nBody\n",
        encoding="utf-8",
    )
    duplicate_receipt = inspect_skill(duplicate_keys, generated_at=FIXED_TIME)
    assert duplicate_receipt["format_validation"]["status"] == "fail"
    assert "AS005" in {item["rule_id"] for item in duplicate_receipt["format_validation"]["findings"]}


@pytest.mark.parametrize(
    "extra_frontmatter",
    [
        "alias: &shared value\nsecond: *shared",
        "<<: {license: Apache-2.0}",
        "observed_at: 2026-07-13",
        "score: .nan",
        "? [complex, key]\n: value",
    ],
)
def test_restricted_yaml_grammar_rejects_ambiguous_features(tmp_path: Path, extra_frontmatter: str) -> None:
    root = tmp_path / "restricted-yaml"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: restricted-yaml\ndescription: Restricted YAML fixture.\n"
        + extra_frontmatter
        + "\n---\nBody\n",
        encoding="utf-8",
    )

    receipt = inspect_skill(root, generated_at=FIXED_TIME)
    assert receipt["format_validation"]["status"] == "fail"
    assert "AS005" in {item["rule_id"] for item in receipt["format_validation"]["findings"]}


def test_skill_md_nul_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "nul-skill"
    root.mkdir()
    (root / "SKILL.md").write_bytes(
        b"---\nname: nul-skill\ndescription: NUL fixture.\n---\nBody\x00tail\n"
    )

    receipt = inspect_skill(root, generated_at=FIXED_TIME)
    assert receipt["format_validation"]["status"] == "fail"
    assert "AS008" in {item["rule_id"] for item in receipt["format_validation"]["findings"]}


def test_derived_evidence_is_bounded_and_reports_truncation(tmp_path: Path) -> None:
    root = tmp_path / "bounded-output"
    root.mkdir()
    links = "\n".join(f"[missing {index}](missing-{index}.txt)" for index in range(80))
    (root / "SKILL.md").write_text(
        "---\nname: bounded-output\ndescription: Output-bound fixture.\n---\n" + links + "\n",
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text(
        "\n".join(f"package-{index}==1.0" for index in range(40)) + "\n",
        encoding="utf-8",
    )
    (root / "script.py").write_text("\n".join("open('input.txt')" for _ in range(20)) + "\n", encoding="utf-8")
    limits = ScanLimits(max_references=50, max_dependencies=25, max_requirement_evidence_per_kind=5)

    receipt = inspect_skill(root, generated_at=FIXED_TIME, limits=limits)

    assert len(receipt["format_validation"]["local_references"]) == 50
    assert "AS299" in {item["rule_id"] for item in receipt["format_validation"]["findings"]}
    assert len(receipt["static_analysis"]["dependencies"]) == 25
    assert receipt["static_analysis"]["coverage"]["dependency_limit_reached"] is True
    assert len(receipt["static_analysis"]["inferred_requirements"]["filesystem_read"]["evidence"]) == 5
    assert receipt["static_analysis"]["inferred_requirements"]["filesystem_read"]["evidence_limit_reached"] is True
    assert len(json.dumps(receipt)) < 100_000
    jsonschema.Draft202012Validator(_schema()).validate(receipt)


def test_reference_dependency_lock_digest_matches_checked_in_lock() -> None:
    lock_path = Path(__file__).parents[1] / "requirements.lock"
    assert hashlib.sha256(lock_path.read_bytes()).hexdigest() == REFERENCE_DEPENDENCY_LOCK_SHA256


def test_timestamp_near_datetime_limit_fails_closed() -> None:
    with pytest.raises(InputRejected) as error:
        inspect_skill(FIXTURES / "valid-skill", generated_at="9999-12-31T23:59:59Z")
    assert error.value.code == "invalid_timestamp"
