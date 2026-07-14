from __future__ import annotations

from http.client import HTTPConnection
import json
from pathlib import Path
import socket
import threading

from capabilityproof.api import create_server


FIXTURES = Path(__file__).parent / "fixtures"


def _request(connection: HTTPConnection, body: bytes) -> tuple[int, dict]:
    connection.request("POST", "/v1/inspect", body=body, headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    response = connection.getresponse()
    payload = json.loads(response.read().decode("utf-8"))
    return response.status, payload


def test_http_inspect_and_path_confinement() -> None:
    server = create_server(FIXTURES, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        connection = HTTPConnection(host, port, timeout=5)
        body = json.dumps({"path": "valid-skill", "generated_at": "2026-07-14T03:00:00Z"}).encode()
        status, payload = _request(connection, body)
        assert status == 200
        assert payload["receipt"]["format_validation"]["status"] == "pass"

        connection = HTTPConnection(host, port, timeout=5)
        status, payload = _request(connection, b'{"path":"../"}')
        assert status == 403
        assert payload["error"]["code"] == "path_rejected"

        connection = HTTPConnection(host, port, timeout=5)
        status, payload = _request(connection, b'{"path":"valid-skill","path":"risky-skill"}')
        assert status == 400
        assert payload["error"]["code"] == "invalid_json"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_health_is_non_sensitive() -> None:
    server = create_server(FIXTURES, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        connection = HTTPConnection(host, port, timeout=5)
        connection.request("GET", "/health")
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert payload == {"service": "vouchspec", "status": "ok", "version": "0.2.0"}
        assert str(FIXTURES) not in json.dumps(payload)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_incomplete_request_does_not_block_other_loopback_clients() -> None:
    server = create_server(FIXTURES, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    stalled = socket.create_connection((host, port), timeout=2)
    try:
        stalled.sendall(
            b"POST /v1/inspect HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 100\r\n\r\n"
            b"{"
        )
        connection = HTTPConnection(host, port, timeout=2)
        connection.request("GET", "/health")
        response = connection.getresponse()
        assert response.status == 200
        response.read()
        connection.close()
    finally:
        stalled.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
