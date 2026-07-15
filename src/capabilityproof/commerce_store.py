"""Durable, environment-bound commerce state for constrained Stage B orders.

Fake-provider and Stripe test-mode activity are persistently marked as
non-commercial evidence and can never count toward revenue. Live Stripe quotes require
an explicit activation acknowledgement outside the public API boundary.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator

from .commerce import (
    FRESH_VALIDATION_CURRENCY,
    OrderStatus,
    PaymentStatus,
    build_fresh_validation_quote,
    parse_fresh_validation_request,
    require_transition,
)
from .errors import InputRejected


STORE_SCHEMA_VERSION = "3"
DIRECT_COST_CATEGORIES = (
    "compute",
    "third_party",
    "hosting",
    "storage",
    "model",
    "network",
    "signing",
    "monitoring",
    "direct_support",
    "other_variable",
)
_ENVIRONMENTS = {"sandbox", "live"}
_IDEMPOTENCY = re.compile(r"[A-Za-z0-9_-]{8,96}")
_BUYER = re.compile(r"[A-Za-z0-9_.:@+-]{8,128}")
_EVENT_ID = re.compile(r"evt_(?:test_)?[0-9a-f]{24}")
_FAKE_PAYMENT_ID = re.compile(r"pay_test_[0-9a-f]{24}")
_STRIPE_PAYMENT_ID = re.compile(r"pi_[A-Za-z0-9]{8,64}")
_STRIPE_CHECKOUT_ID = re.compile(r"cs_(?:test|live)_[A-Za-z0-9]{8,128}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_KEY_ID = re.compile(r"[A-Za-z0-9_-]{43}")
_EVENT_TYPES = {
    "payment.captured",
    "payment.available",
    "payment.failed",
    "payment.refund_pending",
    "payment.refunded",
    "payment.disputed",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise InputRejected("commerce timestamp must be a string", code="invalid_commerce_event")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InputRejected("commerce timestamp is invalid", code="invalid_commerce_event") from exc
    if parsed.tzinfo is None:
        raise InputRejected("commerce timestamp requires a timezone", code="invalid_commerce_event")
    return parsed.astimezone(timezone.utc)


class CommerceStore:
    """SQLite order/event ledger that refuses cross-environment reuse."""

    def __init__(self, path: Path, *, environment: str) -> None:
        if environment not in _ENVIRONMENTS:
            raise ValueError("environment must be sandbox or live")
        self.path = path.expanduser().resolve(strict=False)
        self.environment = environment
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
        with self._connection(write=True) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quotes (
                    quote_id TEXT PRIMARY KEY,
                    environment TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    quote_json TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL CHECK(amount_minor >= 0),
                    currency TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    orderable INTEGER NOT NULL CHECK(orderable IN (0, 1)),
                    counts_for_goal INTEGER NOT NULL CHECK(counts_for_goal IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    environment TEXT NOT NULL,
                    quote_id TEXT NOT NULL UNIQUE REFERENCES quotes(quote_id),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    buyer_reference TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_checkout_id TEXT,
                    provider_payment_id TEXT UNIQUE,
                    order_status TEXT NOT NULL,
                    payment_status TEXT NOT NULL,
                    quoted_amount_minor INTEGER NOT NULL,
                    collected_amount_minor INTEGER NOT NULL DEFAULT 0,
                    refunded_amount_minor INTEGER NOT NULL DEFAULT 0,
                    processing_fee_minor INTEGER NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL,
                    direct_costs_recorded INTEGER NOT NULL DEFAULT 0 CHECK(direct_costs_recorded IN (0, 1)),
                    receipt_id TEXT,
                    receipt_sha256 TEXT,
                    envelope_sha256 TEXT,
                    signing_keyid TEXT,
                    delivery_status TEXT NOT NULL,
                    counts_for_goal INTEGER NOT NULL CHECK(counts_for_goal IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS provider_events (
                    event_id TEXT PRIMARY KEY,
                    environment TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_payment_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    applied_at TEXT,
                    FOREIGN KEY(provider_payment_id) REFERENCES orders(provider_payment_id)
                );
                CREATE INDEX IF NOT EXISTS provider_events_payment_status
                    ON provider_events(provider_payment_id, status, received_at);
                CREATE TABLE IF NOT EXISTS financial_entries (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL REFERENCES orders(order_id),
                    category TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL CHECK(amount_minor >= 0),
                    contribution_impact_minor INTEGER NOT NULL,
                    source_reference TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(order_id, category, source_reference)
                );
                CREATE TABLE IF NOT EXISTS cost_records (
                    order_id TEXT NOT NULL REFERENCES orders(order_id),
                    idempotency_key TEXT NOT NULL,
                    costs_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    PRIMARY KEY(order_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS order_history (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL REFERENCES orders(order_id),
                    dimension TEXT NOT NULL,
                    prior_status TEXT,
                    new_status TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                """
            )
            order_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(orders)").fetchall()
            }
            if "provider_checkout_id" not in order_columns:
                connection.execute("ALTER TABLE orders ADD COLUMN provider_checkout_id TEXT")
            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS orders_provider_checkout_id
                ON orders(provider_checkout_id) WHERE provider_checkout_id IS NOT NULL"""
            )
            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS orders_receipt_id
                ON orders(receipt_id) WHERE receipt_id IS NOT NULL"""
            )
            metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
            if not metadata:
                connection.executemany(
                    "INSERT INTO metadata(key, value) VALUES (?, ?)",
                    (("schema_version", STORE_SCHEMA_VERSION), ("environment", self.environment)),
                )
            elif metadata.get("environment") != self.environment:
                raise InputRejected(
                    "commerce store schema or environment does not match",
                    code="commerce_environment_mismatch",
                )
            elif metadata.get("schema_version") == "2":
                connection.execute(
                    "UPDATE metadata SET value = ? WHERE key = 'schema_version'",
                    (STORE_SCHEMA_VERSION,),
                )
            elif metadata != {"schema_version": STORE_SCHEMA_VERSION, "environment": self.environment}:
                raise InputRejected(
                    "commerce store schema or environment does not match",
                    code="commerce_environment_mismatch",
                )

    def create_quote(
        self,
        request_value: Any,
        *,
        quote_id: str,
        generated_at: datetime,
        payment_provider: str = "fake",
        live_checkout_enabled: bool = False,
    ) -> dict[str, Any]:
        """Create an immutable provider quote behind an explicit live activation gate."""

        if payment_provider not in {"fake", "stripe"}:
            raise InputRejected("unsupported payment provider", code="invalid_commerce_request")
        if payment_provider == "fake" and self.environment != "sandbox":
            raise InputRejected("live orderable quotes are not activated", code="commerce_live_not_enabled")
        if self.environment == "live" and not (
            payment_provider == "stripe" and live_checkout_enabled
        ):
            raise InputRejected("live orderable quotes are not activated", code="commerce_live_not_enabled")
        request = parse_fresh_validation_request(request_value)
        # This SQLite adapter is retained only as historical Stripe/test evidence.
        # The active agent-only x402 launch surface uses the 0.25-USDC public quote.
        quote = build_fresh_validation_quote(
            request,
            generated_at=generated_at,
            quote_id=quote_id,
            legacy_stripe_adapter=True,
        )
        if quote["quote_status"] == "declined_max_price":
            return quote
        quote = dict(quote)
        if payment_provider == "fake":
            provider_fields = {
                "quote_status": "sandbox_orderable_nonsettling",
                "availability": "sandbox_fake_provider_only",
                "settlement_available": False,
                "payment_options": [{"provider": "fake", "status": "sandbox_only"}],
            }
        elif self.environment == "sandbox":
            quote["expires_at"] = (
                generated_at.astimezone(timezone.utc) + timedelta(minutes=30)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            provider_fields = {
                "quote_status": "stripe_test_orderable_nonsettling",
                "availability": "stripe_test_mode_only",
                "settlement_available": False,
                "payment_options": [{"provider": "stripe_checkout", "status": "test_mode"}],
            }
        else:
            quote["expires_at"] = (
                generated_at.astimezone(timezone.utc) + timedelta(minutes=30)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            provider_fields = {
                "quote_status": "stripe_live_orderable_activation_acknowledged",
                "availability": "stripe_live_account_configured",
                "settlement_available": True,
                "payment_options": [{"provider": "stripe_checkout", "status": "live"}],
            }
        quote.update(provider_fields | {"orderable": True, "counts_for_goal": False})
        quote["quote_digest"] = f"sha256:{_digest({key: value for key, value in quote.items() if key != 'quote_digest'})}"
        serialized_request = _canonical(request)
        serialized_quote = _canonical(quote)
        with self._connection(write=True) as connection:
            existing = connection.execute(
                "SELECT request_json, quote_json FROM quotes WHERE quote_id = ?", (quote_id,)
            ).fetchone()
            if existing is not None:
                if existing["request_json"] != serialized_request or existing["quote_json"] != serialized_quote:
                    raise InputRejected("quote identifier was reused with different content", code="idempotency_conflict")
                return json.loads(existing["quote_json"])
            connection.execute(
                """INSERT INTO quotes(
                    quote_id, environment, request_digest, request_json, quote_json,
                    amount_minor, currency, generated_at, expires_at, orderable, counts_for_goal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)""",
                (
                    quote_id,
                    self.environment,
                    quote["request_digest"],
                    serialized_request,
                    serialized_quote,
                    quote["amount_minor"],
                    quote["currency"],
                    quote["generated_at"],
                    quote["expires_at"],
                ),
            )
        return quote

    def create_order(
        self,
        quote_id: str,
        *,
        idempotency_key: str,
        buyer_reference: str,
        now: datetime,
    ) -> dict[str, Any]:
        if not _IDEMPOTENCY.fullmatch(idempotency_key):
            raise InputRejected("invalid order idempotency key", code="invalid_commerce_request")
        if not _BUYER.fullmatch(buyer_reference):
            raise InputRejected("buyer_reference must be an opaque identifier", code="invalid_commerce_request")
        if now.tzinfo is None:
            raise InputRejected("order timestamp requires a timezone", code="invalid_commerce_request")
        now_utc = now.astimezone(timezone.utc)
        timestamp = now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with self._connection(write=True) as connection:
            existing = connection.execute(
                "SELECT * FROM orders WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if existing is not None:
                if existing["quote_id"] != quote_id or existing["buyer_reference"] != buyer_reference:
                    raise InputRejected("order idempotency key was reused", code="idempotency_conflict")
                return self._order_view(connection, existing["order_id"])
            quote = connection.execute("SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone()
            if quote is None or quote["environment"] != self.environment or not quote["orderable"]:
                raise InputRejected("quote is missing or not orderable", code="quote_not_orderable")
            if now_utc >= _parse_timestamp(quote["expires_at"]):
                raise InputRejected("quote has expired", code="quote_expired")
            quote_document = json.loads(quote["quote_json"])
            payment_options = quote_document.get("payment_options")
            provider = (
                "fake"
                if payment_options == [{"provider": "fake", "status": "sandbox_only"}]
                else "stripe"
                if isinstance(payment_options, list)
                and len(payment_options) == 1
                and payment_options[0].get("provider") == "stripe_checkout"
                else None
            )
            if provider is None or (self.environment == "live" and provider != "stripe"):
                raise InputRejected("quote payment provider is invalid", code="quote_not_orderable")
            order_prefix = "ord_test_" if self.environment == "sandbox" else "ord_"
            order_id = order_prefix + hashlib.sha256(
                f"{quote_id}\0{idempotency_key}\0{buyer_reference}".encode("utf-8")
            ).hexdigest()[:24]
            try:
                connection.execute(
                    """INSERT INTO orders(
                        order_id, environment, quote_id, idempotency_key, buyer_reference, provider,
                        order_status, payment_status, quoted_amount_minor, currency, delivery_status,
                        counts_for_goal, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'not_started', 0, ?, ?)""",
                    (
                        order_id,
                        self.environment,
                        quote_id,
                        idempotency_key,
                        buyer_reference,
                        provider,
                        OrderStatus.CHECKOUT_PENDING.value,
                        PaymentStatus.PENDING.value,
                        quote["amount_minor"],
                        quote["currency"],
                        timestamp,
                        timestamp,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise InputRejected("quote already has an order", code="quote_already_used") from exc
            self._history(
                connection, order_id, "order", None, OrderStatus.CHECKOUT_PENDING.value,
                idempotency_key, timestamp,
            )
            return self._order_view(connection, order_id)

    def attach_checkout(
        self,
        order_id: str,
        checkout_id: str,
        *,
        occurred_at: str,
        payment_id: str | None = None,
    ) -> dict[str, Any]:
        _parse_timestamp(occurred_at)
        with self._connection(write=True) as connection:
            order = self._require_order(connection, order_id)
            provider = order["provider"]
            if provider == "fake":
                if (
                    self.environment != "sandbox"
                    or not _FAKE_PAYMENT_ID.fullmatch(checkout_id)
                    or payment_id not in {None, checkout_id}
                ):
                    raise InputRejected("fake checkout identity is invalid", code="invalid_commerce_request")
                payment_id = checkout_id
            elif provider == "stripe":
                expected_prefix = "cs_test_" if self.environment == "sandbox" else "cs_live_"
                if not _STRIPE_CHECKOUT_ID.fullmatch(checkout_id) or not checkout_id.startswith(expected_prefix):
                    raise InputRejected("Stripe checkout identity is invalid", code="invalid_commerce_request")
                if payment_id is not None and not _STRIPE_PAYMENT_ID.fullmatch(payment_id):
                    raise InputRejected("Stripe payment identity is invalid", code="invalid_commerce_request")
            else:
                raise InputRejected("order payment provider is invalid", code="invalid_commerce_request")
            if order["provider_checkout_id"] is not None:
                if (
                    order["provider_checkout_id"] != checkout_id
                    or (payment_id is not None and order["provider_payment_id"] != payment_id)
                ):
                    raise InputRejected("order already has a different payment", code="idempotency_conflict")
                return self._order_view(connection, order_id)
            current = OrderStatus(order["order_status"])
            require_transition(current, OrderStatus.PAYMENT_PENDING)
            try:
                connection.execute(
                    """UPDATE orders SET provider_checkout_id = ?, provider_payment_id = ?,
                    order_status = ?, updated_at = ?
                    WHERE order_id = ?""",
                    (
                        checkout_id,
                        payment_id,
                        OrderStatus.PAYMENT_PENDING.value,
                        occurred_at,
                        order_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise InputRejected("payment identifier is already bound", code="idempotency_conflict") from exc
            self._history(
                connection, order_id, "order", current.value, OrderStatus.PAYMENT_PENDING.value,
                checkout_id, occurred_at,
            )
            return self._order_view(connection, order_id)

    def bind_provider_payment(
        self,
        order_id: str,
        payment_id: str,
        *,
        checkout_id: str,
        occurred_at: str,
    ) -> dict[str, Any]:
        """Bind a retrieved Stripe PaymentIntent to its already-attached Checkout Session."""

        if not _STRIPE_PAYMENT_ID.fullmatch(payment_id):
            raise InputRejected("Stripe payment identity is invalid", code="invalid_commerce_request")
        _parse_timestamp(occurred_at)
        with self._connection(write=True) as connection:
            order = self._require_order(connection, order_id)
            if order["provider"] != "stripe" or order["provider_checkout_id"] != checkout_id:
                raise InputRejected("Stripe checkout binding is invalid", code="idempotency_conflict")
            if order["provider_payment_id"] is not None:
                if order["provider_payment_id"] != payment_id:
                    raise InputRejected("order already has a different payment", code="idempotency_conflict")
                return self._order_view(connection, order_id)
            try:
                connection.execute(
                    "UPDATE orders SET provider_payment_id = ?, updated_at = ? WHERE order_id = ?",
                    (payment_id, occurred_at, order_id),
                )
            except sqlite3.IntegrityError as exc:
                raise InputRejected("payment identifier is already bound", code="idempotency_conflict") from exc
            return self._order_view(connection, order_id)

    def ingest_provider_event(self, event_value: Any, *, received_at: str | None = None) -> dict[str, Any]:
        event = self._validate_event(event_value)
        payload = _canonical(event)
        payload_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        received = received_at or _utc_now()
        _parse_timestamp(received)
        with self._connection(write=True) as connection:
            existing = connection.execute(
                "SELECT payload_digest, status FROM provider_events WHERE event_id = ?", (event["event_id"],)
            ).fetchone()
            if existing is not None:
                if existing["payload_digest"] != payload_digest:
                    raise InputRejected("provider event identifier was reused", code="provider_event_conflict")
                order = connection.execute(
                    "SELECT order_id FROM orders WHERE provider_payment_id = ?", (event["payment_id"],)
                ).fetchone()
                return {
                    "duplicate": True,
                    "event_id": event["event_id"],
                    "event_status": existing["status"],
                    "order": self._order_view(connection, order["order_id"]),
                }
            order = connection.execute(
                "SELECT order_id, provider FROM orders WHERE provider_payment_id = ?", (event["payment_id"],)
            ).fetchone()
            if order is None:
                raise InputRejected("provider event payment is unknown", code="unknown_provider_payment")
            if order["provider"] != event["provider"]:
                raise InputRejected("provider event does not match the order", code="invalid_commerce_event")
            connection.execute(
                """INSERT INTO provider_events(
                    event_id, environment, provider, provider_payment_id, event_type,
                    payload_digest, payload_json, status, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (
                    event["event_id"], self.environment, event["provider"], event["payment_id"],
                    event["type"], payload_digest, payload, received,
                ),
            )
            self._reconcile_payment(connection, event["payment_id"])
            status = connection.execute(
                "SELECT status FROM provider_events WHERE event_id = ?", (event["event_id"],)
            ).fetchone()["status"]
            return {
                "duplicate": False,
                "event_id": event["event_id"],
                "event_status": status,
                "order": self._order_view(connection, order["order_id"]),
            }

    def record_direct_costs(
        self,
        order_id: str,
        costs: dict[str, int],
        *,
        idempotency_key: str,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        if set(costs) != set(DIRECT_COST_CATEGORIES) or any(
            isinstance(amount, bool) or not isinstance(amount, int) or not 0 <= amount <= 10_000_000
            for amount in costs.values()
        ):
            raise InputRejected("direct costs must explicitly contain all bounded categories", code="invalid_cost_record")
        if not _IDEMPOTENCY.fullmatch(idempotency_key):
            raise InputRejected("invalid cost idempotency key", code="invalid_cost_record")
        serialized = _canonical(costs)
        timestamp = recorded_at or _utc_now()
        _parse_timestamp(timestamp)
        with self._connection(write=True) as connection:
            order = self._require_order(connection, order_id)
            existing = connection.execute(
                "SELECT costs_json FROM cost_records WHERE order_id = ? AND idempotency_key = ?",
                (order_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["costs_json"] != serialized:
                    raise InputRejected("cost idempotency key was reused", code="idempotency_conflict")
                return self._order_view(connection, order_id)
            if order["direct_costs_recorded"]:
                raise InputRejected("direct costs are already finalized", code="costs_already_recorded")
            connection.execute(
                "INSERT INTO cost_records(order_id, idempotency_key, costs_json, recorded_at) VALUES (?, ?, ?, ?)",
                (order_id, idempotency_key, serialized, timestamp),
            )
            for category in DIRECT_COST_CATEGORIES:
                amount = costs[category]
                connection.execute(
                    """INSERT INTO financial_entries(
                        order_id, category, amount_minor, contribution_impact_minor, source_reference, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (order_id, category, amount, -amount, idempotency_key, timestamp),
                )
            connection.execute(
                "UPDATE orders SET direct_costs_recorded = 1, updated_at = ? WHERE order_id = ?",
                (timestamp, order_id),
            )
            return self._order_view(connection, order_id)

    def begin_fulfillment(self, order_id: str, *, source_reference: str, occurred_at: str) -> dict[str, Any]:
        return self._transition_order(
            order_id, OrderStatus.RUNNING, source_reference=source_reference,
            occurred_at=occurred_at, delivery_status="running",
        )

    def deliver(
        self,
        order_id: str,
        *,
        receipt_id: str,
        receipt_sha256: str,
        envelope_sha256: str,
        signing_keyid: str,
        source_reference: str,
        occurred_at: str,
    ) -> dict[str, Any]:
        if not isinstance(receipt_id, str) or not re.fullmatch(r"cpr_[0-9a-f]{24}", receipt_id):
            raise InputRejected("receipt identifier is invalid", code="invalid_delivery")
        if not isinstance(receipt_sha256, str) or not _SHA256.fullmatch(receipt_sha256):
            raise InputRejected("receipt digest is invalid", code="invalid_delivery")
        if not isinstance(envelope_sha256, str) or not _SHA256.fullmatch(envelope_sha256):
            raise InputRejected("signed envelope digest is invalid", code="invalid_delivery")
        if not isinstance(signing_keyid, str) or not _KEY_ID.fullmatch(signing_keyid):
            raise InputRejected("signing key identifier is invalid", code="invalid_delivery")
        _parse_timestamp(occurred_at)
        with self._connection(write=True) as connection:
            order = self._require_order(connection, order_id)
            if not order["direct_costs_recorded"]:
                raise InputRejected("all direct costs must be recorded before delivery", code="cost_record_required")
            current = OrderStatus(order["order_status"])
            if current is OrderStatus.DELIVERED:
                if (
                    order["receipt_id"] != receipt_id
                    or order["receipt_sha256"] != receipt_sha256
                    or order["envelope_sha256"] != envelope_sha256
                    or order["signing_keyid"] != signing_keyid
                ):
                    raise InputRejected("delivered order cannot be rebound", code="idempotency_conflict")
                return self._order_view(connection, order_id)
            require_transition(current, OrderStatus.DELIVERED)
            try:
                connection.execute(
                    """UPDATE orders SET order_status = ?, receipt_id = ?, receipt_sha256 = ?,
                        envelope_sha256 = ?, signing_keyid = ?,
                        delivery_status = 'delivered', updated_at = ? WHERE order_id = ?""",
                    (
                        OrderStatus.DELIVERED.value, receipt_id, receipt_sha256,
                        envelope_sha256, signing_keyid, occurred_at, order_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise InputRejected("receipt identifier is already bound", code="idempotency_conflict") from exc
            self._history(
                connection, order_id, "order", current.value, OrderStatus.DELIVERED.value,
                source_reference, occurred_at,
            )
            return self._order_view(connection, order_id)

    def get_order(self, order_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            self._require_order(connection, order_id)
            return self._order_view(connection, order_id)

    def get_quote(self, quote_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT quote_json FROM quotes WHERE quote_id = ? AND environment = ?",
                (quote_id, self.environment),
            ).fetchone()
            if row is None:
                raise InputRejected("quote does not exist", code="object_not_found")
            return json.loads(row["quote_json"])

    def get_order_request(self, order_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT quotes.request_json FROM orders
                JOIN quotes ON quotes.quote_id = orders.quote_id WHERE orders.order_id = ?""",
                (order_id,),
            ).fetchone()
            if row is None:
                raise InputRejected("order does not exist", code="unknown_order")
            return json.loads(row["request_json"])

    def list_delivered_orders(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT order_id FROM orders WHERE order_status = ? ORDER BY receipt_id, order_id",
                (OrderStatus.DELIVERED.value,),
            ).fetchall()
            return [self._order_view(connection, row["order_id"]) for row in rows]

    def fail_fulfillment(
        self,
        order_id: str,
        *,
        source_reference: str,
        occurred_at: str,
    ) -> dict[str, Any]:
        return self._transition_order(
            order_id,
            OrderStatus.FULFILLMENT_FAILED,
            source_reference=source_reference,
            occurred_at=occurred_at,
            delivery_status="failed",
        )

    def get_financial_summary(self) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT COUNT(*) AS orders,
                    COALESCE(SUM(collected_amount_minor), 0) AS collected,
                    COALESCE(SUM(refunded_amount_minor), 0) AS refunded,
                    COALESCE(SUM(processing_fee_minor), 0) AS fees,
                    COALESCE(SUM(CASE WHEN counts_for_goal = 1 THEN collected_amount_minor ELSE 0 END), 0)
                        AS goal_collected
                FROM orders"""
            ).fetchone()
            contribution = connection.execute(
                "SELECT COALESCE(SUM(contribution_impact_minor), 0) AS value FROM financial_entries"
            ).fetchone()["value"]
            goal_contribution = connection.execute(
                """SELECT COALESCE(SUM(financial_entries.contribution_impact_minor), 0) AS value
                FROM financial_entries JOIN orders ON orders.order_id = financial_entries.order_id
                WHERE orders.counts_for_goal = 1"""
            ).fetchone()["value"]
            pending = connection.execute(
                "SELECT COUNT(*) AS value FROM provider_events WHERE status = 'pending'"
            ).fetchone()["value"]
            return {
                "environment": self.environment,
                "orders": row["orders"],
                "collected_amount_minor": row["collected"],
                "refunded_amount_minor": row["refunded"],
                "processing_fee_minor": row["fees"],
                "ledger_contribution_minor": contribution,
                "counts_for_goal_contribution_minor": goal_contribution,
                "pending_provider_events": pending,
                "counts_for_goal_collected_minor": row["goal_collected"],
            }

    def _validate_event(self, value: Any) -> dict[str, Any]:
        keys = {
            "schema_version", "provider", "environment", "event_id", "type", "payment_id",
            "amount_minor", "fee_minor", "currency", "occurred_at",
        }
        if not isinstance(value, dict) or set(value) != keys:
            raise InputRejected("provider event fields are invalid", code="invalid_commerce_event")
        provider = value.get("provider")
        if (
            value["schema_version"] != "1.0.0"
            or provider not in {"fake", "stripe"}
            or value["environment"] != self.environment
            or not isinstance(value["event_id"], str)
            or not _EVENT_ID.fullmatch(value["event_id"])
            or value["type"] not in _EVENT_TYPES
            or not isinstance(value["payment_id"], str)
            or value["currency"] != FRESH_VALIDATION_CURRENCY
        ):
            raise InputRejected("provider event identity or environment is invalid", code="invalid_commerce_event")
        if provider == "fake" and (
            self.environment != "sandbox"
            or not value["event_id"].startswith("evt_test_")
            or not _FAKE_PAYMENT_ID.fullmatch(value["payment_id"])
        ):
            raise InputRejected("fake provider event identity is invalid", code="invalid_commerce_event")
        if provider == "stripe" and not _STRIPE_PAYMENT_ID.fullmatch(value["payment_id"]):
            raise InputRejected("Stripe provider event identity is invalid", code="invalid_commerce_event")
        for field in ("amount_minor", "fee_minor"):
            amount = value[field]
            if isinstance(amount, bool) or not isinstance(amount, int) or not 0 <= amount <= 10_000_000:
                raise InputRejected("provider event amount is invalid", code="invalid_commerce_event")
        if value["fee_minor"] > value["amount_minor"]:
            raise InputRejected("provider fee exceeds event amount", code="invalid_commerce_event")
        _parse_timestamp(value["occurred_at"])
        return dict(value)

    def _reconcile_payment(self, connection: sqlite3.Connection, payment_id: str) -> None:
        made_progress = True
        while made_progress:
            made_progress = False
            events = connection.execute(
                """SELECT * FROM provider_events
                WHERE provider_payment_id = ? AND status = 'pending'
                ORDER BY received_at, event_id""",
                (payment_id,),
            ).fetchall()
            for event_row in events:
                event = json.loads(event_row["payload_json"])
                order = connection.execute(
                    "SELECT * FROM orders WHERE provider_payment_id = ?", (payment_id,)
                ).fetchone()
                assert order is not None
                current_payment = PaymentStatus(order["payment_status"])
                event_type = event["type"]
                targets = {
                    "payment.captured": PaymentStatus.CAPTURED,
                    "payment.available": PaymentStatus.AVAILABLE,
                    "payment.failed": PaymentStatus.FAILED,
                    "payment.refund_pending": PaymentStatus.REFUND_PENDING,
                    "payment.refunded": PaymentStatus.REFUNDED,
                    "payment.disputed": PaymentStatus.DISPUTED,
                }
                target = targets[event_type]
                if event["amount_minor"] != order["quoted_amount_minor"] or event["currency"] != order["currency"]:
                    connection.execute(
                        "UPDATE provider_events SET status = 'rejected_amount_mismatch' WHERE event_id = ?",
                        (event["event_id"],),
                    )
                    made_progress = True
                    continue
                if current_payment is target:
                    effect_matches = (
                        target is not PaymentStatus.CAPTURED
                        or event["fee_minor"] == order["processing_fee_minor"]
                    ) and (
                        target is not PaymentStatus.REFUNDED
                        or event["amount_minor"] == order["refunded_amount_minor"]
                    )
                    self._mark_event(
                        connection,
                        event,
                        "applied_duplicate_effect" if effect_matches else "rejected_effect_conflict",
                    )
                    made_progress = True
                    continue
                try:
                    require_transition(current_payment, target)
                except InputRejected:
                    continue
                order_target: OrderStatus | None = None
                if target is PaymentStatus.CAPTURED:
                    if OrderStatus(order["order_status"]) is not OrderStatus.PAYMENT_PENDING:
                        continue
                    order_target = OrderStatus.QUEUED
                    connection.execute(
                        """UPDATE orders SET payment_status = ?, order_status = ?, collected_amount_minor = ?,
                            processing_fee_minor = ?, updated_at = ? WHERE order_id = ?""",
                        (
                            target.value, order_target.value, event["amount_minor"], event["fee_minor"],
                            event["occurred_at"], order["order_id"],
                        ),
                    )
                    self._financial_entry(
                        connection, order["order_id"], "gross_collected", event["amount_minor"],
                        event["amount_minor"], event["event_id"], event["occurred_at"],
                    )
                    self._financial_entry(
                        connection, order["order_id"], "processing_fee", event["fee_minor"],
                        -event["fee_minor"], event["event_id"], event["occurred_at"],
                    )
                elif target is PaymentStatus.FAILED:
                    order_target = OrderStatus.PAYMENT_FAILED
                    connection.execute(
                        "UPDATE orders SET payment_status = ?, order_status = ?, updated_at = ? WHERE order_id = ?",
                        (target.value, order_target.value, event["occurred_at"], order["order_id"]),
                    )
                elif target is PaymentStatus.REFUNDED:
                    connection.execute(
                        """UPDATE orders SET payment_status = ?, refunded_amount_minor = ?, updated_at = ?
                        WHERE order_id = ?""",
                        (target.value, event["amount_minor"], event["occurred_at"], order["order_id"]),
                    )
                    self._financial_entry(
                        connection, order["order_id"], "refund", event["amount_minor"],
                        -event["amount_minor"], event["event_id"], event["occurred_at"],
                    )
                else:
                    connection.execute(
                        "UPDATE orders SET payment_status = ?, updated_at = ? WHERE order_id = ?",
                        (target.value, event["occurred_at"], order["order_id"]),
                    )
                self._history(
                    connection, order["order_id"], "payment", current_payment.value, target.value,
                    event["event_id"], event["occurred_at"],
                )
                if order_target is not None:
                    self._history(
                        connection, order["order_id"], "order", order["order_status"], order_target.value,
                        event["event_id"], event["occurred_at"],
                    )
                self._mark_event(connection, event, "applied")
                made_progress = True

    def _mark_event(self, connection: sqlite3.Connection, event: dict[str, Any], status: str) -> None:
        connection.execute(
            "UPDATE provider_events SET status = ?, applied_at = ? WHERE event_id = ?",
            (status, event["occurred_at"], event["event_id"]),
        )

    def _transition_order(
        self,
        order_id: str,
        target: OrderStatus,
        *,
        source_reference: str,
        occurred_at: str,
        delivery_status: str,
    ) -> dict[str, Any]:
        _parse_timestamp(occurred_at)
        with self._connection(write=True) as connection:
            order = self._require_order(connection, order_id)
            current = OrderStatus(order["order_status"])
            if current is target:
                return self._order_view(connection, order_id)
            require_transition(current, target)
            connection.execute(
                "UPDATE orders SET order_status = ?, delivery_status = ?, updated_at = ? WHERE order_id = ?",
                (target.value, delivery_status, occurred_at, order_id),
            )
            self._history(
                connection, order_id, "order", current.value, target.value,
                source_reference, occurred_at,
            )
            return self._order_view(connection, order_id)

    @staticmethod
    def _require_order(connection: sqlite3.Connection, order_id: str) -> sqlite3.Row:
        order = connection.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if order is None:
            raise InputRejected("order does not exist", code="unknown_order")
        return order

    @staticmethod
    def _history(
        connection: sqlite3.Connection,
        order_id: str,
        dimension: str,
        prior_status: str | None,
        new_status: str,
        source_reference: str,
        occurred_at: str,
    ) -> None:
        connection.execute(
            """INSERT INTO order_history(
                order_id, dimension, prior_status, new_status, source_reference, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, dimension, prior_status, new_status, source_reference, occurred_at),
        )

    @staticmethod
    def _financial_entry(
        connection: sqlite3.Connection,
        order_id: str,
        category: str,
        amount_minor: int,
        impact_minor: int,
        source_reference: str,
        recorded_at: str,
    ) -> None:
        connection.execute(
            """INSERT INTO financial_entries(
                order_id, category, amount_minor, contribution_impact_minor, source_reference, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, category, amount_minor, impact_minor, source_reference, recorded_at),
        )

    def _order_view(self, connection: sqlite3.Connection, order_id: str) -> dict[str, Any]:
        order = self._require_order(connection, order_id)
        rows = connection.execute(
            """SELECT category, COALESCE(SUM(amount_minor), 0) AS amount,
                COALESCE(SUM(contribution_impact_minor), 0) AS impact
            FROM financial_entries WHERE order_id = ? GROUP BY category""",
            (order_id,),
        ).fetchall()
        amounts = {row["category"]: row["amount"] for row in rows}
        contribution = sum(row["impact"] for row in rows)
        costs = {category: amounts.get(category, 0) for category in DIRECT_COST_CATEGORIES}
        pending_events = connection.execute(
            """SELECT event_id, event_type FROM provider_events
            WHERE provider_payment_id = ? AND status = 'pending' ORDER BY received_at, event_id""",
            (order["provider_payment_id"],),
        ).fetchall() if order["provider_payment_id"] else []
        payment_status = PaymentStatus(order["payment_status"])
        refund_status = {
            PaymentStatus.REFUND_PENDING: "refund_pending",
            PaymentStatus.REFUNDED: "refunded",
            PaymentStatus.DISPUTED: "disputed",
        }.get(payment_status, "not_refunded")
        return {
            "order_id": order["order_id"],
            "environment": order["environment"],
            "quote_id": order["quote_id"],
            "buyer_reference": order["buyer_reference"],
            "provider": order["provider"],
            "provider_checkout_id": order["provider_checkout_id"],
            "provider_payment_id": order["provider_payment_id"],
            "order_status": order["order_status"],
            "payment_status": order["payment_status"],
            "quoted_amount_minor": order["quoted_amount_minor"],
            "collected_amount_minor": order["collected_amount_minor"],
            "processing_fee_minor": order["processing_fee_minor"],
            "direct_costs_minor": costs,
            "direct_costs_recorded": bool(order["direct_costs_recorded"]),
            "refunded_amount_minor": order["refunded_amount_minor"],
            "gross_contribution_minor": contribution,
            "currency": order["currency"],
            "receipt_id": order["receipt_id"],
            "receipt_sha256": order["receipt_sha256"],
            "envelope_sha256": order["envelope_sha256"],
            "signing_keyid": order["signing_keyid"],
            "delivery_status": order["delivery_status"],
            "refund_status": refund_status,
            "settlement_status": (
                "sandbox_nonsettling"
                if self.environment == "sandbox"
                else "available_not_goal_qualified"
                if payment_status is PaymentStatus.AVAILABLE and not bool(order["counts_for_goal"])
                else "available_goal_qualified"
                if payment_status is PaymentStatus.AVAILABLE
                else "pending_provider_availability"
                if payment_status is PaymentStatus.CAPTURED
                else "not_confirmed"
            ),
            "pending_provider_events": [dict(row) for row in pending_events],
            "counts_for_goal": bool(order["counts_for_goal"]),
            "created_at": order["created_at"],
            "updated_at": order["updated_at"],
        }


class FakePaymentProvider:
    """Deterministic sandbox provider for replay, reordering, and reconciliation tests."""

    def __init__(self, store: CommerceStore) -> None:
        if store.environment != "sandbox":
            raise ValueError("fake payment provider requires a sandbox store")
        self.store = store

    @staticmethod
    def _payment_id(order_id: str) -> str:
        return "pay_test_" + hashlib.sha256(order_id.encode("ascii")).hexdigest()[:24]

    @staticmethod
    def _event_id(payment_id: str, event_type: str) -> str:
        return "evt_test_" + hashlib.sha256(f"{payment_id}\0{event_type}".encode("ascii")).hexdigest()[:24]

    def create_checkout(self, order_id: str, *, occurred_at: str) -> dict[str, Any]:
        return self.store.attach_checkout(order_id, self._payment_id(order_id), occurred_at=occurred_at)

    def event(
        self,
        order_id: str,
        event_type: str,
        *,
        occurred_at: str,
        processing_fee_minor: int = 0,
    ) -> dict[str, Any]:
        if event_type not in _EVENT_TYPES:
            raise ValueError("unsupported fake event type")
        order = self.store.get_order(order_id)
        payment_id = order["provider_payment_id"]
        if payment_id is None:
            raise InputRejected("checkout is not attached", code="unknown_provider_payment")
        event = {
            "schema_version": "1.0.0",
            "provider": "fake",
            "environment": "sandbox",
            "event_id": self._event_id(payment_id, event_type),
            "type": event_type,
            "payment_id": payment_id,
            "amount_minor": order["quoted_amount_minor"],
            "fee_minor": processing_fee_minor if event_type == "payment.captured" else 0,
            "currency": order["currency"],
            "occurred_at": occurred_at,
        }
        return self.store.ingest_provider_event(event, received_at=occurred_at)
