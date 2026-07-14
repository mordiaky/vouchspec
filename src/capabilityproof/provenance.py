"""Controlled local Git provenance checks without fetching or executing artifact content."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit, urlunsplit

from .errors import InputRejected, PathRejected
from .snapshot import Snapshot, resolve_operator_root


COMMIT_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


@dataclass(frozen=True)
class ProvenanceEvidence:
    repository_url: str
    commit: str
    artifact_path: str
    method: str = "exact-local-git-blob-match-v1"


def _safe_git_environment() -> dict[str, str]:
    keep = ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP")
    environment = {key: os.environ[key] for key in keep if key in os.environ}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_EXTERNAL_DIFF": "",
        }
    )
    return environment


def _git(
    repository_root: Path,
    *arguments: str,
    binary: bool = False,
    input_data: bytes | None = None,
) -> bytes | str:
    command = [
        "git",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "credential.helper=",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        "diff.external=",
        "-C",
        str(repository_root),
        *arguments,
    ]
    try:
        result = subprocess.run(
            command,
            input=input_data,
            stdin=subprocess.DEVNULL if input_data is None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
            env=_safe_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InputRejected("Git provenance command failed", code="provenance_failed") from exc
    if result.returncode != 0:
        raise InputRejected("Git provenance could not be verified", code="provenance_failed")
    if binary:
        return result.stdout
    try:
        return result.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise InputRejected("Git provenance output was not UTF-8", code="provenance_failed") from exc


def _verify_commit_blobs(snapshot: Snapshot, repository_root: Path, artifact_relative: str) -> None:
    object_names = [
        f"HEAD:{artifact_relative}/{item.path}" if artifact_relative != "." else f"HEAD:{item.path}"
        for item in snapshot.files
    ]
    request = "".join(f"{name}\n" for name in object_names).encode("utf-8")
    raw = _git(repository_root, "cat-file", "--batch", binary=True, input_data=request)
    assert isinstance(raw, bytes)
    cursor = 0
    for item in snapshot.files:
        header_end = raw.find(b"\n", cursor)
        if header_end < 0:
            raise InputRejected("Git blob response was incomplete", code="provenance_failed")
        header = raw[cursor:header_end].split()
        if len(header) != 3 or header[1] != b"blob":
            raise InputRejected("Git commit blob could not be resolved", code="provenance_scope_mismatch")
        try:
            size = int(header[2])
        except ValueError as exc:
            raise InputRejected("Git blob size was invalid", code="provenance_failed") from exc
        content_start = header_end + 1
        content_end = content_start + size
        if content_end >= len(raw) or raw[content_end : content_end + 1] != b"\n":
            raise InputRejected("Git blob response was malformed", code="provenance_failed")
        if raw[content_start:content_end] != item.content:
            raise InputRejected(
                "working-tree bytes do not exactly match the referenced Git commit",
                code="provenance_blob_mismatch",
            )
        cursor = content_end + 1
    if cursor != len(raw):
        raise InputRejected("Git blob response contained unexpected data", code="provenance_failed")


def _sanitize_remote(remote: str) -> str:
    if len(remote) > 2_048 or any(ord(character) < 32 for character in remote):
        raise InputRejected("Git remote URL is invalid", code="provenance_failed")
    parsed = urlsplit(remote)
    if parsed.scheme and parsed.netloc:
        if parsed.scheme.lower() not in {"http", "https", "ssh", "git", "git+ssh"}:
            raise InputRejected("Git remote URL scheme is unsupported", code="provenance_failed")
        hostname = parsed.hostname or ""
        if not hostname:
            raise InputRejected("Git remote URL has no host", code="provenance_failed")
        try:
            parsed_port = parsed.port
        except ValueError as exc:
            raise InputRejected("Git remote URL port is invalid", code="provenance_failed") from exc
        display_hostname = f"[{hostname.lower()}]" if ":" in hostname else hostname.lower()
        port = f":{parsed_port}" if parsed_port else ""
        # Query strings commonly carry credentials; they are never provenance evidence.
        return urlunsplit((parsed.scheme.lower(), f"{display_hostname}{port}", parsed.path, "", ""))
    # SCP-like remotes contain a username. Preserve the host/path but remove the user.
    if "@" in remote and ":" in remote.split("@", 1)[1]:
        return remote.split("@", 1)[1].split("?", 1)[0].split("#", 1)[0]
    raise InputRejected("Git origin must be a network repository URL", code="provenance_failed")


def verify_git_provenance(snapshot: Snapshot, repository_root: str | Path) -> ProvenanceEvidence:
    try:
        root = resolve_operator_root(repository_root)
    except PathRejected as exc:
        raise PathRejected(str(exc).replace("configured root", "repository root")) from exc
    try:
        artifact_relative = snapshot.root.relative_to(root).as_posix()
    except ValueError as exc:
        raise PathRejected("artifact must be inside the repository root") from exc

    actual_root = Path(str(_git(root, "rev-parse", "--show-toplevel"))).resolve(strict=True)
    if actual_root != root:
        raise InputRejected("configured repository root is not the Git top level", code="provenance_failed")
    commit = str(_git(root, "rev-parse", "HEAD")).lower()
    if not COMMIT_PATTERN.fullmatch(commit):
        raise InputRejected("Git commit identity is invalid", code="provenance_failed")

    tracked_raw = _git(root, "ls-files", "-z", "--", artifact_relative, binary=True)
    assert isinstance(tracked_raw, bytes)
    try:
        tracked = {part.decode("utf-8", errors="strict") for part in tracked_raw.split(b"\x00") if part}
    except UnicodeDecodeError as exc:
        raise InputRejected("tracked Git paths were not UTF-8", code="provenance_failed") from exc
    expected = {
        f"{artifact_relative}/{item.path}" if artifact_relative != "." else item.path
        for item in snapshot.files
    }
    if tracked != expected:
        raise InputRejected("artifact file set does not exactly match tracked Git files", code="provenance_scope_mismatch")

    _verify_commit_blobs(snapshot, root, artifact_relative)

    staged = str(_git(root, "ls-files", "--stage", "--", artifact_relative))
    if any(line.startswith("160000 ") for line in staged.splitlines()):
        raise InputRejected("Git submodules are outside the MVP provenance scope", code="provenance_scope_mismatch")

    remote = _sanitize_remote(str(_git(root, "remote", "get-url", "origin")))
    if not remote:
        raise InputRejected("Git origin remote is required for Level 2 provenance", code="provenance_failed")
    return ProvenanceEvidence(
        repository_url=remote,
        commit=commit,
        artifact_path=artifact_relative,
    )
