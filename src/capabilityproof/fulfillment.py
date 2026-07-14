"""Sandbox end-to-end orchestration for one constrained Stage B validation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, TYPE_CHECKING

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .commerce import OrderStatus, PaymentStatus
from .commerce_store import CommerceStore, DIRECT_COST_CATEGORIES
from .errors import InputRejected
from .receipt import deterministic_json
from .stage_b import DockerNoEgressWorker, freeze_public_source
from .stage_b_signer import sign_verified_worker_result

if TYPE_CHECKING:
    from .commerce_access import CommerceAccessStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SandboxFulfillmentCoordinator:
    """Run freeze → no-egress inspect → constrained sign → ledger → delivery."""

    def __init__(
        self,
        store: CommerceStore,
        *,
        worker: DockerNoEgressWorker,
        signing_key: Ed25519PrivateKey,
        access_store: CommerceAccessStore | None = None,
    ) -> None:
        if store.environment != "sandbox":
            raise ValueError("sandbox coordinator requires a sandbox commerce store")
        self.store = store
        self.worker = worker
        self.signing_key = signing_key
        self.access_store = access_store

    def fulfill(
        self,
        order_id: str,
        *,
        frozen_cache_root: Path,
        delivery_root: Path,
        direct_costs_minor: dict[str, int],
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        order = self.store.get_order(order_id)
        if order["order_status"] == OrderStatus.DELIVERED.value:
            if self.access_store is not None:
                envelope_path = (
                    delivery_root.expanduser().resolve(strict=False)
                    / order_id
                    / "receipt.dsse.json"
                )
                self.access_store.publish_result(order_id, envelope_path.read_bytes())
            return order
        if (
            order["order_status"] != OrderStatus.QUEUED.value
            or order["payment_status"] not in {PaymentStatus.CAPTURED.value, PaymentStatus.AVAILABLE.value}
            or order["counts_for_goal"]
            or order["settlement_status"] != "sandbox_nonsettling"
        ):
            raise InputRejected("sandbox order is not ready for fulfillment", code="order_not_fulfillable")
        if set(direct_costs_minor) != set(DIRECT_COST_CATEGORIES):
            raise InputRejected("all direct cost categories are required", code="invalid_cost_record")
        job_root = delivery_root.expanduser().resolve(strict=False) / order_id
        if job_root.exists():
            raise InputRejected("delivery job directory already exists", code="delivery_output_exists")
        job_root.mkdir(parents=True)
        source_reference = f"job_{hashlib.sha256(order_id.encode('ascii')).hexdigest()[:24]}"
        try:
            self.store.begin_fulfillment(
                order_id,
                source_reference=source_reference,
                occurred_at=_utc_now(),
            )
            request = self.store.get_order_request(order_id)
            frozen = freeze_public_source(request, frozen_cache_root.expanduser().resolve(strict=False))
            worker_result = self.worker.run(
                frozen.root,
                job_root / "worker",
                generated_at=generated_at,
            )
            envelope_path = job_root / "receipt.dsse.json"
            signing = sign_verified_worker_result(
                frozen.root,
                worker_result.output_root,
                envelope_path,
                self.signing_key,
                allowed_image_references={self.worker.image_reference},
            )
            recorded_at = _utc_now()
            self.store.record_direct_costs(
                order_id,
                direct_costs_minor,
                idempotency_key=f"cost_{source_reference[4:]}",
                recorded_at=recorded_at,
            )
            delivery_manifest = {
                "schema_version": "1.0.0",
                "environment": "sandbox",
                "order_id": order_id,
                "counts_for_goal": False,
                "settlement_status": "sandbox_nonsettling",
                "receipt_id": signing["receipt_id"],
                "receipt_sha256": signing["receipt_sha256"],
                "envelope_sha256": signing["envelope_sha256"],
                "signing_keyid": signing["signing_keyid"],
                "freeze_manifest_digest": signing["freeze_manifest_digest"],
                "container_image": signing["container_image"],
                "artifact_execution": "not_performed",
            }
            (job_root / "delivery-manifest.json").write_bytes(deterministic_json(delivery_manifest) + b"\n")
            delivered = self.store.deliver(
                order_id,
                receipt_id=signing["receipt_id"],
                receipt_sha256=signing["receipt_sha256"],
                envelope_sha256=signing["envelope_sha256"],
                signing_keyid=signing["signing_keyid"],
                source_reference=source_reference,
                occurred_at=_utc_now(),
            )
            if self.access_store is not None:
                self.access_store.publish_result(order_id, envelope_path.read_bytes())
            return delivered
        except Exception:
            try:
                current = self.store.get_order(order_id)
                if current["order_status"] in {OrderStatus.QUEUED.value, OrderStatus.RUNNING.value}:
                    self.store.fail_fulfillment(
                        order_id,
                        source_reference=source_reference,
                        occurred_at=_utc_now(),
                    )
            except Exception:
                pass
            raise
