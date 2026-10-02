"""Offline reproductions of PUBLIC6 findings through real MCP/setup boundaries."""

import asyncio
from unittest.mock import Mock

import pytest
from mcp import ClientSession
from mcp.client._memory import InMemoryTransport
from mycase_mcp import client as client_module, server


@pytest.fixture
def boundary(monkeypatch):
    client = object.__new__(client_module.MyCaseClient)
    calls = Mock(return_value={"id": "123"})
    for name in ("get", "put", "patch", "post", "_detail", "_send", "_request"):
        monkeypatch.setattr(client, name, calls, raising=False)
    monkeypatch.setattr(server, "MyCaseClient", lambda: client)
    for name in ("_c", "_client", "get_client"):
        if hasattr(server, name):
            monkeypatch.setattr(server, name, lambda: client)

    async def invoke(name, arguments):
        async with InMemoryTransport(server.mcp) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(name, arguments)

    return lambda name, arguments: asyncio.run(invoke(name, arguments)), calls


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("update_case", {"case_id": 123}),
        ("update_client", {"client_id": 123}),
        ("update_company", {"company_id": 123}),
        ("update_task", {"task_id": 123}),
        ("update_event", {"event_id": 123}),
        ("update_note", {"note_id": 123}),
        ("update_document", {"doc_id": 123}),
        ("update_lead", {"lead_id": 123}),
        ("update_location", {"location_id": 123}),
        ("update_call", {"call_id": 123}),
    ],
)
def test_empty_write_rejected_at_mcp_boundary(boundary, name, arguments):
    call, requests = boundary
    result = call(name, arguments)
    assert result.is_error, result
    assert any(
        "field" in item.text or "non-empty" in item.text for item in result.content
    )
    requests.assert_not_called()


BAD_URLS = [
    "file:///etc/passwd",
    "http://2130706433/",
    "https://2130706433/",
    "https://0x7f000001/",
    "https://017700000001/",
    "https://127.1/",
    "https://0177.0.0.1/",
    "https://[::ffff:127.0.0.1]/",
    "https://[::1]/",
    "https://[fe80::1]/",
    "https://169.254.169.254/",
    "https://10.0.0.1/",
    "https://192.168.1.1/",
    "https://100.64.0.1/",
    "https://localhost/",
    "https://localhost.localdomain/",
    "https://a.localhost./",
    "https://host.local/",
    "https://user:pass@example.com/",
    "https://%31%32%37.0.0.1/",
    "https://example.com:8443/",
    "https://example.com/#fragment",
    "https://224.0.0.1/",
    "https://[::ffff:0:127.0.0.1]/",
]


@pytest.mark.parametrize("url", BAD_URLS)
@pytest.mark.parametrize(
    "name,arguments,key",
    [
        ("create_webhook_subscription", {"model": "case", "actions": "created"}, "url"),
        ("upload_document", {"filename": "test.txt"}, "path"),
        ("upload_case_document", {"case_id": 123, "filename": "test.txt"}, "path"),
    ],
)
def test_unsafe_url_rejected_at_mcp_boundary(boundary, url, name, arguments, key):
    call, requests = boundary
    result = call(name, {**arguments, key: url})
    assert result.is_error
    assert ("HTTPS" if key == "url" else "relative MyCase") in str(result.content)
    requests.assert_not_called()


def test_verify_uses_secret_store_without_fallback_file(monkeypatch, tmp_path):
    from mycase_mcp.setup import verify

    monkeypatch.setattr(verify, "CONFIG_DIR", tmp_path)
    (tmp_path / "tokens.json").write_text("{}")
    lookup = Mock(
        side_effect=lambda key: (
            "dummy" if key in {"MYCASE_CLIENT_ID", "MYCASE_CLIENT_SECRET"} else ""
        )
    )
    monkeypatch.setattr(verify.credentials, "get_secret", lookup)
    assert verify.check_config()
    assert lookup.call_count == 2
    assert not (tmp_path / ".env").exists()
    lookup.side_effect = lambda key: ""
    assert not verify.check_config()
