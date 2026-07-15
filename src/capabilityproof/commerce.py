"""Provider-neutral commerce contracts for the constrained Stage B product.

This module prepares request validation, quote generation, payment/order state rules, and
Stripe webhook authentication without enabling checkout or artifact intake.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import hmac
import json
from pathlib import PurePosixPath
import re
import secrets
from typing import Any

from .errors import InputRejected


FRESH_VALIDATION_AMOUNT_MINOR = 25
LEGACY_STRIPE_AMOUNT_MINOR = 4_900
FRESH_VALIDATION_CURRENCY = "usd"
FRESH_VALIDATION_PROFILE = "vouchspec-public-static-v1"
QUOTE_TTL_MINUTES = 15

_COMMIT = re.compile(r"[0-9a-f]{40}")
_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
_REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})")
_DELIVERY_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")
_QUOTE_ID = re.compile(r"q_[0-9a-f]{24}")
_SKILL_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")

REFUND_CONDITIONS = (
    "duplicate_charge",
    "payment_settled_but_job_never_started_due_to_vouchspec_failure",
    "job_failed_before_a_signed_receipt_was_produced",
    "unsupported_request_accepted_due_to_vouchspec_validation_defect",
    "invalid_signature_or_wrong_source_commit_path_or_digest_after_one_automatic_rerun",
)


class OrderStatus(StrEnum):
    CHECKOUT_PENDING = "checkout_pending"
    PAYMENT_PENDING = "payment_pending"
    QUEUED = "queued"
    RUNNING = "running"
    DELIVERED = "delivered"
    PAYMENT_FAILED = "payment_failed"
    FULFILLMENT_FAILED = "fulfillment_failed"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    CAPTURED = "captured"
    AVAILABLE = "available"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    FAILED = "failed"


ORDER_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CHECKOUT_PENDING: frozenset({OrderStatus.PAYMENT_PENDING, OrderStatus.CANCELLED}),
    OrderStatus.PAYMENT_PENDING: frozenset({OrderStatus.QUEUED, OrderStatus.PAYMENT_FAILED, OrderStatus.CANCELLED}),
    OrderStatus.QUEUED: frozenset({OrderStatus.RUNNING, OrderStatus.FULFILLMENT_FAILED}),
    OrderStatus.RUNNING: frozenset({OrderStatus.DELIVERED, OrderStatus.FULFILLMENT_FAILED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.PAYMENT_FAILED: frozenset(),
    OrderStatus.FULFILLMENT_FAILED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

PAYMENT_TRANSITIONS: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.PENDING: frozenset({PaymentStatus.CAPTURED, PaymentStatus.FAILED}),
    PaymentStatus.CAPTURED: frozenset(
        {PaymentStatus.AVAILABLE, PaymentStatus.REFUND_PENDING, PaymentStatus.DISPUTED}
    ),
    PaymentStatus.AVAILABLE: frozenset({PaymentStatus.REFUND_PENDING, PaymentStatus.DISPUTED}),
    PaymentStatus.REFUND_PENDING: frozenset({PaymentStatus.REFUNDED, PaymentStatus.DISPUTED}),
    PaymentStatus.REFUNDED: frozenset(),
    PaymentStatus.DISPUTED: frozenset(),
    PaymentStatus.FAILED: frozenset(),
}


def _exact_object(value: Any, keys: set[str], *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys or any(not isinstance(key, str) for key in value):
        raise InputRejected(f"{name} must contain exactly {sorted(keys)}", code="invalid_commerce_request")
    return value


def _validate_skill_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 1_024:
        raise InputRejected("skill_path must be a non-empty relative UTF-8 path", code="invalid_commerce_request")
    if "\\" in value or value.startswith("/") or ":" in value:
        raise InputRejected("skill_path must use a relative POSIX path", code="invalid_commerce_request")
    path = PurePosixPath(value)
    parts = path.parts
    if value != path.as_posix() or not 1 <= len(parts) <= 32 or any(part in {"", ".", ".."} for part in parts):
        raise InputRejected("skill_path contains an unsupported segment or depth", code="invalid_commerce_request")
    if any(not _SKILL_SEGMENT.fullmatch(part) for part in parts):
        raise InputRejected(
            "skill_path segments must be 1-100 ASCII letters, digits, dot, underscore, or hyphen and start alphanumeric",
            code="invalid_commerce_request",
        )
    return path.as_posix()


def load_strict_commerce_json(text: str) -> Any:
    """Load JSON while rejecting duplicate keys at every nesting level."""

    def build_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise InputRejected(f"duplicate JSON key: {key}", code="invalid_commerce_request")
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=build_object)
    except json.JSONDecodeError as exc:
        raise InputRejected("commerce request must be valid JSON", code="invalid_commerce_request") from exc


def parse_fresh_validation_request(value: Any) -> dict[str, Any]:
    """Validate and normalize the only planned initial paid request profile."""

    request = _exact_object(
        value,
        {"schema_version", "operation", "source", "profile", "max_price", "delivery_id"},
        name="request",
    )
    if request["schema_version"] != "1.0.0":
        raise InputRejected("unsupported commerce request schema", code="invalid_commerce_request")
    if request["operation"] != "fresh_public_static_validation":
        raise InputRejected("unsupported paid operation", code="invalid_commerce_request")
    if request["profile"] != FRESH_VALIDATION_PROFILE:
        raise InputRejected("unsupported validation profile", code="invalid_commerce_request")

    source = _exact_object(
        request["source"], {"host", "owner", "repository", "commit", "skill_path"}, name="source"
    )
    if source["host"] != "github.com":
        raise InputRejected("source host is not allowlisted", code="unsupported_source_host")
    if not isinstance(source["owner"], str) or not _OWNER.fullmatch(source["owner"]):
        raise InputRejected("source owner is invalid", code="invalid_commerce_request")
    if not isinstance(source["repository"], str) or not _REPOSITORY.fullmatch(source["repository"]):
        raise InputRejected("source repository is invalid", code="invalid_commerce_request")
    if not isinstance(source["commit"], str) or not _COMMIT.fullmatch(source["commit"]):
        raise InputRejected("source commit must be a full lowercase Git SHA-1", code="mutable_source_reference")

    maximum = _exact_object(request["max_price"], {"currency", "amount_minor"}, name="max_price")
    if maximum["currency"] != FRESH_VALIDATION_CURRENCY:
        raise InputRejected("max_price currency must be usd", code="invalid_commerce_request")
    amount = maximum["amount_minor"]
    if isinstance(amount, bool) or not isinstance(amount, int) or not 0 <= amount <= 1_000_000:
        raise InputRejected("max_price amount_minor is invalid", code="invalid_commerce_request")
    if not isinstance(request["delivery_id"], str) or not _DELIVERY_ID.fullmatch(request["delivery_id"]):
        raise InputRejected("delivery_id must be an opaque 8-64 character identifier", code="invalid_commerce_request")

    return {
        "schema_version": "1.0.0",
        "operation": "fresh_public_static_validation",
        "source": {
            "host": "github.com",
            "owner": source["owner"],
            "repository": source["repository"],
            "commit": source["commit"],
            "skill_path": _validate_skill_path(source["skill_path"]),
        },
        "profile": FRESH_VALIDATION_PROFILE,
        "max_price": {"currency": FRESH_VALIDATION_CURRENCY, "amount_minor": amount},
        "delivery_id": request["delivery_id"],
    }


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_fresh_validation_quote(
    request_value: Any,
    *,
    generated_at: datetime | None = None,
    quote_id: str | None = None,
    legacy_stripe_adapter: bool = False,
) -> dict[str, Any]:
    """Build a precise non-orderable quote preview while live settlement remains disabled."""

    request = parse_fresh_validation_request(request_value)
    now = generated_at or datetime.now(timezone.utc)
    identifier = quote_id or f"q_{secrets.token_hex(12)}"
    if not _QUOTE_ID.fullmatch(identifier):
        raise ValueError("quote_id must match q_ followed by 24 lowercase hex characters")
    request_digest = hashlib.sha256(_canonical_bytes(request)).hexdigest()
    amount_minor = LEGACY_STRIPE_AMOUNT_MINOR if legacy_stripe_adapter else FRESH_VALIDATION_AMOUNT_MINOR
    within_maximum = request["max_price"]["amount_minor"] >= amount_minor
    if legacy_stripe_adapter:
        amount = "49.00"
        quote_status = "preview_account_and_worker_not_live"
        availability = "stage_b_worker_and_payment_activation_required"
        payment_options = [
            {"provider": "stripe_checkout", "status": "account_activation_required"},
            {"provider": "x402", "status": "secondary_not_enabled"},
        ]
        payment_gate = "activated payment account and verified webhook secret"
    else:
        amount = "0.25"
        quote_status = "preview_mainnet_not_live"
        availability = "stage_b_mainnet_activation_required"
        payment_options = [{"provider": "x402", "status": "mainnet_not_enabled"}]
        payment_gate = "exact x402 mainnet settlement and automated remedy controls"
    quote: dict[str, Any] = {
        "schema_version": "1.0.0",
        "service": "VouchSpec",
        "quote_id": identifier,
        "operation": "fresh_public_static_validation",
        "request_digest": f"sha256:{request_digest}",
        "currency": FRESH_VALIDATION_CURRENCY,
        "amount_minor": amount_minor,
        "amount": amount,
        "generated_at": _timestamp(now),
        "expires_at": _timestamp(now + timedelta(minutes=QUOTE_TTL_MINUTES)),
        "quote_status": quote_status if within_maximum else "declined_max_price",
        "availability": availability,
        "orderable": False,
        "settlement_available": False,
        "payment_options": payment_options,
        "deliverable": {
            "type": "signed_exact_version_static_receipt",
            "source": request["source"],
            "profile": FRESH_VALIDATION_PROFILE,
            "delivery_id": request["delivery_id"],
            "execution": "artifact_content_not_executed",
            "evidence_not_promised": ["universal_safety", "malware_free", "runtime_behavior", "publisher_identity"],
        },
        "hard_limits": {
            "artifact_total_bytes": 25_000_000,
            "files": 1_000,
            "individual_file_bytes": 2_000_000,
            "directory_depth": 32,
            "worker_wall_seconds": 60,
        },
        "refund_conditions": list(REFUND_CONDITIONS),
        "non_refund_condition": "an accurately reported structural or static finding is the purchased result",
        "live_gates": [
            "allowlisted immutable fetcher and isolated no-egress worker",
            "separate constrained signing service",
            payment_gate,
            "idempotent order store and provider reconciliation",
        ],
    }
    quote["quote_digest"] = f"sha256:{hashlib.sha256(_canonical_bytes(quote)).hexdigest()}"
    return quote


def require_transition(current: StrEnum, target: StrEnum) -> None:
    """Fail closed when an order or payment state transition is not explicitly allowed."""

    if isinstance(current, OrderStatus) and isinstance(target, OrderStatus):
        allowed = ORDER_TRANSITIONS[current]
    elif isinstance(current, PaymentStatus) and isinstance(target, PaymentStatus):
        allowed = PAYMENT_TRANSITIONS[current]
    else:
        raise ValueError("state types do not match")
    if target not in allowed:
        raise InputRejected(f"transition {current.value} -> {target.value} is not allowed", code="invalid_commerce_transition")


def verify_stripe_webhook_signature(
    raw_body: bytes,
    signature_header: str,
    secret: bytes,
    *,
    now: int,
    tolerance_seconds: int = 300,
) -> int:
    """Authenticate a Stripe webhook over its exact raw bytes and return its timestamp."""

    if not raw_body or not isinstance(signature_header, str) or not secret:
        raise InputRejected("webhook signature inputs are incomplete", code="invalid_webhook_signature")
    timestamp: int | None = None
    signatures: list[str] = []
    for item in signature_header.split(","):
        key, separator, value = item.strip().partition("=")
        if not separator:
            continue
        if key == "t" and timestamp is None:
            try:
                timestamp = int(value)
            except ValueError:
                pass
        elif key == "v1" and re.fullmatch(r"[0-9a-f]{64}", value):
            signatures.append(value)
    if timestamp is None or not signatures or abs(now - timestamp) > tolerance_seconds:
        raise InputRejected("webhook signature is missing, malformed, or stale", code="invalid_webhook_signature")
    expected = hmac.new(secret, str(timestamp).encode("ascii") + b"." + raw_body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise InputRejected("webhook signature did not verify", code="invalid_webhook_signature")
    return timestamp
