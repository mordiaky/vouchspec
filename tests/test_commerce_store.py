from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from capabilityproof.commerce_store import (
    CommerceStore,
    DIRECT_COST_CATEGORIES,
    FakePaymentProvider,
)
from capabilityproof.errors import InputRejected


REQUEST = {
    "schema_version": "1.0.0",
    "operation": "fresh_public_static_validation",
    "source": {
        "host": "github.com",
        "owner": "supabase",
        "repository": "agent-skills",
        "commit": "a" * 40,
        "skill_path": "skills/postgres-best-practices",
    },
    "profile": "vouchspec-public-static-v1",
    "max_price": {"currency": "usd", "amount_minor": 4_900},
    "delivery_id": "delivery_1234",
}
NOW = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)


def _create_checkout(tmp_path, *, quote_id: str = "q_0123456789abcdef01234567"):
    store = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    quote = store.create_quote(REQUEST, quote_id=quote_id, generated_at=NOW)
    order = store.create_order(
        quote["quote_id"],
        idempotency_key="order_attempt_001",
        buyer_reference="buyer_test_001",
        now=NOW + timedelta(minutes=1),
    )
    provider = FakePaymentProvider(store)
    order = provider.create_checkout(order["order_id"], occurred_at="2026-07-14T12:01:00Z")
    return store, provider, order


def test_store_is_persistently_bound_to_one_environment(tmp_path) -> None:
    path = tmp_path / "commerce.db"
    CommerceStore(path, environment="sandbox")
    CommerceStore(path, environment="sandbox")
    with pytest.raises(InputRejected) as error:
        CommerceStore(path, environment="live")
    assert error.value.code == "commerce_environment_mismatch"


def test_live_store_cannot_create_orderable_quote_or_fake_provider(tmp_path) -> None:
    store = CommerceStore(tmp_path / "live.db", environment="live")
    with pytest.raises(InputRejected) as error:
        store.create_quote(REQUEST, quote_id="q_0123456789abcdef01234567", generated_at=NOW)
    assert error.value.code == "commerce_live_not_enabled"
    with pytest.raises(ValueError):
        FakePaymentProvider(store)


def test_quote_and_order_are_immutable_and_idempotent(tmp_path) -> None:
    store = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    quote = store.create_quote(REQUEST, quote_id="q_0123456789abcdef01234567", generated_at=NOW)
    assert quote["orderable"] is True
    assert quote["settlement_available"] is False
    assert quote["counts_for_goal"] is False
    assert store.create_quote(REQUEST, quote_id=quote["quote_id"], generated_at=NOW) == quote

    order = store.create_order(
        quote["quote_id"],
        idempotency_key="order_attempt_001",
        buyer_reference="buyer_test_001",
        now=NOW + timedelta(minutes=1),
    )
    duplicate = store.create_order(
        quote["quote_id"],
        idempotency_key="order_attempt_001",
        buyer_reference="buyer_test_001",
        now=NOW + timedelta(minutes=2),
    )
    assert duplicate["order_id"] == order["order_id"]
    assert duplicate["counts_for_goal"] is False
    with pytest.raises(InputRejected) as error:
        store.create_order(
            quote["quote_id"],
            idempotency_key="order_attempt_001",
            buyer_reference="buyer_changed_002",
            now=NOW + timedelta(minutes=2),
        )
    assert error.value.code == "idempotency_conflict"


def test_expired_quote_cannot_be_ordered(tmp_path) -> None:
    store = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    quote = store.create_quote(REQUEST, quote_id="q_0123456789abcdef01234567", generated_at=NOW)
    with pytest.raises(InputRejected) as error:
        store.create_order(
            quote["quote_id"],
            idempotency_key="order_attempt_001",
            buyer_reference="buyer_test_001",
            now=NOW + timedelta(minutes=16),
        )
    assert error.value.code == "quote_expired"
    with pytest.raises(InputRejected, match="timezone"):
        store.create_order(
            quote["quote_id"],
            idempotency_key="order_attempt_002",
            buyer_reference="buyer_test_002",
            now=datetime(2026, 7, 14, 12, 1),
        )


def test_out_of_order_events_reconcile_and_duplicate_delivery_is_idempotent(tmp_path) -> None:
    store, provider, order = _create_checkout(tmp_path)
    available = provider.event(
        order["order_id"], "payment.available", occurred_at="2026-07-14T12:03:00Z"
    )
    assert available["event_status"] == "pending"
    assert available["order"]["payment_status"] == "pending"

    captured = provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T12:02:00Z",
        processing_fee_minor=172,
    )
    assert captured["event_status"] == "applied"
    assert captured["order"]["payment_status"] == "available"
    assert captured["order"]["order_status"] == "queued"
    assert captured["order"]["pending_provider_events"] == []
    assert captured["order"]["collected_amount_minor"] == 4_900
    assert captured["order"]["processing_fee_minor"] == 172

    duplicate = provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T12:02:00Z",
        processing_fee_minor=172,
    )
    assert duplicate["duplicate"] is True

    costs = {category: 0 for category in DIRECT_COST_CATEGORIES}
    costs.update({"compute": 7, "third_party": 3, "signing": 1, "monitoring": 2})
    costed = store.record_direct_costs(
        order["order_id"], costs, idempotency_key="cost_record_001",
        recorded_at="2026-07-14T12:04:00Z",
    )
    assert costed["direct_costs_recorded"] is True
    assert costed["gross_contribution_minor"] == 4_900 - 172 - 13
    running = store.begin_fulfillment(
        order["order_id"], source_reference="job_test_001", occurred_at="2026-07-14T12:05:00Z"
    )
    assert running["delivery_status"] == "running"
    delivered = store.deliver(
        order["order_id"],
        receipt_id="cpr_" + "b" * 24,
        receipt_sha256="c" * 64,
        envelope_sha256="d" * 64,
        signing_keyid="A" * 43,
        source_reference="job_test_001",
        occurred_at="2026-07-14T12:06:00Z",
    )
    assert delivered["order_status"] == "delivered"
    assert store.deliver(
        order["order_id"],
        receipt_id="cpr_" + "b" * 24,
        receipt_sha256="c" * 64,
        envelope_sha256="d" * 64,
        signing_keyid="A" * 43,
        source_reference="job_test_001",
        occurred_at="2026-07-14T12:06:00Z",
    ) == delivered
    summary = store.get_financial_summary()
    assert summary["ledger_contribution_minor"] == 4_715
    assert summary["counts_for_goal_contribution_minor"] == 0
    assert summary["counts_for_goal_collected_minor"] == 0


def test_provider_event_identifier_conflicts_are_rejected(tmp_path) -> None:
    store, provider, order = _create_checkout(tmp_path)
    applied = provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T12:02:00Z",
        processing_fee_minor=172,
    )
    payment_id = applied["order"]["provider_payment_id"]
    event_id = FakePaymentProvider._event_id(payment_id, "payment.captured")
    conflicting = {
        "schema_version": "1.0.0",
        "provider": "fake",
        "environment": "sandbox",
        "event_id": event_id,
        "type": "payment.captured",
        "payment_id": payment_id,
        "amount_minor": 4_900,
        "fee_minor": 171,
        "currency": "usd",
        "occurred_at": "2026-07-14T12:02:00Z",
    }
    with pytest.raises(InputRejected) as error:
        store.ingest_provider_event(conflicting)
    assert error.value.code == "provider_event_conflict"


def test_delivery_requires_explicit_complete_cost_record(tmp_path) -> None:
    store, provider, order = _create_checkout(tmp_path)
    provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T12:02:00Z",
        processing_fee_minor=172,
    )
    store.begin_fulfillment(
        order["order_id"], source_reference="job_test_001", occurred_at="2026-07-14T12:03:00Z"
    )
    with pytest.raises(InputRejected) as error:
        store.deliver(
            order["order_id"],
            receipt_id="cpr_" + "b" * 24,
            receipt_sha256="c" * 64,
            envelope_sha256="d" * 64,
            signing_keyid="A" * 43,
            source_reference="job_test_001",
            occurred_at="2026-07-14T12:04:00Z",
        )
    assert error.value.code == "cost_record_required"
    with pytest.raises(InputRejected) as cost_error:
        store.record_direct_costs(
            order["order_id"], {"compute": 1}, idempotency_key="cost_record_001"
        )
    assert cost_error.value.code == "invalid_cost_record"


def test_refunds_have_a_separate_payment_state_and_negative_ledger_impact(tmp_path) -> None:
    store, provider, order = _create_checkout(tmp_path)
    provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T12:02:00Z",
        processing_fee_minor=172,
    )
    provider.event(order["order_id"], "payment.available", occurred_at="2026-07-14T12:03:00Z")
    provider.event(order["order_id"], "payment.refund_pending", occurred_at="2026-07-14T12:04:00Z")
    refunded = provider.event(
        order["order_id"], "payment.refunded", occurred_at="2026-07-14T12:05:00Z"
    )["order"]
    assert refunded["payment_status"] == "refunded"
    assert refunded["refunded_amount_minor"] == 4_900
    assert refunded["refund_status"] == "refunded"
    assert refunded["gross_contribution_minor"] == -172
    assert store.get_financial_summary()["counts_for_goal_collected_minor"] == 0


def test_database_records_remain_machine_readable_after_reopen(tmp_path) -> None:
    store, provider, order = _create_checkout(tmp_path)
    provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T12:02:00Z",
        processing_fee_minor=172,
    )
    reopened = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    serialized = json.dumps(reopened.get_order(order["order_id"]), sort_keys=True)
    assert json.loads(serialized)["collected_amount_minor"] == 4_900
