"""Tenant and capability access controls for the constrained commerce boundary.

This extension shares the CommerceStore SQLite file but keeps authentication state in
separate tables. API keys and delivery capabilities are never persisted in plaintext.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import sqlite3
from typing import Any, Iterator

from .errors import InputRejected


ACCESS_SCHEMA_VERSION = "2"
MAX_RESULT_BYTES = 1_000_000
DELIVERY_TOKEN_TTL = timedelta(days=30)

_TENANT_ID = re.compile(r"ten_[0-9a-f]{24}")
_API_KEY = re.compile(r"vsk_(?:test|live)_[A-Za-z0-9_-]{43}")
_DELIVERY_TOKEN = re.compile(r"vsd_(?:test|live)_[A-Za-z0-9_-]{43}")
_QUOTE_ID = re.compile(r"q_[0-9a-f]{24}")
_ORDER_ID = re.compile(r"ord_(?:test_)?[0-9a-f]{24}")
_IDEMPOTENCY = re.compile(r"[A-Za-z0-9_-]{8,96}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise InputRejected("access timestamp must be a string", code="invalid_commerce_request")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InputRejected("access timestamp is invalid", code="invalid_commerce_request") from exc
    if parsed.tzinfo is None:
        raise InputRejected("access timestamp requires a timezone", code="invalid_commerce_request")
    return parsed.astimezone(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _token_bytes(value: bytes, label: bytes, *parts: str) -> bytes:
    message = label + b"\0" + b"\0".join(part.encode("ascii") for part in parts)
    return hmac.new(value, message, hashlib.sha256).digest()


def _urlsafe(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class CommerceAccessStore:
    """Keyed-digest tenant, quote, order, and result authorization state."""

    def __init__(
        self,
        path: Path,
        *,
        environment: str,
        auth_pepper: bytes,
        delivery_secret: bytes,
    ) -> None:
        if environment not in {"sandbox", "live"}:
            raise ValueError("environment must be sandbox or live")
        if not isinstance(auth_pepper, bytes) or len(auth_pepper) < 32:
            raise ValueError("auth_pepper must contain at least 32 bytes")
        if not isinstance(delivery_secret, bytes) or len(delivery_secret) < 32:
            raise ValueError("delivery_secret must contain at least 32 bytes")
        if hmac.compare_digest(auth_pepper, delivery_secret):
            raise ValueError("authentication and delivery secrets must be distinct")
        self.path = path.expanduser().resolve(strict=False)
        self.environment = environment
        self._auth_pepper = auth_pepper
        self._delivery_secret = delivery_secret
        self._initialize()

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            if write:
                connection.commit()
        except Exception:
            if write:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        if not self.path.is_file():
            raise InputRejected("commerce store must exist before access state", code="commerce_store_missing")
        with self._connection(write=True) as connection:
            metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
            if metadata.get("environment") != self.environment:
                raise InputRejected(
                    "commerce access environment does not match the store",
                    code="commerce_environment_mismatch",
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS access_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS access_tenants (
                    tenant_id TEXT PRIMARY KEY,
                    api_key_digest BLOB NOT NULL UNIQUE,
                    state TEXT NOT NULL CHECK(state IN ('active', 'revoked')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS access_quote_bindings (
                    quote_id TEXT PRIMARY KEY REFERENCES quotes(quote_id),
                    tenant_id TEXT NOT NULL REFERENCES access_tenants(tenant_id),
                    idempotency_digest BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(tenant_id, idempotency_digest)
                );
                CREATE TABLE IF NOT EXISTS access_order_bindings (
                    order_id TEXT PRIMARY KEY REFERENCES orders(order_id),
                    quote_id TEXT NOT NULL UNIQUE REFERENCES access_quote_bindings(quote_id),
                    tenant_id TEXT NOT NULL REFERENCES access_tenants(tenant_id),
                    token_version INTEGER NOT NULL CHECK(token_version >= 1),
                    token_digest BLOB NOT NULL,
                    token_state TEXT NOT NULL CHECK(token_state IN ('active', 'revoked')),
                    token_expires_at TEXT NOT NULL,
                    result_sha256 TEXT,
                    result_body BLOB,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK((result_sha256 IS NULL) = (result_body IS NULL))
                );
                CREATE INDEX IF NOT EXISTS access_orders_tenant
                    ON access_order_bindings(tenant_id, order_id);
                CREATE TABLE IF NOT EXISTS access_audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    tenant_id TEXT,
                    quote_id TEXT,
                    order_id TEXT,
                    outcome TEXT NOT NULL CHECK(outcome IN ('success', 'rejected')),
                    observed_at TEXT NOT NULL
                );
                """
            )
            access_metadata = dict(
                connection.execute("SELECT key, value FROM access_metadata").fetchall()
            )
            expected = {
                "schema_version": ACCESS_SCHEMA_VERSION,
                "environment": self.environment,
                "auth_key_id": hashlib.sha256(self._auth_pepper).hexdigest(),
                "delivery_key_id": hashlib.sha256(self._delivery_secret).hexdigest(),
            }
            if not access_metadata:
                connection.executemany(
                    "INSERT INTO access_metadata(key, value) VALUES (?, ?)", expected.items()
                )
            elif access_metadata != expected:
                raise InputRejected(
                    "commerce access schema or environment does not match",
                    code="commerce_environment_mismatch",
                )

    def _api_digest(self, api_key: str) -> bytes:
        return _token_bytes(self._auth_pepper, b"api-key", api_key)

    def _idempotency_digest(self, tenant_id: str, idempotency_key: str) -> bytes:
        return _token_bytes(self._auth_pepper, b"quote-idempotency", tenant_id, idempotency_key)

    def _delivery_token(self, tenant_id: str, order_id: str, version: int) -> str:
        raw = _token_bytes(
            self._delivery_secret, b"delivery-token", tenant_id, order_id, str(version)
        )
        prefix = "vsd_test_" if self.environment == "sandbox" else "vsd_live_"
        return prefix + _urlsafe(raw)

    def _delivery_digest(self, token: str) -> bytes:
        return _token_bytes(self._auth_pepper, b"delivery-digest", token)

    def provision_tenant(self, *, tenant_id: str | None = None, created_at: str | None = None) -> dict[str, str]:
        identifier = tenant_id or "ten_" + secrets.token_hex(12)
        if not _TENANT_ID.fullmatch(identifier):
            raise InputRejected("tenant identifier is invalid", code="invalid_tenant")
        prefix = "vsk_test_" if self.environment == "sandbox" else "vsk_live_"
        api_key = prefix + _urlsafe(secrets.token_bytes(32))
        timestamp = created_at or _utc_now()
        _parse_timestamp(timestamp)
        digest = self._api_digest(api_key)
        with self._connection(write=True) as connection:
            try:
                connection.execute(
                    """INSERT INTO access_tenants(
                        tenant_id, api_key_digest, state, created_at, updated_at
                    ) VALUES (?, ?, 'active', ?, ?)""",
                    (identifier, digest, timestamp, timestamp),
                )
                self._audit(connection, "tenant.provisioned", timestamp, tenant_id=identifier)
            except sqlite3.IntegrityError as exc:
                raise InputRejected("tenant already exists", code="tenant_conflict") from exc
        return {"tenant_id": identifier, "api_key": api_key}

    def authenticate_api_key(self, api_key: str) -> str:
        valid_format = isinstance(api_key, str) and len(api_key) <= 96 and bool(_API_KEY.fullmatch(api_key))
        expected_prefix = "vsk_test_" if self.environment == "sandbox" else "vsk_live_"
        valid_format = valid_format and api_key.startswith(expected_prefix)
        candidate = self._api_digest(api_key if valid_format else "invalid")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT tenant_id, api_key_digest, state FROM access_tenants WHERE api_key_digest = ?",
                (candidate,),
            ).fetchone()
        dummy = _token_bytes(self._auth_pepper, b"api-key", "not-a-real-key")
        expected = bytes(row["api_key_digest"]) if row is not None else dummy
        verified = hmac.compare_digest(candidate, expected)
        if not valid_format or row is None or row["state"] != "active" or not verified:
            raise InputRejected("authentication failed", code="authentication_failed")
        return str(row["tenant_id"])

    def rotate_api_key(self, tenant_id: str, *, updated_at: str | None = None) -> str:
        if not _TENANT_ID.fullmatch(tenant_id):
            raise InputRejected("tenant identifier is invalid", code="invalid_tenant")
        prefix = "vsk_test_" if self.environment == "sandbox" else "vsk_live_"
        api_key = prefix + _urlsafe(secrets.token_bytes(32))
        timestamp = updated_at or _utc_now()
        _parse_timestamp(timestamp)
        with self._connection(write=True) as connection:
            changed = connection.execute(
                """UPDATE access_tenants SET api_key_digest = ?, updated_at = ?
                WHERE tenant_id = ? AND state = 'active'""",
                (self._api_digest(api_key), timestamp, tenant_id),
            ).rowcount
            if changed != 1:
                raise InputRejected("tenant is not active", code="authentication_failed")
            self._audit(connection, "tenant.api_key_rotated", timestamp, tenant_id=tenant_id)
        return api_key

    def revoke_tenant(self, tenant_id: str, *, updated_at: str | None = None) -> None:
        timestamp = updated_at or _utc_now()
        _parse_timestamp(timestamp)
        with self._connection(write=True) as connection:
            changed = connection.execute(
                """UPDATE access_tenants SET state = 'revoked', updated_at = ?
                WHERE tenant_id = ? AND state = 'active'""",
                (timestamp, tenant_id),
            ).rowcount
            if changed != 1:
                raise InputRejected("tenant is not active", code="authentication_failed")
            self._audit(connection, "tenant.revoked", timestamp, tenant_id=tenant_id)

    def derive_quote_id(self, tenant_id: str, idempotency_key: str) -> str:
        if not _TENANT_ID.fullmatch(tenant_id) or not _IDEMPOTENCY.fullmatch(idempotency_key):
            raise InputRejected("idempotency key is invalid", code="invalid_commerce_request")
        digest = _token_bytes(self._auth_pepper, b"quote-id", tenant_id, idempotency_key)
        return "q_" + digest.hex()[:24]

    def derive_order_idempotency_key(self, tenant_id: str, idempotency_key: str) -> str:
        if not _TENANT_ID.fullmatch(tenant_id) or not _IDEMPOTENCY.fullmatch(idempotency_key):
            raise InputRejected("idempotency key is invalid", code="invalid_commerce_request")
        digest = _token_bytes(
            self._auth_pepper, b"order-idempotency", tenant_id, idempotency_key
        )
        return "oid_" + digest.hex()[:32]

    def bind_quote(
        self,
        tenant_id: str,
        quote_id: str,
        *,
        idempotency_key: str,
        created_at: str | None = None,
    ) -> None:
        if not _QUOTE_ID.fullmatch(quote_id) or not _IDEMPOTENCY.fullmatch(idempotency_key):
            raise InputRejected("quote binding is invalid", code="invalid_commerce_request")
        digest = self._idempotency_digest(tenant_id, idempotency_key)
        timestamp = created_at or _utc_now()
        _parse_timestamp(timestamp)
        with self._connection(write=True) as connection:
            self._require_active_tenant(connection, tenant_id)
            if connection.execute("SELECT 1 FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone() is None:
                raise InputRejected("quote does not exist", code="object_not_found")
            existing = connection.execute(
                "SELECT tenant_id, idempotency_digest FROM access_quote_bindings WHERE quote_id = ?",
                (quote_id,),
            ).fetchone()
            if existing is not None:
                if existing["tenant_id"] != tenant_id or not hmac.compare_digest(
                    bytes(existing["idempotency_digest"]), digest
                ):
                    raise InputRejected("quote binding conflict", code="authorization_failed")
                return
            try:
                connection.execute(
                    """INSERT INTO access_quote_bindings(
                        quote_id, tenant_id, idempotency_digest, created_at
                    ) VALUES (?, ?, ?, ?)""",
                    (quote_id, tenant_id, digest, timestamp),
                )
                self._audit(
                    connection,
                    "quote.bound",
                    timestamp,
                    tenant_id=tenant_id,
                    quote_id=quote_id,
                )
            except sqlite3.IntegrityError as exc:
                raise InputRejected("quote binding conflict", code="authorization_failed") from exc

    def authorize_quote(self, tenant_id: str, quote_id: str) -> None:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT 1 FROM access_quote_bindings AS binding
                JOIN access_tenants AS tenant ON tenant.tenant_id = binding.tenant_id
                WHERE binding.quote_id = ? AND binding.tenant_id = ? AND tenant.state = 'active'""",
                (quote_id, tenant_id),
            ).fetchone()
        if row is None:
            raise InputRejected("object was not found", code="authorization_failed")

    def tenant_resource_counts(self, tenant_id: str) -> dict[str, int]:
        with self._connection() as connection:
            self._require_active_tenant(connection, tenant_id)
            quotes = connection.execute(
                "SELECT COUNT(*) AS value FROM access_quote_bindings WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()["value"]
            orders = connection.execute(
                "SELECT COUNT(*) AS value FROM access_order_bindings WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()["value"]
        return {"quotes": int(quotes), "orders": int(orders)}

    def quote_owned(self, tenant_id: str, quote_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT 1 FROM access_quote_bindings AS binding
                JOIN access_tenants AS tenant ON tenant.tenant_id = binding.tenant_id
                WHERE binding.tenant_id = ? AND binding.quote_id = ? AND tenant.state = 'active'""",
                (tenant_id, quote_id),
            ).fetchone()
        return row is not None

    def order_for_quote(self, tenant_id: str, quote_id: str) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT binding.order_id FROM access_order_bindings AS binding
                JOIN access_tenants AS tenant ON tenant.tenant_id = binding.tenant_id
                WHERE binding.tenant_id = ? AND binding.quote_id = ? AND tenant.state = 'active'""",
                (tenant_id, quote_id),
            ).fetchone()
        return None if row is None else str(row["order_id"])

    def bind_order(
        self,
        tenant_id: str,
        order_id: str,
        quote_id: str,
        *,
        created_at: str | None = None,
    ) -> str:
        if not _ORDER_ID.fullmatch(order_id) or not _QUOTE_ID.fullmatch(quote_id):
            raise InputRejected("order binding is invalid", code="invalid_commerce_request")
        timestamp = created_at or _utc_now()
        created = _parse_timestamp(timestamp)
        expires_at = _format_timestamp(created + DELIVERY_TOKEN_TTL)
        with self._connection(write=True) as connection:
            self._require_active_tenant(connection, tenant_id)
            quote = connection.execute(
                "SELECT tenant_id FROM access_quote_bindings WHERE quote_id = ?", (quote_id,)
            ).fetchone()
            order = connection.execute(
                "SELECT quote_id FROM orders WHERE order_id = ?", (order_id,)
            ).fetchone()
            if quote is None or quote["tenant_id"] != tenant_id or order is None or order["quote_id"] != quote_id:
                raise InputRejected("object was not found", code="authorization_failed")
            existing = connection.execute(
                "SELECT * FROM access_order_bindings WHERE order_id = ?", (order_id,)
            ).fetchone()
            if existing is not None:
                if existing["tenant_id"] != tenant_id or existing["quote_id"] != quote_id:
                    raise InputRejected("object was not found", code="authorization_failed")
                if existing["token_state"] != "active":
                    raise InputRejected("delivery capability is revoked", code="authorization_failed")
                token = self._delivery_token(tenant_id, order_id, existing["token_version"])
                if not hmac.compare_digest(self._delivery_digest(token), bytes(existing["token_digest"])):
                    raise InputRejected("delivery capability state is invalid", code="authorization_failed")
                return token
            token = self._delivery_token(tenant_id, order_id, 1)
            connection.execute(
                """INSERT INTO access_order_bindings(
                    order_id, quote_id, tenant_id, token_version, token_digest, token_state,
                    token_expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, 1, ?, 'active', ?, ?, ?)""",
                (
                    order_id,
                    quote_id,
                    tenant_id,
                    self._delivery_digest(token),
                    expires_at,
                    timestamp,
                    timestamp,
                ),
            )
            self._audit(
                connection,
                "order.bound",
                timestamp,
                tenant_id=tenant_id,
                quote_id=quote_id,
                order_id=order_id,
            )
            return token

    def authorize_order(
        self,
        tenant_id: str,
        order_id: str,
        delivery_token: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        valid_format = (
            isinstance(delivery_token, str)
            and len(delivery_token) <= 64
            and bool(_DELIVERY_TOKEN.fullmatch(delivery_token))
        )
        candidate = self._delivery_digest(delivery_token if valid_format else "invalid")
        with self._connection() as connection:
            row = connection.execute(
                """SELECT binding.* FROM access_order_bindings AS binding
                JOIN access_tenants AS tenant ON tenant.tenant_id = binding.tenant_id
                WHERE binding.order_id = ? AND binding.tenant_id = ? AND tenant.state = 'active'""",
                (order_id, tenant_id),
            ).fetchone()
        dummy = _token_bytes(self._auth_pepper, b"delivery-digest", "not-a-real-token")
        expected = bytes(row["token_digest"]) if row is not None else dummy
        verified = hmac.compare_digest(candidate, expected)
        moment = now or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            raise ValueError("authorization clock must be timezone-aware")
        moment = moment.astimezone(timezone.utc)
        expired = row is None or moment >= _parse_timestamp(row["token_expires_at"])
        if (
            not valid_format
            or row is None
            or row["token_state"] != "active"
            or not verified
            or expired
        ):
            raise InputRejected("object was not found", code="authorization_failed")
        return {
            "tenant_id": str(row["tenant_id"]),
            "order_id": str(row["order_id"]),
            "quote_id": str(row["quote_id"]),
            "token_version": int(row["token_version"]),
            "token_expires_at": str(row["token_expires_at"]),
            "result_sha256": row["result_sha256"],
        }

    def rotate_delivery_token(
        self,
        tenant_id: str,
        order_id: str,
        current_token: str,
        *,
        updated_at: str | None = None,
    ) -> str:
        timestamp = updated_at or _utc_now()
        updated = _parse_timestamp(timestamp)
        self.authorize_order(tenant_id, order_id, current_token, now=updated)
        expires_at = _format_timestamp(updated + DELIVERY_TOKEN_TTL)
        with self._connection(write=True) as connection:
            row = connection.execute(
                """SELECT * FROM access_order_bindings
                WHERE order_id = ? AND tenant_id = ?""",
                (order_id, tenant_id),
            ).fetchone()
            assert row is not None
            if row["token_state"] != "active" or not hmac.compare_digest(
                self._delivery_digest(current_token), bytes(row["token_digest"])
            ):
                raise InputRejected("object was not found", code="authorization_failed")
            version = int(row["token_version"]) + 1
            token = self._delivery_token(tenant_id, order_id, version)
            connection.execute(
                """UPDATE access_order_bindings
                SET token_version = ?, token_digest = ?, token_expires_at = ?, updated_at = ?
                WHERE order_id = ?""",
                (version, self._delivery_digest(token), expires_at, timestamp, order_id),
            )
            self._audit(
                connection,
                "delivery_token.rotated",
                timestamp,
                tenant_id=tenant_id,
                quote_id=str(row["quote_id"]),
                order_id=order_id,
            )
        return token

    def revoke_delivery_token(
        self,
        tenant_id: str,
        order_id: str,
        current_token: str,
        *,
        updated_at: str | None = None,
    ) -> None:
        timestamp = updated_at or _utc_now()
        updated = _parse_timestamp(timestamp)
        self.authorize_order(tenant_id, order_id, current_token, now=updated)
        with self._connection(write=True) as connection:
            changed = connection.execute(
                """UPDATE access_order_bindings SET token_state = 'revoked', updated_at = ?
                WHERE order_id = ? AND tenant_id = ? AND token_state = 'active'
                    AND token_digest = ?""",
                (timestamp, order_id, tenant_id, self._delivery_digest(current_token)),
            ).rowcount
            if changed != 1:
                raise InputRejected("object was not found", code="authorization_failed")
            row = connection.execute(
                "SELECT quote_id FROM access_order_bindings WHERE order_id = ?", (order_id,)
            ).fetchone()
            self._audit(
                connection,
                "delivery_token.revoked",
                timestamp,
                tenant_id=tenant_id,
                quote_id=str(row["quote_id"]),
                order_id=order_id,
            )

    def publish_result(self, order_id: str, envelope_bytes: bytes, *, updated_at: str | None = None) -> str:
        if not _ORDER_ID.fullmatch(order_id):
            raise InputRejected("order identifier is invalid", code="invalid_delivery")
        if not isinstance(envelope_bytes, bytes) or not 1 <= len(envelope_bytes) <= MAX_RESULT_BYTES:
            raise InputRejected("delivery result size is invalid", code="invalid_delivery")
        digest = hashlib.sha256(envelope_bytes).hexdigest()
        timestamp = updated_at or _utc_now()
        _parse_timestamp(timestamp)
        with self._connection(write=True) as connection:
            row = connection.execute(
                """SELECT orders.order_status, orders.envelope_sha256,
                    binding.result_sha256, binding.result_body
                FROM orders JOIN access_order_bindings AS binding
                    ON binding.order_id = orders.order_id
                WHERE orders.order_id = ?""",
                (order_id,),
            ).fetchone()
            if row is None or row["order_status"] != "delivered":
                raise InputRejected("order is not delivered", code="result_not_ready")
            if row["envelope_sha256"] != digest:
                raise InputRejected("delivery bytes do not match the signed envelope", code="invalid_delivery")
            if row["result_body"] is not None:
                if row["result_sha256"] != digest or bytes(row["result_body"]) != envelope_bytes:
                    raise InputRejected("delivery result cannot be rebound", code="idempotency_conflict")
                return digest
            connection.execute(
                """UPDATE access_order_bindings SET result_sha256 = ?, result_body = ?, updated_at = ?
                WHERE order_id = ?""",
                (digest, envelope_bytes, timestamp, order_id),
            )
            binding = connection.execute(
                "SELECT tenant_id, quote_id FROM access_order_bindings WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            self._audit(
                connection,
                "result.published",
                timestamp,
                tenant_id=str(binding["tenant_id"]),
                quote_id=str(binding["quote_id"]),
                order_id=order_id,
            )
        return digest

    def get_result(
        self,
        tenant_id: str,
        order_id: str,
        delivery_token: str,
        *,
        now: datetime | None = None,
    ) -> bytes:
        self.authorize_order(tenant_id, order_id, delivery_token, now=now)
        with self._connection() as connection:
            row = connection.execute(
                """SELECT result_body FROM access_order_bindings
                WHERE order_id = ? AND tenant_id = ?""",
                (order_id, tenant_id),
            ).fetchone()
        if row is None or row["result_body"] is None:
            raise InputRejected("delivery result is not ready", code="result_not_ready")
        return bytes(row["result_body"])

    def audit_events(self, *, order_id: str | None = None) -> list[dict[str, Any]]:
        with self._connection() as connection:
            if order_id is None:
                rows = connection.execute(
                    "SELECT * FROM access_audit_events ORDER BY sequence"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM access_audit_events WHERE order_id = ? ORDER BY sequence",
                    (order_id,),
                ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        event_type: str,
        observed_at: str,
        *,
        tenant_id: str | None = None,
        quote_id: str | None = None,
        order_id: str | None = None,
        outcome: str = "success",
    ) -> None:
        connection.execute(
            """INSERT INTO access_audit_events(
                event_type, tenant_id, quote_id, order_id, outcome, observed_at
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (event_type, tenant_id, quote_id, order_id, outcome, observed_at),
        )

    @staticmethod
    def _require_active_tenant(connection: sqlite3.Connection, tenant_id: str) -> None:
        if not _TENANT_ID.fullmatch(tenant_id):
            raise InputRejected("tenant is not active", code="authentication_failed")
        row = connection.execute(
            "SELECT state FROM access_tenants WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        if row is None or row["state"] != "active":
            raise InputRejected("tenant is not active", code="authentication_failed")
