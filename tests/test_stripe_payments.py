from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import sqlite3
from types import SimpleNamespace

import pytest

from capabilityproof.commerce_store import CommerceStore
from capabilityproof.errors import InputRejected
from capabilityproof.stripe_payments import STRIPE_API_VERSION, StripePaymentAdapter


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=timezone.utc)
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
API_KEY = "sk_test_" + "A" * 40
WEBHOOK_SECRET = "whsec_" + "B" * 40
ACCOUNT_ID = "acct_1234567890ABCDEFG"
ACCOUNT = {
    "id": ACCOUNT_ID,
    "object": "account",
    "charges_enabled": True,
    "payouts_enabled": True,
    "details_submitted": True,
}
CHECKOUT_ID = "cs_test_1234567890ABCDEFG"
PAYMENT_ID = "pi_1234567890ABCDEFG"
CHARGE_ID = "ch_1234567890ABCDEFG"
BALANCE_ID = "txn_1234567890ABCDEFG"


class _Endpoint:
    def __init__(self, values: dict[str, dict], *, create_value: dict | None = None) -> None:
        self.values = values
        self.create_value = create_value
        self.create_calls: list[tuple[dict, dict]] = []
        self.retrieve_calls: list[str] = []

    def create(self, params: dict, options: dict) -> dict:
        self.create_calls.append((deepcopy(params), deepcopy(options)))
        assert self.create_value is not None
        return deepcopy(self.create_value)

    def retrieve(self, identifier: str) -> dict:
        self.retrieve_calls.append(identifier)
        return deepcopy(self.values[identifier])


class _FakeStripeClient:
    def __init__(self, *, expires_at: int) -> None:
        self.session = {
            "id": CHECKOUT_ID,
            "object": "checkout.session",
            "livemode": False,
            "mode": "payment",
            "currency": "usd",
            "amount_total": 4_900,
            "client_reference_id": "ord_test_placeholder",
            "metadata": {},
            "status": "open",
            "payment_status": "unpaid",
            "payment_intent": None,
            "expires_at": expires_at,
            "url": "https://checkout.stripe.com/c/pay/cs_test_1234567890ABCDEFG",
        }
        self.payment = {
            "id": PAYMENT_ID,
            "object": "payment_intent",
            "livemode": False,
            "currency": "usd",
            "amount": 4_900,
            "amount_received": 4_900,
            "metadata": {},
            "status": "succeeded",
            "latest_charge": CHARGE_ID,
            "created": int((NOW + timedelta(minutes=1)).timestamp()),
        }
        self.charge = {
            "id": CHARGE_ID,
            "object": "charge",
            "livemode": False,
            "payment_intent": PAYMENT_ID,
            "currency": "usd",
            "amount": 4_900,
            "amount_captured": 4_900,
            "amount_refunded": 0,
            "paid": True,
            "captured": True,
            "disputed": False,
            "balance_transaction": BALANCE_ID,
            "created": int((NOW + timedelta(minutes=1)).timestamp()),
        }
        self.balance = {
            "id": BALANCE_ID,
            "object": "balance_transaction",
            "source": CHARGE_ID,
            "currency": "usd",
            "amount": 4_900,
            "fee": 172,
            "net": 4_728,
            "status": "pending",
            "created": int((NOW + timedelta(minutes=1)).timestamp()),
            "available_on": int((NOW + timedelta(days=2)).timestamp()),
        }
        self.disputes: dict[str, dict] = {
            "dp_1234567890ABCDEFG": {
                "id": "dp_1234567890ABCDEFG",
                "object": "dispute",
                "charge": CHARGE_ID,
            }
        }
        self.checkout_endpoint = _Endpoint({CHECKOUT_ID: self.session}, create_value=self.session)
        self.payment_endpoint = _Endpoint({PAYMENT_ID: self.payment})
        self.charge_endpoint = _Endpoint({CHARGE_ID: self.charge})
        self.balance_endpoint = _Endpoint({BALANCE_ID: self.balance})
        self.dispute_endpoint = _Endpoint(self.disputes)
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=self.checkout_endpoint),
            payment_intents=self.payment_endpoint,
            charges=self.charge_endpoint,
            balance_transactions=self.balance_endpoint,
            disputes=self.dispute_endpoint,
        )

    def bind_order(self, order_id: str, quote_id: str) -> None:
        metadata = {
            "vouchspec_order_id": order_id,
            "vouchspec_quote_id": quote_id,
            "vouchspec_account_id": ACCOUNT_ID,
        }
        self.session.update({"client_reference_id": order_id, "metadata": metadata})
        self.payment["metadata"] = metadata
        self.checkout_endpoint.values[CHECKOUT_ID] = self.session
        self.checkout_endpoint.create_value = self.session

    def complete(self, *, available: bool = False) -> None:
        self.session.update(
            {"status": "complete", "payment_status": "paid", "payment_intent": PAYMENT_ID}
        )
        self.checkout_endpoint.values[CHECKOUT_ID] = self.session
        self.payment_endpoint.values[PAYMENT_ID] = self.payment
        self.charge_endpoint.values[CHARGE_ID] = self.charge
        if available:
            self.balance.update(
                {
                    "status": "available",
                    "available_on": int((NOW + timedelta(minutes=2)).timestamp()),
                }
            )
        self.balance_endpoint.values[BALANCE_ID] = self.balance


def _adapter(tmp_path):
    store = CommerceStore(tmp_path / "commerce.db", environment="sandbox")
    client = _FakeStripeClient(expires_at=int((NOW + timedelta(minutes=30)).timestamp()))
    adapter = StripePaymentAdapter(
        store,
        mode="test",
        api_key=API_KEY,
        webhook_secret=WEBHOOK_SECRET,
        expected_account_id=ACCOUNT_ID,
        success_url="https://vouchspec.example/complete?session={CHECKOUT_SESSION_ID}",
        cancel_url="https://vouchspec.example/cancel",
        client=client,
        account=ACCOUNT,
    )
    quote_id = "q_0123456789abcdef01234567"
    predicted_order_id = "ord_test_" + hashlib.sha256(
        f"{quote_id}\0stripe_order_001\0buyer_test_001".encode("utf-8")
    ).hexdigest()[:24]
    client.bind_order(predicted_order_id, quote_id)
    checkout = adapter.prepare_checkout(
        REQUEST,
        quote_id=quote_id,
        idempotency_key="stripe_order_001",
        buyer_reference="buyer_test_001",
        now=NOW,
    )
    return store, client, adapter, checkout


def _event_body(event_id: str = "evt_1234567890ABCDEFG", event_type: str = "checkout.session.completed") -> bytes:
    value = {
        "id": event_id,
        "object": "event",
        "api_version": STRIPE_API_VERSION,
        "created": int(datetime.now(timezone.utc).timestamp()),
        "data": {"object": {"id": CHECKOUT_ID, "object": "checkout.session"}},
        "livemode": False,
        "pending_webhooks": 1,
        "request": {"id": None, "idempotency_key": None},
        "type": event_type,
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _signature(body: bytes, *, timestamp: int | None = None) -> str:
    observed = timestamp or int(datetime.now(timezone.utc).timestamp())
    digest = hmac.new(
        WEBHOOK_SECRET.encode(),
        str(observed).encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={observed},v1={digest}"


def test_configuration_fails_closed_for_mode_and_live_activation(tmp_path) -> None:
    sandbox = CommerceStore(tmp_path / "sandbox.db", environment="sandbox")
    with pytest.raises(ValueError, match="mode"):
        StripePaymentAdapter(
            sandbox,
            mode="live",
            api_key="sk_live_" + "A" * 40,
            webhook_secret=WEBHOOK_SECRET,
            expected_account_id=ACCOUNT_ID,
            success_url="https://example.test/s?session={CHECKOUT_SESSION_ID}",
            cancel_url="https://example.test/c",
            live_checkout_enabled=True,
        )
    live = CommerceStore(tmp_path / "live.db", environment="live")
    with pytest.raises(ValueError, match="activation"):
        StripePaymentAdapter(
            live,
            mode="live",
            api_key="sk_live_" + "A" * 40,
            webhook_secret=WEBHOOK_SECRET,
            expected_account_id=ACCOUNT_ID,
            success_url="https://example.test/s?session={CHECKOUT_SESSION_ID}",
            cancel_url="https://example.test/c",
        )

    account_store = CommerceStore(tmp_path / "account.db", environment="sandbox")
    client = _FakeStripeClient(expires_at=int((NOW + timedelta(minutes=30)).timestamp()))
    with pytest.raises(InputRejected) as mismatch:
        StripePaymentAdapter(
            account_store,
            mode="test",
            api_key=API_KEY,
            webhook_secret=WEBHOOK_SECRET,
            expected_account_id="acct_DIFFERENT12345678",
            success_url="https://example.test/s?session={CHECKOUT_SESSION_ID}",
            cancel_url="https://example.test/c",
            client=client,
            account=ACCOUNT,
        )
    assert mismatch.value.code == "stripe_account_mismatch"


def test_prepare_checkout_is_exact_idempotent_and_does_not_persist_secrets_or_url(tmp_path) -> None:
    store, client, adapter, checkout = _adapter(tmp_path)
    order = checkout["order"]
    assert order["provider"] == "stripe"
    assert order["provider_checkout_id"] == CHECKOUT_ID
    assert order["provider_payment_id"] is None
    assert order["counts_for_goal"] is False
    params, options = client.checkout_endpoint.create_calls[0]
    assert params["line_items"][0]["price_data"]["unit_amount"] == 4_900
    assert params["expires_at"] == int((NOW + timedelta(minutes=30)).timestamp())
    assert params["payment_method_types"] == ["card"]
    assert params["metadata"]["vouchspec_account_id"] == ACCOUNT_ID
    assert options["idempotency_key"].startswith("vouchspec_")
    assert checkout["checkout"]["url"].startswith("https://checkout.stripe.com/")

    duplicate = adapter.prepare_checkout(
        REQUEST,
        quote_id=order["quote_id"],
        idempotency_key="stripe_order_001",
        buyer_reference="buyer_test_001",
        now=NOW,
    )
    assert duplicate["order"]["order_id"] == order["order_id"]
    assert len(client.checkout_endpoint.create_calls) == 1
    database = (tmp_path / "commerce.db").read_bytes()
    assert API_KEY.encode() not in database
    assert WEBHOOK_SECRET.encode() not in database
    assert checkout["checkout"]["url"].encode() not in database
    assert store.get_quote(order["quote_id"])["payment_options"] == [
        {"provider": "stripe_checkout", "status": "test_mode"}
    ]


def test_server_retrieval_reconciles_captured_then_available_funds(tmp_path) -> None:
    store, client, adapter, checkout = _adapter(tmp_path)
    client.complete()
    captured = adapter.reconcile_order(
        checkout["order"]["order_id"], observed_at=NOW + timedelta(minutes=2)
    )
    assert captured["state"] == "pending"
    assert captured["order"]["payment_status"] == "captured"
    assert captured["order"]["processing_fee_minor"] == 172
    assert captured["order"]["gross_contribution_minor"] == 4_728
    assert captured["order"]["counts_for_goal"] is False

    client.complete(available=True)
    available = adapter.reconcile_order(
        checkout["order"]["order_id"], observed_at=NOW + timedelta(minutes=3)
    )
    assert available["state"] == "available"
    assert available["order"]["payment_status"] == "available"
    assert available["order"]["settlement_status"] == "sandbox_nonsettling"
    assert store.get_financial_summary()["counts_for_goal_collected_minor"] == 0


def test_signed_webhook_is_deduplicated_and_raw_body_is_not_persisted(tmp_path) -> None:
    _, client, adapter, checkout = _adapter(tmp_path)
    client.complete(available=True)
    body = _event_body()
    signature = _signature(body)
    result = adapter.process_webhook(body, signature)
    assert result == {
        "event_id": "evt_1234567890ABCDEFG",
        "duplicate": False,
        "status": "processed",
        "order_id": checkout["order"]["order_id"],
        "payment_status": "available",
    }
    calls = len(client.checkout_endpoint.retrieve_calls)
    duplicate = adapter.process_webhook(body, signature)
    assert duplicate["duplicate"] is True
    assert duplicate["status"] == "processed"
    assert len(client.checkout_endpoint.retrieve_calls) == calls
    assert adapter.audit_events()[0]["status"] == "processed"
    assert body not in (tmp_path / "commerce.db").read_bytes()

    with pytest.raises(InputRejected) as error:
        adapter.process_webhook(body + b" ", signature)
    assert error.value.code == "invalid_webhook_signature"


def test_webhook_processing_lease_retries_crash_orphan_without_parallel_reconciliation(tmp_path) -> None:
    _, _, adapter, _ = _adapter(tmp_path)
    event_id = "evt_PROCESSING12345678"
    digest = "a" * 64
    received = "2026-07-14T14:00:00Z"
    reservation = adapter._reserve_webhook(
        event_id,
        digest,
        "checkout.session.completed",
        CHECKOUT_ID,
        STRIPE_API_VERSION,
        received,
    )
    assert reservation["duplicate"] is False
    with pytest.raises(InputRejected) as active:
        adapter._reserve_webhook(
            event_id,
            digest,
            "checkout.session.completed",
            CHECKOUT_ID,
            STRIPE_API_VERSION,
            received,
        )
    assert active.value.code == "stripe_event_processing"

    with sqlite3.connect(tmp_path / "commerce.db") as connection:
        connection.execute(
            "UPDATE stripe_webhook_events SET updated_at = '2026-07-14T13:00:00Z' WHERE event_id = ?",
            (event_id,),
        )
        connection.commit()
    recovered = adapter._reserve_webhook(
        event_id,
        digest,
        "checkout.session.completed",
        CHECKOUT_ID,
        STRIPE_API_VERSION,
        received,
    )
    assert recovered["duplicate"] is False


def test_webhook_rejects_wrong_api_version_and_conflicting_event_id(tmp_path) -> None:
    _, client, adapter, _ = _adapter(tmp_path)
    client.complete()
    body = _event_body()
    adapter.process_webhook(body, _signature(body))
    conflicting = json.loads(body)
    conflicting["created"] += 1
    conflicting_body = json.dumps(conflicting, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(InputRejected) as conflict:
        adapter.process_webhook(conflicting_body, _signature(conflicting_body))
    assert conflict.value.code == "stripe_event_conflict"

    wrong = json.loads(_event_body("evt_ABCDEFGH12345678"))
    wrong["api_version"] = "2026-02-25.clover"
    wrong_body = json.dumps(wrong, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(InputRejected) as version:
        adapter.process_webhook(wrong_body, _signature(wrong_body))
    assert version.value.code == "invalid_stripe_event"


def test_cross_binding_partial_refund_and_future_availability_fail_closed(tmp_path) -> None:
    _, client, adapter, checkout = _adapter(tmp_path)
    client.complete()
    client.payment["metadata"] = {
        "vouchspec_order_id": "ord_test_" + "f" * 24,
        "vouchspec_quote_id": checkout["order"]["quote_id"],
    }
    client.payment_endpoint.values[PAYMENT_ID] = client.payment
    with pytest.raises(InputRejected) as binding:
        adapter.reconcile_order(checkout["order"]["order_id"])
    assert binding.value.code == "invalid_stripe_object"

    client.bind_order(checkout["order"]["order_id"], checkout["order"]["quote_id"])
    client.payment_endpoint.values[PAYMENT_ID] = client.payment
    client.charge["amount_refunded"] = 1_000
    client.charge_endpoint.values[CHARGE_ID] = client.charge
    with pytest.raises(InputRejected) as partial:
        adapter.reconcile_order(checkout["order"]["order_id"])
    assert partial.value.code == "stripe_partial_refund"

    client.charge["amount_refunded"] = 0
    client.charge_endpoint.values[CHARGE_ID] = client.charge
    client.balance["status"] = "available"
    client.balance["available_on"] = int((NOW + timedelta(days=2)).timestamp())
    client.balance_endpoint.values[BALANCE_ID] = client.balance
    with pytest.raises(InputRejected, match="future"):
        adapter.reconcile_order(
            checkout["order"]["order_id"], observed_at=NOW + timedelta(minutes=5)
        )


def test_full_refund_and_dispute_are_terminal_negative_or_nonsettled_states(tmp_path) -> None:
    _, client, adapter, checkout = _adapter(tmp_path)
    client.complete(available=True)
    adapter.reconcile_order(
        checkout["order"]["order_id"], observed_at=NOW + timedelta(minutes=3)
    )
    client.charge["amount_refunded"] = 4_900
    client.charge_endpoint.values[CHARGE_ID] = client.charge
    refunded = adapter.reconcile_order(
        checkout["order"]["order_id"], observed_at=NOW + timedelta(minutes=4)
    )["order"]
    assert refunded["payment_status"] == "refunded"
    assert refunded["gross_contribution_minor"] == -172
    assert refunded["counts_for_goal"] is False

    other_path = tmp_path / "other"
    other_path.mkdir()
    _, other_client, other_adapter, other_checkout = _adapter(other_path)
    other_client.complete(available=True)
    other_client.charge["disputed"] = True
    other_client.charge_endpoint.values[CHARGE_ID] = other_client.charge
    disputed = other_adapter.reconcile_order(
        other_checkout["order"]["order_id"], observed_at=NOW + timedelta(minutes=3)
    )["order"]
    assert disputed["payment_status"] == "disputed"
    assert disputed["settlement_status"] == "sandbox_nonsettling"


def test_schema_v2_database_migrates_without_rebinding_environment(tmp_path) -> None:
    path = tmp_path / "commerce.db"
    store = CommerceStore(path, environment="sandbox")
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE metadata SET value = '2' WHERE key = 'schema_version'")
        connection.commit()
    reopened = CommerceStore(path, environment="sandbox")
    assert reopened.environment == store.environment
    with sqlite3.connect(path) as connection:
        assert dict(connection.execute("SELECT key, value FROM metadata"))["schema_version"] == "3"
