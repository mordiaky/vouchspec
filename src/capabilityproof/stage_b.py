"""Immutable public-Git intake and isolated no-egress Stage B worker orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import threading
import time
from typing import Any, BinaryIO
import unicodedata
from uuid import uuid4

from .commerce import load_strict_commerce_json, parse_fresh_validation_request
from .errors import InputRejected, LimitExceeded, PathRejected
from .receipt import deterministic_json, verify_receipt_integrity
from .snapshot import ScanLimits, collect_snapshot


FROZEN_SOURCE_PROFILE = "vouchspec-frozen-public-git-v1"
WORKER_PROFILE = "vouchspec-docker-no-egress-static-v1"
MAX_GIT_METADATA_BYTES = 2_000_000
MAX_GIT_DIAGNOSTIC_BYTES = 16_384
MAX_ARCHIVE_OVERHEAD_BYTES = 4_000_000
MAX_WORKER_RECEIPT_BYTES = 1_000_000
MAX_GIT_REPOSITORY_BYTES = 64_000_000
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_IMAGE_REFERENCE = re.compile(
    r"(?:sha256:[0-9a-f]{64}|[A-Za-z0-9][A-Za-z0-9._/:+-]{0,254}@sha256:[0-9a-f]{64})"
)
_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul", *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


@dataclass(frozen=True)
class FrozenSource:
    root: Path
    artifact_root: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class WorkerResult:
    output_root: Path
    receipt_path: Path
    execution_path: Path
    receipt: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _remove_tree(path: Path, *, ignore_errors: bool = False) -> None:
    """Remove a private work tree, including read-only Git/Docker files on Windows."""

    def make_writable_and_retry(function: Any, failed_path: str, _: Any) -> None:
        os.chmod(failed_path, stat.S_IREAD | stat.S_IWRITE)
        function(failed_path)

    try:
        shutil.rmtree(path, onerror=make_writable_and_retry)
    except FileNotFoundError:
        return
    except OSError:
        if not ignore_errors:
            raise


def _enforce_repository_disk_limit(repository: Path) -> None:
    total = 0
    for directory, directory_names, file_names in os.walk(repository, followlinks=False):
        directory_names[:] = [
            name for name in directory_names if not (Path(directory) / name).is_symlink()
        ]
        for name in file_names:
            path = Path(directory) / name
            try:
                metadata = path.lstat()
            except OSError as exc:
                raise InputRejected(
                    "Git repository metadata could not be measured", code="source_checkout_failed"
                ) from exc
            if not stat.S_ISREG(metadata.st_mode):
                raise InputRejected(
                    "Git repository created a special filesystem entry", code="source_checkout_failed"
                )
            total += metadata.st_size
            if total > MAX_GIT_REPOSITORY_BYTES:
                raise LimitExceeded("Git repository metadata exceeds the 64 MB disk limit")


def request_digest(request: dict[str, Any]) -> str:
    normalized = parse_fresh_validation_request(request)
    return hashlib.sha256(_canonical(normalized)).hexdigest()


def _safe_git_environment() -> dict[str, str]:
    keep = ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP")
    environment = {key: os.environ[key] for key in keep if key in os.environ}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_EXTERNAL_DIFF": "",
            "GIT_ALLOW_PROTOCOL": "https",
            "GIT_PROTOCOL_FROM_USER": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def _safe_docker_environment() -> dict[str, str]:
    """Give the Docker client only connection/runtime state, never buyer or worker secrets."""

    keep = (
        "PATH", "HOME", "TMPDIR", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
        "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH",
    )
    return {key: os.environ[key] for key in keep if key in os.environ}


def _read_bounded(
    stream: BinaryIO,
    limit: int,
    output: bytearray,
    overflow: threading.Event,
    process: subprocess.Popen[bytes],
) -> None:
    try:
        while True:
            chunk = stream.read(65_536)
            if not chunk:
                return
            if len(output) + len(chunk) > limit:
                overflow.set()
                process.kill()
                return
            output.extend(chunk)
    finally:
        stream.close()


def _run_bounded(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    stdout_limit: int,
    code: str,
    environment: dict[str, str] | None = None,
) -> bytes:
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise InputRejected("bounded subprocess could not start", code=code) from exc
    assert process.stdout is not None and process.stderr is not None
    stdout = bytearray()
    stderr = bytearray()
    overflow = threading.Event()
    readers = [
        threading.Thread(
            target=_read_bounded,
            args=(process.stdout, stdout_limit, stdout, overflow, process),
            daemon=True,
        ),
        threading.Thread(
            target=_read_bounded,
            args=(process.stderr, MAX_GIT_DIAGNOSTIC_BYTES, stderr, overflow, process),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait(timeout=5)
        raise InputRejected("bounded subprocess timed out", code=code) from exc
    finally:
        for reader in readers:
            reader.join(timeout=5)
    if overflow.is_set():
        raise LimitExceeded("bounded subprocess output exceeded its limit", code=code)
    if return_code != 0:
        raise InputRejected("bounded subprocess failed", code=code)
    return bytes(stdout)


def _git(repository: Path, *arguments: str, timeout: int = 60, limit: int = MAX_GIT_METADATA_BYTES) -> bytes:
    command = [
        "git",
        "-c", f"core.hooksPath={os.devnull}",
        "-c", "credential.helper=",
        "-c", "protocol.file.allow=never",
        "-c", "protocol.ext.allow=never",
        "-c", "submodule.recurse=false",
        "-c", "core.fsmonitor=false",
        "-C", str(repository),
        *arguments,
    ]
    return _run_bounded(
        command,
        cwd=repository,
        timeout_seconds=timeout,
        stdout_limit=limit,
        code="source_checkout_failed",
        environment=_safe_git_environment(),
    )


def _validate_artifact_relative(path: str, limits: ScanLimits) -> str:
    if not path or "\\" in path or ":" in path:
        raise PathRejected("source contains a non-portable path")
    if unicodedata.normalize("NFC", path) != path:
        raise PathRejected("source path is not Unicode NFC")
    if any(ord(character) < 32 or ord(character) == 127 for character in path):
        raise PathRejected("source path contains a control character")
    pure = PurePosixPath(path)
    parts = pure.parts
    if path != pure.as_posix() or not parts or len(parts) > limits.max_depth:
        raise PathRejected("source path is absolute, ambiguous, or too deep")
    if len(path.encode("utf-8")) > limits.max_path_bytes:
        raise PathRejected("source path exceeds the byte limit")
    for component in parts:
        if component in {"", ".", ".."} or component.casefold() in {".git", ".hg", ".svn"}:
            raise PathRejected("source path contains a reserved segment")
        if component.endswith((" ", ".")) or len(component.encode("utf-8")) > 255:
            raise PathRejected("source path contains a non-portable segment")
        if component.split(".", 1)[0].casefold() in _WINDOWS_RESERVED:
            raise PathRejected("source path contains a reserved device name")
    return pure.as_posix()


def _parse_tree_listing(raw: bytes, skill_path: str, limits: ScanLimits) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    folded: set[str] = set()
    total_bytes = 0
    directories: set[str] = set()
    prefix = skill_path + "/"
    for record in raw.split(b"\x00"):
        if not record:
            continue
        header, separator, encoded_path = record.partition(b"\t")
        fields = header.split()
        if not separator or len(fields) != 4:
            raise InputRejected("Git tree metadata was malformed", code="source_tree_invalid")
        mode, object_type, oid, encoded_size = fields
        if object_type != b"blob" or mode not in {b"100644", b"100755"}:
            raise PathRejected("symlinks, submodules, and special Git entries are not accepted")
        try:
            full_path = encoded_path.decode("utf-8", errors="strict")
            size = int(encoded_size)
        except (UnicodeDecodeError, ValueError) as exc:
            raise InputRejected("Git tree path or size was invalid", code="source_tree_invalid") from exc
        if not full_path.startswith(prefix):
            raise InputRejected("Git tree entry escaped the requested skill path", code="source_tree_invalid")
        relative = _validate_artifact_relative(full_path[len(prefix):], limits)
        if len(oid) != 40 or any(character not in b"0123456789abcdef" for character in oid):
            raise InputRejected("Git blob identity was invalid", code="source_tree_invalid")
        if size < 0 or size > limits.max_file_bytes:
            raise LimitExceeded("source file exceeds the individual-file limit")
        if relative == "SKILL.md" and size > limits.max_skill_md_bytes:
            raise LimitExceeded("SKILL.md exceeds its configured byte limit")
        if len(expected) >= limits.max_files:
            raise LimitExceeded("source exceeds the file-count limit")
        total_bytes += size
        if total_bytes > limits.max_total_bytes:
            raise LimitExceeded("source exceeds the total-byte limit")
        identity = relative.casefold()
        if identity in folded:
            raise PathRejected("source contains a case-insensitive path collision")
        folded.add(identity)
        parent = PurePosixPath(relative).parent
        while parent.as_posix() != ".":
            directories.add(parent.as_posix().casefold())
            parent = parent.parent
        if len(directories) > limits.max_directories:
            raise LimitExceeded("source exceeds the directory-count limit")
        expected[relative] = {
            "size": size,
            "git_blob_sha1": oid.decode("ascii"),
            "git_mode": mode.decode("ascii"),
        }
    if not expected or "SKILL.md" not in expected:
        raise InputRejected("requested directory has no tracked SKILL.md", code="source_scope_invalid")
    return expected


def _extract_verified_archive(
    archive: bytes,
    artifact_root: Path,
    skill_path: str,
    expected: dict[str, dict[str, Any]],
    limits: ScanLimits,
) -> None:
    seen: set[str] = set()
    prefix = skill_path + "/"
    artifact_root.mkdir(parents=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as stream:
            for member in stream:
                name = member.name.rstrip("/")
                if member.isdir() and (name == skill_path or skill_path.startswith(name + "/")):
                    continue
                if not name.startswith(prefix):
                    raise PathRejected("archive member escaped the requested skill path")
                relative = _validate_artifact_relative(name[len(prefix):], limits)
                if member.isdir():
                    continue
                if not member.isreg() or member.linkname:
                    raise PathRejected("archive links and special entries are not accepted")
                metadata = expected.get(relative)
                if metadata is None or relative in seen or member.size != metadata["size"]:
                    raise InputRejected("archive did not match the verified Git tree", code="source_archive_mismatch")
                extracted = stream.extractfile(member)
                if extracted is None:
                    raise InputRejected("archive file could not be read", code="source_archive_mismatch")
                content = extracted.read(limits.max_file_bytes + 1)
                if len(content) != member.size:
                    raise InputRejected("archive file length was inconsistent", code="source_archive_mismatch")
                git_blob = hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()
                if git_blob != metadata["git_blob_sha1"]:
                    raise InputRejected("archive blob did not match Git metadata", code="source_archive_mismatch")
                destination = artifact_root.joinpath(*PurePosixPath(relative).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with destination.open("xb") as output:
                        output.write(content)
                except OSError as exc:
                    raise InputRejected("frozen source file could not be written", code="freeze_failed") from exc
                metadata["sha256"] = hashlib.sha256(content).hexdigest()
                seen.add(relative)
    except tarfile.TarError as exc:
        raise InputRejected("Git archive was malformed", code="source_archive_mismatch") from exc
    if seen != set(expected):
        raise InputRejected("archive file set did not match the verified Git tree", code="source_archive_mismatch")


def _manifest_digest(manifest: dict[str, Any]) -> str:
    candidate = dict(manifest)
    candidate.pop("manifest_digest", None)
    return hashlib.sha256(_canonical(candidate)).hexdigest()


def freeze_public_source(
    request_value: Any,
    output_root: Path,
    *,
    limits: ScanLimits | None = None,
) -> FrozenSource:
    """Fetch one immutable GitHub subdirectory and freeze verified regular-file bytes."""

    request = parse_fresh_validation_request(request_value)
    limits = limits or ScanLimits()
    digest = request_digest(request)
    output_root.mkdir(parents=True, exist_ok=True)
    output_root = output_root.resolve(strict=True)
    target = output_root / digest
    if target.exists():
        return verify_frozen_source(target, limits=limits)
    partial = output_root / f".partial-{digest}-{uuid4().hex}"
    repository = partial / "repository"
    source = request["source"]
    artifact_relative = PurePosixPath("source") / PurePosixPath(source["skill_path"]).name
    artifact_root = partial.joinpath(*artifact_relative.parts)
    repository_url = f"https://github.com/{source['owner']}/{source['repository']}.git"
    partial.mkdir()
    repository.mkdir()
    try:
        _git(repository, "init", "-q")
        _git(repository, "config", "core.autocrlf", "false")
        _git(repository, "config", "core.eol", "lf")
        _git(repository, "remote", "add", "origin", repository_url)
        _git(
            repository,
            "fetch", "--depth=1", "--no-tags", "--filter=tree:0", "origin", source["commit"],
            timeout=90,
        )
        _enforce_repository_disk_limit(repository)
        fetched = _git(repository, "rev-parse", "FETCH_HEAD").decode("ascii", errors="strict").strip()
        if fetched != source["commit"]:
            raise InputRejected("fetched commit did not match the request", code="source_commit_mismatch")
        object_type = _git(
            repository, "cat-file", "-t", f"FETCH_HEAD:{source['skill_path']}"
        ).decode("ascii", errors="strict").strip()
        if object_type != "tree":
            raise InputRejected("requested skill path is not a Git tree", code="source_scope_invalid")
        listing = _git(
            repository,
            "ls-tree", "-r", "-z", "-l", "--full-tree", "FETCH_HEAD", "--", source["skill_path"],
        )
        expected = _parse_tree_listing(listing, source["skill_path"], limits)
        _enforce_repository_disk_limit(repository)
        archive_limit = limits.max_total_bytes + MAX_ARCHIVE_OVERHEAD_BYTES
        archive = _git(
            repository,
            "archive", "--format=tar", "FETCH_HEAD", "--", source["skill_path"],
            timeout=90,
            limit=archive_limit,
        )
        _enforce_repository_disk_limit(repository)
        _extract_verified_archive(archive, artifact_root, source["skill_path"], expected, limits)
        snapshot = collect_snapshot(artifact_root, limits)
        files = []
        for file_data in snapshot.files:
            metadata = expected[file_data.path]
            if metadata.get("sha256") != file_data.sha256 or metadata["size"] != file_data.size:
                raise InputRejected("frozen snapshot did not match the Git archive", code="freeze_failed")
            files.append(
                {
                    "path": file_data.path,
                    "size": file_data.size,
                    "sha256": file_data.sha256,
                    "git_blob_sha1": metadata["git_blob_sha1"],
                    "git_mode": metadata["git_mode"],
                }
            )
        manifest: dict[str, Any] = {
            "schema_version": "1.0.0",
            "profile": FROZEN_SOURCE_PROFILE,
            "request_digest": f"sha256:{digest}",
            "source": source,
            "repository_url": repository_url,
            "fetched_commit": fetched,
            "frozen_artifact_path": artifact_relative.as_posix(),
            "artifact_directory_sha256": snapshot.directory_sha256,
            "file_count": len(files),
            "total_bytes": snapshot.total_bytes,
            "files": files,
            "network_phase": "completed_before_worker",
            "artifact_execution": "not_performed",
        }
        manifest["manifest_digest"] = f"sha256:{_manifest_digest(manifest)}"
        (partial / "freeze-manifest.json").write_bytes(deterministic_json(manifest) + b"\n")
        _remove_tree(repository)
        try:
            os.replace(partial, target)
        except FileExistsError:
            _remove_tree(partial, ignore_errors=True)
        return verify_frozen_source(target, limits=limits)
    except Exception:
        _remove_tree(partial, ignore_errors=True)
        raise


def verify_frozen_source(path: Path, *, limits: ScanLimits | None = None) -> FrozenSource:
    """Re-hash a frozen source and reject mutation before every worker invocation."""

    limits = limits or ScanLimits()
    root = path.resolve(strict=True)
    manifest_path = root / "freeze-manifest.json"
    try:
        manifest = load_strict_commerce_json(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputRejected("frozen source manifest is missing", code="frozen_source_invalid") from exc
    required = {
        "schema_version", "profile", "request_digest", "source", "repository_url",
        "fetched_commit", "frozen_artifact_path", "artifact_directory_sha256",
        "file_count", "total_bytes", "files",
        "network_phase", "artifact_execution", "manifest_digest",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise InputRejected("frozen source manifest fields are invalid", code="frozen_source_invalid")
    if (
        manifest["schema_version"] != "1.0.0"
        or manifest["profile"] != FROZEN_SOURCE_PROFILE
        or manifest["network_phase"] != "completed_before_worker"
        or manifest["artifact_execution"] != "not_performed"
        or not isinstance(manifest["manifest_digest"], str)
        or not _SHA256.fullmatch(manifest["manifest_digest"])
        or manifest["manifest_digest"] != f"sha256:{_manifest_digest(manifest)}"
    ):
        raise InputRejected("frozen source manifest integrity failed", code="frozen_source_invalid")
    source_request = {
        "schema_version": "1.0.0",
        "operation": "fresh_public_static_validation",
        "source": manifest["source"],
        "profile": "vouchspec-public-static-v1",
        "max_price": {"currency": "usd", "amount_minor": 4_900},
        "delivery_id": "frozen_verify",
    }
    normalized_source = parse_fresh_validation_request(source_request)["source"]
    expected_artifact_path = (
        PurePosixPath("source") / PurePosixPath(normalized_source["skill_path"]).name
    ).as_posix()
    if (
        normalized_source != manifest["source"]
        or manifest["repository_url"]
        != f"https://github.com/{normalized_source['owner']}/{normalized_source['repository']}.git"
        or manifest["fetched_commit"] != normalized_source["commit"]
        or manifest["frozen_artifact_path"] != expected_artifact_path
    ):
        raise InputRejected("frozen source coordinates are inconsistent", code="frozen_source_invalid")
    artifact_root = root.joinpath(*PurePosixPath(expected_artifact_path).parts)
    snapshot = collect_snapshot(artifact_root, limits)
    expected_files = [
        {"path": item.path, "size": item.size, "sha256": item.sha256}
        for item in snapshot.files
    ]
    manifest_files = manifest["files"]
    if not isinstance(manifest_files, list) or any(
        not isinstance(item, dict)
        or set(item) != {"path", "size", "sha256", "git_blob_sha1", "git_mode"}
        or not isinstance(item["git_blob_sha1"], str)
        or not re.fullmatch(r"[0-9a-f]{40}", item["git_blob_sha1"])
        or item["git_mode"] not in {"100644", "100755"}
        for item in manifest_files
    ) or [
        {"path": item["path"], "size": item["size"], "sha256": item["sha256"]}
        for item in manifest_files
    ] != expected_files:
        raise InputRejected("frozen source file inventory changed", code="frozen_source_mutated")
    if (
        manifest["file_count"] != len(snapshot.files)
        or manifest["total_bytes"] != snapshot.total_bytes
        or manifest["artifact_directory_sha256"] != snapshot.directory_sha256
    ):
        raise InputRejected("frozen source digest changed", code="frozen_source_mutated")
    return FrozenSource(root=root, artifact_root=artifact_root, manifest=manifest)


class DockerNoEgressWorker:
    """Run the static inspector in a pinned, least-privilege Docker container."""

    def __init__(self, image_reference: str, *, docker_binary: str = "docker") -> None:
        if not isinstance(image_reference, str) or not _IMAGE_REFERENCE.fullmatch(image_reference):
            raise ValueError("worker image must be an immutable sha256 image ID or registry digest")
        self.image_reference = image_reference
        self.docker_binary = docker_binary

    def command(
        self,
        frozen: FrozenSource,
        *,
        generated_at: str,
        expires_in_days: int,
        container_name: str,
    ) -> list[str]:
        return [
            self.docker_binary,
            "run", "--rm", "--pull=never", "--name", container_name,
            "--network", "none",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "64",
            "--memory", "256m",
            "--cpus", "1.0",
            "--ipc", "none",
            "--ulimit", "nofile=128:128",
            "--ulimit", "fsize=1048576:1048576",
            "--stop-timeout", "1",
            "--user", "65532:65532",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16777216",
            "--mount", f"type=bind,src={frozen.root},dst=/frozen,readonly",
            self.image_reference,
            "--frozen-root", "/frozen",
            "--generated-at", generated_at,
            "--expires-in-days", str(expires_in_days),
        ]

    def run(
        self,
        frozen_root: Path,
        output_root: Path,
        *,
        generated_at: str | None = None,
        expires_in_days: int = 7,
        timeout_seconds: int = 75,
    ) -> WorkerResult:
        frozen = verify_frozen_source(frozen_root)
        if output_root.exists():
            raise InputRejected("refusing to overwrite worker output", code="worker_output_exists")
        if not 1 <= expires_in_days <= 30:
            raise ValueError("expires_in_days must be 1 through 30")
        timestamp = generated_at or _utc_now()
        name = f"vouchspec-worker-{uuid4().hex[:20]}"
        command = self.command(
            frozen,
            generated_at=timestamp,
            expires_in_days=expires_in_days,
            container_name=name,
        )
        started = time.monotonic()
        started_at = _utc_now()
        try:
            receipt_bytes = _run_bounded(
                command,
                cwd=frozen.root,
                timeout_seconds=timeout_seconds,
                stdout_limit=MAX_WORKER_RECEIPT_BYTES,
                code="isolated_worker_failed",
                environment=_safe_docker_environment(),
            )
        except Exception:
            subprocess.run(
                [self.docker_binary, "rm", "-f", name],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=_safe_docker_environment(),
                timeout=10,
                check=False,
            )
            raise
        duration_ms = int((time.monotonic() - started) * 1_000)
        try:
            receipt = load_strict_commerce_json(receipt_bytes.decode("utf-8", errors="strict"))
        except UnicodeError as exc:
            raise InputRejected("worker did not produce a readable receipt", code="isolated_worker_failed") from exc
        if not isinstance(receipt, dict) or not verify_receipt_integrity(receipt):
            raise InputRejected("worker receipt integrity failed", code="isolated_worker_failed")
        if (
            receipt["artifact"]["digest"]["sha256"] != frozen.manifest["artifact_directory_sha256"]
            or receipt["provenance"]["source_commit"] != frozen.manifest["fetched_commit"]
            or receipt["provenance"]["artifact_path"] != frozen.manifest["source"]["skill_path"]
        ):
            raise InputRejected("worker receipt did not bind the frozen source", code="isolated_worker_failed")
        output_root.mkdir(parents=True)
        receipt_path = output_root / "receipt.json"
        receipt_path.write_bytes(receipt_bytes)
        execution = {
            "schema_version": "1.0.0",
            "profile": WORKER_PROFILE,
            "container_image": self.image_reference,
            "network": "none",
            "root_filesystem": "read_only",
            "input_mount": "read_only",
            "capabilities": "all_dropped",
            "no_new_privileges": True,
            "uid_gid": "65532:65532",
            "pids_limit": 64,
            "memory_limit_bytes": 268_435_456,
            "cpu_limit": "1.0",
            "tmpfs": "16MiB_noexec_nosuid_nodev",
            "ipc": "none",
            "open_files_limit": 128,
            "file_size_limit_bytes": 1_048_576,
            "stop_timeout_seconds": 1,
            "output_channel": "bounded_stdout_1000000_bytes",
            "started_at": started_at,
            "completed_at": _utc_now(),
            "duration_ms": duration_ms,
            "receipt_id": receipt["receipt_id"],
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "freeze_manifest_digest": frozen.manifest["manifest_digest"],
            "artifact_execution": "not_performed",
        }
        execution_path = output_root / "worker-execution.json"
        execution_path.write_bytes(deterministic_json(execution) + b"\n")
        return WorkerResult(
            output_root=output_root,
            receipt_path=receipt_path,
            execution_path=execution_path,
            receipt=receipt,
        )
