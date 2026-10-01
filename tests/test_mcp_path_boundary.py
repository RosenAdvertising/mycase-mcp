"""Regression calls cross the official MCP transport before real client routing."""

import asyncio
from types import SimpleNamespace

import pytest
import requests
from mcp.client import ClientSession
from mcp.client._memory import InMemoryTransport
from requests.adapters import BaseAdapter

from mycase_mcp import client as client_module
from mycase_mcp import server

CASES = [
    ("get_staff_member", "staff_id", {"staff_id": 123}),
    ("get_case", "case_id", {"case_id": 123}),
    ("update_case", "case_id", {"case_id": 123}),
    ("delete_case", "case_id", {"case_id": 123}),
    ("list_cases_for_client", "client_id", {"client_id": 123}),
    ("add_client_to_case", "case_id", {"case_id": 123, "client_id": 123}),
    ("add_company_to_case", "case_id", {"case_id": 123, "company_id": 123}),
    ("add_staff_to_case", "case_id", {"case_id": 123, "staff_id": 123}),
    ("get_client", "client_id", {"client_id": 123}),
    ("update_client", "client_id", {"client_id": 123}),
    ("delete_client", "client_id", {"client_id": 123}),
    ("list_client_notes", "client_id", {"client_id": 123}),
    ("list_client_message_threads", "client_id", {"client_id": 123}),
    ("get_company", "company_id", {"company_id": 123}),
    ("update_company", "company_id", {"company_id": 123}),
    ("delete_company", "company_id", {"company_id": 123}),
    ("add_client_to_company", "company_id", {"company_id": 123, "client_id": 123}),
    ("update_task", "task_id", {"task_id": 123}),
    ("delete_task", "task_id", {"task_id": 123}),
    ("assign_task_to_staff", "task_id", {"task_id": 123, "staff_id": 123}),
    ("update_event", "event_id", {"event_id": 123}),
    ("delete_event", "event_id", {"event_id": 123}),
    ("add_staff_to_event", "event_id", {"event_id": 123, "staff_id": 123}),
    ("get_time_entry", "entry_id", {"entry_id": 123}),
    ("delete_time_entry", "entry_id", {"entry_id": 123}),
    (
        "record_invoice_payment",
        "invoice_id",
        {"invoice_id": 123, "amount": 1.0, "date": "2026-10-01"},
    ),
    ("get_note", "note_id", {"note_id": 123}),
    ("update_note", "note_id", {"note_id": 123}),
    ("delete_note", "note_id", {"note_id": 123}),
    ("list_case_notes", "case_id", {"case_id": 123}),
    (
        "create_case_note",
        "case_id",
        {
            "case_id": 123,
            "note": "normal-id",
            "subject": "normal-id",
            "date": "2026-10-01",
        },
    ),
    (
        "create_client_note",
        "client_id",
        {
            "client_id": 123,
            "note": "normal-id",
            "subject": "normal-id",
            "date": "2026-10-01",
        },
    ),
    (
        "create_company_note",
        "company_id",
        {
            "company_id": 123,
            "note": "normal-id",
            "subject": "normal-id",
            "date": "2026-10-01",
        },
    ),
    ("get_document", "doc_id", {"doc_id": 123}),
    ("update_document", "doc_id", {"doc_id": 123}),
    ("delete_document", "doc_id", {"doc_id": 123}),
    ("list_case_documents", "case_id", {"case_id": 123}),
    ("list_document_versions", "doc_id", {"doc_id": 123}),
    ("get_case_folder", "case_id", {"case_id": 123}),
    (
        "upload_case_document",
        "case_id",
        {"case_id": 123, "filename": "normal-id", "path": "normal-id"},
    ),
    ("upload_document_version", "doc_id", {"doc_id": 123}),
    ("get_document_data", "doc_id", {"doc_id": 123}),
    ("get_document_version_data", "doc_id", {"doc_id": 123, "version_number": 123}),
    (
        "get_document_version_data",
        "version_number",
        {"doc_id": 123, "version_number": 123},
    ),
    ("delete_document_version", "doc_id", {"doc_id": 123, "version_number": 123}),
    (
        "delete_document_version",
        "version_number",
        {"doc_id": 123, "version_number": 123},
    ),
    ("get_lead", "lead_id", {"lead_id": 123}),
    ("update_lead", "lead_id", {"lead_id": 123}),
    (
        "create_case_message_thread",
        "case_id",
        {"case_id": 123, "subject": "normal-id", "first_message_body": "normal-id"},
    ),
    ("post_message", "thread_id", {"thread_id": 123, "body": "normal-id"}),
    ("update_case_stage", "stage_id", {"stage_id": 123, "name": "normal-id"}),
    ("delete_case_stage", "stage_id", {"stage_id": 123}),
    ("update_location", "location_id", {"location_id": 123}),
    ("delete_location", "location_id", {"location_id": 123}),
    ("update_people_group", "group_id", {"group_id": 123, "name": "normal-id"}),
    ("delete_people_group", "group_id", {"group_id": 123}),
    ("update_practice_area", "area_id", {"area_id": 123, "name": "normal-id"}),
    ("delete_practice_area", "area_id", {"area_id": 123}),
    ("get_custom_field", "field_id", {"field_id": 123}),
    ("delete_custom_field", "field_id", {"field_id": 123}),
    ("list_custom_field_options", "field_id", {"field_id": 123}),
    (
        "create_custom_field_option",
        "field_id",
        {"field_id": 123, "option_value": "normal-id"},
    ),
    (
        "update_custom_field_option",
        "field_id",
        {"field_id": 123, "key": "normal-id", "option_value": "normal-id"},
    ),
    ("delete_custom_field_option", "field_id", {"field_id": 123, "key": "normal-id"}),
    ("get_expense", "expense_id", {"expense_id": 123}),
    ("delete_expense", "expense_id", {"expense_id": 123}),
    ("update_call", "call_id", {"call_id": 123}),
    ("delete_call", "call_id", {"call_id": 123}),
    ("list_folder_documents", "folder_id", {"folder_id": 123}),
    ("list_folder_subfolders", "folder_id", {"folder_id": 123}),
    ("create_case_subfolder", "case_id", {"case_id": 123, "path": "normal-id"}),
    ("delete_webhook_subscription", "subscription_id", {"subscription_id": 123}),
]


@pytest.fixture
def boundary(monkeypatch):
    client = object.__new__(client_module.MyCaseClient)
    prepared, sent, constructed = [], [], []

    class Adapter(BaseAdapter):
        def send(self, request, **kwargs):
            sent.append(request)
            response = requests.Response()
            response.status_code = 200
            response.request = request
            response.url = request.url
            response.headers["Content-Type"] = "application/json"
            response._content = b'{"id":"normal-id","success":true,"name":"probe","data":{"id":"normal-id"},"items":[],"results":[]}'
            return response

        def close(self):
            pass

    client.session = requests.Session()
    client.session.trust_env = False
    client.session.mount("http://", Adapter())
    client.session.mount("https://", Adapter())
    prepare = client.session.prepare_request

    def record_prepare(request):
        prepared.append(request)
        return prepare(request)

    monkeypatch.setattr(client.session, "prepare_request", record_prepare)
    client.tm = SimpleNamespace(
        is_expired=lambda: False, access_token="", refresh_token=""
    )
    client.api_endpoint = "https://example.invalid"
    client._token_valid = lambda: True
    client._headers = lambda: {}
    client.access_token = ""
    client._rate_waited = 0
    client.timeout = 30
    client._api_url = "https://example.invalid/v1"

    def factory():
        constructed.append(True)
        return client

    monkeypatch.setattr(server, "MyCaseClient", factory)
    for name in ("_c", "_client", "get_client"):
        if hasattr(server, name):
            monkeypatch.setattr(server, name, factory)

    async def call(tool, arguments):
        async with InMemoryTransport(server.mcp) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                return result.model_dump(mode="json", by_alias=True)

    return SimpleNamespace(
        call=lambda tool, arguments: asyncio.run(call(tool, arguments)),
        prepared=prepared,
        sent=sent,
        constructed=constructed,
        client=client,
    )


@pytest.mark.parametrize("tool,parameter,arguments", CASES)
@pytest.mark.parametrize("value", [True, False])
def test_boolean_path_id_rejected_before_client(
    boundary, tool, parameter, arguments, value
):
    result = boundary.call(tool, {**arguments, parameter: value})
    text = " ".join(item.get("text", "") for item in result["content"])
    assert result["isError"]
    assert parameter in text
    assert "integer" in text
    assert not boundary.constructed
    assert not boundary.prepared
    assert not boundary.sent


@pytest.mark.parametrize("tool,parameter,arguments", CASES)
@pytest.mark.parametrize("value", [123, "123", "00123", 123.0, "123.0", 0, -1])
def test_existing_integer_coercions_preserved(
    boundary, tool, parameter, arguments, value
):
    result = boundary.call(tool, {**arguments, parameter: value})
    assert not result["isError"], result
    assert boundary.prepared
    assert boundary.sent


KEY_TOOLS = ["update_custom_field_option", "delete_custom_field_option"]
BAD_KEYS = [
    "",
    ".",
    "..",
    "a/../b",
    "%2e%2e",
    "%2E%2E",
    "a\\b",
    "a?b",
    "a#b",
    " ",
    "a\n",
    "é",
    "%252e%252e",
]


@pytest.mark.parametrize("tool", KEY_TOOLS)
@pytest.mark.parametrize("key", BAD_KEYS)
def test_key_error_is_reviewed_and_actionable(boundary, tool, key):
    arguments = {"field_id": 123, "key": key}
    if tool == "update_custom_field_option":
        arguments["option_value"] = "probe"
    result = boundary.call(tool, arguments)
    text = " ".join(item.get("text", "") for item in result["content"])
    assert result["isError"]
    assert "key" in text
    assert "non-empty plain identifier" in text
    assert "ASCII letters, digits, -, _, ., ~" in text
    assert "not . or .." in text
    assert not boundary.prepared
    assert not boundary.sent


@pytest.mark.parametrize("tool", KEY_TOOLS)
@pytest.mark.parametrize("exception", [RuntimeError, client_module.MyCaseToolError])
def test_arbitrary_exception_text_remains_private(
    boundary, monkeypatch, tool, exception
):
    def fail(*args, **kwargs):
        raise exception("private exception marker")

    monkeypatch.setattr(boundary.client, tool, fail)
    arguments = {"field_id": 123, "key": "valid_key"}
    if tool == "update_custom_field_option":
        arguments["option_value"] = "probe"
    result = boundary.call(tool, arguments)
    assert result["isError"]
    assert "private exception marker" not in str(result)
    assert not boundary.prepared
