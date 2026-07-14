"""Bounded loopback HTTP retrieval API for the Stage A catalog."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from .catalog import validate_receipt_id
from .catalog_runtime import VerifiedCatalog
from .errors import CapabilityProofError, InputRejected
from .pricing import price_quote
from .signing import load_public_jwk


CONNECTION_TIMEOUT_SECONDS = 5
MAX_ACTIVE_CONNECTIONS = 32


class BoundedCatalogServer(ThreadingHTTPServer):
    request_queue_size = 64

    def __init__(self, *args: Any, max_active: int = MAX_ACTIVE_CONNECTIONS, **kwargs: Any) -> None:
        self._capacity = threading.BoundedSemaphore(max_active)
        super().__init__(*args, **kwargs)

    def process_request(self, request: Any, client_address: Any) -> None:
        if not self._capacity.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._capacity.release()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._capacity.release()


def make_catalog_handler(
    catalog_root: Path,
    trusted_root_key: Path,
    sequence_state_path: Path,
) -> type[BaseHTTPRequestHandler]:
    runtime = VerifiedCatalog(catalog_root, load_public_jwk(trusted_root_key), sequence_state_path)

    class VouchSpecCatalogHandler(BaseHTTPRequestHandler):
        server_version = "VouchSpec/0.2"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(CONNECTION_TIMEOUT_SECONDS)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _send_bytes(self, status: int, body: bytes, *, cache: str = "public, max-age=60") -> None:
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", cache)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                return

        def _send(self, status: int, payload: Any, *, cache: str = "public, max-age=60") -> None:
            self._send_bytes(
                status,
                (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"),
                cache=cache,
            )

        def do_GET(self) -> None:  # noqa: N802
            try:
                parsed = urlsplit(self.path)
                if len(parsed.query) > 2_048:
                    raise InputRejected("query string is too long", code="invalid_query")
                route = unquote(parsed.path)
                if route == "/health":
                    self._send(200, {"service": "VouchSpec", "stage": "A_PUBLIC_ARTIFACT_INDEX", "status": "ok", "version": "0.2.0"})
                    return
                if route == "/v1/index":
                    self._send_bytes(200, runtime.index_envelope_bytes(), cache="public, max-age=60, must-revalidate")
                    return
                if route == "/v1/quote":
                    query = parse_qs(parsed.query, keep_blank_values=False, strict_parsing=True)
                    if set(query) != {"operation"} or len(query["operation"]) != 1:
                        raise InputRejected("exactly one operation is required", code="invalid_query")
                    self._send(200, price_quote(query["operation"][0]), cache="public, max-age=300")
                    return
                if route == "/v1/receipts":
                    query = parse_qs(parsed.query, keep_blank_values=False, strict_parsing=True)
                    if set(query) - {"q", "repository_owner", "limit"} or any(len(values) != 1 for values in query.values()):
                        raise InputRejected("unsupported or repeated query parameter", code="invalid_query")
                    try:
                        limit = int(query.get("limit", ["50"])[0])
                    except ValueError as exc:
                        raise InputRejected("limit must be an integer", code="invalid_query") from exc
                    entries = runtime.list_entries(
                        query=query.get("q", [None])[0],
                        repository_owner=query.get("repository_owner", [None])[0],
                        limit=limit,
                    )
                    self._send(200, {"count": len(entries), "entries": entries}, cache="public, max-age=60, must-revalidate")
                    return
                if route == "/v1/lifecycle":
                    self._send_bytes(200, runtime.lifecycle_envelope_bytes(), cache="public, max-age=60, must-revalidate")
                    return
                if route == "/v1/keys/root":
                    self._send_bytes(200, runtime.root_jwk_bytes(), cache="public, max-age=3600")
                    return
                if route == "/v1/keys/issuer":
                    self._send_bytes(200, runtime.issuer_jwk_bytes(), cache="public, max-age=3600")
                    return
                parts = [part for part in route.split("/") if part]
                if len(parts) in {3, 4} and parts[:2] == ["v1", "receipts"]:
                    receipt_id = validate_receipt_id(parts[2])
                    if len(parts) == 3:
                        self._send_bytes(200, runtime.receipt_envelope_bytes(receipt_id), cache="public, max-age=31536000, immutable")
                        return
                    if parts[3] == "status":
                        self._send(200, runtime.status(receipt_id), cache="public, max-age=60, must-revalidate")
                        return
                self._send(404, {"error": {"code": "not_found", "message": "route not found"}})
            except (ValueError, UnicodeError) as exc:
                self._send(400, {"error": {"code": "invalid_query", "message": str(exc)[:200]}})
            except CapabilityProofError as exc:
                status = 404 if exc.code == "not_found" else 422
                self._send(status, {"error": {"code": exc.code, "message": str(exc)}})
            except Exception:
                self._send(500, {"error": {"code": "internal_error", "message": "catalog retrieval failed"}})

        def do_POST(self) -> None:  # noqa: N802
            self._send(405, {"error": {"code": "read_only", "message": "Stage A accepts retrieval requests only"}})

    return VouchSpecCatalogHandler


def create_catalog_server(
    catalog_root: Path,
    port: int,
    trusted_root_key: Path,
    sequence_state_path: Path,
    *,
    max_active: int = MAX_ACTIVE_CONNECTIONS,
) -> BoundedCatalogServer:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65_535:
        raise ValueError("port must be from 0 through 65535")
    if isinstance(max_active, bool) or not isinstance(max_active, int) or not 1 <= max_active <= 256:
        raise ValueError("max_active must be from 1 through 256")
    server = BoundedCatalogServer(
        ("127.0.0.1", port),
        make_catalog_handler(catalog_root, trusted_root_key, sequence_state_path),
        max_active=max_active,
    )
    server.daemon_threads = True
    return server
