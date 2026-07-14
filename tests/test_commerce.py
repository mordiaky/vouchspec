from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
from importlib.resources import files

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from capabilityproof.commerce import (
    OrderStatus,
    PaymentStatus,
    REFUND_CONDITIONS,
    build_fresh_validation_quote,
    load_strict_commerce_json,
    parse_fresh_validation_request,
    require_transition,
    verify_stripe_webhook_signature,
)
from capabilityproof.cli import main
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


def _schema(name: str) -> dict:
    return json.loads(files("capabilityproof").joinpath(f"schemas/{name}").read_text(encoding="utf-8"))


def test_fresh_validation_request_and_quote_are_strict_and_schema_valid() -> None:
    request = parse_fresh_validation_request(REQUEST)
    Draft202012Validator(_schema("fresh-validation-request.schema.json")).validate(request)
    quote = build_fresh_validation_quote(
        request,
        generated_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        quote_id="q_0123456789abcdef01234567",
    )
    Draft202012Validator(
        _schema("fresh-validation-quote.schema.json"), format_checker=FormatChecker()
    ).validate(quote)
    assert quote["amount_minor"] == 4_900
    assert quote["orderable"] is False
    assert quote["deliverable"]["source"]["commit"] == "a" * 40
    assert quote["expires_at"] == "2026-07-14T12:15:00Z"
    assert quote["refund_conditions"] == list(REFUND_CONDITIONS)


def test_request_digest_is_deterministic_and_maximum_is_respected() -> None:
    first = build_fresh_validation_quote(
        REQUEST,
        generated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        quote_id="q_111111111111111111111111",
    )
    second = build_fresh_validation_quote(
        dict(reversed(list(REQUEST.items()))),
        generated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        quote_id="q_222222222222222222222222",
    )
    assert first["request_digest"] == second["request_digest"]
    below = json.loads(json.dumps(REQUEST))
    below["max_price"]["amount_minor"] = 4_899
    declined = build_fresh_validation_quote(
        below,
        generated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        quote_id="q_333333333333333333333333",
    )
    assert declined["quote_status"] == "declined_max_price"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        (("source", "host"), "example.com", "unsupported_source_host"),
        (("source", "commit"), "main", "mutable_source_reference"),
        (("source", "skill_path"), "skills/../secret", "invalid_commerce_request"),
        (("source", "skill_path"), "skills//ambiguous", "invalid_commerce_request"),
    ],
)
def test_request_rejects_unallowlisted_mutable_or_ambiguous_sources(field: tuple[str, str], value: str, code: str) -> None:
    request = json.loads(json.dumps(REQUEST))
    request[field[0]][field[1]] = value
    with pytest.raises(InputRejected) as error:
        parse_fresh_validation_request(request)
    assert error.value.code == code


@pytest.mark.parametrize("skill_path", ["../private", "skills//ambiguous", "skills/space here", "skills/ümlaut"])
def test_request_schema_and_parser_both_reject_unsafe_paths(skill_path: str) -> None:
    request = json.loads(json.dumps(REQUEST))
    request["source"]["skill_path"] = skill_path
    with pytest.raises(InputRejected):
        parse_fresh_validation_request(request)
    assert not Draft202012Validator(_schema("fresh-validation-request.schema.json")).is_valid(request)


def test_strict_commerce_json_rejects_duplicate_keys_at_any_depth() -> None:
    with pytest.raises(InputRejected, match="duplicate JSON key: commit"):
        load_strict_commerce_json(
            '{"source":{"commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
            '"commit":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}}'
        )


def test_quote_schema_rejects_weakened_nested_contracts() -> None:
    quote = build_fresh_validation_quote(
        REQUEST,
        generated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        quote_id="q_444444444444444444444444",
    )
    validator = Draft202012Validator(_schema("fresh-validation-quote.schema.json"))
    mutations = []
    empty_deliverable = json.loads(json.dumps(quote))
    empty_deliverable["deliverable"] = {}
    mutations.append(empty_deliverable)
    duplicate_provider = json.loads(json.dumps(quote))
    duplicate_provider["payment_options"][1] = duplicate_provider["payment_options"][0]
    mutations.append(duplicate_provider)
    empty_limits = json.loads(json.dumps(quote))
    empty_limits["hard_limits"] = {}
    mutations.append(empty_limits)
    for mutation in mutations:
        assert not validator.is_valid(mutation)


def test_state_transitions_fail_closed_and_settlement_is_separate_from_delivery() -> None:
    require_transition(OrderStatus.PAYMENT_PENDING, OrderStatus.QUEUED)
    require_transition(PaymentStatus.CAPTURED, PaymentStatus.AVAILABLE)
    with pytest.raises(InputRejected, match="not allowed"):
        require_transition(OrderStatus.QUEUED, OrderStatus.DELIVERED)
    with pytest.raises(ValueError, match="do not match"):
        require_transition(OrderStatus.QUEUED, PaymentStatus.CAPTURED)


def test_stripe_webhook_signature_verifies_exact_bytes_and_rejects_replay_window() -> None:
    body = b'{"id":"evt_123","type":"checkout.session.completed"}'
    secret = b"whsec_test"
    timestamp = 1_784_030_400
    signature = hmac.new(secret, str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
    header = f"t={timestamp},v1={'0' * 64},v1={signature}"
    assert verify_stripe_webhook_signature(body, header, secret, now=timestamp + 10) == timestamp
    with pytest.raises(InputRejected):
        verify_stripe_webhook_signature(body + b" ", header, secret, now=timestamp + 10)
    with pytest.raises(InputRejected):
        verify_stripe_webhook_signature(body, header, secret, now=timestamp + 301)


def test_quote_cli_emits_machine_readable_preview(tmp_path, capsys) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(REQUEST), encoding="utf-8")
    assert (
        main(
            [
                "quote-fresh-validation",
                str(request_path),
                "--quote-id",
                "q_abcdefabcdefabcdefabcdef",
                "--generated-at",
                "2026-07-14T12:00:00Z",
            ]
        )
        == 0
    )
    quote = json.loads(capsys.readouterr().out)
    assert quote["quote_id"] == "q_abcdefabcdefabcdefabcdef"
    assert quote["orderable"] is False


def test_quote_cli_rejects_duplicate_request_keys(tmp_path, capsys) -> None:
    request_path = tmp_path / "request.json"
    # Use an explicit minimal duplicate-key document so the parser fails before semantic validation.
    request_path.write_text('{"commit":"' + "a" * 40 + '","commit":"' + "b" * 40 + '"}', encoding="utf-8")
    assert main(["quote-fresh-validation", str(request_path)]) == 1
    assert "duplicate JSON key: commit" in capsys.readouterr().err
