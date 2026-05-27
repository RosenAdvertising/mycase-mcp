"""mcp-test-kit configuration for mycase-mcp.

Usage (once mcp-test-kit is installed):
    mcp-test-kit run tests/config.py
    mcp-test-kit run tests/config.py --tier smoke
    mcp-test-kit run tests/config.py --tier contract
    mcp-test-kit run tests/config.py --tier coverage
"""

from __future__ import annotations

from pathlib import Path

from mcp_test_kit.config import (
    ResilienceConfig,
    SpecCheckConfig,
    SmokeConfig,
    ToolkitConfig,
)

from mycase_mcp.server import mcp

_TESTS_DIR = Path(__file__).parent

# MyCase API uses filter[X] param naming in OpenAPI; MCP tools expose them as plain
# names.  Map each tool's MCP param name → OpenAPI query param name.
_FILTER_ALIASES: dict[str, dict[str, str]] = {
    "list_cases": {
        "status": "filter[status]",
    },
    "list_staff": {
        "status": "filter[status]",
    },
    "list_clients": {
        "email": "filter[email]",
        "first_name": "filter[first_name]",
        "last_name": "filter[last_name]",
        "cell_phone_number": "filter[cell_phone_number]",
        "updated_after": "filter[updated_after]",
    },
    "list_companies": {
        "name": "filter[name]",
        "email": "filter[email]",
        "updated_after": "filter[updated_after]",
    },
    "list_tasks": {"updated_after": "filter[updated_after]"},
    "list_time_entries": {"updated_after": "filter[updated_after]"},
    "list_invoice_payments": {
        "status": "filter[status]",
        "payable_id": "filter[payable_id]",
    },
    "list_expenses": {"updated_after": "filter[updated_after]"},
    "list_calls": {"updated_after": "filter[updated_after]"},
}

# Params that the MCP client sends but are not documented in the OpenAPI spec.
# These are real API params confirmed in client.py but absent from the spec files.
_LOCAL_ONLY: dict[str, set[str]] = {
    "list_events": {"start_date", "end_date"},
    "list_invoices": {"status"},
    "list_leads": {"status"},
    # Sub-resource endpoints: page_size is sent by client but absent from API spec
    "list_cases_for_client": {"page_size"},
    "list_client_notes": {"page_size"},
    "list_client_message_threads": {"page_size"},
    "list_case_notes": {"page_size"},
    "list_case_documents": {"page_size"},
}

spec_check = SpecCheckConfig(
    endpoints_path=_TESTS_DIR / "endpoints.yaml",
    openapi_path=_TESTS_DIR / "openapi-merged.json",
    # merge_specs.py strips /v1 from all paths so endpoints.yaml paths (/cases, /clients…)
    # match directly — no prefix or suffix needed here.
    path_prefix="",
    path_suffix="",
    resource_schemas={},
    body_fields={},
    always_body_fields={},
    param_aliases=_FILTER_ALIASES,
    local_only_params=_LOCAL_ONLY,
    known_defaults={},
    list_safety_params={},
    endpoint_id_names={
        "id",
        "case_id",
        "contact_id",
        "task_id",
        "document_id",
        "version_number",
        "key",
    },
)

smoke = SmokeConfig(
    server=mcp,
    read_tools=[
        # identity
        "who_am_i",
        "get_firm",
        # staff
        "list_staff",
        # cases
        "list_cases",
        # clients / companies
        "list_clients",
        "list_companies",
        # tasks / events
        "list_tasks",
        "list_events",
        # time & billing
        "list_time_entries",
        "list_invoices",
        "list_invoice_payments",
        # documents
        "list_documents",
        "list_all_document_versions",
        # leads
        "list_leads",
        # reference data
        "list_case_stages",
        "list_case_roles",
        "list_referral_sources",
        "list_locations",
        "list_people_groups",
        "list_practice_areas",
        "list_custom_fields",
        # expenses / calls / webhooks
        "list_expenses",
        "list_calls",
        "list_webhook_subscriptions",
    ],
)

TOOLKIT = ToolkitConfig(
    mcp_server=mcp,
    spec_check=spec_check,
    smoke=smoke,
    source_path=_TESTS_DIR.parent / "mycase_mcp",
    module_path="mycase_mcp",
    server_path=_TESTS_DIR.parent / "mycase_mcp" / "server.py",
    resilience=ResilienceConfig(tools_to_timeout_test=["who_am_i"]),
    skip_tiers={
        "smoke": "requires live MyCase OAuth credentials (run mycase-mcp-setup first)",
    },
)
