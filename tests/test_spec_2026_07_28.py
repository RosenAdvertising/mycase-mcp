"""Offline raw-wire conformance regressions for MCP 2026-07-28."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
from mcp import Client
from mcp.types import LATEST_PROTOCOL_VERSION
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

from mycase_mcp import server


PROTOCOL_VERSION = "2026-07-28"
LEGACY_PROTOCOL_VERSION = "2025-11-25"
PROTOCOL_VERSION_META_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_CAPABILITIES_META_KEY = "io.modelcontextprotocol/clientCapabilities"
CLIENT_INFO_META_KEY = "io.modelcontextprotocol/clientInfo"
SERVER_INFO_META_KEY = "io.modelcontextprotocol/serverInfo"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _modern_request(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    protocol_version: str = PROTOCOL_VERSION,
    request_id: int = 1,
) -> tuple[dict[str, str], dict[str, Any]]:
    request_params = dict(params or {})
    request_params["_meta"] = {
        PROTOCOL_VERSION_META_KEY: protocol_version,
        CLIENT_CAPABILITIES_META_KEY: {},
        CLIENT_INFO_META_KEY: {"name": "mycase-spec-test", "version": "0"},
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "mcp-protocol-version": protocol_version,
        "mcp-method": method,
    }
    if method == "tools/call":
        headers["mcp-name"] = str(request_params["name"])
    elif method == "prompts/get":
        headers["mcp-name"] = str(request_params["name"])
    elif method == "resources/read":
        headers["mcp-name"] = str(request_params["uri"])
    return headers, {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": request_params,
    }


async def _post_modern(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    protocol_version: str = PROTOCOL_VERSION,
    header_overrides: dict[str, str] | None = None,
    drop_headers: set[str] | None = None,
) -> httpx.Response:
    app = server.mcp.streamable_http_app(
        host="127.0.0.1",
        stateless_http=True,
        json_response=True,
    )
    headers, body = _modern_request(
        method,
        params,
        protocol_version=protocol_version,
    )
    if header_overrides:
        headers.update(header_overrides)
    for header in drop_headers or set():
        headers.pop(header, None)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:8000",
        ) as client:
            return await client.post("/mcp", headers=headers, json=body)


def _result(response: httpx.Response) -> dict[str, Any]:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    return payload["result"]


def test_spec_guard_pins_the_2026_revision() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tests" / "spec_check.py")],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Spec check: PASS" in result.stdout
    assert LATEST_PROTOCOL_VERSION == PROTOCOL_VERSION
    assert MODERN_PROTOCOL_VERSIONS == (PROTOCOL_VERSION,)


def test_modern_discovery_is_sessionless_and_declares_actual_capabilities() -> None:
    response = asyncio.run(_post_modern("server/discover"))
    result = _result(response)

    assert "mcp-session-id" not in response.headers
    assert result["supportedVersions"] == [PROTOCOL_VERSION]
    assert result["resultType"] == "complete"
    assert result["ttlMs"] == 0
    assert result["cacheScope"] == "private"
    assert result["capabilities"] == {
        "prompts": {"listChanged": True},
        "resources": {"listChanged": True, "subscribe": True},
        "tools": {"listChanged": True},
    }
    assert "extensions" not in result["capabilities"]
    assert result["_meta"][SERVER_INFO_META_KEY]["name"] == "mycase-mcp"
    assert result["_meta"][SERVER_INFO_META_KEY]["version"] == "0.1.0"


def test_client_defaults_modern_and_retains_legacy_negotiation() -> None:
    async def negotiate() -> tuple[str, str]:
        async with Client(server.mcp, cache=None) as modern:
            modern_version = modern.protocol_version
        async with Client(server.mcp, mode="legacy", cache=None) as legacy:
            legacy_version = legacy.protocol_version
        return modern_version, legacy_version

    modern_version, legacy_version = asyncio.run(negotiate())
    assert modern_version == PROTOCOL_VERSION
    assert legacy_version == LEGACY_PROTOCOL_VERSION


def test_cacheable_results_are_complete_private_and_deterministic() -> None:
    async def list_results() -> list[dict[str, Any]]:
        methods = (
            "tools/list",
            "tools/list",
            "prompts/list",
            "resources/list",
            "resources/templates/list",
        )
        return [_result(await _post_modern(method)) for method in methods]

    first_tools, second_tools, prompts, resources, templates = asyncio.run(
        list_results()
    )
    for result in (first_tools, second_tools, prompts, resources, templates):
        assert result["resultType"] == "complete"
        assert result["ttlMs"] == 0
        assert result["cacheScope"] == "private"

    first_names = [tool["name"] for tool in first_tools["tools"]]
    second_names = [tool["name"] for tool in second_tools["tools"]]
    assert first_names == second_names
    assert len(first_names) == 112
    assert all(tool["inputSchema"]["type"] == "object" for tool in first_tools["tools"])
    assert len(prompts["prompts"]) == 3
    assert [item["uri"] for item in resources["resources"]] == [
        "mycase://practice_areas",
        "mycase://case_stages",
        "mycase://security-notes",
    ]
    assert templates["resourceTemplates"] == []


def test_resource_read_cache_hints_and_not_found_error() -> None:
    found = asyncio.run(
        _post_modern("resources/read", {"uri": "mycase://security-notes"})
    )
    result = _result(found)
    assert result["resultType"] == "complete"
    assert result["ttlMs"] == 0
    assert result["cacheScope"] == "private"
    assert "Data sensitivity" in result["contents"][0]["text"]

    missing = asyncio.run(
        _post_modern("resources/read", {"uri": "mycase://does-not-exist"})
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == -32602


def test_modern_tool_result_is_complete(monkeypatch) -> None:
    class StubMyCaseClient:
        def list_staff(self, page_size: int = 50) -> list[dict[str, Any]]:
            return [{"id": 7, "role": "staff"}][:page_size]

    monkeypatch.setattr(server, "MyCaseClient", StubMyCaseClient)
    response = asyncio.run(
        _post_modern(
            "tools/call",
            {"name": "list_staff", "arguments": {"limit": 1}},
        )
    )
    result = _result(response)
    assert result["resultType"] == "complete"
    assert json.loads(result["content"][0]["text"]) == [
        {"id": 7, "role": "staff"}
    ]


def test_raw_modern_requests_carry_protocol_method_and_name_headers() -> None:
    headers, _body = _modern_request(
        "tools/call",
        {"name": "list_staff", "arguments": {"limit": 1}},
    )
    assert headers["mcp-protocol-version"] == PROTOCOL_VERSION
    assert headers["mcp-method"] == "tools/call"
    assert headers["mcp-name"] == "list_staff"


def test_http_requires_method_and_name_routing_headers() -> None:
    cases = (
        ("tools/list", {}, {"mcp-method"}),
        (
            "tools/call",
            {"name": "list_staff", "arguments": {"limit": 1}},
            {"mcp-name"},
        ),
    )
    for method, params, dropped in cases:
        response = asyncio.run(
            _post_modern(method, params, drop_headers=dropped)
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32020


def test_http_routing_version_and_unknown_method_errors() -> None:
    mismatch = asyncio.run(
        _post_modern(
            "tools/list",
            header_overrides={"mcp-method": "resources/list"},
        )
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["error"]["code"] == -32020

    unsupported = asyncio.run(_post_modern("tools/list", protocol_version="2099-01-01"))
    assert unsupported.status_code == 400
    assert unsupported.json()["error"] == {
        "code": -32022,
        "message": "Unsupported protocol version",
        "data": {
            "supported": [PROTOCOL_VERSION],
            "requested": "2099-01-01",
        },
    }

    unknown = asyncio.run(_post_modern("example/unknown"))
    assert unknown.status_code == 404
    assert unknown.json()["error"] == {
        "code": -32601,
        "message": "Method not found",
        "data": "example/unknown",
    }
