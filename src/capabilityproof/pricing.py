"""Machine-readable Stage A price hypotheses without order or payment intake."""

from __future__ import annotations

from typing import Any

from .errors import InputRejected


PRICE_HYPOTHESES: dict[str, dict[str, Any]] = {
    "catalog_search": {"amount_usd": "0.00", "availability": "stage_a_available_free"},
    "receipt_retrieval": {"amount_usd": "0.00", "availability": "stage_a_available_free"},
    "receipt_comparison": {"amount_usd": "0.01", "availability": "planned_not_orderable"},
    "fresh_public_static_validation": {"amount_usd": "0.25", "availability": "stage_b_not_orderable"},
    "signed_receipt_issuance": {"amount_usd": "0.25", "availability": "planned_not_orderable"},
    "public_artifact_monitoring_monthly": {"amount_usd": "5.00", "availability": "planned_not_orderable"},
}


def price_quote(operation: str) -> dict[str, Any]:
    if not isinstance(operation, str) or not 1 <= len(operation) <= 100:
        raise InputRejected("operation is required", code="invalid_query")
    try:
        price = PRICE_HYPOTHESES[operation]
    except KeyError as exc:
        raise InputRejected("operation is not in the public price card", code="unknown_operation") from exc
    available = price["availability"] == "stage_a_available_free"
    quote = {
        "schema_version": "1.0.0",
        "service": "VouchSpec",
        "operation": operation,
        "currency": "USD",
        "amount": price["amount_usd"],
        "amount_minor": int(price["amount_usd"].replace(".", "")),
        "availability": price["availability"],
        "orders_accepted": False,
        "settlement_available": False,
        "quote_status": "free_service" if available else "non_binding_price_hypothesis",
        "warning": "No paid order or payment is accepted by the Stage A retrieval service.",
    }
    if operation == "fresh_public_static_validation":
        quote.update(
            {
                "profile": "vouchspec-public-static-v1",
                "deliverable": "signed exact-version static receipt",
                "request_schema": "urn:vouchspec:schema:fresh-validation-request:1.0.0",
                "payment_provider_preference": "x402_exact_usdc",
                "refund_policy": "automatic for duplicate charge or VouchSpec failure before a signed receipt; an accurately reported finding is not refundable",
            }
        )
    return quote
