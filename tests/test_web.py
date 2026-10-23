from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import grabit.web as web


@pytest.fixture
def server(tmp_path, monkeypatch):
    calls = []

    def fake_download(options, on_progress=None):
        calls.append(options)
        return []

    monkeypatch.setattr(web, "download", fake_download)
    web.Handler.output_dir = Path(tmp_path)
    web.Handler.allowed_hosts = set(web.LOOPBACK)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv.server_address[1], calls
    srv.shutdown()
    srv.server_close()


def request(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    res = conn.getresponse()
    data = res.read()
    conn.close()
    return res.status, data


def post(port, payload, **headers):
    hdrs = {"content-type": "application/json", **headers}
    return request(port, "POST", "/api/download", json.dumps(payload), hdrs)


def test_page_served(server):
    port, _ = server
    status, body = request(port, "GET", "/")
    assert status == 200
    assert b"innerHTML" not in body


def test_rejects_foreign_host_header(server):
    port, _ = server
    status, _ = request(port, "GET", "/", headers={"host": "evil.example:8787"})
    assert status == 403


def test_rejects_cross_origin_post(server):
    port, calls = server
    status, _ = post(port, {"url": "https://x"}, origin="https://evil.example")
    assert status == 403
    assert calls == []


def test_rejects_non_json_content_type(server):
    port, _ = server
    status, _ = request(port, "POST", "/api/download", "url=https://x",
                        {"content-type": "text/plain"})
    assert status == 415


def test_rejects_oversized_body(server):
    port, _ = server
    status, _ = request(port, "POST", "/api/download", b"{}",
                        {"content-type": "application/json",
                         "content-length": str(web.MAX_BODY + 1)})
    assert status == 413


def test_same_origin_post_starts_job(server):
    port, _ = server
    status, body = post(port, {"url": "https://x"}, origin=f"http://127.0.0.1:{port}")
    assert status == 202
    assert "id" in json.loads(body)


def test_run_rejects_non_http_scheme(monkeypatch, tmp_path):
    monkeypatch.setattr(web, "download", lambda *a, **k: pytest.fail("should not download"))
    web.Handler.output_dir = tmp_path
    web._jobs["j"] = {"status": "starting", "percent": None, "detail": "", "files": []}
    web._run("j", {"url": "file:///etc/passwd"})
    assert web._jobs["j"]["status"] == "error"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("127.0.0.1:8787", "127.0.0.1"),
        ("localhost", "localhost"),
        ("[::1]:8787", "::1"),
        ("http://LOCALHOST:8787", "localhost"),
        ("null", "null"),
    ],
)
def test_hostname(value, expected):
    assert web._hostname(value) == expected
