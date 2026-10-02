"""Destination policy at the real MCP protocol and requests transport boundary.

Vendor examples (both use the same path):
https://mycaseapi.stoplight.io/docs/mycase-api-documentation/rh7lgmsrahr9d-document-request
https://mycaseapi.stoplight.io/docs/mycase-api-documentation/zlvjohvugwzvt-document-request
"""

import asyncio
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
import requests
from mcp import ClientSession
from mcp.client._memory import InMemoryTransport

from mycase_mcp import client as client_module, server
from mycase_mcp.url_validation import DESTINATION_SETTING, DESTINATION_KEYS
from test_public6_security import BAD_URLS


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.delenv(DESTINATION_SETTING, raising=False)
    client = object.__new__(client_module.MyCaseClient)
    client.session = requests.Session()
    response = Mock(status_code=201, headers={})
    response.json.return_value = {"id": 123}
    transport = Mock(return_value=response)
    monkeypatch.setattr(requests.Session, "request", transport)
    monkeypatch.setattr(server, "MyCaseClient", lambda: client)

    async def invoke(name, arguments):
        async with InMemoryTransport(server.mcp) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(name, arguments)

    return lambda name, args: asyncio.run(invoke(name, args)), transport


UPLOADS = [
    ("upload_document", {"filename": "file.txt"}, "/documents"),
    (
        "upload_case_document",
        {"case_id": 123, "filename": "file.txt"},
        "/cases/123/documents",
    ),
]
VENDOR_PATH = "example_folder1/example_folder2/example_name"


@pytest.mark.parametrize("name,args,endpoint", UPLOADS)
@pytest.mark.parametrize(
    "path",
    [
        VENDOR_PATH,
        "report.pdf",
        "Client Files/2026/Report (1).pdf",
        "a" * 255,
        "/".join(["a" * 255] * 3 + ["a" * 254, "b"]),
    ],
)
def test_safe_relative_path_passes(boundary, name, args, endpoint, path):
    call, transport = boundary
    result = call(name, {**args, "path": path})
    assert not result.is_error, result
    transport.assert_called_once()
    assert transport.call_args.args == ("POST", client_module.BASE_URL + endpoint)
    assert transport.call_args.kwargs["json"]["path"] == path


BAD_PATHS = [
    "",
    "/name",
    "\\name",
    "//example.com/name",
    "\\\\example.com\\name",
    ".",
    "..",
    "./name",
    "../name",
    "a/./name",
    "a/../name",
    "a//name",
    "a/",
    "https://example.com/name",
    "http://example.com/name",
    "ftp://example.com/name",
    "file:///etc/passwd",
    "data:text/plain,hello",
    "mailto:a@example.com",
    "https:name",
    "example.com/name",
    "www.example.com",
    "127.0.0.1/name",
    "localhost/name",
    "C:/name",
    "a\\name",
    "a/%2e%2e/name",
    "a/%252e%252e/name",
    "a%2fname",
    "a%5cname",
    "a%00name",
    "a/%EF%BC%8F/name",
    "a\u2215..\u2215name",
    "a\uff0f..\uff0fname",
    "a\u2044name",
    "a\uff3cname",
    "a/\uff0e\uff0e/name",
    "a\x00name",
    "a\nname",
    "a\rname",
    "a\tname",
    "a\x7fname",
    "a\x85name",
    "a\u202ename",
    "a\u200bname",
    "a?url=https://example.com",
    "a#name",
    "a@host",
    " a/name",
    "a /name",
    "a./name",
    "a" * 256,
    "/".join(["a" * 255] * 4) + "/a",
]


@pytest.mark.parametrize("name,args,endpoint", UPLOADS)
@pytest.mark.parametrize("path", BAD_PATHS)
def test_unsafe_path_has_zero_requests(boundary, name, args, endpoint, path):
    call, transport = boundary
    result = call(name, {**args, "path": path})
    assert result.is_error
    assert "relative MyCase" in str(result.content)
    transport.assert_not_called()


HOOK_ARGS = {"model": "case", "actions": "created"}


@pytest.mark.parametrize(
    "allowlist,url",
    [
        ("hooks.example.com", "https://hooks.example.com/callback"),
        (
            " HOOKS.EXAMPLE.COM. , other.example.com ",
            "https://Hooks.Example.Com./callback",
        ),
        (".example.com", "https://example.com/hook"),
        (".example.com", "https://one.two.example.com/hook"),
        ("bücher.example", "https://xn--bcher-kva.example/hook"),
    ],
)
def test_allowlisted_webhook_passes(boundary, monkeypatch, allowlist, url):
    monkeypatch.setenv(DESTINATION_SETTING, allowlist)
    call, transport = boundary
    result = call("create_webhook_subscription", {**HOOK_ARGS, "url": url})
    assert not result.is_error, result
    transport.assert_called_once()
    assert transport.call_args.kwargs["json"] == {
        "model": "case",
        "actions": ["created"],
        "url": url,
    }


@pytest.mark.parametrize(
    "allowlist,url",
    [
        ("hooks.example.com", "https://unlisted.example.com/hook"),
        ("hooks.example.com", "https://127.0.0.1.sslip.io/hook"),
        (
            "hooks.example.com",
            "https://httpbin.org/redirect-to?url=https://hooks.example.com",
        ),
        ("hooks.example.com", "https://redirect.example.net/?target=https://127.0.0.1"),
        ("hooks.example.com", "https://sub.hooks.example.com/hook"),
        (".example.com", "https://notexample.com/hook"),
        (".example.com", "https://example.com.evil.org/hook"),
        ("hooks.example.com", "https://hooks.example.com@evil.org/"),
        ("hooks.example.com", "https://hooks.example.com%2eevil.org/"),
        ("hooks.example.com", "https://hooks\uff0eexample.com/"),
        ("hooks.example.com", "https://hooks.example.com/\n"),
        ("hooks.example.com", "https://hooks.example.com\\@evil.org/"),
        ("hooks.example.com", "https://hooks.example.com../"),
        ("", "https://hooks.example.com/hook"),
        (" , , ", "https://hooks.example.com/hook"),
        (None, "https://hooks.example.com/hook"),
        ("*.example.com", "https://hooks.example.com/hook"),
        ("https://hooks.example.com", "https://hooks.example.com/hook"),
        ("hooks.example.com,malformed/rule", "https://hooks.example.com/hook"),
    ],
)
def test_disallowed_webhook_has_zero_requests(boundary, monkeypatch, allowlist, url):
    if allowlist is not None:
        monkeypatch.setenv(DESTINATION_SETTING, allowlist)
    call, transport = boundary
    result = call("create_webhook_subscription", {**HOOK_ARGS, "url": url})
    assert result.is_error, result
    if allowlist in (None, "", " , , "):
        assert DESTINATION_SETTING in str(result.content)
    transport.assert_not_called()


@pytest.mark.parametrize(
    "key",
    sorted(DESTINATION_KEYS)
    + ["targetUrl", "target_url", "TARGET-URL", "baseUrlPattern", " Callback_Url "],
)
@pytest.mark.parametrize(
    "value",
    ["https://unlisted.example.com/", None, {"nested": "https://hooks.example.com"}],
)
def test_nested_destination_keys_cannot_smuggle(boundary, monkeypatch, key, value):
    monkeypatch.setenv(DESTINATION_SETTING, "hooks.example.com")
    call, transport = boundary
    result = call(
        "upload_document",
        {"filename": "file.txt", "path": VENDOR_PATH, "extra": [{key: value}]},
    )
    assert result.is_error
    transport.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"targetUrl": "https://hooks.example.com/hook"},
        {
            "my_url_notes": "https://unlisted.example.com/",
            "url_count": 2,
            "callbackUrlDescription": "notes",
        },
    ],
)
def test_nested_validation_matches_only_explicit_keys(boundary, monkeypatch, extra):
    monkeypatch.setenv(DESTINATION_SETTING, "hooks.example.com")
    call, transport = boundary
    result = call(
        "upload_document",
        {"filename": "file.txt", "path": VENDOR_PATH, "extra": [extra]},
    )
    assert not result.is_error
    transport.assert_called_once()


def test_model_cannot_supply_allowlist(boundary):
    call, transport = boundary
    result = call(
        "create_webhook_subscription",
        {
            **HOOK_ARGS,
            "url": "https://hooks.example.com/hook",
            DESTINATION_SETTING: "hooks.example.com",
        },
    )
    assert result.is_error
    assert DESTINATION_SETTING in str(result.content)
    transport.assert_not_called()


# Reuse every round-1 literal probe, now asserting at Session.request with the
# candidate host present in configuration so an empty list cannot mask failures.
@pytest.mark.parametrize(
    "url",
    BAD_URLS
    + [
        "https://[fc00::1]/",
        "https://[::]/",
        "https://[ff02::1]/",
        "https://0.0.0.0/",
        "https://127.0.0.1/",
        "https://172.16.0.1/",
        "https://example.com\x00/",
        "https://exämple.com/",
        "https://example.com:bad/",
    ],
)
def test_all_literal_probes_refused_even_when_allowlisted(boundary, monkeypatch, url):
    monkeypatch.setenv(
        DESTINATION_SETTING,
        (urlsplit(url).hostname or "example.com").replace("\x00", ""),
    )
    call, transport = boundary
    result = call("create_webhook_subscription", {**HOOK_ARGS, "url": url})
    assert result.is_error
    assert "HTTPS" in str(result.content)
    transport.assert_not_called()
