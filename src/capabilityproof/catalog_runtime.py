"""Trusted runtime view over a signed catalog and root-signed lifecycle feed."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from .catalog import CatalogStore, filter_catalog_entries, validate_catalog_index, validate_receipt_id
from .errors import InputRejected
from .lifecycle import (
    LifecycleSequenceStore,
    evaluate_receipt_lifecycle_with_state,
    verify_lifecycle_envelope,
)
from .signing import (
    CATALOG_INDEX_PAYLOAD_TYPE,
    _strict_json,
    jwk_thumbprint,
    verify_dsse_envelope,
    verify_receipt_envelope,
)


class VerifiedCatalog:
    """Immutable in-memory view of one fully verified on-disk catalog generation."""

    def __init__(self, catalog_root: Path, trusted_root_jwk: dict[str, Any], sequence_state_path: Path) -> None:
        store = CatalogStore(catalog_root)
        self.trusted_root_jwk = trusted_root_jwk
        self.sequence_store = LifecycleSequenceStore(sequence_state_path)
        root_jwk_bytes = store.root_jwk_bytes()
        bundled_root = _strict_json(root_jwk_bytes, code="invalid_key")
        if jwk_thumbprint(bundled_root) != jwk_thumbprint(trusted_root_jwk):
            raise InputRejected("catalog discovery root differs from the configured trust root", code="untrusted_key")
        lifecycle_envelope_bytes = store.lifecycle_envelope_bytes()
        feed, lifecycle_payload = verify_lifecycle_envelope(lifecycle_envelope_bytes, trusted_root_jwk)
        index_envelope_bytes = store.index_envelope_bytes()
        index_envelope = _strict_json(index_envelope_bytes, code="invalid_envelope")
        signatures = index_envelope.get("signatures") if isinstance(index_envelope, dict) else None
        if not isinstance(signatures, list) or len(signatures) != 1 or not isinstance(signatures[0], dict):
            raise InputRejected("catalog index signature set is invalid", code="invalid_envelope")
        keyid = signatures[0].get("keyid")
        issuer = next((record for record in feed["issuer_keys"] if record["keyid"] == keyid), None)
        if issuer is None or issuer["status"] == "compromised":
            raise InputRejected("catalog index signer is not currently trusted", code="untrusted_key")
        exact_index = verify_dsse_envelope(
            index_envelope_bytes,
            CATALOG_INDEX_PAYLOAD_TYPE,
            issuer["jwk"],
            maximum_payload_bytes=5_000_000,
        )
        if exact_index != store.index_bytes():
            raise InputRejected("signed catalog index bytes do not match index.json", code="invalid_catalog")
        index = validate_catalog_index(_strict_json(exact_index, code="invalid_catalog"))

        issuer_jwk_bytes = store.issuer_jwk_bytes()
        bundled_issuer = _strict_json(issuer_jwk_bytes, code="invalid_key")
        if bundled_issuer != issuer["jwk"] or jwk_thumbprint(bundled_issuer) != keyid:
            raise InputRejected("catalog discovery issuer differs from the signed lifecycle feed", code="untrusted_key")

        receipts: dict[str, bytes] = {}
        for entry in index["entries"]:
            envelope_bytes = store.receipt_envelope_bytes(entry["receipt_id"])
            receipt, _ = verify_receipt_envelope(envelope_bytes, issuer["jwk"])
            skill_name = receipt["artifact"]["claims_untrusted"]["name"] or receipt["artifact"]["root_directory"]
            if (
                receipt["receipt_id"] != entry["receipt_id"]
                or receipt["artifact"]["digest"]["sha256"] != entry["artifact_sha256"]
                or receipt["provenance"]["source_repository"] != entry["source_repository"]
                or receipt["provenance"]["source_commit"] != entry["source_commit"]
                or receipt["provenance"]["artifact_path"] != entry["artifact_path"]
                or receipt["evidence_labels"] != entry["evidence_labels"]
                or receipt["validity"]["generated_at"] != entry["issued_at"]
                or receipt["validity"]["expires_at"] != entry["expires_at"]
                or skill_name != entry["skill_name"]
            ):
                raise InputRejected("signed receipt does not match the signed catalog index", code="invalid_catalog")
            receipts[entry["receipt_id"]] = envelope_bytes

        # Persist the signed feed before the first request so a restart cannot reopen a rollback window.
        self.sequence_store.record(
            trusted_root_jwk,
            feed["sequence"],
            hashlib.sha256(lifecycle_payload).hexdigest(),
        )
        self._index = index
        self._index_envelope_bytes = index_envelope_bytes
        self._lifecycle_envelope_bytes = lifecycle_envelope_bytes
        self._root_jwk_bytes = root_jwk_bytes
        self._issuer_jwk_bytes = issuer_jwk_bytes
        self._receipts = receipts

    def index_envelope_bytes(self) -> bytes:
        return self._index_envelope_bytes

    def lifecycle_envelope_bytes(self) -> bytes:
        return self._lifecycle_envelope_bytes

    def root_jwk_bytes(self) -> bytes:
        return self._root_jwk_bytes

    def issuer_jwk_bytes(self) -> bytes:
        return self._issuer_jwk_bytes

    def receipt_envelope_bytes(self, receipt_id: str) -> bytes:
        validate_receipt_id(receipt_id)
        try:
            return self._receipts[receipt_id]
        except KeyError as exc:
            raise InputRejected("receipt was not found", code="not_found") from exc

    def status(self, receipt_id: str) -> dict[str, Any]:
        return evaluate_receipt_lifecycle_with_state(
            self.receipt_envelope_bytes(receipt_id),
            self._lifecycle_envelope_bytes,
            self.trusted_root_jwk,
            self.sequence_store,
        )

    def list_entries(
        self,
        *,
        query: str | None = None,
        repository_owner: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        entries = filter_catalog_entries(
            self._index,
            query=query,
            repository_owner=repository_owner,
            limit=limit,
        )
        results: list[dict[str, Any]] = []
        for entry in entries:
            status = self.status(entry["receipt_id"])
            result = deepcopy(entry)
            result.update({"lifecycle": status["lifecycle"], "lifecycle_feed_sequence": status["feed_sequence"]})
            results.append(result)
        return results
