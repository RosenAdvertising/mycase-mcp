"""Regression coverage for bounded MyCase collection tools."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mycase_mcp import server
from mycase_mcp.client import MyCaseClient


def _list_tools():
    return [
        tool
        for tool in asyncio.run(server.mcp.list_tools())
        if tool.name.startswith("list_")
    ]


class RecordingClient(MyCaseClient):
    def __init__(self, payload: Any):
        self.payload = payload
        self.requests: list[tuple[str, dict[str, Any] | None]] = []

    def get(self, path, params=None):
        self.requests.append((path, params))
        return self.payload


def test_every_list_tool_schema_exposes_one_to_two_hundred_total_limit() -> None:
    tools = _list_tools()

    assert len(tools) == 31
    for tool in tools:
        properties = tool.input_schema["properties"]
        assert "page_size" not in properties
        limit = properties["limit"]
        assert limit["minimum"] == 1
        assert limit["maximum"] == 200
        assert 1 <= limit["default"] <= 200


def test_list_tool_schemas_do_not_invent_unsupported_sort_parameters() -> None:
    # The retained MyCase OpenAPI history has no collection sort/order query
    # parameter. Do not claim a control that the vendor API cannot honor.
    for tool in _list_tools():
        properties = tool.input_schema["properties"]
        assert "order" not in properties
        assert "sort" not in properties


@pytest.mark.parametrize("limit", [0, 201])
def test_list_tool_rejects_out_of_bounds_limit(limit: int) -> None:
    tool = server.mcp._tool_manager.get_tool("list_staff")
    assert tool is not None

    with pytest.raises(ToolError, match="validation error"):
        asyncio.run(tool.run({"limit": limit}, None))


def test_vendor_over_delivery_is_capped_for_plain_list_response() -> None:
    client = RecordingClient([{"id": record_id} for record_id in range(10)])

    result = client.list_cases(page_size=3)

    assert result == [{"id": 0}, {"id": 1}, {"id": 2}]
    assert client.requests == [("/cases", {"page_size": 3})]


def test_vendor_over_delivery_is_capped_inside_response_envelope() -> None:
    client = RecordingClient(
        {"data": [{"id": record_id} for record_id in range(10)], "meta": {}}
    )

    result = client.list_tasks(page_size=4)

    assert [item["id"] for item in result["data"]] == [0, 1, 2, 3]
    assert result["meta"] == {}
    assert client.requests == [("/tasks", {"page_size": 4})]


def test_unpaged_vendor_collection_is_locally_capped_without_fake_query() -> None:
    client = RecordingClient([{"id": record_id} for record_id in range(10)])

    result = client.list_webhook_subscriptions(page_size=2)

    assert result == [{"id": 0}, {"id": 1}]
    assert client.requests == [("/webhooks/subscriptions", None)]
