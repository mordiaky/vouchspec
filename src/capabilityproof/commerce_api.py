"""Authenticated loopback HTTP boundary for sandbox Stage B commerce.

The server is intentionally sandbox-only and must sit behind managed HTTPS before any
external deployment. It never accepts uploads or enables live settlement.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any
from urllib.parse import urlsplit

from .commerce import load_strict_commerce_json
from .commerce_access import CommerceAccessStore
from .commerce_store import CommerceStore, FakePaymentProvider
from .errors import CapabilityProofError, InputRejected


CONNECTION_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class CommerceApiLimits:
    max_body_bytes: int = 16_384
    max_active_connections: int = 32
    window_seconds: int = 60
    global_requests_per_window: int = 240
    ip_requests_per_window: int = 60
    tenant_requests_per_window: int = 30
    max_quotes_per_tenant: int = 100
    max_orders_per_tenant: int = 50

    def __post_init__(self) -> None:
        values = {
            "max_body_bytes": (self.max_body_bytes, 256, 65_536),
            "max_active_connections": (self.max_active_connections, 1, 256),
            "window_seconds": (self.window_seconds, 1, 3_600),
            "global_requests_per_window": (self.global_requests_per_window, 1, 100_000),
            "ip_requests_per_window": (self.ip_requests_per_window, 1, 100_000),
            "tenant_requests_per_window": (self.tenant_requests_per_window, 1, 100_000),
            "max_quotes_per_tenant": (self.max_quotes_per_tenant, 1, 10_000),
            "max_orders_per_tenant": (self.max_orders_per_tenant, 1, 10_000),
        }
        for name, (value, lower, upper) in values.items():
            if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
                raise ValueError(f"{name} must be from {lower} through {upper}")


class SlidingWindowRateLimiter:
    """Small single-process limiter for the loopback application boundary."""

    def __init__(self, window_seconds: int) -> None:
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, *, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        cutoff = moment - self.window_seconds
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(moment)
            if len(self._events) > 10_000:
                stale = [
                    candidate
                    for candidate, values in self._events.items()
                    if not values or values[-1] <= cutoff
                ]
                for candidate in stale[:1_000]:
                    self._events.pop(candidate, None)
            return True


class BoundedCommerceServer(ThreadingHTTPServer):
    request_queue_size = 64

    def __init__(self, *args: Any, max_active: int, **kwargs: Any) -> None:
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


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("commerce API clock must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _public_order(order: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "order_id",
        "environment",
        "quote_id",
        "order_status",
        "payment_status",
        "quoted_amount_minor",
        "collected_amount_minor",
        "refunded_amount_minor",
        "currency",
        "receipt_id",
        "receipt_sha256",
        "envelope_sha256",
        "signing_keyid",
        "delivery_status",
        "refund_status",
        "settlement_status",
        "counts_for_goal",
        "created_at",
        "updated_at",
    )
    return {key: order[key] for key in keys}


def make_commerce_handler(
    store: CommerceStore,
    access: CommerceAccessStore,
    *,
    limits: CommerceApiLimits | None = None,
    now_source: Callable[[], datetime] | None = None,
) -> type[BaseHTTPRequestHandler]:
    settings = limits or CommerceApiLimits()
    rate_limiter = SlidingWindowRateLimiter(settings.window_seconds)
    clock = now_source or (lambda: datetime.now(timezone.utc))
    payment_provider = FakePaymentProvider(store)
    creation_lock = threading.Lock()

    class VouchSpecCommerceHandler(BaseHTTPRequestHandler):
        server_version = "VouchSpec-Commerce/0.2"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(CONNECTION_TIMEOUT_SECONDS)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _send_bytes(
            self,
            status: int,
            body: bytes,
            *,
            content_type: str = "application/json; charset=utf-8",
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            try:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "private, no-store")
                self.send_header("Pragma", "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
                self.send_header("Connection", "close")
                for name, value in (extra_headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                if body:
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                return

        def _send(self, status: int, payload: Any, *, extra_headers: dict[str, str] | None = None) -> None:
            body = (
                json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                + "\n"
            ).encode("utf-8")
            self._send_bytes(status, body, extra_headers=extra_headers)

        def _apply_public_limits(self) -> None:
            client_ip = str(self.client_address[0])
            if not rate_limiter.allow("global", settings.global_requests_per_window):
                raise InputRejected("request rate exceeded", code="rate_limited")
            if not rate_limiter.allow("ip:" + client_ip, settings.ip_requests_per_window):
                raise InputRejected("request rate exceeded", code="rate_limited")

        def _authenticate(self) -> str:
            headers = self.headers.get_all("Authorization", failobj=[])
            if len(headers) != 1 or not headers[0].startswith("Bearer ") or headers[0].count(" ") != 1:
                raise InputRejected("authentication failed", code="authentication_failed")
            tenant_id = access.authenticate_api_key(headers[0][7:])
            if not rate_limiter.allow("tenant:" + tenant_id, settings.tenant_requests_per_window):
                raise InputRejected("request rate exceeded", code="rate_limited")
            return tenant_id

        def _delivery_token(self) -> str:
            headers = self.headers.get_all("X-VouchSpec-Delivery-Token", failobj=[])
            if len(headers) != 1:
                raise InputRejected("object was not found", code="authorization_failed")
            return headers[0]

        def _idempotency_key(self) -> str:
            headers = self.headers.get_all("Idempotency-Key", failobj=[])
            if len(headers) != 1:
                raise InputRejected("exactly one Idempotency-Key is required", code="invalid_commerce_request")
            return headers[0]

        def _route(self) -> str:
            if len(self.path) > 256 or any(ord(character) < 0x20 for character in self.path):
                raise InputRejected("request target is invalid", code="invalid_commerce_request")
            parsed = urlsplit(self.path)
            if parsed.query or parsed.fragment or "%" in parsed.path:
                raise InputRejected("query strings and encoded commerce paths are not accepted", code="invalid_commerce_request")
            return parsed.path

        def _read_json(self) -> Any:
            if self.headers.get_all("Transfer-Encoding", failobj=[]):
                raise InputRejected("transfer encoding is not accepted", code="invalid_commerce_request")
            content_types = self.headers.get_all("Content-Type", failobj=[])
            lengths = self.headers.get_all("Content-Length", failobj=[])
            if content_types != ["application/json"] or len(lengths) != 1:
                raise InputRejected(
                    "Content-Type application/json and one Content-Length are required",
                    code="invalid_commerce_request",
                )
            try:
                length = int(lengths[0])
            except ValueError as exc:
                raise InputRejected("Content-Length is invalid", code="invalid_commerce_request") from exc
            if not 1 <= length <= settings.max_body_bytes:
                raise InputRejected("request body size is invalid", code="invalid_commerce_request")
            body = self.rfile.read(length)
            if len(body) != length:
                raise InputRejected("request body is incomplete", code="invalid_commerce_request")
            try:
                text = body.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise InputRejected("request body must be UTF-8", code="invalid_commerce_request") from exc
            return load_strict_commerce_json(text)

        @staticmethod
        def _exact_object(value: Any, keys: set[str]) -> dict[str, Any]:
            if not isinstance(value, dict) or set(value) != keys:
                raise InputRejected(
                    f"request body must contain exactly {sorted(keys)}",
                    code="invalid_commerce_request",
                )
            return value

        def _handle_error(self, error: CapabilityProofError) -> None:
            code = error.code
            headers: dict[str, str] = {}
            if code == "authentication_failed":
                status, public_code, message = 401, "authentication_failed", "authentication failed"
                headers["WWW-Authenticate"] = 'Bearer realm="vouchspec-commerce"'
            elif code in {"authorization_failed", "object_not_found", "unknown_order"}:
                status, public_code, message = 404, "not_found", "resource not found"
            elif code == "rate_limited":
                status, public_code, message = 429, "rate_limited", "request rate exceeded"
                headers["Retry-After"] = str(settings.window_seconds)
            elif code in {
                "idempotency_conflict",
                "quote_already_used",
                "result_not_ready",
                "resource_limit",
            }:
                status, public_code, message = 409, code, str(error)[:200]
            elif code == "commerce_live_not_enabled":
                status, public_code, message = 503, code, "live commerce is not enabled"
            else:
                status, public_code, message = 422, code, str(error)[:200]
            self._send(status, {"error": {"code": public_code, "message": message}}, extra_headers=headers)

        def do_GET(self) -> None:  # noqa: N802
            try:
                self._apply_public_limits()
                route = self._route()
                if route == "/health":
                    self._send(
                        200,
                        {
                            "service": "vouchspec-commerce",
                            "environment": "sandbox",
                            "live_settlement": False,
                            "status": "ok",
                            "version": "0.2.0",
                        },
                    )
                    return
                tenant_id = self._authenticate()
                parts = [part for part in route.split("/") if part]
                if len(parts) not in {4, 5} or parts[:3] != ["v1", "commerce", "orders"]:
                    self._send(404, {"error": {"code": "not_found", "message": "route not found"}})
                    return
                order_id = parts[3]
                delivery_token = self._delivery_token()
                now = clock()
                access.authorize_order(tenant_id, order_id, delivery_token, now=now)
                if len(parts) == 4:
                    self._send(200, {"order": _public_order(store.get_order(order_id))})
                    return
                if parts[4] == "result":
                    result = access.get_result(tenant_id, order_id, delivery_token, now=now)
                    self._send_bytes(
                        200,
                        result,
                        content_type="application/vnd.dsse.envelope.v1+json",
                        extra_headers={"ETag": '"sha256:' + hashlib.sha256(result).hexdigest() + '"'},
                    )
                    return
                self._send(404, {"error": {"code": "not_found", "message": "route not found"}})
            except CapabilityProofError as exc:
                self._handle_error(exc)
            except Exception:
                self._send(500, {"error": {"code": "internal_error", "message": "commerce request failed"}})

        def do_POST(self) -> None:  # noqa: N802
            try:
                self._apply_public_limits()
                route = self._route()
                tenant_id = self._authenticate()
                now = clock()
                timestamp = _timestamp(now)
                if route == "/v1/commerce/quotes":
                    request = self._read_json()
                    idempotency_key = self._idempotency_key()
                    quote_id = access.derive_quote_id(tenant_id, idempotency_key)
                    with creation_lock:
                        if (
                            not access.quote_owned(tenant_id, quote_id)
                            and access.tenant_resource_counts(tenant_id)["quotes"]
                            >= settings.max_quotes_per_tenant
                        ):
                            raise InputRejected(
                                "tenant quote storage limit reached", code="resource_limit"
                            )
                        quote = store.create_quote(request, quote_id=quote_id, generated_at=now)
                        if quote["orderable"]:
                            access.bind_quote(
                                tenant_id,
                                quote_id,
                                idempotency_key=idempotency_key,
                                created_at=timestamp,
                            )
                    self._send(201, {"quote": quote})
                    return
                if route == "/v1/commerce/orders":
                    body = self._exact_object(self._read_json(), {"quote_id"})
                    if not isinstance(body["quote_id"], str):
                        raise InputRejected("quote_id must be a string", code="invalid_commerce_request")
                    idempotency_key = self._idempotency_key()
                    internal_idempotency_key = access.derive_order_idempotency_key(
                        tenant_id, idempotency_key
                    )
                    access.authorize_quote(tenant_id, body["quote_id"])
                    with creation_lock:
                        if (
                            access.order_for_quote(tenant_id, body["quote_id"]) is None
                            and access.tenant_resource_counts(tenant_id)["orders"]
                            >= settings.max_orders_per_tenant
                        ):
                            raise InputRejected(
                                "tenant order storage limit reached", code="resource_limit"
                            )
                        order = store.create_order(
                            body["quote_id"],
                            idempotency_key=internal_idempotency_key,
                            buyer_reference=tenant_id,
                            now=now,
                        )
                        delivery_token = access.bind_order(
                            tenant_id,
                            order["order_id"],
                            body["quote_id"],
                            created_at=timestamp,
                        )
                    token_state = access.authorize_order(
                        tenant_id, order["order_id"], delivery_token, now=now
                    )
                    order = payment_provider.create_checkout(order["order_id"], occurred_at=timestamp)
                    self._send(
                        201,
                        {
                            "order": _public_order(order),
                            "delivery_token": delivery_token,
                            "delivery_token_expires_at": token_state["token_expires_at"],
                            "delivery_token_notice": "store securely; required with the tenant API key",
                            "payment": {"provider": "fake", "environment": "sandbox", "settles": False},
                        },
                    )
                    return
                parts = [part for part in route.split("/") if part]
                if (
                    len(parts) == 6
                    and parts[:3] == ["v1", "commerce", "orders"]
                    and parts[4] == "delivery-token"
                    and parts[5] in {"rotate", "revoke"}
                ):
                    self._exact_object(self._read_json(), set())
                    current = self._delivery_token()
                    if parts[5] == "rotate":
                        token = access.rotate_delivery_token(
                            tenant_id, parts[3], current, updated_at=timestamp
                        )
                        token_state = access.authorize_order(
                            tenant_id, parts[3], token, now=now
                        )
                        self._send(
                            200,
                            {
                                "order_id": parts[3],
                                "delivery_token": token,
                                "delivery_token_expires_at": token_state["token_expires_at"],
                                "prior_token_status": "revoked_by_rotation",
                            },
                        )
                    else:
                        access.revoke_delivery_token(
                            tenant_id, parts[3], current, updated_at=timestamp
                        )
                        self._send(200, {"order_id": parts[3], "delivery_token_status": "revoked"})
                    return
                self._send(404, {"error": {"code": "not_found", "message": "route not found"}})
            except CapabilityProofError as exc:
                self._handle_error(exc)
            except Exception:
                self._send(500, {"error": {"code": "internal_error", "message": "commerce request failed"}})

        def do_PUT(self) -> None:  # noqa: N802
            try:
                self._apply_public_limits()
                self._send(405, {"error": {"code": "method_not_allowed", "message": "method not allowed"}})
            except CapabilityProofError as exc:
                self._handle_error(exc)

        do_DELETE = do_PUT
        do_PATCH = do_PUT
        do_OPTIONS = do_PUT
        do_TRACE = do_PUT
        do_CONNECT = do_PUT

        def do_HEAD(self) -> None:  # noqa: N802
            try:
                self._apply_public_limits()
                self._send_bytes(405, b"")
            except CapabilityProofError as exc:
                self._handle_error(exc)

    return VouchSpecCommerceHandler


def create_commerce_server(
    store: CommerceStore,
    access: CommerceAccessStore,
    port: int,
    *,
    limits: CommerceApiLimits | None = None,
    now_source: Callable[[], datetime] | None = None,
) -> BoundedCommerceServer:
    if store.environment != "sandbox" or access.environment != "sandbox":
        raise InputRejected("live commerce API is not enabled", code="commerce_live_not_enabled")
    if store.path != access.path:
        raise ValueError("commerce and access stores must share one SQLite file")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65_535:
        raise ValueError("port must be from 0 through 65535")
    settings = limits or CommerceApiLimits()
    server = BoundedCommerceServer(
        ("127.0.0.1", port),
        make_commerce_handler(store, access, limits=settings, now_source=now_source),
        max_active=settings.max_active_connections,
    )
    server.daemon_threads = True
    return server
