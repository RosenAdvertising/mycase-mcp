"""Protocol error results use safe, exact messages with isError=true."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Any, cast

import pytest
import requests
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolRequestParams

from mycase_mcp import client, server

SETUP = (
    "MyCase is not configured. Run mycase-mcp-setup to connect your account "
    "and configure the required OAuth credentials."
)
REAUTHORIZE = (
    "The MyCase authorization expired or was rejected. "
    "Run mycase-mcp-setup to reauthorize the account."
)
PRIVATE = "private-token private@example.test https://example.test/?key=private"


def _call(name="who_am_i", arguments=None):
    result = asyncio.run(
        server.mcp._handle_call_tool(
            cast(Any, None), CallToolRequestParams(name=name, arguments=arguments or {})
        )
    )
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
        (403, {"error": PRIVATE}, REAUTHORIZE),
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
    assert _call() == REAUTHORIZE


def test_expired_access_without_refresh_requires_reauthorization(
    fake_http, monkeypatch
):
    fake_http(401)
    monkeypatch.setattr(
        client.TokenManager, "_load", lambda self: {"access_token": "fake-access"}
    )
    assert _call() == REAUTHORIZE


@pytest.mark.parametrize(
    ("header", "seconds"), [("7", 7), ("999999999999", 300), (PRIVATE, 10), ("-9", 1)]
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
