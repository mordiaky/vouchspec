"""Strict, bounded parsing and structural checks for Agent Skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlparse, urlunsplit

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import Node, ScalarNode
from yaml.resolver import BaseResolver
from yaml.tokens import AliasToken, AnchorToken

from .snapshot import ScanLimits, Snapshot


AGENT_SKILLS_SPEC_URL = "https://agentskills.io/specification"
KNOWN_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
RESOURCE_PATH_PATTERN = re.compile(r"(?<![A-Za-z0-9_.-])((?:scripts|references|assets)/[A-Za-z0-9_.\-/]+)")
URL_SCHEMES = {"http", "https", "mailto", "data"}
MAX_FRONTMATTER_BYTES = 65_536
MAX_YAML_NODES = 1_000
MAX_YAML_DEPTH = 24
MAX_YAML_ALIASES = 50


class UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeySafeLoader, node: Node, deep: bool = False) -> dict[Any, Any]:
    loader.flatten_mapping(node)  # type: ignore[arg-type]
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:  # type: ignore[attr-defined]
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError("while constructing a mapping", node.start_mark, "found an unhashable key", key_node.start_mark) from exc
        if duplicate:
            raise ConstructorError("while constructing a mapping", node.start_mark, "found a duplicate key", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


@dataclass(frozen=True)
class ParsedSkill:
    metadata: dict[str, Any]
    body: str
    structural_findings: tuple[dict[str, Any], ...]
    local_references: tuple[dict[str, Any], ...]
    external_references: tuple[str, ...]
    body_start_line: int = 1

    @property
    def structure_valid(self) -> bool:
        return not any(item["severity"] == "error" for item in self.structural_findings)


def _finding(rule_id: str, severity: str, message: str, *, line: int | None = None) -> dict[str, Any]:
    safe_message = "".join(character if character >= " " or character == "\t" else " " for character in message)[:500]
    item: dict[str, Any] = {"rule_id": rule_id, "severity": severity, "message": safe_message}
    if line is not None:
        item["line"] = line
    return item


def _walk_yaml(node: Node, depth: int = 0, seen: set[int] | None = None) -> tuple[int, int]:
    if depth > MAX_YAML_DEPTH:
        raise ValueError(f"YAML nesting exceeds {MAX_YAML_DEPTH}")
    seen = seen or set()
    identity = id(node)
    if identity in seen:
        raise ValueError("YAML aliases are not allowed")
    seen.add(identity)
    if isinstance(node, ScalarNode):
        if node.tag == "tag:yaml.org,2002:merge":
            raise ValueError("YAML merge keys are not allowed")
        if node.tag == "tag:yaml.org,2002:timestamp":
            raise ValueError("implicit YAML timestamps are not allowed")
        if node.tag == "tag:yaml.org,2002:float" and node.value.lower() in {
            ".nan", ".inf", "+.inf", "-.inf"
        }:
            raise ValueError("non-finite YAML numbers are not allowed")
    count = 1
    max_depth = depth
    value = getattr(node, "value", None)
    if isinstance(value, list):
        for child in value:
            if isinstance(child, tuple) and not isinstance(child[0], ScalarNode):
                raise ValueError("complex YAML mapping keys are not allowed")
            nodes = child if isinstance(child, tuple) else (child,)
            for part in nodes:
                child_count, child_depth = _walk_yaml(part, depth + 1, seen)
                count += child_count
                max_depth = max(max_depth, child_depth)
                if count > MAX_YAML_NODES:
                    raise ValueError(f"YAML node count exceeds {MAX_YAML_NODES}")
    return count, max_depth


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str, list[dict[str, Any]], int]:
    findings: list[dict[str, Any]] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, [_finding("AS001", "error", "SKILL.md must start with YAML frontmatter")], 1

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        return {}, text, [_finding("AS002", "error", "YAML frontmatter is not closed")], 1

    raw_frontmatter = "\n".join(lines[1:closing_index])
    if len(raw_frontmatter.encode("utf-8")) > MAX_FRONTMATTER_BYTES:
        return {}, "\n".join(lines[closing_index + 1 :]), [
            _finding("AS003", "error", f"YAML frontmatter exceeds {MAX_FRONTMATTER_BYTES} bytes")
        ], closing_index + 2
    alias_count = len(re.findall(r"(?<![A-Za-z0-9_])\*[A-Za-z0-9_-]+", raw_frontmatter))
    if alias_count > MAX_YAML_ALIASES:
        return {}, "\n".join(lines[closing_index + 1 :]), [
            _finding("AS004", "error", f"YAML alias count exceeds {MAX_YAML_ALIASES}")
        ], closing_index + 2

    try:
        tokens = yaml.scan(raw_frontmatter, Loader=UniqueKeySafeLoader)
        if any(isinstance(token, (AnchorToken, AliasToken)) for token in tokens):
            raise ValueError("YAML anchors and aliases are not allowed")
        node = yaml.compose(raw_frontmatter, Loader=UniqueKeySafeLoader)
        if node is not None:
            _walk_yaml(node)
        parsed = yaml.load(raw_frontmatter, Loader=UniqueKeySafeLoader)
    except (yaml.YAMLError, ValueError, RecursionError) as exc:
        safe_message = str(exc).splitlines()[0][:200]
        return {}, "\n".join(lines[closing_index + 1 :]), [
            _finding("AS005", "error", f"YAML frontmatter is invalid: {safe_message}")
        ], closing_index + 2

    if not isinstance(parsed, dict):
        findings.append(_finding("AS006", "error", "YAML frontmatter must be a mapping"))
        parsed = {}
    return parsed, "\n".join(lines[closing_index + 1 :]), findings, closing_index + 2


def _validate_metadata(metadata: dict[str, Any], parent_name: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        findings.append(_finding("AS101", "error", "name is required and must be a string"))
    else:
        if len(name) > 64 or not NAME_PATTERN.fullmatch(name):
            findings.append(
                _finding(
                    "AS102",
                    "error",
                    "name must be 1-64 lowercase ASCII letters/numbers/hyphens with no edge or consecutive hyphen",
                )
            )
        if name != parent_name:
            findings.append(_finding("AS103", "error", "name must match the parent directory name"))

    description = metadata.get("description")
    if not isinstance(description, str) or not description:
        findings.append(_finding("AS104", "error", "description is required and must be a non-empty string"))
    elif len(description) > 1_024:
        findings.append(_finding("AS105", "error", "description must not exceed 1024 characters"))

    license_value = metadata.get("license")
    if license_value is not None and not isinstance(license_value, str):
        findings.append(_finding("AS106", "error", "license must be a string when provided"))

    compatibility = metadata.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str) or not compatibility:
            findings.append(_finding("AS107", "error", "compatibility must be a non-empty string when provided"))
        elif len(compatibility) > 500:
            findings.append(_finding("AS108", "error", "compatibility must not exceed 500 characters"))

    extra_metadata = metadata.get("metadata")
    if extra_metadata is not None:
        if not isinstance(extra_metadata, dict):
            findings.append(_finding("AS109", "error", "metadata must be a mapping"))
        elif any(not isinstance(key, str) or not isinstance(value, str) for key, value in extra_metadata.items()):
            findings.append(_finding("AS110", "error", "metadata keys and values must all be strings"))

    allowed_tools = metadata.get("allowed-tools")
    if allowed_tools is not None and not isinstance(allowed_tools, str):
        findings.append(_finding("AS111", "error", "allowed-tools must be a space-separated string"))

    non_string_fields = [field for field in metadata if not isinstance(field, str)]
    if non_string_fields:
        findings.append(_finding("AS115", "error", "frontmatter field names must be strings"))
    for field in sorted(field for field in metadata if isinstance(field, str) and field not in KNOWN_FIELDS):
        display_field = "".join(character if character >= " " else " " for character in field)[:200]
        findings.append(_finding("AS112", "warning", f"unrecognized frontmatter field: {display_field}"))
    return findings


def _normalize_link_target(raw_target: str) -> str:
    target = raw_target.strip().strip("<>")
    if " " in target and not target.startswith(("http://", "https://")):
        target = target.split(" ", 1)[0]
    return unquote(target.split("#", 1)[0])


def _sanitize_external_target(target: str) -> str:
    parsed = urlparse(target)
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https"}:
        try:
            hostname = parsed.hostname
            port = parsed.port
        except ValueError:
            return f"{scheme}:<invalid>"
        if not hostname:
            return f"{scheme}:<invalid>"
        display_hostname = f"[{hostname.lower()}]" if ":" in hostname else hostname.lower()
        netloc = f"{display_hostname}:{port}" if port else display_hostname
        return urlunsplit((scheme, netloc, parsed.path[:400], "", ""))[:500]
    if scheme == "mailto":
        return "mailto:<redacted>"
    if scheme == "data":
        return "data:<omitted>"
    return f"{scheme}:<unsupported>"[:500]


def _extract_references(
    body: str, snapshot: Snapshot, body_start_line: int, limits: ScanLimits
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    candidates: list[tuple[str, int, str]] = []
    in_fence = False
    reference_limit_reached = False
    for body_line_number, line in enumerate(body.splitlines(), start=1):
        line_number = body_start_line + body_line_number - 1
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        example_context = in_fence or bool(re.search(r"(?i)\bexamples?\b", line))
        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            if len(candidates) >= limits.max_references:
                reference_limit_reached = True
                break
            kind = "example-link" if example_context else "markdown-link"
            candidates.append((_normalize_link_target(match.group(1)), line_number, kind))
        if reference_limit_reached:
            break
        for match in RESOURCE_PATH_PATTERN.finditer(line):
            if len(candidates) >= limits.max_references:
                reference_limit_reached = True
                break
            candidates.append((_normalize_link_target(match.group(1)), line_number, "resource-candidate"))
        if reference_limit_reached:
            break

    local: list[dict[str, Any]] = []
    external: set[str] = set()
    findings: list[dict[str, Any]] = []
    if reference_limit_reached:
        findings.append(
            _finding(
                "AS299",
                "error",
                f"reference analysis exceeded the {limits.max_references} candidate limit",
            )
        )
    seen: set[tuple[str, int, str]] = set()
    available = {item.path for item in snapshot.files}
    root = snapshot.root

    for target, line_number, kind in candidates:
        if not target or (target, line_number, kind) in seen:
            continue
        seen.add((target, line_number, kind))
        try:
            parsed = urlparse(target)
        except ValueError:
            local.append({"path": target[:500], "line": line_number, "kind": kind, "status": "outside-root"})
            findings.append(_finding("AS201", "error", "file reference is not a valid URI or local path", line=line_number))
            continue
        if parsed.scheme.lower() in URL_SCHEMES or target.startswith("#"):
            if target:
                external.add(_sanitize_external_target(target) if parsed.scheme else target[:500])
            continue
        if parsed.scheme:
            local.append({"path": target[:500], "line": line_number, "kind": kind, "status": "outside-root"})
            findings.append(_finding("AS201", "error", "file reference uses an unsupported URI scheme", line=line_number))
            continue

        normalized = target.replace("\\", "/")
        if normalized.startswith("/") or (len(normalized) >= 2 and normalized[1] == ":"):
            local.append({"path": normalized[:500], "line": line_number, "kind": kind, "status": "outside-root"})
            findings.append(_finding("AS201", "error", "file reference is absolute or outside the skill root", line=line_number))
            continue
        resolved = (root / normalized).resolve(strict=False)
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            local.append({"path": normalized[:500], "line": line_number, "kind": kind, "status": "outside-root"})
            findings.append(_finding("AS201", "error", "file reference escapes the skill root", line=line_number))
            continue
        if relative in available:
            status = "present"
        elif kind == "markdown-link":
            status = "missing"
        elif kind == "example-link":
            status = "unresolved-example"
        else:
            status = "unresolved-candidate"
        local.append({"path": relative, "line": line_number, "kind": kind, "status": status})
        if status == "missing":
            findings.append(_finding("AS202", "warning", f"referenced file was not found: {relative}", line=line_number))

    local.sort(key=lambda item: (item["path"], item["line"]))
    return local, sorted(external), findings


def parse_skill(snapshot: Snapshot, limits: ScanLimits | None = None) -> ParsedSkill:
    limits = limits or ScanLimits()
    skill_file = snapshot.get("SKILL.md")
    if skill_file is None:
        return ParsedSkill(
            metadata={},
            body="",
            structural_findings=(_finding("AS000", "error", "SKILL.md is required"),),
            local_references=(),
            external_references=(),
            body_start_line=1,
        )
    try:
        text = skill_file.content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return ParsedSkill(
            metadata={},
            body="",
            structural_findings=(_finding("AS007", "error", "SKILL.md must be valid UTF-8"),),
            local_references=(),
            external_references=(),
            body_start_line=1,
        )
    if "\x00" in text:
        return ParsedSkill(
            metadata={},
            body="",
            structural_findings=(_finding("AS008", "error", "SKILL.md must not contain NUL bytes"),),
            local_references=(),
            external_references=(),
            body_start_line=1,
        )

    metadata, body, findings, body_start_line = _parse_frontmatter(text)
    findings.extend(_validate_metadata(metadata, snapshot.root.name))
    if not body.strip():
        findings.append(_finding("AS113", "warning", "SKILL.md body is empty"))
    if len(text.splitlines()) > 500:
        findings.append(_finding("AS114", "warning", "SKILL.md exceeds the 500-line recommendation"))

    local, external, reference_findings = _extract_references(body, snapshot, body_start_line, limits)
    findings.extend(reference_findings)
    findings.sort(key=lambda item: (item["severity"] != "error", item["rule_id"], item.get("line", 0)))
    if len(findings) > limits.max_findings:
        findings = findings[: limits.max_findings - 1]
        findings.append(
            _finding(
                "AS299",
                "error",
                f"structural findings exceeded the {limits.max_findings} finding limit",
            )
        )
    return ParsedSkill(
        metadata=metadata,
        body=body,
        structural_findings=tuple(findings),
        local_references=tuple(local),
        external_references=tuple(external),
        body_start_line=body_start_line,
    )
