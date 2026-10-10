"""Stateless Streamable HTTP serving against the repo's create_serve_app()."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import requests
from mcp.server import MCPServer
from mcp_types import Tool

from mycase_mcp import client, server


PROTOCOL_VERSION = "2026-07-28"
PROTOCOL_VERSION_META_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_CAPABILITIES_META_KEY = "io.modelcontextprotocol/clientCapabilities"
CLIENT_INFO_META_KEY = "io.modelcontextprotocol/clientInfo"
SERVER_INFO_META_KEY = "io.modelcontextprotocol/serverInfo"


def _clear_transport_env(monkeypatch) -> None:
    for key in (
        "MYCASE_MCP_TRANSPORT",
        "MYCASE_MCP_HOST",
        "PORT",
        "MYCASE_MCP_ALLOWED_HOSTS",
        "MYCASE_MCP_ALLOWED_ORIGINS",
    ):
        monkeypatch.delenv(key, raising=False)


def _headers(method: str, params: dict[str, Any] | None = None) -> dict[str, str]:
    request_params = dict(params or {})
    headers = {
        # create_serve_app() keeps the SDK's SSE default, so clients must
        # accept both the JSON envelope and the event-stream upgrade.
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": PROTOCOL_VERSION,
        "mcp-method": method,
    }
    if method == "tools/call":
        headers["mcp-name"] = str(request_params["name"])
    elif method == "prompts/get":
        headers["mcp-name"] = str(request_params["name"])
    elif method == "resources/read":
        headers["mcp-name"] = str(request_params["uri"])
    return headers


def _body(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: int = 1,
) -> dict[str, Any]:
    request_params = dict(params or {})
    request_params["_meta"] = {
        PROTOCOL_VERSION_META_KEY: PROTOCOL_VERSION,
        CLIENT_CAPABILITIES_META_KEY: {},
        CLIENT_INFO_META_KEY: {"name": "mycase-http-test", "version": "0"},
    }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": request_params,
    }


def _result(response: httpx.Response) -> dict[str, Any]:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    return payload["result"]


async def _post(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    app: Any,
    host: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    headers = _headers(method, params)
    if host is not None:
        headers["host"] = host
    headers.update(extra_headers or {})
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8000"
        ) as http:
            return await http.post("/mcp", headers=headers, json=_body(method, params))


@pytest.fixture
def vendor_mock(monkeypatch, tmp_path):
    """The fake HTTP vendor used across this repo's test suite (test_tool_errors)."""
    monkeypatch.setattr(client, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(client, "CLIENT_ID", "fake-client")
    monkeypatch.setattr(client, "CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr(
        client.TokenManager,
        "_load",
        lambda self: {"access_token": "fake-access", "refresh_token": "fake-refresh"},
    )

    def configure(status=200, body=None):
        response = SimpleNamespace(
            status_code=status,
            ok=200 <= status < 400,
            headers={"Retry-After": "7"},
            json=lambda: body,
        )
        monkeypatch.setattr(requests.Session, "request", lambda *_a, **_k: response)
        return response

    return configure


def test_http_tools_list_matches_stdio_tools(monkeypatch) -> None:
    _clear_transport_env(monkeypatch)
    app = server.create_serve_app()

    async def scenario() -> tuple[list[Tool], httpx.Response]:
        stdio_tools = await server.mcp.list_tools()
        response = await _post("tools/list", app=app)
        return stdio_tools, response

    stdio_tools, response = asyncio.run(scenario())
    result = _result(response)
    http_tools = result["tools"]

    assert [tool["name"] for tool in http_tools] == [tool.name for tool in stdio_tools]
    assert {tool["name"]: tool["inputSchema"] for tool in http_tools} == {
        tool.name: tool.input_schema for tool in stdio_tools
    }


def test_read_tool_runs_end_to_end_over_http(monkeypatch, vendor_mock) -> None:
    _clear_transport_env(monkeypatch)
    vendor_response = vendor_mock(200, {"id": 7, "role": "staff"})
    vendor_requests = []

    def request(session, method, url, **kwargs):
        vendor_requests.append((method, url, session.headers["Authorization"]))
        return vendor_response

    monkeypatch.setattr(requests.Session, "request", request)
    app = server.create_serve_app()

    response = asyncio.run(
        _post(
            "tools/call",
            {"name": "who_am_i", "arguments": {}},
            app=app,
            extra_headers={"authorization": "Bearer fake-request-credential"},
        )
    )
    result = _result(response)
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == {"id": 7, "role": "staff"}
    assert vendor_requests == [("GET", f"{client.BASE_URL}/me", "Bearer fake-access")]


def test_responses_are_sessionless_and_share_no_state(monkeypatch, vendor_mock) -> None:
    _clear_transport_env(monkeypatch)
    vendor_mock(200, {"id": 7, "role": "staff"})
    connections = []
    counts = []
    call_tool = server.mcp.call_tool

    async def observe_state(name, arguments=None, context=None):
        connection = context.request_context.session._connection
        connections.append(connection)
        connection.state["calls"] = connection.state.get("calls", 0) + 1
        counts.append(connection.state["calls"])
        return await call_tool(name, arguments, context)

    monkeypatch.setattr(server.mcp, "call_tool", observe_state)
    app = server.create_serve_app()
    params = {"name": "who_am_i", "arguments": {}}

    async def scenario() -> list[httpx.Response]:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://127.0.0.1:8000"
            ) as http:
                return await asyncio.gather(
                    *(
                        http.post(
                            "/mcp",
                            headers={
                                **_headers("tools/call", params),
                                "mcp-session-id": "ignored-client-session",
                            },
                            json=_body("tools/call", params),
                        )
                        for _ in range(2)
                    )
                )

    first, second = asyncio.run(scenario())
    assert "mcp-session-id" not in first.headers
    assert "mcp-session-id" not in second.headers
    assert _result(first)["content"] == _result(second)["content"]
    assert counts == [1, 1]
    assert connections[0] is not connections[1]
    assert all(connection.session_id is None for connection in connections)


def test_bogus_transport_exits_naming_both_options(monkeypatch) -> None:
    monkeypatch.setenv("MYCASE_MCP_TRANSPORT", "bogus")
    with pytest.raises(SystemExit) as excinfo:
        server.main()
    message = str(excinfo.value)
    assert "bogus" in message
    assert "stdio" in message
    assert "streamable-http" in message


def test_default_transport_is_stdio(monkeypatch) -> None:
    monkeypatch.delenv("MYCASE_MCP_TRANSPORT", raising=False)
    assert server._requested_transport() == "stdio"
    monkeypatch.setenv("MYCASE_MCP_TRANSPORT", "")
    assert server._requested_transport() == "stdio"
    monkeypatch.setenv("MYCASE_MCP_TRANSPORT", "  STREAMABLE-HTTP  ")
    assert server._requested_transport() == "streamable-http"


def test_main_preserves_stdio_run_call(monkeypatch) -> None:
    _clear_transport_env(monkeypatch)
    calls = []
    monkeypatch.setattr(
        server.mcp, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    server.main()
    assert calls == [((), {})]


def test_main_selects_http_transport(monkeypatch) -> None:
    monkeypatch.setenv("MYCASE_MCP_TRANSPORT", " STREAMABLE-HTTP ")
    calls = []

    async def serve():
        calls.append("http")

    monkeypatch.setattr(server, "_serve_streamable_http", serve)
    server.main()
    assert calls == ["http"]


def test_tool_cancellation_propagates(monkeypatch) -> None:
    async def cancel(*args, **kwargs):
        raise asyncio.CancelledError("client disconnected")

    monkeypatch.setattr(MCPServer, "call_tool", cancel)
    with pytest.raises(asyncio.CancelledError, match="client disconnected"):
        asyncio.run(server.mcp.call_tool("who_am_i", {}))


def test_port_must_be_an_integer(monkeypatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    assert server._port() == 8080
    monkeypatch.setenv("PORT", "9100")
    assert server._port() == 9100
    monkeypatch.setenv("PORT", "not-a-port")
    with pytest.raises(SystemExit) as excinfo:
        server._port()
    assert "PORT" in str(excinfo.value)
    assert "not-a-port" in str(excinfo.value)


def test_loopback_host_needs_no_allowed_hosts(monkeypatch) -> None:
    _clear_transport_env(monkeypatch)
    assert server._transport_security() is None
    monkeypatch.setenv("MYCASE_MCP_HOST", "localhost")
    assert server._transport_security() is None


def test_loopback_sdk_protection_refuses_bad_host_and_origin(monkeypatch) -> None:
    _clear_transport_env(monkeypatch)

    async def scenario():
        app = server.create_serve_app()
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://127.0.0.1:8000"
            ) as http:
                bad_host = await http.post(
                    "/mcp",
                    headers={**_headers("tools/list"), "host": "evil.example"},
                    json=_body("tools/list"),
                )
                bad_origin = await http.post(
                    "/mcp",
                    headers={
                        **_headers("tools/list"),
                        "origin": "https://evil.example",
                    },
                    json=_body("tools/list"),
                )
                return bad_host, bad_origin

    bad_host, bad_origin = asyncio.run(scenario())
    assert bad_host.status_code == 421
    assert bad_origin.status_code == 403


@pytest.mark.parametrize("allowed_hosts", [None, "", " ", ",", " , , "])
def test_non_loopback_host_without_allowed_hosts_exits(
    monkeypatch, allowed_hosts
) -> None:
    _clear_transport_env(monkeypatch)
    monkeypatch.setenv("MYCASE_MCP_HOST", "0.0.0.0")
    if allowed_hosts is not None:
        monkeypatch.setenv("MYCASE_MCP_ALLOWED_HOSTS", allowed_hosts)
    with pytest.raises(SystemExit) as excinfo:
        server.create_serve_app()
    assert "MYCASE_MCP_ALLOWED_HOSTS" in str(excinfo.value)


def test_allowed_hosts_and_origins_are_enforced(monkeypatch) -> None:
    _clear_transport_env(monkeypatch)
    monkeypatch.setenv("MYCASE_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MYCASE_MCP_ALLOWED_HOSTS", " allowed.example , other.example ")
    monkeypatch.setenv(
        "MYCASE_MCP_ALLOWED_ORIGINS",
        " https://allowed.example , https://other.example ",
    )
    app = server.create_serve_app()

    async def scenario() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        # One app, one lifespan: the SDK session manager starts once per app.
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://127.0.0.1:8000"
            ) as http:
                refused = await http.post(
                    "/mcp",
                    headers={**_headers("tools/list"), "host": "evil.example"},
                    json=_body("tools/list"),
                )
                forbidden = await http.post(
                    "/mcp",
                    headers={
                        **_headers("tools/list"),
                        "host": "allowed.example",
                        "origin": "https://evil.example",
                    },
                    json=_body("tools/list"),
                )
                allowed = await http.post(
                    "/mcp",
                    headers={
                        **_headers("tools/list"),
                        "host": "allowed.example",
                        "origin": "https://allowed.example",
                    },
                    json=_body("tools/list"),
                )
        return refused, forbidden, allowed

    refused, forbidden, allowed = asyncio.run(scenario())
    assert refused.status_code == 421
    assert forbidden.status_code == 403
    _result(allowed)


def test_get_delete_rejected_and_discover_declares_the_modern_revision(
    monkeypatch,
) -> None:
    _clear_transport_env(monkeypatch)
    app = server.create_serve_app()

    async def scenario() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://127.0.0.1:8000"
            ) as http:
                get = await http.get("/mcp", headers=_headers("tools/list"))
                delete = await http.delete("/mcp", headers=_headers("tools/list"))
                discover = await http.post(
                    "/mcp",
                    headers=_headers("server/discover"),
                    json=_body("server/discover"),
                )
        return get, delete, discover

    get, delete, discover = asyncio.run(scenario())
    assert get.status_code == 405
    assert delete.status_code == 405

    result = _result(discover)
    assert PROTOCOL_VERSION in result["supportedVersions"]
    assert result["_meta"][SERVER_INFO_META_KEY]["version"]


def test_lifespan_runs_once_per_app_not_per_request_in_stateless_mode(
    monkeypatch,
) -> None:
    _clear_transport_env(monkeypatch)
    starts: list[str] = []

    @asynccontextmanager
    async def counting_lifespan(_server):
        starts.append("enter")
        try:
            yield {"count": len(starts)}
        finally:
            starts.append("exit")

    monkeypatch.setattr(server.mcp._lowlevel_server, "lifespan", counting_lifespan)
    app = server.create_serve_app()

    async def scenario() -> list[httpx.Response]:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://127.0.0.1:8000"
            ) as http:
                return [
                    await http.post(
                        "/mcp",
                        headers=_headers("tools/list"),
                        json=_body("tools/list", request_id=number),
                    )
                    for number in range(1, 4)
                ]

    responses = asyncio.run(scenario())
    assert [response.status_code for response in responses] == [200, 200, 200]
    assert starts.count("enter") == 1
    assert starts == ["enter", "exit"]
