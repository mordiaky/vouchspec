"""Small loopback-only JSON API around the deterministic inspector."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any, Callable

from .errors import CapabilityProofError, InputRejected, PathRejected
from .receipt import inspect_skill
from .snapshot import ScanLimits, resolve_allowed_path, resolve_operator_root


MAX_REQUEST_BYTES = 16_384
CONNECTION_TIMEOUT_SECONDS = 5


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _validate_request(payload: Any) -> tuple[str, str | None, int]:
    if not isinstance(payload, dict):
        raise InputRejected("request body must be a JSON object")
    unknown = set(payload) - {"path", "generated_at", "expires_in_days"}
    if unknown:
        raise InputRejected(f"unsupported request fields: {', '.join(sorted(unknown))}")
    path = payload.get("path")
    generated_at = payload.get("generated_at")
    expires = payload.get("expires_in_days", 7)
    if not isinstance(path, str):
        raise InputRejected("path must be a string")
    if generated_at is not None and not isinstance(generated_at, str):
        raise InputRejected("generated_at must be a string")
    if isinstance(expires, bool) or not isinstance(expires, int):
        raise InputRejected("expires_in_days must be an integer")
    return path, generated_at, expires


def make_handler(allowed_root: Path, limits: ScanLimits | None = None) -> type[BaseHTTPRequestHandler]:
    root = resolve_operator_root(allowed_root)
    limits = limits or ScanLimits()

    class CapabilityProofHandler(BaseHTTPRequestHandler):
        server_version = "VouchSpec/0.2"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(CONNECTION_TIMEOUT_SECONDS)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            # Avoid reflecting submitted paths or payloads into default logs.
            return

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                return

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._send(200, {"status": "ok", "service": "vouchspec", "version": "0.2.0"})
            else:
                self._send(404, {"error": {"code": "not_found", "message": "route not found"}})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/inspect":
                self._send(404, {"error": {"code": "not_found", "message": "route not found"}})
                return
            content_types = self.headers.get_all("Content-Type") or []
            if len(content_types) != 1:
                self._send(400, {"error": {"code": "ambiguous_headers", "message": "exactly one Content-Type header is required"}})
                return
            content_type = content_types[0].split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                self._send(415, {"error": {"code": "unsupported_media_type", "message": "Content-Type must be application/json"}})
                return
            if self.headers.get_all("Transfer-Encoding"):
                self._send(400, {"error": {"code": "unsupported_transfer", "message": "Transfer-Encoding is not supported"}})
                return
            content_lengths = self.headers.get_all("Content-Length") or []
            if len(content_lengths) != 1:
                self._send(400, {"error": {"code": "ambiguous_headers", "message": "exactly one Content-Length header is required"}})
                return
            raw_length = content_lengths[0]
            try:
                length = int(raw_length or "")
            except ValueError:
                self._send(411, {"error": {"code": "length_required", "message": "valid Content-Length required"}})
                return
            if length < 0 or length > MAX_REQUEST_BYTES:
                self._send(413, {"error": {"code": "request_too_large", "message": "request body exceeds limit"}})
                return

            try:
                raw_body = self.rfile.read(length)
                if len(raw_body) != length:
                    raise ValueError("request body ended before Content-Length bytes were read")
                payload = json.loads(raw_body.decode("utf-8"), object_pairs_hook=_no_duplicate_object)
                submitted_path, generated_at, expires = _validate_request(payload)
                target = resolve_allowed_path(root, submitted_path)
                receipt = inspect_skill(target, generated_at=generated_at, expires_in_days=expires, limits=limits)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
                self._send(400, {"error": {"code": "invalid_json", "message": str(exc)[:200]}})
                return
            except PathRejected as exc:
                self._send(403, {"error": {"code": exc.code, "message": str(exc)}})
                return
            except CapabilityProofError as exc:
                self._send(422, {"error": {"code": exc.code, "message": str(exc)}})
                return
            except TimeoutError:
                self._send(408, {"error": {"code": "request_timeout", "message": "request body timed out"}})
                return
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                self._send(500, {"error": {"code": "internal_error", "message": "inspection failed"}})
                return
            self._send(200, {"receipt": receipt})

    return CapabilityProofHandler


def create_server(allowed_root: Path, port: int, limits: ScanLimits | None = None) -> ThreadingHTTPServer:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65_535:
        raise ValueError("port must be from 0 through 65535")
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(allowed_root, limits))
    server.daemon_threads = True
    return server
