"""PII-free logging and local OAuth callback ceremony regressions."""

from __future__ import annotations

import logging
import threading
from http.server import HTTPServer
from types import SimpleNamespace
from urllib.parse import urlencode

import requests

from mycase_mcp import client as client_module
from mycase_mcp.setup import oauth_flow, verify


def _callback_request(params: dict[str, str]) -> requests.Response:
    httpd = HTTPServer(("127.0.0.1", 0), oauth_flow._CallbackHandler)
    thread = threading.Thread(target=httpd.handle_request)
    thread.start()
    host, port = httpd.server_address[:2]
    try:
        return requests.get(
            f"http://{host}:{port}/callback?{urlencode(params)}",
            timeout=3,
        )
    finally:
        thread.join(timeout=3)
        httpd.server_close()


def test_oauth_callback_is_state_bound_and_csp_hardened() -> None:
    oauth_flow._oauth_state = "expected-state-marker"
    oauth_flow._auth_code = None

    response = _callback_request(
        {"code": "private-code-marker", "state": "expected-state-marker"}
    )

    assert response.status_code == 200
    assert oauth_flow._auth_code == "private-code-marker"
    assert response.headers["content-security-policy"] == oauth_flow._CALLBACK_CSP
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    oauth_flow._auth_code = None
    oauth_flow._oauth_state = None


def test_oauth_callback_rejection_has_pii_free_reason_log(caplog) -> None:
    private_state = "private-state-marker"
    private_code = "private-code-marker"
    oauth_flow._oauth_state = "expected-state-marker"
    oauth_flow._auth_code = None
    caplog.set_level(logging.WARNING, logger=oauth_flow.__name__)

    response = _callback_request({"code": private_code, "state": private_state})

    assert response.status_code == 400
    assert oauth_flow._auth_code is None
    assert "oauth_state_mismatch" in caplog.text
    assert private_state not in caplog.text
    assert private_code not in caplog.text
    oauth_flow._oauth_state = None


def test_verifier_does_not_print_authenticated_person_name(monkeypatch, capsys) -> None:
    private_name = "Private Person Marker"

    class StubMyCaseClient:
        def get_me(self):
            return {"full_name": private_name, "email": "private@example.test"}

        def list_cases(self, page_size=5):
            return []

    monkeypatch.setattr(client_module, "MyCaseClient", StubMyCaseClient)

    assert verify.check_api() is True
    output = capsys.readouterr().out
    assert "Authenticated MyCase user" in output
    assert private_name not in output
    assert "private@example.test" not in output


def test_token_refresh_uses_a_finite_timeout(monkeypatch, tmp_path) -> None:
    calls = []

    def post(url, *, data, timeout):
        calls.append((url, data, timeout))
        return SimpleNamespace(
            status_code=200, json=lambda: {"access_token": "test-access"}
        )

    monkeypatch.setattr(client_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(client_module, "CLIENT_ID", "test-client")
    monkeypatch.setattr(client_module, "CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(client_module.requests, "post", post)
    manager = client_module.TokenManager()
    manager.tokens = {"refresh_token": "test-refresh"}

    result = manager.refresh()

    assert len(calls) == 1
    assert calls[0][0] == client_module.TOKEN_URL
    assert calls[0][2] == 30
    assert result["access_token"] == "test-access"
    assert result["refresh_token"] == "test-refresh"


def test_oauth_token_exchange_uses_a_finite_timeout(monkeypatch, tmp_path) -> None:
    calls = []

    def post(url, *, data, timeout):
        calls.append((url, data, timeout))
        return SimpleNamespace(
            status_code=200, json=lambda: {"access_token": "test-access"}
        )

    class CallbackServer:
        def handle_request(self):
            oauth_flow._auth_code = "test-code"

        def server_close(self):
            pass

    monkeypatch.setattr("builtins.input", lambda _prompt: "test-client")
    monkeypatch.setattr(oauth_flow, "getpass", lambda _prompt: "test-secret")
    monkeypatch.setattr(oauth_flow.webbrowser, "open", lambda _url: True)
    monkeypatch.setattr(oauth_flow, "HTTPServer", lambda *_args: CallbackServer())
    monkeypatch.setattr(oauth_flow.requests, "post", post)
    monkeypatch.setattr(oauth_flow.credentials, "set_secret", lambda *_args: "file")
    monkeypatch.setattr(oauth_flow, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(oauth_flow, "_auth_code", None)
    monkeypatch.setattr(oauth_flow, "_oauth_state", None)

    oauth_flow.main()

    assert len(calls) == 1
    assert calls[0][0] == oauth_flow.TOKEN_URL
    assert calls[0][1]["code"] == "test-code"
    assert calls[0][2] == 30
