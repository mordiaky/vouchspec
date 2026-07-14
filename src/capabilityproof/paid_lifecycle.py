"""Root-authorized lifecycle publication for delivered paid Stage B receipts.

The online commerce process can build an unsigned draft, but it cannot publish lifecycle
state. Publication requires an exact DSSE envelope signed by the separately trusted root.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3
from typing import Any, Iterator

from .commerce_store import CommerceStore
from .errors import InputRejected
from .lifecycle import (
    RECEIPT_STATUSES,
    evaluate_receipt_lifecycle,
    validate_lifecycle_feed,
    verify_lifecycle_envelope,
)
from .receipt import deterministic_json
from .signing import jwk_thumbprint


PAID_LIFECYCLE_SCHEMA_VERSION = "1"
MAX_FEED_LIFETIME = timedelta(days=7)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_time(value: datetime) -> str:
    return _aware_datetime(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _aware_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InputRejected("lifecycle timestamp requires a timezone", code="invalid_lifecycle_feed")
    return value.astimezone(timezone.utc)


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise InputRejected("lifecycle timestamp is invalid", code="invalid_lifecycle_feed")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except (ValueError, OverflowError) as exc:
        raise InputRejected("lifecycle timestamp is invalid", code="invalid_lifecycle_feed") from exc
    if parsed.tzinfo is None:
        raise InputRejected("lifecycle timestamp requires a timezone", code="invalid_lifecycle_feed")
    return parsed.astimezone(timezone.utc)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


class PaidReceiptLifecycleStore:
    """Build drafts and import only root-signed, monotonic paid-receipt lifecycle feeds."""

    def __init__(self, store: CommerceStore) -> None:
        self.store = store
        self._initialize()

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

    def _initialize(self) -> None:
        with self._connection(write=True) as connection:
            metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
            if metadata.get("environment") != self.store.environment:
                raise InputRejected(
                    "paid lifecycle environment does not match the commerce store",
                    code="commerce_environment_mismatch",
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS paid_lifecycle_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paid_lifecycle_publications (
                    sequence INTEGER PRIMARY KEY CHECK(sequence >= 1),
                    root_keyid TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL UNIQUE,
                    feed_json TEXT NOT NULL,
                    envelope_body BLOB NOT NULL,
                    generated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    published_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paid_lifecycle_status (
                    receipt_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL UNIQUE REFERENCES orders(order_id),
                    status TEXT NOT NULL,
                    superseded_by TEXT,
                    reason TEXT,
                    sequence INTEGER NOT NULL REFERENCES paid_lifecycle_publications(sequence),
                    updated_at TEXT NOT NULL
                );
                """
            )
            expected = {
                "schema_version": PAID_LIFECYCLE_SCHEMA_VERSION,
                "environment": self.store.environment,
            }
            actual = dict(
                connection.execute("SELECT key, value FROM paid_lifecycle_metadata").fetchall()
            )
            if not actual:
                connection.executemany(
                    "INSERT INTO paid_lifecycle_metadata(key, value) VALUES (?, ?)",
                    expected.items(),
                )
            elif any(actual.get(key) != value for key, value in expected.items()):
                raise InputRejected(
                    "paid lifecycle schema or environment does not match",
                    code="commerce_environment_mismatch",
                )

    def build_draft(
        self,
        issuer_keys: list[dict[str, Any]],
        *,
        generated_at: datetime,
        expires_at: datetime,
        changes: dict[str, dict[str, Any]] | None = None,
    ) -> bytes:
        """Return exact unsigned feed bytes for transfer to the offline root signer."""

        generated = _aware_datetime(generated_at)
        expires = _aware_datetime(expires_at)
        if (
            expires <= generated
            or expires - generated > MAX_FEED_LIFETIME
        ):
            raise InputRejected("paid lifecycle feed lifetime is invalid", code="invalid_lifecycle_feed")
        requested = changes or {}
        if not isinstance(requested, dict) or len(requested) > 100_000:
            raise InputRejected("paid lifecycle changes are invalid", code="invalid_lifecycle_feed")
        orders = self._delivered_orders()
        if not orders:
            raise InputRejected("no delivered receipts exist", code="paid_lifecycle_empty")
        with self._connection() as connection:
            prior_rows = connection.execute(
                "SELECT * FROM paid_lifecycle_status ORDER BY receipt_id"
            ).fetchall()
            previous = {row["receipt_id"]: dict(row) for row in prior_rows}
            sequence_row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value FROM paid_lifecycle_publications"
            ).fetchone()
            latest_row = connection.execute(
                "SELECT feed_json FROM paid_lifecycle_publications ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        records = self._derive_records(orders, previous, requested)
        feed = {
            "schema_version": "1.0.0",
            "sequence": int(sequence_row["value"]) + 1,
            "generated_at": _format_time(generated),
            "expires_at": _format_time(expires),
            "issuer_keys": issuer_keys,
            "receipts": records,
        }
        validate_lifecycle_feed(feed)
        self._validate_issuer_coverage(feed, orders)
        prior_feed = json.loads(latest_row["feed_json"]) if latest_row is not None else None
        self._validate_issuer_transitions(feed, prior_feed)
        return deterministic_json(feed)

    def publish(
        self,
        envelope_bytes: bytes,
        trusted_root_jwk: dict[str, Any],
        *,
        published_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Verify and atomically import one offline root-signed lifecycle publication."""

        if not isinstance(envelope_bytes, bytes) or not 1 <= len(envelope_bytes) <= 1_100_000:
            raise InputRejected("paid lifecycle envelope is invalid", code="invalid_lifecycle_feed")
        feed, payload = verify_lifecycle_envelope(envelope_bytes, trusted_root_jwk)
        root_keyid = jwk_thumbprint(trusted_root_jwk)
        payload_digest = hashlib.sha256(payload).hexdigest()
        observed = _aware_datetime(published_at or datetime.now(timezone.utc))
        generated = _parse_time(feed["generated_at"])
        expires = _parse_time(feed["expires_at"])
        if (
            generated > observed + timedelta(minutes=5)
            or expires <= observed
            or expires - generated > MAX_FEED_LIFETIME
        ):
            raise InputRejected("paid lifecycle publication time is invalid", code="invalid_lifecycle_feed")
        orders = self._delivered_orders()
        if not orders:
            raise InputRejected("no delivered receipts exist", code="paid_lifecycle_empty")
        self._validate_issuer_coverage(feed, orders)
        by_receipt = {order["receipt_id"]: order for order in orders}
        if {record["receipt_id"] for record in feed["receipts"]} != set(by_receipt):
            raise InputRejected(
                "paid lifecycle feed does not exactly cover delivered receipts",
                code="paid_lifecycle_coverage",
            )
        published_timestamp = _format_time(observed)
        with self._connection(write=True) as connection:
            metadata = dict(
                connection.execute("SELECT key, value FROM paid_lifecycle_metadata").fetchall()
            )
            bound_root = metadata.get("root_keyid")
            if bound_root is not None and bound_root != root_keyid:
                raise InputRejected("paid lifecycle root changed", code="untrusted_key")
            latest = connection.execute(
                """SELECT sequence, payload_sha256, feed_json
                FROM paid_lifecycle_publications ORDER BY sequence DESC LIMIT 1"""
            ).fetchone()
            if latest is not None and feed["sequence"] < latest["sequence"]:
                raise InputRejected("paid lifecycle rollback detected", code="lifecycle_rollback")
            if latest is not None and feed["sequence"] == latest["sequence"]:
                if payload_digest != latest["payload_sha256"]:
                    raise InputRejected(
                        "paid lifecycle equal-sequence equivocation detected",
                        code="lifecycle_equivocation",
                    )
                return self._publication_view(connection, feed["sequence"])
            expected_sequence = 1 if latest is None else latest["sequence"] + 1
            if feed["sequence"] != expected_sequence:
                raise InputRejected("paid lifecycle sequence is not contiguous", code="lifecycle_rollback")
            prior_feed = json.loads(latest["feed_json"]) if latest is not None else None
            self._validate_issuer_transitions(feed, prior_feed)
            prior_rows = connection.execute("SELECT * FROM paid_lifecycle_status").fetchall()
            previous = {row["receipt_id"]: dict(row) for row in prior_rows}
            self._validate_published_transitions(feed["receipts"], previous, by_receipt)
            connection.execute(
                """INSERT INTO paid_lifecycle_publications(
                    sequence, root_keyid, payload_sha256, feed_json, envelope_body,
                    generated_at, expires_at, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    feed["sequence"],
                    root_keyid,
                    payload_digest,
                    _canonical(feed),
                    envelope_bytes,
                    feed["generated_at"],
                    feed["expires_at"],
                    published_timestamp,
                ),
            )
            if bound_root is None:
                connection.execute(
                    "INSERT INTO paid_lifecycle_metadata(key, value) VALUES ('root_keyid', ?)",
                    (root_keyid,),
                )
            for record in feed["receipts"]:
                order = by_receipt[record["receipt_id"]]
                connection.execute(
                    """INSERT INTO paid_lifecycle_status(
                        receipt_id, order_id, status, superseded_by, reason, sequence, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(receipt_id) DO UPDATE SET
                        status = excluded.status,
                        superseded_by = excluded.superseded_by,
                        reason = excluded.reason,
                        sequence = excluded.sequence,
                        updated_at = excluded.updated_at""",
                    (
                        record["receipt_id"],
                        order["order_id"],
                        record["status"],
                        record.get("superseded_by"),
                        record.get("reason"),
                        feed["sequence"],
                        published_timestamp,
                    ),
                )
            return self._publication_view(connection, feed["sequence"])

    def latest_envelope(self) -> bytes:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT envelope_body FROM paid_lifecycle_publications ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        if row is None:
            raise InputRejected("paid lifecycle has not been published", code="paid_lifecycle_missing")
        return bytes(row["envelope_body"])

    def evaluate_order_receipt(
        self,
        order_id: str,
        receipt_envelope_bytes: bytes,
        trusted_root_jwk: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if not isinstance(receipt_envelope_bytes, bytes):
            raise InputRejected("receipt envelope is invalid", code="invalid_delivery")
        if now is not None:
            _aware_datetime(now)
        order = self.store.get_order(order_id)
        if order["delivery_status"] != "delivered" or order["envelope_sha256"] is None:
            raise InputRejected("order has no delivered receipt", code="invalid_delivery")
        if hashlib.sha256(receipt_envelope_bytes).hexdigest() != order["envelope_sha256"]:
            raise InputRejected("receipt envelope does not match the order", code="invalid_delivery")
        result = evaluate_receipt_lifecycle(
            receipt_envelope_bytes,
            self.latest_envelope(),
            trusted_root_jwk,
            now=now,
        )
        if result.get("receipt_id") != order["receipt_id"]:
            raise InputRejected("lifecycle receipt does not match the order", code="invalid_delivery")
        return result

    def publications(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT sequence FROM paid_lifecycle_publications ORDER BY sequence"
            ).fetchall()
            return [self._publication_view(connection, row["sequence"]) for row in rows]

    def _delivered_orders(self) -> list[dict[str, Any]]:
        orders = self.store.list_delivered_orders()
        for order in orders:
            if not all(
                isinstance(order.get(field), str) and order[field]
                for field in ("receipt_id", "receipt_sha256", "envelope_sha256", "signing_keyid")
            ):
                raise InputRejected("delivered order evidence is incomplete", code="invalid_delivery")
        return orders

    @staticmethod
    def _validate_issuer_coverage(feed: dict[str, Any], orders: list[dict[str, Any]]) -> None:
        issuer_ids = {record["keyid"] for record in feed["issuer_keys"]}
        signing_ids = {order["signing_keyid"] for order in orders}
        if signing_ids != issuer_ids:
            raise InputRejected(
                "paid lifecycle issuer keys do not exactly match delivered receipt signers",
                code="paid_lifecycle_coverage",
            )

    @staticmethod
    def _validate_issuer_transitions(
        feed: dict[str, Any],
        prior_feed: dict[str, Any] | None,
    ) -> None:
        if prior_feed is None:
            return
        previous = {record["keyid"]: record for record in prior_feed["issuer_keys"]}
        current = {record["keyid"]: record for record in feed["issuer_keys"]}
        if set(previous) - set(current):
            raise InputRejected("paid lifecycle issuer key was removed", code="lifecycle_rollback")
        for keyid, prior in previous.items():
            status = current[keyid]["status"]
            if prior["status"] == "compromised" and status != "compromised":
                raise InputRejected(
                    "compromised paid lifecycle issuer cannot be restored",
                    code="lifecycle_rollback",
                )
            if prior["status"] == "retired" and status == "active":
                raise InputRejected(
                    "retired paid lifecycle issuer cannot be restored",
                    code="lifecycle_rollback",
                )

    @staticmethod
    def _derive_records(
        orders: list[dict[str, Any]],
        previous: dict[str, dict[str, Any]],
        requested: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_receipt = {order["receipt_id"]: order for order in orders}
        if set(requested) - set(by_receipt):
            raise InputRejected("lifecycle change names an unknown receipt", code="paid_lifecycle_coverage")
        records: list[dict[str, Any]] = []
        for receipt_id in sorted(by_receipt):
            prior = previous.get(receipt_id)
            change = requested.get(receipt_id)
            if change is None:
                record = (
                    {"receipt_id": receipt_id, "status": "current"}
                    if prior is None
                    else PaidReceiptLifecycleStore._record_from_row(prior)
                )
            else:
                if not isinstance(change, dict) or not {"status"}.issubset(change) or set(change) - {
                    "status",
                    "superseded_by",
                    "reason",
                }:
                    raise InputRejected("paid lifecycle change is invalid", code="invalid_lifecycle_feed")
                record = {"receipt_id": receipt_id, **change}
            PaidReceiptLifecycleStore._validate_transition(prior, record, set(by_receipt))
            records.append(record)
        return records

    @staticmethod
    def _validate_published_transitions(
        records: list[dict[str, Any]],
        previous: dict[str, dict[str, Any]],
        by_receipt: dict[str, dict[str, Any]],
    ) -> None:
        for record in records:
            PaidReceiptLifecycleStore._validate_transition(
                previous.get(record["receipt_id"]),
                record,
                set(by_receipt),
            )

    @staticmethod
    def _validate_transition(
        prior: dict[str, Any] | None,
        record: dict[str, Any],
        delivered_receipts: set[str],
    ) -> None:
        status = record.get("status")
        if status not in RECEIPT_STATUSES:
            raise InputRejected("paid lifecycle status is invalid", code="invalid_lifecycle_feed")
        if status == "current" and ("reason" in record or "superseded_by" in record):
            raise InputRejected("current paid receipts cannot carry an invalidation", code="invalid_lifecycle_feed")
        if status == "superseded":
            successor = record.get("superseded_by")
            if successor not in delivered_receipts or successor == record.get("receipt_id"):
                raise InputRejected("paid receipt successor is invalid", code="invalid_lifecycle_feed")
        if status.startswith("revoked_") and not isinstance(record.get("reason"), str):
            raise InputRejected("revoked paid receipt requires a reason", code="invalid_lifecycle_feed")
        if prior is None:
            if status != "current":
                raise InputRejected("new paid receipts must first publish as current", code="invalid_lifecycle_feed")
            return
        prior_record = PaidReceiptLifecycleStore._record_from_row(prior)
        if prior_record["status"] != "current" and prior_record != record:
            raise InputRejected("paid receipt terminal lifecycle state cannot change", code="lifecycle_rollback")
        if prior_record["status"] == "current" and status == "current" and prior_record != record:
            raise InputRejected("current paid receipt state is inconsistent", code="lifecycle_equivocation")

    @staticmethod
    def _record_from_row(row: dict[str, Any]) -> dict[str, Any]:
        record = {"receipt_id": row["receipt_id"], "status": row["status"]}
        if row.get("superseded_by") is not None:
            record["superseded_by"] = row["superseded_by"]
        if row.get("reason") is not None:
            record["reason"] = row["reason"]
        return record

    @staticmethod
    def _publication_view(connection: sqlite3.Connection, sequence: int) -> dict[str, Any]:
        row = connection.execute(
            """SELECT sequence, root_keyid, payload_sha256, feed_json,
                generated_at, expires_at, published_at
            FROM paid_lifecycle_publications WHERE sequence = ?""",
            (sequence,),
        ).fetchone()
        if row is None:
            raise InputRejected("paid lifecycle publication is missing", code="paid_lifecycle_missing")
        view = dict(row)
        feed = json.loads(view.pop("feed_json"))
        order_rows = connection.execute(
            "SELECT receipt_id, order_id FROM orders WHERE receipt_id IS NOT NULL"
        ).fetchall()
        order_ids = {item["receipt_id"]: item["order_id"] for item in order_rows}
        view["receipts"] = [
            {**record, "order_id": order_ids[record["receipt_id"]]}
            for record in feed["receipts"]
        ]
        return view
