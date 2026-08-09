"""PII-free logging and local OAuth callback ceremony regressions."""

from __future__ import annotations

import logging
import threading
from http.server import HTTPServer
from urllib.parse import urlencode

import requests

from mycase_mcp import client as client_module
from mycase_mcp.setup import oauth_flow, verify


def _callback_request(params: dict[str, str]) -> requests.Response:
    httpd = HTTPServer(("127.0.0.1", 0), oauth_flow._CallbackHandler)
    thread = threading.Thread(target=httpd.handle_request)
    thread.start()
    host, port = httpd.server_address
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
