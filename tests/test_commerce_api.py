from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from http.client import HTTPConnection
import hashlib
import json
import socket
import threading

import pytest

from capabilityproof.commerce_access import CommerceAccessStore
from capabilityproof.commerce_api import CommerceApiLimits, create_commerce_server
from capabilityproof.commerce_store import CommerceStore, DIRECT_COST_CATEGORIES, FakePaymentProvider
from capabilityproof.cli import main
from capabilityproof.errors import InputRejected


AUTH_PEPPER = bytes.fromhex("31" * 32)
DELIVERY_SECRET = bytes.fromhex("42" * 32)
NOW = datetime(2026, 7, 14, 15, 0, tzinfo=timezone.utc)
REQUEST = {
    "schema_version": "1.0.0",
    "operation": "fresh_public_static_validation",
    "source": {
        "host": "github.com",
        "owner": "K-Dense-AI",
        "repository": "scientific-agent-skills",
        "commit": "a" * 40,
        "skill_path": "scientific_skills/example-skill",
    },
    "profile": "vouchspec-public-static-v1",
    "max_price": {"currency": "usd", "amount_minor": 4_900},
    "delivery_id": "delivery_machine_001",
}


@contextmanager
def _running_api(tmp_path, *, limits=None):
    path = tmp_path / "commerce.db"
    store = CommerceStore(path, environment="sandbox")
    access = CommerceAccessStore(
        path,
        environment="sandbox",
        auth_pepper=AUTH_PEPPER,
        delivery_secret=DELIVERY_SECRET,
    )
    first = access.provision_tenant(tenant_id="ten_" + "1" * 24)
    second = access.provision_tenant(tenant_id="ten_" + "2" * 24)
    server = create_commerce_server(
        store,
        access,
        0,
        limits=limits,
        now_source=lambda: NOW,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address, store, access, first, second
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class _StripeApiStub:
    mode = "test"
    live_checkout_enabled = False

    def __init__(self, store):
        self.store = store
        self.webhook_calls = []
        self.webhook_error = None

    def prepare_order_checkout(self, order_id, *, now):
        occurred_at = now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        order = self.store.attach_checkout(
            order_id,
            "cs_test_1234567890ABCDEFG",
            occurred_at=occurred_at,
        )
        return {
            "order": order,
            "checkout": {
                "provider": "stripe_checkout",
                "checkout_id": "cs_test_1234567890ABCDEFG",
                "url": "https://checkout.stripe.com/c/pay/cs_test_1234567890ABCDEFG",
                "expires_at": "2026-07-14T15:30:00Z",
                "livemode": False,
            },
        }

    def process_webhook(self, raw_body, signature_header):
        self.webhook_calls.append((raw_body, signature_header))
        if self.webhook_error is not None:
            raise self.webhook_error
        return {
            "event_id": "evt_1234567890ABCDEFG",
            "duplicate": False,
            "status": "processed",
            "order_id": None,
        }


@contextmanager
def _running_stripe_api(tmp_path, *, limits=None):
    path = tmp_path / "commerce.db"
    store = CommerceStore(path, environment="sandbox")
    access = CommerceAccessStore(
        path,
        environment="sandbox",
        auth_pepper=AUTH_PEPPER,
        delivery_secret=DELIVERY_SECRET,
    )
    credential = access.provision_tenant(tenant_id="ten_" + "3" * 24)
    adapter = _StripeApiStub(store)
    server = create_commerce_server(
        store,
        access,
        0,
        stripe_adapter=adapter,
        limits=limits,
        now_source=lambda: NOW,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address, store, access, credential, adapter
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _request(address, method, path, *, body=b"", headers=None):
    connection = HTTPConnection(*address, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    payload = response.read()
    response_headers = {name.lower(): value for name, value in response.getheaders()}
    status = response.status
    connection.close()
    return status, response_headers, payload


def _json_headers(api_key, *, idempotency=None, delivery_token=None):
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    if idempotency is not None:
        headers["Idempotency-Key"] = idempotency
    if delivery_token is not None:
        headers["X-VouchSpec-Delivery-Token"] = delivery_token
    return headers


def _post_json(address, path, value, headers):
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return _request(address, "POST", path, body=body, headers=headers)


def _create_order(address, credential, *, suffix="001"):
    status, _, body = _post_json(
        address,
        "/v1/commerce/quotes",
        REQUEST,
        _json_headers(credential["api_key"], idempotency=f"quote_attempt_{suffix}"),
    )
    assert status == 201
    quote = json.loads(body)["quote"]
    status, headers, body = _post_json(
        address,
        "/v1/commerce/orders",
        {"quote_id": quote["quote_id"]},
        _json_headers(credential["api_key"], idempotency=f"order_attempt_{suffix}"),
    )
    assert status == 201
    return quote, json.loads(body), headers


def test_authenticated_api_binds_tenant_quote_order_and_sanitizes_output(tmp_path) -> None:
    with _running_api(tmp_path) as (address, store, _, first, second):
        assert address[0] == "127.0.0.1"
        status, headers, body = _request(address, "GET", "/health")
        assert status == 200
        assert json.loads(body)["live_settlement"] is False
        assert "access-control-allow-origin" not in headers
        assert "no-store" in headers["cache-control"]

        raw = json.dumps(REQUEST).encode()
        status, headers, body = _request(
            address,
            "POST",
            "/v1/commerce/quotes",
            body=raw,
            headers={"Content-Type": "application/json", "Idempotency-Key": "quote_attempt_unauth"},
        )
        assert status == 401
        assert headers["www-authenticate"].startswith("Bearer")
        assert json.loads(body)["error"]["code"] == "authentication_failed"

        quote, created, headers = _create_order(address, first)
        assert quote["counts_for_goal"] is False
        assert created["payment"] == {"environment": "sandbox", "provider": "fake", "settles": False}
        assert created["order"]["settlement_status"] == "sandbox_nonsettling"
        assert "no-store" in headers["cache-control"]
        serialized = json.dumps(created)
        assert "buyer_reference" not in serialized
        assert "provider_payment_id" not in serialized
        assert "idempotency_key" not in serialized

        order_id = created["order"]["order_id"]
        token = created["delivery_token"]
        assert token.startswith("vsd_test_")
        assert created["delivery_token_expires_at"] == "2026-08-13T15:00:00Z"
        status, _, body = _request(
            address,
            "GET",
            f"/v1/commerce/orders/{order_id}",
            headers={
                "Authorization": "Bearer " + first["api_key"],
                "X-VouchSpec-Delivery-Token": token,
            },
        )
        assert status == 200
        assert json.loads(body)["order"]["order_id"] == order_id

        status, _, body = _request(
            address,
            "GET",
            f"/v1/commerce/orders/{order_id}",
            headers={
                "Authorization": "Bearer " + second["api_key"],
                "X-VouchSpec-Delivery-Token": token,
            },
        )
        assert status == 404
        assert json.loads(body)["error"] == {"code": "not_found", "message": "resource not found"}

        status, _, _ = _request(
            address,
            "GET",
            f"/v1/commerce/orders/{order_id}",
            headers={"Authorization": "Bearer " + first["api_key"]},
        )
        assert status == 404
        assert token.encode() not in store.path.read_bytes()

        repeated_quote, repeated, _ = _create_order(address, first)
        assert repeated_quote["quote_id"] == quote["quote_id"]
        assert repeated["order"]["order_id"] == order_id
        assert repeated["delivery_token"] == token

        _, second_created, _ = _create_order(address, second)
        assert second_created["order"]["order_id"] != order_id


def test_authenticated_stripe_test_checkout_and_exact_body_webhook_are_wired(tmp_path) -> None:
    limits = CommerceApiLimits(ip_requests_per_window=3)
    with _running_stripe_api(tmp_path, limits=limits) as (address, store, _, credential, adapter):
        status, _, body = _request(address, "GET", "/health")
        assert status == 200
        assert json.loads(body)["payment_provider"] == "stripe_test"

        quote, created, headers = _create_order(address, credential)
        assert quote["payment_options"] == [{"provider": "stripe_checkout", "status": "test_mode"}]
        assert created["payment"] == {
            "checkout_id": "cs_test_1234567890ABCDEFG",
            "environment": "test",
            "expires_at": "2026-07-14T15:30:00Z",
            "livemode": False,
            "provider": "stripe_checkout",
            "settles": False,
            "url": "https://checkout.stripe.com/c/pay/cs_test_1234567890ABCDEFG",
        }
        assert "no-store" in headers["cache-control"]
        assert b"checkout.stripe.com" not in store.path.read_bytes()

        raw_body = b'{ "opaque": [1, 2], "spacing": "preserved" }\n'
        status, _, body = _request(
            address,
            "POST",
            "/v1/commerce/webhooks/stripe",
            body=raw_body,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=123,v1=abcdef",
            },
        )
        assert status == 200
        assert json.loads(body) == {"duplicate": False, "received": True, "status": "processed"}
        assert adapter.webhook_calls == [(raw_body, "t=123,v1=abcdef")]
        assert b"opaque" not in store.path.read_bytes()


def test_stripe_webhook_rejects_missing_signature_and_retries_in_progress_event(tmp_path) -> None:
    with _running_stripe_api(tmp_path) as (address, _, _, _, adapter):
        raw_body = b'{"id":"evt_1234567890ABCDEFG"}'
        status, _, body = _request(
            address,
            "POST",
            "/v1/commerce/webhooks/stripe",
            body=raw_body,
            headers={"Content-Type": "application/json"},
        )
        assert status == 400
        assert json.loads(body)["error"]["code"] == "invalid_stripe_webhook"
        assert adapter.webhook_calls == []

        adapter.webhook_error = InputRejected(
            "reconciliation already running",
            code="stripe_event_processing",
        )
        status, headers, body = _request(
            address,
            "POST",
            "/v1/commerce/webhooks/stripe",
            body=raw_body,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=123,v1=abcdef",
            },
        )
        assert status == 503
        assert headers["retry-after"] == "10"
        assert json.loads(body)["error"]["code"] == "stripe_temporarily_unavailable"


def test_delivery_capability_rotation_and_revocation_take_effect_immediately(tmp_path) -> None:
    with _running_api(tmp_path) as (address, _, _, first, _):
        _, created, _ = _create_order(address, first)
        order_id = created["order"]["order_id"]
        old_token = created["delivery_token"]
        status, _, body = _post_json(
            address,
            f"/v1/commerce/orders/{order_id}/delivery-token/rotate",
            {},
            _json_headers(first["api_key"], delivery_token=old_token),
        )
        assert status == 200
        new_token = json.loads(body)["delivery_token"]
        assert new_token != old_token
        assert json.loads(body)["delivery_token_expires_at"] == "2026-08-13T15:00:00Z"

        for token, expected in ((old_token, 404), (new_token, 200)):
            status, _, _ = _request(
                address,
                "GET",
                f"/v1/commerce/orders/{order_id}",
                headers={
                    "Authorization": "Bearer " + first["api_key"],
                    "X-VouchSpec-Delivery-Token": token,
                },
            )
            assert status == expected

        status, _, body = _post_json(
            address,
            f"/v1/commerce/orders/{order_id}/delivery-token/revoke",
            {},
            _json_headers(first["api_key"], delivery_token=new_token),
        )
        assert status == 200
        assert json.loads(body)["delivery_token_status"] == "revoked"
        status, _, _ = _request(
            address,
            "GET",
            f"/v1/commerce/orders/{order_id}",
            headers={
                "Authorization": "Bearer " + first["api_key"],
                "X-VouchSpec-Delivery-Token": new_token,
            },
        )
        assert status == 404


def test_result_endpoint_returns_only_exact_digest_bound_signed_bytes(tmp_path) -> None:
    with _running_api(tmp_path) as (address, store, access, first, _):
        _, created, _ = _create_order(address, first)
        order_id = created["order"]["order_id"]
        token = created["delivery_token"]
        provider = FakePaymentProvider(store)
        provider.event(
            order_id,
            "payment.captured",
            occurred_at="2026-07-14T15:01:00Z",
            processing_fee_minor=172,
        )
        store.record_direct_costs(
            order_id,
            {category: 0 for category in DIRECT_COST_CATEGORIES},
            idempotency_key="cost_record_001",
            recorded_at="2026-07-14T15:02:00Z",
        )
        store.begin_fulfillment(
            order_id, source_reference="job_test_001", occurred_at="2026-07-14T15:03:00Z"
        )
        envelope = b'{"payload":"ZXhhY3Q=","payloadType":"application/test","signatures":[]}\n'
        digest = hashlib.sha256(envelope).hexdigest()
        store.deliver(
            order_id,
            receipt_id="cpr_" + "b" * 24,
            receipt_sha256="c" * 64,
            envelope_sha256=digest,
            signing_keyid="A" * 43,
            source_reference="job_test_001",
            occurred_at="2026-07-14T15:04:00Z",
        )
        access.publish_result(order_id, envelope)

        status, headers, body = _request(
            address,
            "GET",
            f"/v1/commerce/orders/{order_id}/result",
            headers={
                "Authorization": "Bearer " + first["api_key"],
                "X-VouchSpec-Delivery-Token": token,
            },
        )
        assert status == 200
        assert body == envelope
        assert headers["content-type"] == "application/vnd.dsse.envelope.v1+json"
        assert headers["etag"] == f'"sha256:{digest}"'


def test_request_framing_validation_and_rate_limits_fail_closed(tmp_path) -> None:
    with _running_api(tmp_path) as (address, _, _, first, _):
        status, _, body = _request(
            address,
            "POST",
            "/v1/commerce/quotes",
            body=b'{"x":1,"x":2}',
            headers=_json_headers(first["api_key"], idempotency="quote_attempt_badjson"),
        )
        assert status == 422
        assert json.loads(body)["error"]["code"] == "invalid_commerce_request"

        status, _, _ = _request(
            address,
            "POST",
            "/v1/commerce/quotes",
            body=b"{}",
            headers={
                "Authorization": "Bearer " + first["api_key"],
                "Content-Type": "text/plain",
                "Idempotency-Key": "quote_attempt_badtype",
            },
        )
        assert status == 422

        status, _, _ = _request(
            address,
            "POST",
            "/v1/commerce/quotes?token=forbidden",
            body=b"{}",
            headers=_json_headers(first["api_key"], idempotency="quote_attempt_query"),
        )
        assert status == 422

    limited = CommerceApiLimits(ip_requests_per_window=1)
    with _running_api(tmp_path / "limited", limits=limited) as (address, _, _, _, _):
        assert _request(address, "GET", "/health")[0] == 200
        status, headers, body = _request(address, "GET", "/health")
        assert status == 429
        assert headers["retry-after"] == str(limited.window_seconds)
        assert json.loads(body)["error"]["code"] == "rate_limited"


def test_duplicate_auth_headers_and_slow_bodies_do_not_cross_the_boundary(tmp_path) -> None:
    with _running_api(tmp_path) as (address, _, _, first, _):
        connection = HTTPConnection(*address, timeout=5)
        connection.putrequest("POST", "/v1/commerce/quotes")
        connection.putheader("Authorization", "Bearer " + first["api_key"])
        connection.putheader("Authorization", "Bearer " + first["api_key"])
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "2")
        connection.putheader("Idempotency-Key", "quote_attempt_duplicate_auth")
        connection.endheaders(b"{}")
        response = connection.getresponse()
        assert response.status == 401
        response.read()
        connection.close()

        connection = HTTPConnection(*address, timeout=5)
        connection.putrequest("POST", "/v1/commerce/quotes")
        connection.putheader("Authorization", "Bearer " + first["api_key"])
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "+2")
        connection.putheader("Idempotency-Key", "quote_attempt_noncanonical_length")
        connection.endheaders(b"{}")
        response = connection.getresponse()
        assert response.status == 422
        response.read()
        connection.close()

        stalled = socket.create_connection(address, timeout=2)
        try:
            stalled.sendall(
                (
                    "POST /v1/commerce/quotes HTTP/1.1\r\n"
                    f"Host: {address[0]}:{address[1]}\r\n"
                    f"Authorization: Bearer {first['api_key']}\r\n"
                    "Content-Type: application/json\r\n"
                    "Content-Length: 100\r\n"
                    "Idempotency-Key: quote_attempt_stalled\r\n\r\n"
                    "{"
                ).encode()
            )
            status, _, body = _request(address, "GET", "/health")
            assert status == 200
            assert json.loads(body)["status"] == "ok"
        finally:
            stalled.close()


def test_per_tenant_storage_quotas_bound_authenticated_database_growth(tmp_path) -> None:
    quote_limited = CommerceApiLimits(max_quotes_per_tenant=1)
    with _running_api(tmp_path / "quotes", limits=quote_limited) as (address, _, _, first, _):
        quote, created, _ = _create_order(address, first)
        repeated_quote, repeated, _ = _create_order(address, first)
        assert repeated_quote["quote_id"] == quote["quote_id"]
        assert repeated["order"]["order_id"] == created["order"]["order_id"]
        status, _, body = _post_json(
            address,
            "/v1/commerce/quotes",
            REQUEST,
            _json_headers(first["api_key"], idempotency="quote_attempt_002"),
        )
        assert status == 409
        assert json.loads(body)["error"]["code"] == "resource_limit"

    order_limited = CommerceApiLimits(max_quotes_per_tenant=2, max_orders_per_tenant=1)
    with _running_api(tmp_path / "orders", limits=order_limited) as (address, _, _, first, _):
        _create_order(address, first)
        status, _, body = _post_json(
            address,
            "/v1/commerce/quotes",
            REQUEST,
            _json_headers(first["api_key"], idempotency="quote_attempt_002"),
        )
        assert status == 201
        quote_id = json.loads(body)["quote"]["quote_id"]
        status, _, body = _post_json(
            address,
            "/v1/commerce/orders",
            {"quote_id": quote_id},
            _json_headers(first["api_key"], idempotency="order_attempt_002"),
        )
        assert status == 409
        assert json.loads(body)["error"]["code"] == "resource_limit"


def test_live_commerce_server_remains_unavailable(tmp_path) -> None:
    path = tmp_path / "live.db"
    store = CommerceStore(path, environment="live")
    access = CommerceAccessStore(
        path,
        environment="live",
        auth_pepper=AUTH_PEPPER,
        delivery_secret=DELIVERY_SECRET,
    )
    with pytest.raises(InputRejected) as error:
        create_commerce_server(store, access, 0)
    assert error.value.code == "commerce_live_not_enabled"


def test_cli_provisions_sandbox_key_from_secret_environment_without_persisting_it(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("VOUCHSPEC_AUTH_PEPPER_HEX", AUTH_PEPPER.hex())
    monkeypatch.setenv("VOUCHSPEC_DELIVERY_SECRET_HEX", DELIVERY_SECRET.hex())
    database = tmp_path / "commerce.db"
    assert main(
        [
            "provision-commerce-tenant",
            "--database",
            str(database),
            "--tenant-id",
            "ten_" + "9" * 24,
        ]
    ) == 0
    output = capsys.readouterr()
    credential = json.loads(output.out)
    assert "not persisted in plaintext" in output.err
    access = CommerceAccessStore(
        database,
        environment="sandbox",
        auth_pepper=AUTH_PEPPER,
        delivery_secret=DELIVERY_SECRET,
    )
    assert access.authenticate_api_key(credential["api_key"]) == credential["tenant_id"]
    assert credential["api_key"].encode() not in database.read_bytes()
