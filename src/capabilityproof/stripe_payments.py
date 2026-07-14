"""Strict Stripe Checkout and settlement reconciliation for Stage B commerce.

Webhook bodies are authenticated with Stripe's official SDK, but webhook object fields
never directly mutate financial state. Every accepted event causes server-side retrieval
of the linked Checkout Session, PaymentIntent, Charge, and BalanceTransaction before a
small provider-neutral event is admitted to :class:`CommerceStore`.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator, Mapping
from urllib.parse import urlsplit

import stripe

from .commerce_store import CommerceStore
from .errors import InputRejected


STRIPE_SDK_VERSION = "15.3.0"
STRIPE_API_VERSION = "2026-06-24.dahlia"
STRIPE_STATE_SCHEMA_VERSION = "1"
MAX_STRIPE_WEBHOOK_BYTES = 64_000
WEBHOOK_PROCESSING_LEASE = timedelta(minutes=10)

_MODE = {"test", "live"}
_ACCOUNT_ID = re.compile(r"acct_[A-Za-z0-9]{8,64}")
_IDEMPOTENCY = re.compile(r"[A-Za-z0-9_-]{8,96}")
_ORDER_ID = re.compile(r"ord_(?:test_)?[0-9a-f]{24}")
_EVENT_ID = re.compile(r"evt_[A-Za-z0-9]{8,64}")
_OBJECT_ID = re.compile(r"[a-z][a-z_]{1,31}_[A-Za-z0-9]{8,128}")
_CHECKOUT_ID = re.compile(r"cs_(?:test|live)_[A-Za-z0-9]{8,128}")
_PAYMENT_ID = re.compile(r"pi_[A-Za-z0-9]{8,64}")
_CHARGE_ID = re.compile(r"ch_[A-Za-z0-9]{8,64}")
_BALANCE_ID = re.compile(r"txn_[A-Za-z0-9]{8,64}")
_WEBHOOK_TYPES = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "charge.succeeded",
    "charge.refunded",
    "charge.dispute.created",
    "charge.dispute.closed",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise InputRejected("Stripe timestamp is invalid", code="invalid_stripe_object")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except (ValueError, OverflowError) as exc:
        raise InputRejected("Stripe timestamp is invalid", code="invalid_stripe_object") from exc
    if parsed.tzinfo is None:
        raise InputRejected("Stripe timestamp requires a timezone", code="invalid_stripe_object")
    return parsed.astimezone(timezone.utc)


def _aware_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InputRejected(f"{field} requires a timezone", code="invalid_commerce_request")
    return value.astimezone(timezone.utc)


def _epoch_time(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4_102_444_800:
        raise InputRejected("Stripe object timestamp is invalid", code="invalid_stripe_object")
    return datetime.fromtimestamp(value, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict_recursive"):
        value = value.to_dict_recursive()
    elif hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise InputRejected("Stripe API returned an invalid object", code="invalid_stripe_object")
    return dict(value)


def _reference_id(value: Any, pattern: re.Pattern[str], field: str) -> str:
    if isinstance(value, Mapping) or hasattr(value, "to_dict_recursive"):
        value = _as_dict(value).get("id")
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise InputRejected(f"Stripe {field} identifier is invalid", code="invalid_stripe_object")
    return value


def _bounded_int(value: Any, field: str, *, maximum: int = 10_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise InputRejected(f"Stripe {field} is invalid", code="invalid_stripe_object")
    return value


def _metadata(value: Any) -> dict[str, str]:
    result = _as_dict(value)
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in result.items()):
        raise InputRejected("Stripe metadata is invalid", code="invalid_stripe_object")
    return result


def _configured_url(value: str, *, success: bool) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 2_048:
        raise ValueError("Stripe redirect URL is invalid")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("Stripe redirect URLs must be credential-free HTTPS URLs")
    if success and "{CHECKOUT_SESSION_ID}" not in value:
        raise ValueError("Stripe success URL must include {CHECKOUT_SESSION_ID}")
    return value


class StripePaymentAdapter:
    """Create Checkout Sessions and reconcile exact server-retrieved Stripe state."""

    def __init__(
        self,
        store: CommerceStore,
        *,
        mode: str,
        api_key: str,
        webhook_secret: str,
        expected_account_id: str,
        success_url: str,
        cancel_url: str,
        live_checkout_enabled: bool = False,
        client: Any | None = None,
        account: Any | None = None,
    ) -> None:
        if mode not in _MODE:
            raise ValueError("Stripe mode must be test or live")
        expected_environment = "sandbox" if mode == "test" else "live"
        if store.environment != expected_environment:
            raise ValueError("Stripe mode does not match the commerce store environment")
        expected_key_prefix = "sk_test_" if mode == "test" else "sk_live_"
        if (
            not isinstance(api_key, str)
            or not 16 <= len(api_key) <= 256
            or not api_key.startswith(expected_key_prefix)
            or any(ord(character) < 0x21 or ord(character) > 0x7E for character in api_key)
        ):
            raise ValueError("Stripe secret key does not match the configured mode")
        if (
            not isinstance(webhook_secret, str)
            or not 16 <= len(webhook_secret) <= 256
            or not webhook_secret.startswith("whsec_")
            or any(ord(character) < 0x21 or ord(character) > 0x7E for character in webhook_secret)
        ):
            raise ValueError("Stripe webhook secret is invalid")
        if mode == "live" and not live_checkout_enabled:
            raise ValueError("live Stripe checkout requires an explicit activation acknowledgement")
        if not isinstance(expected_account_id, str) or not _ACCOUNT_ID.fullmatch(expected_account_id):
            raise ValueError("expected Stripe account identifier is invalid")
        if stripe.VERSION != STRIPE_SDK_VERSION or stripe.api_version != STRIPE_API_VERSION:
            raise RuntimeError("installed Stripe SDK does not match the reviewed API contract")
        self.store = store
        self.mode = mode
        self._livemode = mode == "live"
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._success_url = _configured_url(success_url, success=True)
        self._cancel_url = _configured_url(cancel_url, success=False)
        self._live_checkout_enabled = live_checkout_enabled
        self._client = client or stripe.StripeClient(
            api_key,
            stripe_version=STRIPE_API_VERSION,
            max_network_retries=2,
        )
        if account is None:
            if client is not None:
                raise ValueError("injected Stripe clients require an injected account object")
            try:
                account = stripe.Account.retrieve(
                    api_key=api_key,
                    stripe_version=STRIPE_API_VERSION,
                )
            except stripe.StripeError as exc:
                raise InputRejected(
                    "Stripe account identity could not be verified",
                    code="stripe_api_error",
                ) from exc
        account_value = _as_dict(account)
        if (
            account_value.get("object") != "account"
            or account_value.get("id") != expected_account_id
            or account_value.get("charges_enabled") is not True
            or account_value.get("details_submitted") is not True
            or (mode == "live" and account_value.get("payouts_enabled") is not True)
        ):
            raise InputRejected(
                "Stripe credential is not bound to the expected enabled account",
                code="stripe_account_mismatch",
            )
        self._account_id = expected_account_id
        self._initialize_state()

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.store.path, timeout=10, isolation_level=None)
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

    def _initialize_state(self) -> None:
        with self._connection(write=True) as connection:
            metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
            if metadata.get("environment") != self.store.environment:
                raise InputRejected(
                    "Stripe adapter environment does not match the commerce store",
                    code="commerce_environment_mismatch",
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS stripe_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                    event_id TEXT PRIMARY KEY,
                    payload_digest TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    api_version TEXT NOT NULL,
                    livemode INTEGER NOT NULL CHECK(livemode IN (0, 1)),
                    status TEXT NOT NULL CHECK(status IN (
                        'processing', 'processed', 'ignored', 'retryable', 'rejected'
                    )),
                    order_id TEXT REFERENCES orders(order_id),
                    received_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stripe_reconciliations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL REFERENCES orders(order_id),
                    source_event_id TEXT,
                    checkout_id TEXT NOT NULL,
                    payment_id TEXT NOT NULL,
                    charge_id TEXT NOT NULL,
                    balance_transaction_id TEXT NOT NULL,
                    snapshot_digest TEXT NOT NULL,
                    payment_state TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    UNIQUE(order_id, snapshot_digest)
                );
                """
            )
            expected = {
                "schema_version": STRIPE_STATE_SCHEMA_VERSION,
                "environment": self.store.environment,
                "mode": self.mode,
                "stripe_sdk_version": STRIPE_SDK_VERSION,
                "stripe_api_version": STRIPE_API_VERSION,
                "stripe_account_id": self._account_id,
            }
            actual = dict(connection.execute("SELECT key, value FROM stripe_metadata").fetchall())
            if not actual:
                connection.executemany(
                    "INSERT INTO stripe_metadata(key, value) VALUES (?, ?)", expected.items()
                )
            elif actual != expected:
                raise InputRejected(
                    "Stripe adapter schema or environment does not match",
                    code="commerce_environment_mismatch",
                )

    def prepare_checkout(
        self,
        request_value: Any,
        *,
        quote_id: str,
        idempotency_key: str,
        buyer_reference: str,
        now: datetime,
    ) -> dict[str, Any]:
        """Create an immutable quote/order and one idempotent hosted Checkout Session."""

        if not _IDEMPOTENCY.fullmatch(idempotency_key):
            raise InputRejected("invalid Stripe idempotency key", code="invalid_commerce_request")
        observed = _aware_datetime(now, "Stripe checkout timestamp")
        quote = self.store.create_quote(
            request_value,
            quote_id=quote_id,
            generated_at=now,
            payment_provider="stripe",
            live_checkout_enabled=self._live_checkout_enabled,
        )
        order = self.store.create_order(
            quote["quote_id"],
            idempotency_key=idempotency_key,
            buyer_reference=buyer_reference,
            now=now,
        )
        if order["provider"] != "stripe":
            raise InputRejected("order is not bound to Stripe", code="invalid_commerce_request")
        if order["provider_checkout_id"] is not None:
            session = self._retrieve_checkout(order["provider_checkout_id"])
            self._validate_checkout(session, order, quote)
            return self._checkout_view(order, session)

        expires_at = int(_parse_time(quote["expires_at"]).timestamp())
        checkout_key = "vouchspec_" + hashlib.sha256(
            f"{self.store.environment}\0{order['order_id']}\0{idempotency_key}".encode("utf-8")
        ).hexdigest()
        params = {
            "mode": "payment",
            "client_reference_id": order["order_id"],
            "success_url": self._success_url,
            "cancel_url": self._cancel_url,
            "expires_at": expires_at,
            "payment_method_types": ["card"],
            "metadata": {
                "vouchspec_order_id": order["order_id"],
                "vouchspec_quote_id": order["quote_id"],
                "vouchspec_account_id": self._account_id,
            },
            "payment_intent_data": {
                "metadata": {
                    "vouchspec_order_id": order["order_id"],
                    "vouchspec_quote_id": order["quote_id"],
                    "vouchspec_account_id": self._account_id,
                }
            },
            "line_items": [
                {
                    "price_data": {
                        "currency": order["currency"],
                        "unit_amount": order["quoted_amount_minor"],
                        "product_data": {
                            "name": "VouchSpec fresh exact-version static validation",
                            "description": "Signed static evidence for one immutable public Agent Skill",
                        },
                    },
                    "quantity": 1,
                }
            ],
        }
        try:
            session = _as_dict(
                self._client.v1.checkout.sessions.create(
                    params,
                    {"idempotency_key": checkout_key},
                )
            )
        except stripe.StripeError as exc:
            raise InputRejected("Stripe Checkout creation failed", code="stripe_api_error") from exc
        self._validate_checkout(session, order, quote)
        checkout_id = _reference_id(session.get("id"), _CHECKOUT_ID, "Checkout Session")
        payment_id = session.get("payment_intent")
        if payment_id is not None:
            payment_id = _reference_id(payment_id, _PAYMENT_ID, "PaymentIntent")
        order = self.store.attach_checkout(
            order["order_id"],
            checkout_id,
            payment_id=payment_id,
            occurred_at=observed.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
        return self._checkout_view(order, session)

    def process_webhook(self, raw_body: bytes, signature_header: str) -> dict[str, Any]:
        """Authenticate one exact webhook body, deduplicate it, and reconcile retrieved state."""

        if not isinstance(raw_body, bytes) or not 1 <= len(raw_body) <= MAX_STRIPE_WEBHOOK_BYTES:
            raise InputRejected("Stripe webhook body size is invalid", code="invalid_webhook_signature")
        if not isinstance(signature_header, str) or not 1 <= len(signature_header) <= 1_024:
            raise InputRejected("Stripe webhook signature is invalid", code="invalid_webhook_signature")
        try:
            event = _as_dict(
                stripe.Webhook.construct_event(
                    raw_body,
                    signature_header,
                    self._webhook_secret,
                    tolerance=300,
                )
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise InputRejected("Stripe webhook signature did not verify", code="invalid_webhook_signature") from exc
        event_id = _reference_id(event.get("id"), _EVENT_ID, "Event")
        event_type = event.get("type")
        api_version = event.get("api_version")
        livemode = event.get("livemode")
        if (
            not isinstance(event_type, str)
            or not 1 <= len(event_type) <= 128
            or api_version != STRIPE_API_VERSION
            or livemode is not self._livemode
            or event.get("account") is not None
            or event.get("context") is not None
        ):
            raise InputRejected("Stripe event context is invalid", code="invalid_stripe_event")
        data = _as_dict(event.get("data"))
        event_object = _as_dict(data.get("object"))
        object_id = _reference_id(event_object.get("id"), _OBJECT_ID, "event object")
        digest = hashlib.sha256(raw_body).hexdigest()
        received_at = _utc_now()
        reservation = self._reserve_webhook(
            event_id,
            digest,
            event_type,
            object_id,
            api_version,
            received_at,
        )
        if reservation["duplicate"]:
            return {
                "event_id": event_id,
                "duplicate": True,
                "status": reservation["status"],
                "order_id": reservation.get("order_id"),
            }
        if event_type not in _WEBHOOK_TYPES:
            self._finish_webhook(event_id, "ignored", received_at)
            return {"event_id": event_id, "duplicate": False, "status": "ignored", "order_id": None}
        try:
            order_id = self._order_id_for_event(event_type, object_id)
            result = self.reconcile_order(order_id, source_event_id=event_id)
        except InputRejected:
            self._finish_webhook(event_id, "rejected", received_at)
            raise
        except stripe.StripeError as exc:
            self._finish_webhook(event_id, "retryable", received_at)
            raise InputRejected("Stripe reconciliation is temporarily unavailable", code="stripe_api_error") from exc
        self._finish_webhook(event_id, "processed", received_at, order_id=order_id)
        return {
            "event_id": event_id,
            "duplicate": False,
            "status": "processed",
            "order_id": order_id,
            "payment_status": result["order"]["payment_status"],
        }

    def reconcile_order(
        self,
        order_id: str,
        *,
        source_event_id: str | None = None,
        observed_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Retrieve and cross-bind the complete Stripe payment chain for one order."""

        if not _ORDER_ID.fullmatch(order_id):
            raise InputRejected("order identifier is invalid", code="unknown_order")
        current_time = _aware_datetime(
            observed_at or datetime.now(timezone.utc),
            "Stripe reconciliation timestamp",
        )
        order = self.store.get_order(order_id)
        if order["provider"] != "stripe" or order["provider_checkout_id"] is None:
            raise InputRejected("order is not attached to Stripe", code="unknown_provider_payment")
        quote = self.store.get_quote(order["quote_id"])
        session = self._retrieve_checkout(order["provider_checkout_id"])
        self._validate_checkout(session, order, quote, allow_completed=True)
        payment_reference = session.get("payment_intent")
        if payment_reference is None:
            if session.get("status") == "expired":
                return {"state": "expired_without_payment_intent", "order": order}
            return {"state": "pending_payment_intent", "order": order}

        payment_id = _reference_id(payment_reference, _PAYMENT_ID, "PaymentIntent")
        order = self.store.bind_provider_payment(
            order_id,
            payment_id,
            checkout_id=order["provider_checkout_id"],
            occurred_at=_utc_now(),
        )
        payment = self._retrieve_payment(payment_id)
        payment_metadata = _metadata(payment.get("metadata"))
        if (
            payment.get("object") != "payment_intent"
            or payment.get("id") != payment_id
            or payment.get("livemode") is not self._livemode
            or payment.get("currency") != order["currency"]
            or _bounded_int(payment.get("amount"), "PaymentIntent amount") != order["quoted_amount_minor"]
            or payment_metadata.get("vouchspec_order_id") != order_id
            or payment_metadata.get("vouchspec_quote_id") != order["quote_id"]
            or payment_metadata.get("vouchspec_account_id") != self._account_id
        ):
            raise InputRejected("Stripe PaymentIntent is not bound to the order", code="invalid_stripe_object")
        payment_status = payment.get("status")
        if payment_status in {"canceled", "requires_payment_method"}:
            order = self._emit(order, "payment.failed", payment_id, 0, _epoch_time(payment.get("created")))
            return {"state": "failed", "order": order}
        if payment_status != "succeeded":
            return {"state": "pending_payment", "order": order}
        if _bounded_int(payment.get("amount_received"), "PaymentIntent received amount") != order["quoted_amount_minor"]:
            raise InputRejected("Stripe received amount does not match the quote", code="stripe_amount_mismatch")

        charge_id = _reference_id(payment.get("latest_charge"), _CHARGE_ID, "Charge")
        charge = self._retrieve_charge(charge_id)
        charge_payment = _reference_id(charge.get("payment_intent"), _PAYMENT_ID, "PaymentIntent")
        amount_refunded = _bounded_int(charge.get("amount_refunded"), "refunded amount")
        if (
            charge.get("object") != "charge"
            or charge.get("id") != charge_id
            or charge_payment != payment_id
            or charge.get("livemode") is not self._livemode
            or charge.get("currency") != order["currency"]
            or _bounded_int(charge.get("amount"), "Charge amount") != order["quoted_amount_minor"]
            or _bounded_int(charge.get("amount_captured"), "captured amount") != order["quoted_amount_minor"]
            or charge.get("paid") is not True
            or charge.get("captured") is not True
            or amount_refunded > order["quoted_amount_minor"]
        ):
            raise InputRejected("Stripe Charge is not bound to the order", code="invalid_stripe_object")
        if 0 < amount_refunded < order["quoted_amount_minor"]:
            raise InputRejected("partial refunds are outside the published policy", code="stripe_partial_refund")

        balance_id = _reference_id(charge.get("balance_transaction"), _BALANCE_ID, "BalanceTransaction")
        balance = self._retrieve_balance(balance_id)
        balance_amount = _bounded_int(balance.get("amount"), "balance amount")
        balance_fee = _bounded_int(balance.get("fee"), "processing fee")
        balance_net = balance.get("net")
        if (
            balance.get("object") != "balance_transaction"
            or balance.get("id") != balance_id
            or _reference_id(balance.get("source"), _CHARGE_ID, "balance source") != charge_id
            or balance.get("currency") != order["currency"]
            or balance_amount != order["quoted_amount_minor"]
            or isinstance(balance_net, bool)
            or not isinstance(balance_net, int)
            or balance_net != balance_amount - balance_fee
            or balance.get("status") not in {"pending", "available"}
        ):
            raise InputRejected("Stripe balance transaction is inconsistent", code="invalid_stripe_object")

        captured_at = _epoch_time(charge.get("created"))
        order = self._emit(order, "payment.captured", balance_id, balance_fee, captured_at)
        balance_status = balance["status"]
        available_at = _epoch_time(balance.get("available_on"))
        if balance_status == "available":
            if _parse_time(available_at) > current_time:
                raise InputRejected("Stripe marked future funds available", code="invalid_stripe_object")
            order = self._emit(order, "payment.available", balance_id, 0, available_at)

        if charge.get("disputed") is True:
            order = self._emit(order, "payment.disputed", charge_id, 0, _utc_now())
            derived_state = "disputed"
        elif amount_refunded == order["quoted_amount_minor"]:
            order = self._emit(order, "payment.refund_pending", charge_id, 0, _utc_now())
            order = self._emit(order, "payment.refunded", charge_id, 0, _utc_now())
            derived_state = "refunded"
        else:
            derived_state = balance_status

        snapshot = {
            "checkout_id": session["id"],
            "payment_id": payment_id,
            "payment_status": payment_status,
            "charge_id": charge_id,
            "amount_refunded": amount_refunded,
            "disputed": charge.get("disputed"),
            "balance_transaction_id": balance_id,
            "balance_amount": balance_amount,
            "balance_fee": balance_fee,
            "balance_net": balance_net,
            "balance_status": balance_status,
            "available_on": balance.get("available_on"),
        }
        self._record_reconciliation(
            order_id,
            source_event_id,
            session["id"],
            payment_id,
            charge_id,
            balance_id,
            hashlib.sha256(_canonical(snapshot).encode("utf-8")).hexdigest(),
            derived_state,
            current_time.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
        return {"state": derived_state, "order": order}

    def audit_events(self) -> list[dict[str, Any]]:
        """Return credential-free webhook audit state for operations and tests."""

        with self._connection() as connection:
            rows = connection.execute(
                """SELECT event_id, event_type, object_id, api_version, livemode, status,
                    order_id, received_at, updated_at
                FROM stripe_webhook_events ORDER BY received_at, event_id"""
            ).fetchall()
        return [dict(row) for row in rows]

    def _validate_checkout(
        self,
        session: dict[str, Any],
        order: dict[str, Any],
        quote: dict[str, Any],
        *,
        allow_completed: bool = False,
    ) -> None:
        checkout_id = _reference_id(session.get("id"), _CHECKOUT_ID, "Checkout Session")
        expected_prefix = "cs_test_" if self.mode == "test" else "cs_live_"
        metadata = _metadata(session.get("metadata"))
        status = session.get("status")
        allowed_statuses = {"open"} | ({"complete", "expired"} if allow_completed else set())
        if (
            not checkout_id.startswith(expected_prefix)
            or session.get("object") != "checkout.session"
            or session.get("livemode") is not self._livemode
            or session.get("mode") != "payment"
            or session.get("currency") != order["currency"]
            or _bounded_int(session.get("amount_total"), "Checkout amount") != order["quoted_amount_minor"]
            or session.get("client_reference_id") != order["order_id"]
            or metadata.get("vouchspec_order_id") != order["order_id"]
            or metadata.get("vouchspec_quote_id") != order["quote_id"]
            or metadata.get("vouchspec_account_id") != self._account_id
            or status not in allowed_statuses
            or _bounded_int(session.get("expires_at"), "Checkout expiry", maximum=4_102_444_800)
            != int(_parse_time(quote["expires_at"]).timestamp())
        ):
            raise InputRejected("Stripe Checkout Session is not bound to the order", code="invalid_stripe_object")
        if not allow_completed:
            checkout_url = session.get("url")
            if (
                not isinstance(checkout_url, str)
                or not 1 <= len(checkout_url) <= 4_096
                or urlsplit(checkout_url).scheme != "https"
                or urlsplit(checkout_url).hostname != "checkout.stripe.com"
            ):
                raise InputRejected("Stripe Checkout URL is invalid", code="invalid_stripe_object")

    @staticmethod
    def _checkout_view(order: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
        return {
            "order": order,
            "checkout": {
                "provider": "stripe_checkout",
                "checkout_id": session["id"],
                "url": session["url"],
                "expires_at": _epoch_time(session["expires_at"]),
                "livemode": bool(session["livemode"]),
            },
        }

    def _retrieve_checkout(self, checkout_id: str) -> dict[str, Any]:
        return _as_dict(self._client.v1.checkout.sessions.retrieve(checkout_id))

    def _retrieve_payment(self, payment_id: str) -> dict[str, Any]:
        return _as_dict(self._client.v1.payment_intents.retrieve(payment_id))

    def _retrieve_charge(self, charge_id: str) -> dict[str, Any]:
        return _as_dict(self._client.v1.charges.retrieve(charge_id))

    def _retrieve_balance(self, balance_id: str) -> dict[str, Any]:
        return _as_dict(self._client.v1.balance_transactions.retrieve(balance_id))

    def _order_id_for_event(self, event_type: str, object_id: str) -> str:
        if event_type.startswith("checkout.session."):
            session_id = _reference_id(object_id, _CHECKOUT_ID, "Checkout Session")
            metadata = _metadata(self._retrieve_checkout(session_id).get("metadata"))
        elif event_type.startswith("payment_intent."):
            payment_id = _reference_id(object_id, _PAYMENT_ID, "PaymentIntent")
            metadata = _metadata(self._retrieve_payment(payment_id).get("metadata"))
        elif event_type.startswith("charge.dispute."):
            dispute_id = _reference_id(object_id, re.compile(r"dp_[A-Za-z0-9]{8,64}"), "Dispute")
            dispute = _as_dict(self._client.v1.disputes.retrieve(dispute_id))
            charge_id = _reference_id(dispute.get("charge"), _CHARGE_ID, "Charge")
            charge = self._retrieve_charge(charge_id)
            payment_id = _reference_id(charge.get("payment_intent"), _PAYMENT_ID, "PaymentIntent")
            metadata = _metadata(self._retrieve_payment(payment_id).get("metadata"))
        elif event_type.startswith("charge."):
            charge_id = _reference_id(object_id, _CHARGE_ID, "Charge")
            charge = self._retrieve_charge(charge_id)
            payment_id = _reference_id(charge.get("payment_intent"), _PAYMENT_ID, "PaymentIntent")
            metadata = _metadata(self._retrieve_payment(payment_id).get("metadata"))
        else:
            raise InputRejected("unsupported Stripe event type", code="invalid_stripe_event")
        order_id = metadata.get("vouchspec_order_id")
        if not isinstance(order_id, str) or not _ORDER_ID.fullmatch(order_id):
            raise InputRejected("Stripe object has no valid order binding", code="invalid_stripe_object")
        return order_id

    def _emit(
        self,
        order: dict[str, Any],
        event_type: str,
        provider_reference: str,
        fee_minor: int,
        occurred_at: str,
    ) -> dict[str, Any]:
        _parse_time(occurred_at)
        prefix = "evt_test_" if self.store.environment == "sandbox" else "evt_"
        identifier = prefix + hashlib.sha256(
            f"stripe\0{order['order_id']}\0{event_type}\0{provider_reference}\0{fee_minor}".encode("utf-8")
        ).hexdigest()[:24]
        result = self.store.ingest_provider_event(
            {
                "schema_version": "1.0.0",
                "provider": "stripe",
                "environment": self.store.environment,
                "event_id": identifier,
                "type": event_type,
                "payment_id": order["provider_payment_id"],
                "amount_minor": order["quoted_amount_minor"],
                "fee_minor": fee_minor if event_type == "payment.captured" else 0,
                "currency": order["currency"],
                "occurred_at": occurred_at,
            },
            received_at=_utc_now(),
        )
        return result["order"]

    def _reserve_webhook(
        self,
        event_id: str,
        payload_digest: str,
        event_type: str,
        object_id: str,
        api_version: str,
        received_at: str,
    ) -> dict[str, Any]:
        with self._connection(write=True) as connection:
            row = connection.execute(
                """SELECT payload_digest, status, order_id, updated_at
                FROM stripe_webhook_events WHERE event_id = ?""",
                (event_id,),
            ).fetchone()
            if row is not None:
                if row["payload_digest"] != payload_digest:
                    raise InputRejected("Stripe event identifier was reused", code="stripe_event_conflict")
                stale_processing = (
                    row["status"] == "processing"
                    and _parse_time(received_at) - _parse_time(row["updated_at"])
                    >= WEBHOOK_PROCESSING_LEASE
                )
                if row["status"] == "retryable" or stale_processing:
                    connection.execute(
                        "UPDATE stripe_webhook_events SET status = 'processing', updated_at = ? WHERE event_id = ?",
                        (received_at, event_id),
                    )
                    return {"duplicate": False, "status": "processing", "order_id": row["order_id"]}
                if row["status"] == "processing":
                    raise InputRejected(
                        "Stripe event reconciliation is already in progress",
                        code="stripe_event_processing",
                    )
                return {"duplicate": True, "status": row["status"], "order_id": row["order_id"]}
            connection.execute(
                """INSERT INTO stripe_webhook_events(
                    event_id, payload_digest, event_type, object_id, api_version, livemode,
                    status, received_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'processing', ?, ?)""",
                (
                    event_id,
                    payload_digest,
                    event_type,
                    object_id,
                    api_version,
                    int(self._livemode),
                    received_at,
                    received_at,
                ),
            )
            return {"duplicate": False, "status": "processing", "order_id": None}

    def _finish_webhook(
        self,
        event_id: str,
        status: str,
        updated_at: str,
        *,
        order_id: str | None = None,
    ) -> None:
        with self._connection(write=True) as connection:
            changed = connection.execute(
                """UPDATE stripe_webhook_events SET status = ?, order_id = COALESCE(?, order_id),
                    updated_at = ? WHERE event_id = ?""",
                (status, order_id, updated_at, event_id),
            ).rowcount
            if changed != 1:
                raise InputRejected("Stripe webhook audit state is missing", code="stripe_event_conflict")

    def _record_reconciliation(
        self,
        order_id: str,
        source_event_id: str | None,
        checkout_id: str,
        payment_id: str,
        charge_id: str,
        balance_id: str,
        snapshot_digest: str,
        payment_state: str,
        observed_at: str,
    ) -> None:
        with self._connection(write=True) as connection:
            connection.execute(
                """INSERT OR IGNORE INTO stripe_reconciliations(
                    order_id, source_event_id, checkout_id, payment_id, charge_id,
                    balance_transaction_id, snapshot_digest, payment_state, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    order_id,
                    source_event_id,
                    checkout_id,
                    payment_id,
                    charge_id,
                    balance_id,
                    snapshot_digest,
                    payment_state,
                    observed_at,
                ),
            )
