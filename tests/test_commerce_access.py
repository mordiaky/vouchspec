from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib

import pytest

from capabilityproof.commerce_access import CommerceAccessStore
from capabilityproof.commerce_store import CommerceStore, DIRECT_COST_CATEGORIES, FakePaymentProvider
from capabilityproof.errors import InputRejected


AUTH_PEPPER = bytes.fromhex("11" * 32)
DELIVERY_SECRET = bytes.fromhex("22" * 32)
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


def _stores(tmp_path):
    path = tmp_path / "commerce.db"
    commerce = CommerceStore(path, environment="sandbox")
    access = CommerceAccessStore(
        path,
        environment="sandbox",
        auth_pepper=AUTH_PEPPER,
        delivery_secret=DELIVERY_SECRET,
    )
    return commerce, access


def _bound_order(commerce, access, tenant_id, *, suffix="001"):
    idempotency = f"quote_attempt_{suffix}"
    quote_id = access.derive_quote_id(tenant_id, idempotency)
    quote = commerce.create_quote(REQUEST, quote_id=quote_id, generated_at=NOW)
    access.bind_quote(tenant_id, quote_id, idempotency_key=idempotency)
    order = commerce.create_order(
        quote_id,
        idempotency_key=f"order_attempt_{suffix}",
        buyer_reference=tenant_id,
        now=NOW + timedelta(minutes=1),
    )
    token = access.bind_order(
        tenant_id,
        order["order_id"],
        quote_id,
        created_at=(NOW + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
    )
    provider = FakePaymentProvider(commerce)
    order = provider.create_checkout(order["order_id"], occurred_at="2026-07-14T14:01:00Z")
    return order, token, provider


def test_api_keys_are_keyed_digests_and_support_rotation_and_revocation(tmp_path) -> None:
    commerce, access = _stores(tmp_path)
    credential = access.provision_tenant(tenant_id="ten_" + "1" * 24)
    assert access.authenticate_api_key(credential["api_key"]) == credential["tenant_id"]
    assert credential["api_key"].encode() not in commerce.path.read_bytes()

    replacement = access.rotate_api_key(credential["tenant_id"])
    assert replacement != credential["api_key"]
    with pytest.raises(InputRejected) as old:
        access.authenticate_api_key(credential["api_key"])
    assert old.value.code == "authentication_failed"
    assert access.authenticate_api_key(replacement) == credential["tenant_id"]

    access.revoke_tenant(credential["tenant_id"])
    with pytest.raises(InputRejected) as revoked:
        access.authenticate_api_key(replacement)
    assert revoked.value.code == "authentication_failed"


def test_access_secrets_are_bounded_distinct_and_environment_bound(tmp_path) -> None:
    path = tmp_path / "commerce.db"
    CommerceStore(path, environment="sandbox")
    with pytest.raises(ValueError, match="32 bytes"):
        CommerceAccessStore(
            path, environment="sandbox", auth_pepper=b"short", delivery_secret=DELIVERY_SECRET
        )
    with pytest.raises(ValueError, match="distinct"):
        CommerceAccessStore(
            path,
            environment="sandbox",
            auth_pepper=AUTH_PEPPER,
            delivery_secret=AUTH_PEPPER,
        )
    with pytest.raises(InputRejected) as mismatch:
        CommerceAccessStore(
            path,
            environment="live",
            auth_pepper=AUTH_PEPPER,
            delivery_secret=DELIVERY_SECRET,
        )
    assert mismatch.value.code == "commerce_environment_mismatch"
    access = CommerceAccessStore(
        path,
        environment="sandbox",
        auth_pepper=AUTH_PEPPER,
        delivery_secret=DELIVERY_SECRET,
    )
    assert access.environment == "sandbox"
    with pytest.raises(InputRejected) as wrong_secret:
        CommerceAccessStore(
            path,
            environment="sandbox",
            auth_pepper=bytes.fromhex("33" * 32),
            delivery_secret=DELIVERY_SECRET,
        )
    assert wrong_secret.value.code == "commerce_environment_mismatch"


def test_tenant_quote_and_order_bindings_hide_cross_tenant_objects(tmp_path) -> None:
    commerce, access = _stores(tmp_path)
    first = access.provision_tenant(tenant_id="ten_" + "1" * 24)
    second = access.provision_tenant(tenant_id="ten_" + "2" * 24)
    order, token, _ = _bound_order(commerce, access, first["tenant_id"])

    access.authorize_quote(first["tenant_id"], order["quote_id"])
    access.authorize_order(first["tenant_id"], order["order_id"], token)
    with pytest.raises(InputRejected) as quote_error:
        access.authorize_quote(second["tenant_id"], order["quote_id"])
    assert quote_error.value.code == "authorization_failed"
    with pytest.raises(InputRejected) as order_error:
        access.authorize_order(second["tenant_id"], order["order_id"], token)
    assert order_error.value.code == "authorization_failed"
    with pytest.raises(InputRejected) as expired:
        access.authorize_order(
            first["tenant_id"], order["order_id"], token, now=NOW + timedelta(days=31)
        )
    assert expired.value.code == "authorization_failed"

    rotated = access.rotate_delivery_token(first["tenant_id"], order["order_id"], token)
    assert rotated != token
    with pytest.raises(InputRejected):
        access.authorize_order(first["tenant_id"], order["order_id"], token)
    access.authorize_order(first["tenant_id"], order["order_id"], rotated)
    access.revoke_delivery_token(first["tenant_id"], order["order_id"], rotated)
    with pytest.raises(InputRejected):
        access.authorize_order(first["tenant_id"], order["order_id"], rotated)
    assert [event["event_type"] for event in access.audit_events(order_id=order["order_id"])] == [
        "order.bound",
        "delivery_token.rotated",
        "delivery_token.revoked",
    ]


def test_signed_result_bytes_are_digest_bound_immutable_and_capability_guarded(tmp_path) -> None:
    commerce, access = _stores(tmp_path)
    tenant = access.provision_tenant(tenant_id="ten_" + "1" * 24)
    order, token, provider = _bound_order(commerce, access, tenant["tenant_id"])

    provider.event(
        order["order_id"],
        "payment.captured",
        occurred_at="2026-07-14T14:02:00Z",
        processing_fee_minor=172,
    )
    commerce.record_direct_costs(
        order["order_id"],
        {category: 0 for category in DIRECT_COST_CATEGORIES},
        idempotency_key="cost_record_001",
        recorded_at="2026-07-14T14:03:00Z",
    )
    commerce.begin_fulfillment(
        order["order_id"], source_reference="job_test_001", occurred_at="2026-07-14T14:04:00Z"
    )
    envelope = b'{"payload":"ZXhhY3Q=","payloadType":"application/test","signatures":[]}\n'
    envelope_digest = hashlib.sha256(envelope).hexdigest()
    commerce.deliver(
        order["order_id"],
        receipt_id="cpr_" + "b" * 24,
        receipt_sha256="c" * 64,
        envelope_sha256=envelope_digest,
        signing_keyid="A" * 43,
        source_reference="job_test_001",
        occurred_at="2026-07-14T14:05:00Z",
    )

    assert access.publish_result(order["order_id"], envelope) == envelope_digest
    assert access.publish_result(order["order_id"], envelope) == envelope_digest
    assert access.get_result(tenant["tenant_id"], order["order_id"], token) == envelope
    with pytest.raises(InputRejected) as mismatch:
        access.publish_result(order["order_id"], envelope + b" ")
    assert mismatch.value.code == "invalid_delivery"
    with pytest.raises(InputRejected):
        access.get_result(tenant["tenant_id"], order["order_id"], "vsd_test_" + "A" * 43)
    assert [event["event_type"] for event in access.audit_events(order_id=order["order_id"])] == [
        "order.bound",
        "result.published",
    ]
