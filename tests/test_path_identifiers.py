"""Regression coverage for every ID-bearing client path call site.

The transport boundary is replaced, so rejected identifiers must fail before
any HTTP call, including a preliminary read in a merge/update operation.
"""

import inspect
from unittest.mock import Mock

import pytest
import requests

from mycase_mcp.client import MyCaseClient

CASES = [
    ("get_staff", "staff_id"),
    ("get_case", "case_id"),
    ("update_case", "case_id"),
    ("delete_case", "case_id"),
    ("list_cases_for_client", "client_id"),
    ("add_client_to_case", "case_id"),
    ("add_company_to_case", "case_id"),
    ("add_staff_to_case", "case_id"),
    ("get_client", "client_id"),
    ("update_client", "client_id"),
    ("delete_client", "client_id"),
    ("get_company", "company_id"),
    ("update_company", "company_id"),
    ("delete_company", "company_id"),
    ("add_client_to_company", "company_id"),
    ("update_task", "task_id"),
    ("delete_task", "task_id"),
    ("assign_task_to_staff", "task_id"),
    ("update_event", "event_id"),
    ("delete_event", "event_id"),
    ("add_staff_to_event", "event_id"),
    ("get_time_entry", "entry_id"),
    ("delete_time_entry", "entry_id"),
    ("delete_invoice", "invoice_id"),
    ("record_invoice_payment", "invoice_id"),
    ("get_note", "note_id"),
    ("update_note", "note_id"),
    ("delete_note", "note_id"),
    ("list_case_notes", "case_id"),
    ("create_case_note", "case_id"),
    ("list_client_notes", "client_id"),
    ("create_client_note", "client_id"),
    ("create_company_note", "company_id"),
    ("get_document", "doc_id"),
    ("update_document", "doc_id"),
    ("delete_document", "doc_id"),
    ("list_document_versions", "doc_id"),
    ("list_case_documents", "case_id"),
    ("get_case_folder", "case_id"),
    ("upload_case_document", "case_id"),
    ("upload_document_version", "doc_id"),
    ("get_document_data", "doc_id"),
    ("get_document_version_data", "doc_id"),
    ("get_document_version_data", "version_number"),
    ("delete_document_version", "doc_id"),
    ("delete_document_version", "version_number"),
    ("get_lead", "lead_id"),
    ("update_lead", "lead_id"),
    ("create_case_message_thread", "case_id"),
    ("list_client_message_threads", "client_id"),
    ("post_message", "thread_id"),
    ("update_case_stage", "stage_id"),
    ("delete_case_stage", "stage_id"),
    ("update_location", "location_id"),
    ("delete_location", "location_id"),
    ("update_people_group", "group_id"),
    ("delete_people_group", "group_id"),
    ("update_practice_area", "area_id"),
    ("delete_practice_area", "area_id"),
    ("get_custom_field", "field_id"),
    ("delete_custom_field", "field_id"),
    ("list_custom_field_options", "field_id"),
    ("create_custom_field_option", "field_id"),
    ("update_custom_field_option", "field_id"),
    ("update_custom_field_option", "key"),
    ("delete_custom_field_option", "field_id"),
    ("delete_custom_field_option", "key"),
    ("get_expense", "expense_id"),
    ("delete_expense", "expense_id"),
    ("update_call", "call_id"),
    ("delete_call", "call_id"),
    ("list_folder_documents", "folder_id"),
    ("list_folder_subfolders", "folder_id"),
    ("create_case_subfolder", "case_id"),
    ("delete_webhook_subscription", "subscription_id"),
]


def client_and_arguments(method):
    client = object.__new__(MyCaseClient)
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"id": "normal-id", "success": true}'
    request = Mock(return_value={"id": "normal-id", "success": True})
    send = Mock(return_value=response)
    client._request = request
    client._send = send
    kwargs = {}
    for key, param in inspect.signature(getattr(client, method)).parameters.items():
        if param.default is not inspect.Parameter.empty or param.kind in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            continue
        annotation = str(param.annotation)
        if "dict" in annotation or key in {"body", "fields", "overlay"}:
            kwargs[key] = {"name": "probe"}
        elif "int" in annotation:
            kwargs[key] = 1
        else:
            kwargs[key] = "normal-id"
    if "resource" in kwargs:
        kwargs["resource"] = "matters"
    if "path" in kwargs:
        kwargs["path"] = "/tasks"
    if method == "tag_call":
        kwargs["tag_ids"] = [1]
    if method == "update_contact" and MyCaseClient.__name__ == "CloudTalkClient":
        kwargs["name"] = "probe"
    if method in {
        "update_case",
        "update_client",
        "update_company",
        "update_task",
        "update_event",
        "update_lead",
        "update_location",
        "update_document",
    }:
        kwargs["name"] = "probe"
    if method == "update_note":
        kwargs["subject"] = "probe"
    if method == "update_call":
        kwargs["caller_name"] = "probe"
    if method == "upload_case_document":
        kwargs["path"] = "example_folder1/example_folder2/example_name"
    return client, kwargs, request, send


@pytest.mark.parametrize(("method", "parameter"), CASES)
@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "a/../b", "%2e%2e", "a?b", "a#b", "a\\b", " ", "a\n", None, True],
)
def test_invalid_path_id_never_reaches_transport(method, parameter, value):
    client, kwargs, request, send = client_and_arguments(method)
    kwargs[parameter] = value
    with pytest.raises(Exception) as caught:
        getattr(client, method)(**kwargs)
    error = caught.value
    assert parameter in str(error) or getattr(error, "field", None) == parameter
    assert "identifier" in str(error) or "identifier" in getattr(error, "expected", "")
    request.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize(("method", "parameter"), CASES)
@pytest.mark.parametrize(
    "value", ["normal-id", "550e8400-e29b-41d4-a716-446655440000", "123", 123]
)
def test_normal_path_id_reaches_transport(method, parameter, value):
    client, kwargs, request, send = client_and_arguments(method)
    kwargs[parameter] = value
    getattr(client, method)(**kwargs)
    calls = request.call_args_list + send.call_args_list
    assert calls
    assert any(str(value) in str(call) for call in calls)
