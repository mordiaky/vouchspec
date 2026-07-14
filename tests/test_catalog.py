from __future__ import annotations

import asyncio
from http.client import HTTPConnection
import json
from pathlib import Path
import shutil
import socket
import threading

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from capabilityproof.catalog import CatalogStore
from capabilityproof.catalog_api import CONNECTION_TIMEOUT_SECONDS, create_catalog_server
from capabilityproof.catalog_builder import finalize_catalog_lifecycle
from capabilityproof.catalog_mcp import build_catalog_mcp_server
from capabilityproof.catalog_runtime import VerifiedCatalog
from capabilityproof.errors import InputRejected
from capabilityproof.lifecycle import LifecycleSequenceStore
from capabilityproof.signing import public_jwk


ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "catalog" / "public"


def _independent_root(tmp_path: Path) -> Path:
    target = tmp_path / "trusted-root.jwk.json"
    target.write_bytes((CATALOG / "keys" / "root.jwk.json").read_bytes())
    return target


def test_catalog_store_searches_bounded_repository_metadata_without_unsigned_lifecycle() -> None:
    store = CatalogStore(CATALOG)
    assert store.index()["entry_count"] == 25
    entry = store.list_entries(query="copilot-sdk")[0]
    assert entry["repository_owner"] == "microsoft"
    assert "lifecycle" not in entry
    assert store.list_entries(query="definitely-missing") == []
    assert len(store.list_entries(repository_owner="openai")) == 3


def test_verified_catalog_persists_feed_before_first_request_and_uses_immutable_snapshot(tmp_path: Path) -> None:
    catalog_copy = tmp_path / "catalog"
    shutil.copytree(CATALOG, catalog_copy)
    trusted_root_path = _independent_root(tmp_path)
    trusted_root = json.loads(trusted_root_path.read_text(encoding="utf-8"))
    sequence_path = tmp_path / "sequence.json"
    runtime = VerifiedCatalog(catalog_copy, trusted_root, sequence_path)
    assert LifecycleSequenceStore(sequence_path).minimum(trusted_root) == 2

    before = runtime.list_entries(query="openai", limit=5)
    (catalog_copy / "index.json").write_text("{}", encoding="utf-8")
    (catalog_copy / "index.dsse.json").write_text("{}", encoding="utf-8")
    assert runtime.list_entries(query="openai", limit=5) == before
    assert runtime.index_envelope_bytes() != b"{}"


def test_catalog_finalization_rejects_same_key_for_root_and_issuer(tmp_path: Path) -> None:
    catalog_copy = tmp_path / "catalog"
    shutil.copytree(CATALOG, catalog_copy)
    (catalog_copy / "lifecycle.dsse.json").unlink()
    (catalog_copy / "keys" / "root.jwk.json").unlink()
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("51" * 32))
    (catalog_copy / "keys" / "issuer.jwk.json").write_text(
        json.dumps(public_jwk(key.public_key()), separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(InputRejected, match="cryptographically distinct"):
        finalize_catalog_lifecycle(catalog_copy, key)


def test_read_only_catalog_http_uses_external_trust_state_and_no_upload_route(tmp_path: Path) -> None:
    server = create_catalog_server(CATALOG, 0, _independent_root(tmp_path), tmp_path / "sequence.json")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    receipt_id = CatalogStore(CATALOG).index()["entries"][0]["receipt_id"]
    try:
        assert host == "127.0.0.1"
        connection = HTTPConnection(host, port, timeout=5)
        connection.request("GET", "/v1/receipts?q=openai&limit=1")
        response = connection.getresponse()
        payload = json.loads(response.read())
        assert response.status == 200
        assert payload["entries"][0]["lifecycle"] == "CURRENT"
        assert payload["entries"][0]["lifecycle_feed_sequence"] == 2
        assert response.getheader("Access-Control-Allow-Origin") == "*"

        connection = HTTPConnection(host, port, timeout=5)
        connection.request("GET", "/v1/quote?operation=fresh_public_static_validation")
        response = connection.getresponse()
        quote = json.loads(response.read())
        assert response.status == 200
        assert quote["amount"] == "49.00"
        assert quote["amount_minor"] == 4900
        assert quote["availability"] == "stage_b_not_orderable"
        assert quote["orders_accepted"] is False
        assert quote["settlement_available"] is False

        connection = HTTPConnection(host, port, timeout=5)
        connection.request("GET", f"/v1/receipts/{receipt_id}")
        response = connection.getresponse()
        assert response.status == 200
        assert "immutable" in response.getheader("Cache-Control")
        response.read()

        connection = HTTPConnection(host, port, timeout=5)
        connection.request("GET", "/v1/index")
        response = connection.getresponse()
        assert json.loads(response.read())["payloadType"] == "application/vnd.vouchspec.catalog-index.v1+json"

        connection = HTTPConnection(host, port, timeout=5)
        connection.request("POST", "/v1/inspect", body=b"{}", headers={"Content-Length": "2"})
        response = connection.getresponse()
        assert response.status == 405
        assert json.loads(response.read())["error"]["code"] == "read_only"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_catalog_http_sets_connection_deadline(tmp_path: Path) -> None:
    server = create_catalog_server(CATALOG, 0, _independent_root(tmp_path), tmp_path / "sequence.json", max_active=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    stalled = socket.create_connection(server.server_address, timeout=2)
    try:
        stalled.sendall(b"GET /health HTTP/1.1\r\n")
        assert stalled.gettimeout() == 2
        connection = HTTPConnection(*server.server_address, timeout=2)
        connection.request("GET", "/health")
        response = connection.getresponse()
        assert response.status == 200
        response.read()
        connection.close()
    finally:
        stalled.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=CONNECTION_TIMEOUT_SECONDS + 2)


def test_catalog_mcp_is_trusted_retrieval_only(tmp_path: Path) -> None:
    server = build_catalog_mcp_server(CATALOG, _independent_root(tmp_path), tmp_path / "sequence.json")
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == {
        "search_receipts",
        "get_receipt",
        "get_receipt_status",
        "get_verification_material",
        "get_price_quote",
    }
    result = asyncio.run(
        server._tool_manager.call_tool("search_receipts", {"query": "openai", "limit": 5}, convert_result=True)
    )
    assert result.structuredContent["count"] >= 1
    assert all(entry["lifecycle"] == "CURRENT" for entry in result.structuredContent["entries"])
    quote = asyncio.run(
        server._tool_manager.call_tool(
            "get_price_quote",
            {"operation": "fresh_public_static_validation"},
            convert_result=True,
        )
    )
    assert quote.structuredContent["orders_accepted"] is False
