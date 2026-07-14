"""Transparent text and manifest indicators; never imports or executes artifact content."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import re
import tomllib
from typing import Any
from urllib.parse import urlparse

from .snapshot import ScanLimits, Snapshot
from .skill import ParsedSkill


TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".pyi", ".sh", ".bash", ".zsh", ".ps1", ".js", ".jsx",
    ".ts", ".tsx", ".mjs", ".cjs", ".json", ".toml", ".yaml", ".yml", ".ini",
    ".cfg", ".conf", ".xml", ".html", ".css", ".go", ".rs", ".rb", ".php",
    ".java", ".kt", ".sql", ".dockerfile",
}
TEXT_NAMES = {"Dockerfile", "Makefile", "requirements.txt", "Pipfile", "LICENSE", "NOTICE"}
URL_PATTERN = re.compile(r"https?://[^\s)\]>'\"`]+", re.IGNORECASE)
SECRET_REDACTIONS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk|ghp|github_pat)-[A-Za-z0-9_-]{10,}\b", re.IGNORECASE),
    re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\s*[:=]\s*(['\"]?)[^\s,'\";]+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{10,}=*"),
)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    severity: str
    message: str
    pattern: re.Pattern[str]


RULES = (
    Rule("CP001", "instruction-integrity", "high", "text appears to override higher-priority or prior instructions", re.compile(r"(?i)\b(?:ignore|disregard|override)\b.{0,80}\b(?:previous|system|developer|higher[- ]priority|safety)\b")),
    Rule("CP002", "secrets", "medium", "credential, secret, environment, or SSH access indicator", re.compile(r"(?i)(?:os\.environ|\bgetenv\s*\(|process\.env|\.env\b|~[/\\]\.ssh|\bcredential|api[_-]?key|password\s*[:=])")),
    Rule("CP003", "process", "medium", "process or shell execution indicator", re.compile(r"(?i)(?:subprocess\.(?:run|Popen|call|check_output)|os\.system\s*\(|child_process|shell\s*=\s*True|Invoke-Expression|\biex\s+)")),
    Rule("CP004", "supply-chain", "critical", "remote content appears to be piped into an interpreter", re.compile(r"(?i)(?:(?:curl|wget|Invoke-WebRequest).{0,180}(?:\|\s*(?:sh|bash|zsh|python|pwsh)|Invoke-Expression|\biex\b))")),
    Rule("CP005", "destructive-filesystem", "high", "recursive or forceful deletion indicator", re.compile(r"(?i)(?:\brm\s+-[^\n]*[rf][^\n]*\s|Remove-Item[^\n]*(?:-Recurse|-Force)|shutil\.rmtree\s*\(|fs\.rm\s*\([^\n]*recursive\s*:\s*true)")),
    Rule("CP006", "privilege", "high", "privilege or broad permission change indicator", re.compile(r"(?i)(?:\bsudo\b|\brunas\b|chmod\s+777|Set-ExecutionPolicy|takeown\s+)")),
    Rule("CP007", "persistence", "high", "host persistence or autostart indicator", re.compile(r"(?i)(?:\bcrontab\b|\bschtasks\b|scheduled\s+task|startup\s+folder|systemctl\s+enable|LaunchAgents)")),
    Rule("CP008", "dynamic-code", "high", "dynamic code evaluation indicator", re.compile(r"(?i)(?:\beval\s*\(|\bexec\s*\(|new\s+Function\s*\(|compile\s*\([^\n]*['\"]exec['\"])")),
    Rule("CP009", "obfuscation", "high", "encoded content and dynamic execution appear together", re.compile(r"(?i)(?:(?:base64|b64decode|fromBase64).{0,160}(?:eval|exec|Invoke-Expression|\biex\b))")),
    Rule("CP010", "network", "low", "outbound network client or download command indicator", re.compile(r"(?i)(?:requests\.(?:get|post|put|delete)|urllib\.request|httpx\.|aiohttp\.|\bfetch\s*\(|\bcurl\b|\bwget\b|Invoke-WebRequest)")),
    Rule("CP011", "security-controls", "high", "security disabling or bypass instruction indicator", re.compile(r"(?i)(?:disable\s+(?:antivirus|defender|firewall|security)|turn\s+off\s+(?:antivirus|defender|firewall)|bypass\s+(?:policy|access control|captcha|rate limit))")),
    Rule(
        "CP012",
        "exfiltration",
        "critical",
        "secret collection and outbound transfer appear together",
        re.compile(
            r"(?i)(?:(?:credential|api[_-]?key|password|secret|\.ssh).{0,160}(?:upload|exfiltrat|send\s+to|requests\.post|\bcurl\b)|(?:upload|exfiltrat|send\s+to|requests\.post|\bcurl\b).{0,160}(?:credential|api[_-]?key|password|secret|\.ssh))"
        ),
    ),
)


def static_ruleset_sha256() -> str:
    descriptor = [
        {
            "rule_id": rule.rule_id,
            "category": rule.category,
            "severity": rule.severity,
            "message": rule.message,
            "pattern": rule.pattern.pattern,
            "flags": rule.pattern.flags,
        }
        for rule in RULES
    ]
    encoded = json.dumps(
        descriptor,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_text_candidate(path: str, content: bytes) -> bool:
    name = path.rsplit("/", 1)[-1]
    suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if name in TEXT_NAMES or suffix in TEXT_SUFFIXES:
        return True
    return b"\x00" not in content[:4_096]


def _redact(text: str, limit: int = 240) -> str:
    cleaned = "".join(character if character >= " " or character == "\t" else " " for character in text)
    for pattern in SECRET_REDACTIONS:
        if pattern.groups:
            cleaned = pattern.sub(lambda match: f"{match.group(1)}=<redacted>", cleaned)
        else:
            cleaned = pattern.sub("<redacted>", cleaned)
    cleaned = " ".join(cleaned.strip().split())
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


def _decode_text(content: bytes) -> str | None:
    try:
        return content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None


def _dependency_records(
    snapshot: Snapshot, limit: int
) -> tuple[list[dict[str, str]], bool, list[dict[str, str]]]:
    dependencies: set[tuple[str, str, str]] = set()
    parse_failures: list[dict[str, str]] = []
    limit_reached = False

    def add(record: tuple[str, str, str]) -> None:
        nonlocal limit_reached
        if record in dependencies:
            return
        if len(dependencies) >= limit:
            limit_reached = True
            return
        dependencies.add(record)

    for item in snapshot.files:
        name = item.path.rsplit("/", 1)[-1]
        text = _decode_text(item.content)
        if text is None:
            continue
        if name.startswith("requirements") and name.endswith(".txt"):
            for line in text.splitlines():
                value = line.strip()
                if value and not value.startswith(("#", "-r", "--")):
                    add(("python", value[:300], item.path))
        elif name == "pyproject.toml":
            try:
                data = tomllib.loads(text)
                project = data.get("project", {})
                values = project.get("dependencies", []) if isinstance(project, dict) else []
                if not isinstance(values, list):
                    parse_failures.append({"path": item.path, "manifest": name, "reason": "unexpected-dependency-shape"})
                    continue
                for value in values:
                    if isinstance(value, str):
                        add(("python", value[:300], item.path))
            except (tomllib.TOMLDecodeError, AttributeError, RecursionError):
                parse_failures.append({"path": item.path, "manifest": name, "reason": "parse-failed"})
                continue
        elif name == "package.json":
            try:
                data = json.loads(text)
                if not isinstance(data, dict):
                    parse_failures.append({"path": item.path, "manifest": name, "reason": "unexpected-root-shape"})
                    continue
                for group in ("dependencies", "devDependencies", "optionalDependencies"):
                    values = data.get(group, {})
                    if isinstance(values, dict):
                        for package, version in values.items():
                            add(("node", f"{package}@{version}"[:300], item.path))
                    else:
                        parse_failures.append({"path": item.path, "manifest": name, "reason": f"unexpected-{group}-shape"})
                        break
            except (json.JSONDecodeError, AttributeError, RecursionError):
                parse_failures.append({"path": item.path, "manifest": name, "reason": "parse-failed"})
                continue
        elif name == "Cargo.toml":
            try:
                data = tomllib.loads(text)
                values = data.get("dependencies", {})
                if isinstance(values, dict):
                    for package, version in values.items():
                        add(("rust", f"{package}@{version}"[:300], item.path))
                else:
                    parse_failures.append({"path": item.path, "manifest": name, "reason": "unexpected-dependency-shape"})
            except (tomllib.TOMLDecodeError, AttributeError, RecursionError):
                parse_failures.append({"path": item.path, "manifest": name, "reason": "parse-failed"})
                continue
    return (
        [
            {"ecosystem": ecosystem, "declaration": declaration, "source_path": source_path}
            for ecosystem, declaration, source_path in sorted(dependencies)
        ],
        limit_reached,
        parse_failures,
    )


def _signal(status: bool, evidence: list[dict[str, Any]], limit_reached: bool, limit: int) -> dict[str, Any]:
    return {
        "status": "indicated" if status else "not-detected",
        "evidence": evidence,
        "evidence_limit_reached": limit_reached,
        "max_evidence": limit,
        "interpretation": "static indicator only; not observed runtime behavior",
    }


def analyze_static(snapshot: Snapshot, skill: ParsedSkill, limits: ScanLimits | None = None) -> dict[str, Any]:
    limits = limits or ScanLimits()
    findings: list[dict[str, Any]] = []
    per_rule: defaultdict[str, int] = defaultdict(int)
    skipped: list[dict[str, str]] = []
    referenced_hosts: set[str] = set()
    requirement_evidence: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    requirement_evidence_limits: set[str] = set()
    script_languages: set[str] = set()
    referenced_host_limit_reached = False
    malformed_url_count = 0
    finding_limit_reached = False
    per_rule_limit_reached = False

    def add_requirement(kind: str, evidence: dict[str, Any]) -> None:
        if len(requirement_evidence[kind]) >= limits.max_requirement_evidence_per_kind:
            requirement_evidence_limits.add(kind)
            return
        requirement_evidence[kind].append(evidence)

    for item in snapshot.files:
        suffix = "." + item.path.rsplit(".", 1)[-1].lower() if "." in item.path.rsplit("/", 1)[-1] else ""
        if item.path.startswith("scripts/"):
            script_languages.add(suffix.lstrip(".") or "unknown")
        if not _is_text_candidate(item.path, item.content):
            continue
        if item.size > limits.max_text_bytes:
            skipped.append({"path": item.path, "reason": "text-size-limit"})
            continue
        text = _decode_text(item.content)
        if text is None:
            skipped.append({"path": item.path, "reason": "non-utf8"})
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            for url_match in URL_PATTERN.finditer(line):
                try:
                    hostname = urlparse(url_match.group(0)).hostname
                except ValueError:
                    malformed_url_count += 1
                    continue
                if hostname:
                    normalized_hostname = hostname.lower()
                    if normalized_hostname not in referenced_hosts:
                        if len(referenced_hosts) >= limits.max_referenced_hosts:
                            referenced_host_limit_reached = True
                        else:
                            referenced_hosts.add(normalized_hostname)
            for rule in RULES:
                if not rule.pattern.search(line):
                    continue
                if len(findings) >= limits.max_findings:
                    finding_limit_reached = True
                    continue
                if per_rule[rule.rule_id] >= limits.max_findings_per_rule:
                    per_rule_limit_reached = True
                    continue
                findings.append(
                    {
                        "rule_id": rule.rule_id,
                        "category": rule.category,
                        "severity": rule.severity,
                        "message": rule.message,
                        "path": item.path,
                        "line": line_number,
                        "evidence_excerpt": _redact(line),
                        "evidence_type": "static-text-match",
                    }
                )
                per_rule[rule.rule_id] += 1

            lowered = line.lower()
            evidence = {"path": item.path, "line": line_number, "excerpt": _redact(line, 140)}
            if any(token in lowered for token in ("open(", "read_text", "read_bytes", "get-content", "cat ")):
                add_requirement("filesystem_read", evidence)
            if any(token in lowered for token in ("write_text", "write_bytes", "open(", "set-content", "out-file", "mkdir", "new-item")):
                add_requirement("filesystem_write", evidence)
            if any(token in lowered for token in ("subprocess.", "os.system", "child_process", "bash(", "shell", "invoke-expression")):
                add_requirement("process_spawn", evidence)
            if any(token in lowered for token in ("requests.", "httpx.", "urllib.request", "aiohttp.", "fetch(", "curl ", "wget ", "invoke-webrequest")):
                add_requirement("network", evidence)
            if any(token in lowered for token in ("os.environ", "getenv(", "process.env", ".env", ".ssh", "credential")):
                add_requirement("secrets", evidence)

    allowed_tools = skill.metadata.get("allowed-tools")
    if isinstance(allowed_tools, str) and any(token in allowed_tools.lower() for token in ("bash", "shell", "powershell")):
        add_requirement(
            "process_spawn",
            {"path": "SKILL.md", "line": 1, "excerpt": "allowed-tools includes a shell-capable tool"}
        )

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda item: (severity_order[item["severity"]], item["path"], item["line"], item["rule_id"]))
    counts = Counter(item["severity"] for item in findings)
    dependencies, dependency_limit_reached, manifest_parse_failures = _dependency_records(
        snapshot, limits.max_dependencies
    )

    return {
        "status": "completed",
        "engine": "capabilityproof-static-v0.1.0",
        "summary": {
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
            "total": len(findings),
        },
        "findings": findings,
        "skipped_text_files": skipped,
        "coverage": {
            "files_in_snapshot": len(snapshot.files),
            "finding_limit_reached": finding_limit_reached,
            "max_findings": limits.max_findings,
            "per_rule_limit_reached": per_rule_limit_reached,
            "max_findings_per_rule": limits.max_findings_per_rule,
            "dependency_limit_reached": dependency_limit_reached,
            "max_dependencies": limits.max_dependencies,
            "referenced_host_limit_reached": referenced_host_limit_reached,
            "max_referenced_hosts": limits.max_referenced_hosts,
            "malformed_url_count": malformed_url_count,
        },
        "inferred_requirements": {
            key: _signal(
                bool(requirement_evidence[key]),
                requirement_evidence[key],
                key in requirement_evidence_limits,
                limits.max_requirement_evidence_per_kind,
            )
            for key in ("filesystem_read", "filesystem_write", "process_spawn", "network", "secrets")
        },
        "dependencies": dependencies,
        "manifest_parse_failures": manifest_parse_failures,
        "script_languages": sorted(script_languages),
        "referenced_hosts": sorted(referenced_hosts),
    }
