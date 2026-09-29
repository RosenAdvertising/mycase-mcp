"""Protocol error results use safe, exact messages with isError=true."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest
import requests
from mcp.server.mcpserver.exceptions import ToolError

from mycase_mcp import client, server

SETUP = (
    "MyCase is not configured. Run mycase-mcp-setup to connect your account "
    "and configure the required OAuth credentials, then restart mycase-mcp."
)
REAUTHORIZE = (
    "The MyCase authorization expired or was rejected. "
    "Run mycase-mcp-setup to reauthorize the account."
)
PRIVATE = "private-token private@example.test https://example.test/?key=private"


def _call(name="who_am_i", arguments=None):
    result = asyncio.run(server.mcp.call_tool(name, arguments or {}))
    wire = result.model_dump(mode="json", by_alias=True)
    assert wire["isError"] is True
    assert len(wire["content"]) == 1
    return wire["content"][0]["text"]


@pytest.fixture
def fake_http(monkeypatch, tmp_path):
    monkeypatch.setattr(client, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(client, "CLIENT_ID", "fake-client")
    monkeypatch.setattr(client, "CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr(
        client.TokenManager,
        "_load",
        lambda self: {"access_token": "fake-access", "refresh_token": "fake-refresh"},
    )
    monkeypatch.setattr(client.time, "sleep", lambda _seconds: None)

    def configure(status, body=None, retry="7"):
        response = SimpleNamespace(
            status_code=status,
            ok=200 <= status < 400,
            headers={"Retry-After": retry},
            json=lambda: body,
        )
        monkeypatch.setattr(requests.Session, "request", lambda *_a, **_k: response)
        return response

    return configure


def test_missing_credentials_exact_result(monkeypatch, tmp_path):
    monkeypatch.setattr(client, "CONFIG_DIR", tmp_path)
    assert _call() == SETUP
    with pytest.raises(ToolError, match="mycase-mcp-setup"):
        client.MyCaseClient()


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (
            400,
            {"code": "invalid_request", "message": PRIVATE},
            "MyCase API returned HTTP 400: request rejected.",
        ),
        (
            403,
            {"error": PRIVATE},
            "MyCase access denied: the connected account lacks permission for this action (or the authorization expired; re-run mycase-mcp-setup if so).",
        ),
        (
            404,
            {"message": PRIVATE},
            "The requested MyCase record was not found (HTTP 404). Check the record ID.",
        ),
        (500, {"code": PRIVATE}, "MyCase API returned HTTP 500: request failed."),
        (
            500,
            {"code": [PRIVATE], "error": {"code": {"private": PRIVATE}}},
            "MyCase API returned HTTP 500: request failed.",
        ),
        (
            422,
            {"error": {"code": "invalid_request", "message": PRIVATE}},
            "MyCase API returned HTTP 422: request rejected.",
        ),
    ],
)
def test_vendor_http_exact_result(fake_http, caplog, status, body, expected):
    caplog.set_level(logging.INFO)
    fake_http(status, body)
    assert _call() == expected
    assert PRIVATE not in caplog.text


@pytest.mark.parametrize("refresh_status", [400, 401, 403, 200])
def test_auth_rejection_and_repeated_401(fake_http, monkeypatch, refresh_status):
    fake_http(401, {"message": PRIVATE})
    monkeypatch.setattr(
        requests,
        "post",
        lambda *_a, **_k: SimpleNamespace(
            status_code=refresh_status,
            headers={},
            json=lambda: {"access_token": "fake-new"},
        ),
    )
    expected = (
        "MyCase access denied: the connected account lacks permission for this action "
        "(or the authorization expired; re-run mycase-mcp-setup if so)."
        if refresh_status == 403
        else REAUTHORIZE
    )
    assert _call() == expected


def test_expired_access_without_refresh_requires_reauthorization(
    fake_http, monkeypatch
):
    fake_http(401)
    monkeypatch.setattr(
        client.TokenManager, "_load", lambda self: {"access_token": "fake-access"}
    )
    assert _call() == REAUTHORIZE


@pytest.mark.parametrize(
    ("header", "seconds"),
    [("7", 7), ("999999999999", 999999999999), (PRIVATE, 10), ("-9", 1)],
)
def test_rate_limit_retry_hint_exact_result(fake_http, header, seconds):
    fake_http(429, {"message": PRIVATE}, retry=header)
    assert _call() == f"MyCase rate limit reached. Retry after {seconds} seconds."


def test_refresh_rate_limit_has_retry_hint(fake_http, monkeypatch):
    fake_http(401)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *_a, **_k: SimpleNamespace(
            status_code=429,
            headers={"Retry-After": "9"},
            json=lambda: {"message": PRIVATE},
        ),
    )
    assert _call() == "MyCase rate limit reached. Retry after 9 seconds."


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        (
            "get_case",
            {"case_id": PRIVATE, PRIVATE: PRIVATE},
            "Invalid argument 'case_id': expected integer.",
        ),
        ("get_case", {}, "Invalid argument 'case_id': expected integer."),
        (
            "list_cases",
            {"limit": 201},
            "Invalid argument 'limit': expected integer between 1 and 200.",
        ),
        (
            "list_cases",
            {"limit": 0},
            "Invalid argument 'limit': expected integer between 1 and 200.",
        ),
    ],
)
def test_argument_errors_are_exact_and_safe(caplog, name, arguments, expected):
    caplog.set_level(logging.INFO)
    assert _call(name, arguments) == expected
    assert PRIVATE not in caplog.text


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (requests.Timeout(PRIVATE), "MyCase request timed out. Retry shortly."),
        (
            requests.ConnectionError(PRIVATE),
            "Could not connect to MyCase. Check connectivity and retry.",
        ),
        (client.MyCaseToolError(PRIVATE), "Error executing tool who_am_i"),
        (RuntimeError(PRIVATE), "Error executing tool who_am_i"),
        (ValueError(PRIVATE), "Error executing tool who_am_i"),
    ],
)
def test_transport_errors_and_unknown_masking(
    fake_http, monkeypatch, caplog, error, expected
):
    caplog.set_level(logging.INFO)

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(requests.Session, "request", fail)
    assert _call() == expected
    assert PRIVATE not in caplog.text
    assert "Traceback" not in caplog.text
    if isinstance(error, (RuntimeError, ValueError)):
        assert "reason=unexpected" in caplog.text


def test_non_json_vendor_response_is_classified(fake_http):
    response = fake_http(200)

    def invalid_json():
        raise ValueError(PRIVATE)

    response.json = invalid_json
    assert _call() == "MyCase API returned HTTP 200: response was not valid JSON."


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_all_requests_have_timeout_and_redirects_disabled(
    fake_http, monkeypatch, method
):
    response = fake_http(302, {"success": True})
    observed = {}

    def capture(_self, actual_method, _url, **kwargs):
        observed.update(method=actual_method, **kwargs)
        return response

    monkeypatch.setattr(requests.Session, "request", capture)
    instance = client.MyCaseClient()
    with pytest.raises(client.VendorHTTPError):
        if method == "GET":
            instance.get("/cases")
        elif method == "POST":
            instance.post("/cases", {})
        elif method == "PUT":
            instance.put("/cases/1", {})
        else:
            instance.delete("/cases/1")
    assert observed["timeout"] == 30
    assert observed["allow_redirects"] is False


@pytest.mark.parametrize("status", [302, 307, 308])
def test_redirect_never_reports_success_even_with_json_body(fake_http, status):
    fake_http(status, {"success": True, "access_token": "private-token"})
    assert _call() == f"MyCase API returned HTTP {status}: request failed."


@pytest.mark.parametrize("status", [302, 307, 308])
def test_token_refresh_redirect_is_rejected_even_with_json_body(
    fake_http, monkeypatch, status
):
    fake_http(401)
    response = SimpleNamespace(
        status_code=status,
        headers={"Location": "https://example.test/private-token"},
        json=lambda: {"access_token": "private-token"},
    )
    calls = []

    def post(url, *, data, timeout, allow_redirects):
        calls.append((url, timeout, allow_redirects))
        return response

    monkeypatch.setattr(requests, "post", post)
    assert _call() == f"MyCase API returned HTTP {status}: request failed."
    assert calls == [(client.TOKEN_URL, 30, False)]


@pytest.mark.parametrize("status", [302, 307, 308])
def test_oauth_exchange_redirect_does_not_save_json_tokens(
    monkeypatch, capsys, tmp_path, status
):
    from mycase_mcp.setup import oauth_flow

    calls = []

    def post(url, *, data, timeout, allow_redirects):
        calls.append((url, timeout, allow_redirects))
        return SimpleNamespace(
            status_code=status,
            headers={"Location": "https://example.test/private-token"},
            json=lambda: {"access_token": "private-token"},
        )

    class CallbackServer:
        def handle_request(self):
            oauth_flow._auth_code = "fake-code"

        def server_close(self):
            pass

    monkeypatch.setattr("builtins.input", lambda _prompt: "fake-client")
    monkeypatch.setattr(oauth_flow, "getpass", lambda _prompt: "fake-secret")
    monkeypatch.setattr(oauth_flow.webbrowser, "open", lambda _url: True)
    monkeypatch.setattr(oauth_flow, "HTTPServer", lambda *_args: CallbackServer())
    monkeypatch.setattr(oauth_flow.requests, "post", post)
    monkeypatch.setattr(oauth_flow.credentials, "set_secret", lambda *_args: "file")
    monkeypatch.setattr(oauth_flow, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(oauth_flow, "_auth_code", None)
    monkeypatch.setattr(oauth_flow, "_oauth_state", None)

    with pytest.raises(SystemExit) as exit_result:
        oauth_flow.main()

    assert exit_result.value.code == 1
    assert calls == [(oauth_flow.TOKEN_URL, 30, False)]
    assert f"Token exchange failed ({status})" in capsys.readouterr().out
    assert not (tmp_path / "tokens.json").exists()


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_timeout_and_connection_outcomes_are_method_aware(
    fake_http, monkeypatch, method
):
    for failure_type in (requests.Timeout, requests.ConnectionError):

        def fail(*_args, **_kwargs):
            raise failure_type(PRIVATE)

        monkeypatch.setattr(requests.Session, "request", fail)
        if method == "GET":
            expected = (
                "MyCase request timed out. Retry shortly."
                if failure_type is requests.Timeout
                else "Could not connect to MyCase. Check connectivity and retry."
            )
            assert _call() == expected
        else:
            name = {
                "POST": "create_case",
                "PUT": "update_case",
                "DELETE": "delete_case",
            }[method]
            args = (
                {"name": "x"}
                if method == "POST"
                else {"case_id": 1, "name": "x"}
                if method == "PUT"
                else {"case_id": 1}
            )
            assert (
                _call(name, args)
                == f"MyCase {method} request outcome is unknown. Check whether it completed before retrying."
            )


def test_request_timeout_and_redirect_options_are_present(fake_http, monkeypatch):
    response = fake_http(200, {})
    calls = []

    def capture(_self, method, _url, **kwargs):
        calls.append((method, kwargs))
        return response

    monkeypatch.setattr(requests.Session, "request", capture)
    client.MyCaseClient().get("/cases")
    assert calls[0][1]["timeout"] == 30
    assert calls[0][1]["allow_redirects"] is False


def test_path_id_is_escaped(fake_http, monkeypatch):
    response = fake_http(200, {})
    urls = []

    def capture(_self, _method, url, **kwargs):
        urls.append(url)
        return response

    monkeypatch.setattr(requests.Session, "request", capture)
    client.MyCaseClient().get_case("../x")
    assert urls == [f"{client.BASE_URL}/cases/..%2Fx"]


@pytest.mark.parametrize(("header", "hint"), [("300", 300), ("60.1", 61)])
def test_retry_after_over_60_is_advised_without_sleep(
    fake_http, monkeypatch, header, hint
):
    fake_http(429, {}, retry=header)
    sleeps = []
    monkeypatch.setattr(client.time, "sleep", sleeps.append)
    assert _call() == f"MyCase rate limit reached. Retry after {hint} seconds."
    assert sleeps == []


def test_retry_after_cumulative_budget_does_not_exceed_60(fake_http, monkeypatch):
    response = fake_http(429, {}, retry="31")
    calls = []
    sleeps = []

    def repeated(*_args, **_kwargs):
        calls.append(1)
        return response

    monkeypatch.setattr(requests.Session, "request", repeated)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)
    assert _call() == "MyCase rate limit reached. Retry after 31 seconds."
    assert sleeps == [31]
    assert len(calls) == 2


def test_retry_budget_survives_token_refresh(fake_http, monkeypatch):
    responses = [
        SimpleNamespace(status_code=status, headers={"Retry-After": "31"})
        for status in (429, 401, 429)
    ]
    monkeypatch.setattr(requests.Session, "request", lambda *_a, **_k: responses.pop(0))
    monkeypatch.setattr(
        requests,
        "post",
        lambda *_a, **_k: SimpleNamespace(
            status_code=200, json=lambda: {"access_token": "fake"}
        ),
    )
    sleeps = []
    monkeypatch.setattr(client.time, "sleep", sleeps.append)
    assert _call() == "MyCase rate limit reached. Retry after 31 seconds."
    assert sleeps == [31]
    assert responses == []


def test_retry_hint_rejects_extreme_exponents_without_allocating_large_integer():
    response = SimpleNamespace(headers={"Retry-After": "1e999999999"})
    assert client._safe_retry_after(response) == 10


def test_unknown_resource_failure_is_redacted(caplog, monkeypatch):
    caplog.set_level(logging.ERROR)
    private = PRIVATE
    original = server.mcp._resource_manager.get_resource

    async def fail(*_args, **_kwargs):
        raise RuntimeError(private)

    monkeypatch.setattr(server.mcp._resource_manager, "get_resource", fail)
    try:
        with pytest.raises(Exception) as caught:
            asyncio.run(server.mcp.read_resource("mycase://practice_areas"))
        assert str(caught.value) == "Error reading resource"
        assert private not in caplog.text
        assert "Traceback" not in caplog.text
    finally:
        monkeypatch.setattr(server.mcp._resource_manager, "get_resource", original)


def test_token_file_is_created_atomically_with_private_mode(tmp_path, monkeypatch):
    import os

    original_dump = client.json.dump
    modes = []

    def checked_dump(value, stream, **kwargs):
        modes.append(os.fstat(stream.fileno()).st_mode & 0o777)
        return original_dump(value, stream, **kwargs)

    monkeypatch.setattr(client.json, "dump", checked_dump)
    manager = client.TokenManager()
    manager.token_file = tmp_path / "tokens.json"
    manager.token_file.write_text("{}")
    manager.token_file.chmod(0o644)
    manager.save({"access_token": "fake"})
    assert manager.token_file.stat().st_mode & 0o777 == 0o600
    assert modes == [0o600]
    assert not list(tmp_path.glob(".tokens-*"))


def test_setup_eof_exits_cleanly(monkeypatch, capsys):
    from mycase_mcp.setup import oauth_flow

    def eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    with pytest.raises(SystemExit) as exit_result:
        oauth_flow.main()
    assert exit_result.value.code == 1
    output = capsys.readouterr().out
    assert "credentials were not provided" in output
    assert "Traceback" not in output


def test_setup_empty_credentials_exits_clearly(monkeypatch, capsys):
    from mycase_mcp.setup import oauth_flow

    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    monkeypatch.setattr(oauth_flow, "getpass", lambda _prompt: "")
    with pytest.raises(SystemExit) as exit_result:
        oauth_flow.main()
    assert exit_result.value.code == 1
    assert "Client ID and Secret are required" in capsys.readouterr().out


@pytest.mark.parametrize("status", [401, 403])
def test_setup_bad_key_response_exits_without_leaking(
    monkeypatch, capsys, tmp_path, status
):
    from mycase_mcp.setup import oauth_flow

    answers = iter(["fake-client"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(oauth_flow, "getpass", lambda _prompt: "fake-secret")
    monkeypatch.setattr(oauth_flow.webbrowser, "open", lambda _url: True)

    class CallbackServer:
        def handle_request(self):
            oauth_flow._auth_code = "fake-code"

        def server_close(self):
            pass

    monkeypatch.setattr(oauth_flow, "HTTPServer", lambda *_args: CallbackServer())
    monkeypatch.setattr(
        oauth_flow.requests,
        "post",
        lambda *_args, **_kwargs: SimpleNamespace(status_code=status),
    )
    monkeypatch.setattr(oauth_flow, "CONFIG_DIR", tmp_path)
    with pytest.raises(SystemExit) as exit_result:
        oauth_flow.main()
    assert exit_result.value.code == 1
    output = capsys.readouterr().out
    if status == 403:
        assert str(client.AccessDeniedError()) in output
    else:
        assert "Token exchange failed (401)" in output
    assert "fake-secret" not in output
    assert "Traceback" not in output


def test_setup_token_exchange_timeout_reports_unknown_outcome(
    monkeypatch, capsys, tmp_path
):
    from mycase_mcp.setup import oauth_flow

    monkeypatch.setattr("builtins.input", lambda _prompt: "fake-client")
    monkeypatch.setattr(oauth_flow, "getpass", lambda _prompt: "fake-secret")
    monkeypatch.setattr(oauth_flow.webbrowser, "open", lambda _url: True)

    class CallbackServer:
        def handle_request(self):
            oauth_flow._auth_code = "fake-code"

        def server_close(self):
            pass

    monkeypatch.setattr(oauth_flow, "HTTPServer", lambda *_args: CallbackServer())

    def timeout(*_args, **_kwargs):
        raise requests.Timeout(PRIVATE)

    monkeypatch.setattr(oauth_flow.requests, "post", timeout)
    monkeypatch.setattr(oauth_flow, "CONFIG_DIR", tmp_path)
    with pytest.raises(SystemExit) as exit_result:
        oauth_flow.main()
    assert exit_result.value.code == 1
    output = capsys.readouterr().out
    assert "outcome is unknown" in output
    assert "before retrying setup" in output
    assert PRIVATE not in output
    assert "Traceback" not in output
