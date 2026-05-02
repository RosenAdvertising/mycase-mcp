#!/usr/bin/env python3
"""MyCase MCP Server — 45 tools covering the full MyCase practice management API."""

import json
from mcp.server.fastmcp import FastMCP
from .client import MyCaseClient

mcp = FastMCP(
    "mycase-mcp",
    instructions="Full access to MyCase practice management: cases, contacts, companies, tasks, calendar, time entries, invoices, notes, documents, leads, and messaging.",
)


# ── Identity ──────────────────────────────────────────────────────────────────

@mcp.tool()
def who_am_i() -> str:
    """Return the currently authenticated MyCase user."""
    return json.dumps(MyCaseClient().get_me(), indent=2)


@mcp.tool()
def get_firm() -> str:
    """Return information about the current firm."""
    return json.dumps(MyCaseClient().get_firm(), indent=2)


@mcp.tool()
def list_staff(per_page: int = 50) -> str:
    """List all staff members in the firm."""
    return json.dumps(MyCaseClient().list_staff(per_page=per_page), indent=2)


@mcp.tool()
def get_staff_member(staff_id: int) -> str:
    """Get a specific staff member by ID."""
    return json.dumps(MyCaseClient().get_staff(staff_id), indent=2)


# ── Cases ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_cases(status: str = "", per_page: int = 25, page: int = 1) -> str:
    """List cases. status: open | closed | pending (leave blank for all)."""
    return json.dumps(MyCaseClient().list_cases(
        status=status or None, per_page=per_page, page=page), indent=2)


@mcp.tool()
def get_case(case_id: int) -> str:
    """Get full detail for a case by ID."""
    return json.dumps(MyCaseClient().get_case(case_id), indent=2)


@mcp.tool()
def create_case(name: str, description: str = "", status: str = "open",
                case_stage_id: int = 0) -> str:
    """Create a new case. status: open | closed | pending."""
    return json.dumps(MyCaseClient().create_case(
        name=name, description=description or None, status=status,
        case_stage_id=case_stage_id or None), indent=2)


@mcp.tool()
def update_case(case_id: int, name: str = "", description: str = "",
                status: str = "") -> str:
    """Update a case. Only pass fields you want to change."""
    fields = {}
    if name:
        fields["name"] = name
    if description:
        fields["description"] = description
    if status:
        fields["status"] = status
    return json.dumps(MyCaseClient().update_case(case_id, **fields), indent=2)


@mcp.tool()
def delete_case(case_id: int) -> str:
    """Delete a case by ID."""
    return json.dumps(MyCaseClient().delete_case(case_id), indent=2)


@mcp.tool()
def list_cases_for_client(client_id: int, per_page: int = 25) -> str:
    """List all cases associated with a specific client."""
    return json.dumps(MyCaseClient().list_cases_for_client(client_id, per_page=per_page), indent=2)


@mcp.tool()
def add_client_to_case(case_id: int, client_id: int, role: str = "") -> str:
    """Associate a client (person) with a case."""
    return json.dumps(MyCaseClient().add_client_to_case(
        case_id, client_id, role=role or None), indent=2)


@mcp.tool()
def add_company_to_case(case_id: int, company_id: int, role: str = "") -> str:
    """Associate a company with a case."""
    return json.dumps(MyCaseClient().add_company_to_case(
        case_id, company_id, role=role or None), indent=2)


@mcp.tool()
def add_staff_to_case(case_id: int, staff_id: int, role: str = "") -> str:
    """Assign a staff member to a case."""
    return json.dumps(MyCaseClient().add_staff_to_case(
        case_id, staff_id, role=role or None), indent=2)


# ── Clients (People) ──────────────────────────────────────────────────────────

@mcp.tool()
def list_clients(query: str = "", per_page: int = 25, page: int = 1) -> str:
    """List clients (people). query: optional name/email search."""
    return json.dumps(MyCaseClient().list_clients(
        query=query or None, per_page=per_page, page=page), indent=2)


@mcp.tool()
def get_client(client_id: int) -> str:
    """Get a client (person) by ID."""
    return json.dumps(MyCaseClient().get_client(client_id), indent=2)


@mcp.tool()
def create_client(first_name: str, last_name: str, email: str = "",
                  phone: str = "") -> str:
    """Create a new client (person)."""
    return json.dumps(MyCaseClient().create_client(
        first_name=first_name, last_name=last_name,
        email=email or None, phone=phone or None), indent=2)


@mcp.tool()
def update_client(client_id: int, first_name: str = "", last_name: str = "",
                  email: str = "", phone: str = "") -> str:
    """Update a client. Only pass fields you want to change."""
    fields = {}
    if first_name:
        fields["first_name"] = first_name
    if last_name:
        fields["last_name"] = last_name
    if email:
        fields["email"] = email
    if phone:
        fields["phone"] = phone
    return json.dumps(MyCaseClient().update_client(client_id, **fields), indent=2)


@mcp.tool()
def delete_client(client_id: int) -> str:
    """Delete a client by ID."""
    return json.dumps(MyCaseClient().delete_client(client_id), indent=2)


@mcp.tool()
def list_client_notes(client_id: int, per_page: int = 25) -> str:
    """List all notes for a client."""
    return json.dumps(MyCaseClient().list_client_notes(client_id, per_page=per_page), indent=2)


@mcp.tool()
def list_client_message_threads(client_id: int, per_page: int = 25) -> str:
    """List all message threads for a client."""
    return json.dumps(MyCaseClient().list_client_message_threads(
        client_id, per_page=per_page), indent=2)


# ── Companies ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_companies(query: str = "", per_page: int = 25, page: int = 1) -> str:
    """List companies. query: optional name search."""
    return json.dumps(MyCaseClient().list_companies(
        query=query or None, per_page=per_page, page=page), indent=2)


@mcp.tool()
def get_company(company_id: int) -> str:
    """Get a company by ID."""
    return json.dumps(MyCaseClient().get_company(company_id), indent=2)


@mcp.tool()
def create_company(name: str, email: str = "", phone: str = "",
                   website: str = "") -> str:
    """Create a new company."""
    return json.dumps(MyCaseClient().create_company(
        name=name, email=email or None, phone=phone or None,
        website=website or None), indent=2)


@mcp.tool()
def update_company(company_id: int, name: str = "", email: str = "",
                   phone: str = "", website: str = "") -> str:
    """Update a company. Only pass fields you want to change."""
    fields = {}
    if name:
        fields["name"] = name
    if email:
        fields["email"] = email
    if phone:
        fields["phone"] = phone
    if website:
        fields["website"] = website
    return json.dumps(MyCaseClient().update_company(company_id, **fields), indent=2)


@mcp.tool()
def delete_company(company_id: int) -> str:
    """Delete a company by ID."""
    return json.dumps(MyCaseClient().delete_company(company_id), indent=2)


# ── Tasks ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_tasks(case_id: int = 0, assignee_id: int = 0,
               status: str = "", per_page: int = 25, page: int = 1) -> str:
    """List tasks. Filter by case_id, assignee_id, or status (open | completed)."""
    return json.dumps(MyCaseClient().list_tasks(
        case_id=case_id or None, assignee_id=assignee_id or None,
        status=status or None, per_page=per_page, page=page), indent=2)


@mcp.tool()
def create_task(name: str, case_id: int = 0, due_date: str = "",
                description: str = "", priority: str = "") -> str:
    """Create a task. due_date: YYYY-MM-DD. priority: low | normal | high."""
    return json.dumps(MyCaseClient().create_task(
        name=name, case_id=case_id or None, due_date=due_date or None,
        description=description or None, priority=priority or None), indent=2)


@mcp.tool()
def update_task(task_id: int, name: str = "", due_date: str = "",
                status: str = "", priority: str = "") -> str:
    """Update a task. status: open | completed."""
    fields = {}
    if name:
        fields["name"] = name
    if due_date:
        fields["due_date"] = due_date
    if status:
        fields["status"] = status
    if priority:
        fields["priority"] = priority
    return json.dumps(MyCaseClient().update_task(task_id, **fields), indent=2)


@mcp.tool()
def delete_task(task_id: int) -> str:
    """Delete a task by ID."""
    return json.dumps(MyCaseClient().delete_task(task_id), indent=2)


@mcp.tool()
def assign_task_to_staff(task_id: int, staff_id: int) -> str:
    """Assign a task to a staff member."""
    return json.dumps(MyCaseClient().assign_task_to_staff(task_id, staff_id), indent=2)


# ── Events / Calendar ─────────────────────────────────────────────────────────

@mcp.tool()
def list_events(case_id: int = 0, start_date: str = "",
                end_date: str = "", per_page: int = 25, page: int = 1) -> str:
    """List calendar events. start_date/end_date: YYYY-MM-DD."""
    return json.dumps(MyCaseClient().list_events(
        case_id=case_id or None, start_date=start_date or None,
        end_date=end_date or None, per_page=per_page, page=page), indent=2)


@mcp.tool()
def create_event(name: str, start_at: str, end_at: str, case_id: int = 0,
                 location: str = "", description: str = "") -> str:
    """Create a calendar event. start_at/end_at: ISO 8601 datetime strings."""
    return json.dumps(MyCaseClient().create_event(
        name=name, start_at=start_at, end_at=end_at,
        case_id=case_id or None, location=location or None,
        description=description or None), indent=2)


@mcp.tool()
def update_event(event_id: int, name: str = "", start_at: str = "",
                 end_at: str = "", location: str = "") -> str:
    """Update a calendar event."""
    fields = {}
    if name:
        fields["name"] = name
    if start_at:
        fields["start_at"] = start_at
    if end_at:
        fields["end_at"] = end_at
    if location:
        fields["location"] = location
    return json.dumps(MyCaseClient().update_event(event_id, **fields), indent=2)


@mcp.tool()
def delete_event(event_id: int) -> str:
    """Delete a calendar event by ID."""
    return json.dumps(MyCaseClient().delete_event(event_id), indent=2)


@mcp.tool()
def add_staff_to_event(event_id: int, staff_id: int) -> str:
    """Add a staff member to a calendar event."""
    return json.dumps(MyCaseClient().add_staff_to_event(event_id, staff_id), indent=2)


# ── Time Entries ──────────────────────────────────────────────────────────────

@mcp.tool()
def list_time_entries(case_id: int = 0, staff_id: int = 0,
                      per_page: int = 25, page: int = 1) -> str:
    """List time entries, optionally filtered by case or staff member."""
    return json.dumps(MyCaseClient().list_time_entries(
        case_id=case_id or None, staff_id=staff_id or None,
        per_page=per_page, page=page), indent=2)


@mcp.tool()
def get_time_entry(entry_id: int) -> str:
    """Get a specific time entry by ID."""
    return json.dumps(MyCaseClient().get_time_entry(entry_id), indent=2)


@mcp.tool()
def create_time_entry(case_id: int, duration_in_seconds: int,
                      note: str = "", date: str = "", rate: float = 0.0) -> str:
    """Create a time entry. date: YYYY-MM-DD. rate: hourly rate in dollars."""
    return json.dumps(MyCaseClient().create_time_entry(
        case_id=case_id, duration_in_seconds=duration_in_seconds,
        note=note or None, date=date or None,
        rate=rate or None), indent=2)


@mcp.tool()
def delete_time_entry(entry_id: int) -> str:
    """Delete a time entry by ID."""
    return json.dumps(MyCaseClient().delete_time_entry(entry_id), indent=2)


# ── Invoices ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_invoices(case_id: int = 0, status: str = "",
                  per_page: int = 25, page: int = 1) -> str:
    """List invoices. status: draft | sent | paid | overdue."""
    return json.dumps(MyCaseClient().list_invoices(
        case_id=case_id or None, status=status or None,
        per_page=per_page, page=page), indent=2)


@mcp.tool()
def record_invoice_payment(invoice_id: int, amount: float,
                           date: str = "", note: str = "") -> str:
    """Record a payment against an invoice. date: YYYY-MM-DD."""
    return json.dumps(MyCaseClient().record_invoice_payment(
        invoice_id=invoice_id, amount=amount,
        date=date or None, note=note or None), indent=2)


@mcp.tool()
def list_invoice_payments(per_page: int = 25, page: int = 1) -> str:
    """List all invoice payments."""
    return json.dumps(MyCaseClient().list_invoice_payments(per_page=per_page, page=page), indent=2)


# ── Notes ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_note(note_id: int) -> str:
    """Get a note by ID."""
    return json.dumps(MyCaseClient().get_note(note_id), indent=2)


@mcp.tool()
def update_note(note_id: int, body_text: str = "", subject: str = "") -> str:
    """Update a note's body or subject."""
    return json.dumps(MyCaseClient().update_note(
        note_id, body_text=body_text or None, subject=subject or None), indent=2)


@mcp.tool()
def delete_note(note_id: int) -> str:
    """Delete a note by ID."""
    return json.dumps(MyCaseClient().delete_note(note_id), indent=2)


@mcp.tool()
def list_case_notes(case_id: int, per_page: int = 25) -> str:
    """List all notes for a case."""
    return json.dumps(MyCaseClient().list_case_notes(case_id, per_page=per_page), indent=2)


@mcp.tool()
def create_case_note(case_id: int, body_text: str, subject: str = "") -> str:
    """Create a note on a case."""
    return json.dumps(MyCaseClient().create_case_note(
        case_id, body_text, subject=subject or None), indent=2)


@mcp.tool()
def create_client_note(client_id: int, body_text: str, subject: str = "") -> str:
    """Create a note on a client (person)."""
    return json.dumps(MyCaseClient().create_client_note(
        client_id, body_text, subject=subject or None), indent=2)


@mcp.tool()
def create_company_note(company_id: int, body_text: str, subject: str = "") -> str:
    """Create a note on a company."""
    return json.dumps(MyCaseClient().create_company_note(
        company_id, body_text, subject=subject or None), indent=2)


# ── Documents ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_documents(case_id: int = 0, per_page: int = 25, page: int = 1) -> str:
    """List documents, optionally filtered by case."""
    return json.dumps(MyCaseClient().list_documents(
        case_id=case_id or None, per_page=per_page, page=page), indent=2)


@mcp.tool()
def get_document(doc_id: int) -> str:
    """Get document metadata by ID."""
    return json.dumps(MyCaseClient().get_document(doc_id), indent=2)


@mcp.tool()
def update_document(doc_id: int, name: str = "", description: str = "") -> str:
    """Update a document's name or description."""
    return json.dumps(MyCaseClient().update_document(
        doc_id, name=name or None, description=description or None), indent=2)


@mcp.tool()
def delete_document(doc_id: int) -> str:
    """Delete a document by ID."""
    return json.dumps(MyCaseClient().delete_document(doc_id), indent=2)


@mcp.tool()
def list_case_documents(case_id: int, per_page: int = 25) -> str:
    """List all documents for a case."""
    return json.dumps(MyCaseClient().list_case_documents(case_id, per_page=per_page), indent=2)


@mcp.tool()
def list_document_versions(doc_id: int) -> str:
    """List all versions of a document."""
    return json.dumps(MyCaseClient().list_document_versions(doc_id), indent=2)


@mcp.tool()
def get_case_folder(case_id: int) -> str:
    """Get the root document folder for a case."""
    return json.dumps(MyCaseClient().get_case_folder(case_id), indent=2)


# ── Leads ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_leads(status: str = "", per_page: int = 25, page: int = 1) -> str:
    """List leads. status: new | contacted | qualified | converted | closed."""
    return json.dumps(MyCaseClient().list_leads(
        status=status or None, per_page=per_page, page=page), indent=2)


@mcp.tool()
def get_lead(lead_id: int) -> str:
    """Get a lead by ID."""
    return json.dumps(MyCaseClient().get_lead(lead_id), indent=2)


@mcp.tool()
def create_lead(first_name: str, last_name: str, email: str = "",
                phone: str = "", referral_source_id: int = 0) -> str:
    """Create a new lead."""
    return json.dumps(MyCaseClient().create_lead(
        first_name=first_name, last_name=last_name,
        email=email or None, phone=phone or None,
        referral_source_id=referral_source_id or None), indent=2)


@mcp.tool()
def update_lead(lead_id: int, status: str = "", notes: str = "",
                first_name: str = "", last_name: str = "") -> str:
    """Update a lead. status: new | contacted | qualified | converted | closed."""
    fields = {}
    if status:
        fields["status"] = status
    if notes:
        fields["notes"] = notes
    if first_name:
        fields["first_name"] = first_name
    if last_name:
        fields["last_name"] = last_name
    return json.dumps(MyCaseClient().update_lead(lead_id, **fields), indent=2)


# ── Messaging ─────────────────────────────────────────────────────────────────

@mcp.tool()
def create_message_thread(subject: str, participant_ids: str) -> str:
    """Create a message thread. participant_ids: comma-separated staff IDs."""
    ids = [int(x.strip()) for x in participant_ids.split(",") if x.strip()]
    return json.dumps(MyCaseClient().create_message_thread(subject, ids), indent=2)


@mcp.tool()
def create_case_message_thread(case_id: int, subject: str,
                                participant_ids: str) -> str:
    """Create a message thread on a case. participant_ids: comma-separated staff IDs."""
    ids = [int(x.strip()) for x in participant_ids.split(",") if x.strip()]
    return json.dumps(MyCaseClient().create_case_message_thread(case_id, subject, ids), indent=2)


@mcp.tool()
def post_message(thread_id: int, body_text: str) -> str:
    """Post a message to an existing message thread."""
    return json.dumps(MyCaseClient().post_message(thread_id, body_text), indent=2)


# ── Reference Data ────────────────────────────────────────────────────────────

@mcp.tool()
def list_case_stages() -> str:
    """List all case stages configured in this firm."""
    return json.dumps(MyCaseClient().list_case_stages(), indent=2)


@mcp.tool()
def list_case_roles() -> str:
    """List all case roles (e.g. plaintiff, defendant, attorney)."""
    return json.dumps(MyCaseClient().list_case_roles(), indent=2)


@mcp.tool()
def list_referral_sources() -> str:
    """List all referral sources configured in this firm."""
    return json.dumps(MyCaseClient().list_referral_sources(), indent=2)


@mcp.tool()
def list_locations() -> str:
    """List all locations (courthouses, offices, etc.) in this firm."""
    return json.dumps(MyCaseClient().list_locations(), indent=2)


@mcp.tool()
def list_people_groups() -> str:
    """List all people groups (contact categories) in this firm."""
    return json.dumps(MyCaseClient().list_people_groups(), indent=2)


@mcp.tool()
def list_custom_fields() -> str:
    """List all custom fields configured in this firm."""
    return json.dumps(MyCaseClient().list_custom_fields(), indent=2)


@mcp.tool()
def create_custom_field(name: str, parent_type: str, field_type: str, list_options: list | None = None) -> str:
    """Create a custom field. parent_type: 'Case'|'Client'|'Lead'. field_type: 'text'|'date'|'list'|'checkbox'|'number'."""
    return json.dumps(MyCaseClient().create_custom_field(name, parent_type, field_type, list_options), indent=2)


@mcp.tool()
def get_custom_field(field_id: int) -> str:
    """Get a custom field by ID."""
    return json.dumps(MyCaseClient().get_custom_field(field_id), indent=2)


@mcp.tool()
def delete_custom_field(field_id: int) -> str:
    """Delete a custom field by ID."""
    return json.dumps(MyCaseClient().delete_custom_field(field_id), indent=2)


@mcp.tool()
def list_custom_field_options(field_id: int) -> str:
    """List all options for a list-type custom field."""
    return json.dumps(MyCaseClient().list_custom_field_options(field_id), indent=2)


@mcp.tool()
def create_custom_field_option(field_id: int, option_value: str) -> str:
    """Add an option to a list-type custom field."""
    return json.dumps(MyCaseClient().create_custom_field_option(field_id, option_value), indent=2)


@mcp.tool()
def update_custom_field_option(field_id: int, key: str, option_value: str) -> str:
    """Update an existing option on a list-type custom field."""
    return json.dumps(MyCaseClient().update_custom_field_option(field_id, key, option_value), indent=2)


@mcp.tool()
def delete_custom_field_option(field_id: int, key: str) -> str:
    """Delete an option from a list-type custom field."""
    return json.dumps(MyCaseClient().delete_custom_field_option(field_id, key), indent=2)


# ── Case Stages CRUD ──────────────────────────────────────────────────────────

@mcp.tool()
def create_case_stage(name: str) -> str:
    """Create a new case stage."""
    return json.dumps(MyCaseClient().create_case_stage(name), indent=2)


@mcp.tool()
def update_case_stage(stage_id: int, name: str) -> str:
    """Rename a case stage."""
    return json.dumps(MyCaseClient().update_case_stage(stage_id, name), indent=2)


@mcp.tool()
def delete_case_stage(stage_id: int) -> str:
    """Delete a case stage by ID."""
    return json.dumps(MyCaseClient().delete_case_stage(stage_id), indent=2)


# ── Locations CRUD ────────────────────────────────────────────────────────────

@mcp.tool()
def create_location(name: str, address1: str | None = None, city: str | None = None,
                    state: str | None = None, zip_code: str | None = None, country: str | None = None) -> str:
    """Create a new location (courthouse, office, etc.)."""
    return json.dumps(MyCaseClient().create_location(name, address1, city, state, zip_code, country), indent=2)


@mcp.tool()
def update_location(location_id: int, name: str | None = None) -> str:
    """Update a location's name or address fields."""
    return json.dumps(MyCaseClient().update_location(location_id, **({} if name is None else {"name": name})), indent=2)


@mcp.tool()
def delete_location(location_id: int) -> str:
    """Delete a location by ID."""
    return json.dumps(MyCaseClient().delete_location(location_id), indent=2)


# ── People Groups CRUD ────────────────────────────────────────────────────────

@mcp.tool()
def create_people_group(name: str) -> str:
    """Create a new people group (contact category)."""
    return json.dumps(MyCaseClient().create_people_group(name), indent=2)


@mcp.tool()
def update_people_group(group_id: int, name: str) -> str:
    """Rename a people group."""
    return json.dumps(MyCaseClient().update_people_group(group_id, name), indent=2)


@mcp.tool()
def delete_people_group(group_id: int) -> str:
    """Delete a people group by ID."""
    return json.dumps(MyCaseClient().delete_people_group(group_id), indent=2)


# ── Practice Areas ────────────────────────────────────────────────────────────

@mcp.tool()
def list_practice_areas() -> str:
    """List all practice areas defined in this firm."""
    return json.dumps(MyCaseClient().list_practice_areas(), indent=2)


@mcp.tool()
def create_practice_area(name: str) -> str:
    """Create a new practice area."""
    return json.dumps(MyCaseClient().create_practice_area(name), indent=2)


@mcp.tool()
def update_practice_area(area_id: int, name: str) -> str:
    """Rename a practice area."""
    return json.dumps(MyCaseClient().update_practice_area(area_id, name), indent=2)


@mcp.tool()
def delete_practice_area(area_id: int) -> str:
    """Delete a practice area by ID."""
    return json.dumps(MyCaseClient().delete_practice_area(area_id), indent=2)


# ── Referral Sources ──────────────────────────────────────────────────────────

@mcp.tool()
def create_referral_source(name: str) -> str:
    """Create a new referral source."""
    return json.dumps(MyCaseClient().create_referral_source(name), indent=2)


# ── Expenses ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_expenses(case_id: int | None = None, staff_id: int | None = None,
                  per_page: int = 25, page: int = 1) -> str:
    """List expense entries, optionally filtered by case or staff."""
    return json.dumps(MyCaseClient().list_expenses(case_id, staff_id, per_page, page), indent=2)


@mcp.tool()
def get_expense(expense_id: int) -> str:
    """Get a specific expense entry by ID."""
    return json.dumps(MyCaseClient().get_expense(expense_id), indent=2)


@mcp.tool()
def create_expense(activity_name: str, cost: float, units: float = 1,
                   case_id: int | None = None, staff_id: int | None = None,
                   description: str | None = None, billable: bool = True,
                   entry_date: str | None = None) -> str:
    """Create an expense entry. cost is the per-unit cost. entry_date format: YYYY-MM-DD."""
    return json.dumps(MyCaseClient().create_expense(
        activity_name, cost, units, case_id, staff_id, description, billable, entry_date), indent=2)


@mcp.tool()
def delete_expense(expense_id: int) -> str:
    """Delete an expense entry by ID."""
    return json.dumps(MyCaseClient().delete_expense(expense_id), indent=2)


# ── Calls ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_calls(per_page: int = 25, updated_after: str | None = None) -> str:
    """List calls logged in the firm's call log. updated_after format: ISO 8601."""
    return json.dumps(MyCaseClient().list_calls(per_page, updated_after), indent=2)


@mcp.tool()
def create_call(called_at: str, caller_name: str | None = None, caller_phone_number: str | None = None,
                call_for: str | None = None, message: str | None = None,
                client_id: int | None = None, lead_id: int | None = None,
                call_type: str | None = None, resolved: bool | None = None) -> str:
    """Log a call. called_at: ISO 8601 datetime. call_type: 'inbound'|'outbound'."""
    return json.dumps(MyCaseClient().create_call(
        called_at, caller_name, caller_phone_number, call_for, message,
        client_id, lead_id, call_type, resolved), indent=2)


@mcp.tool()
def update_call(call_id: int, **fields) -> str:
    """Update a call log entry."""
    return json.dumps(MyCaseClient().update_call(call_id, **fields), indent=2)


@mcp.tool()
def delete_call(call_id: int) -> str:
    """Delete a call log entry by ID."""
    return json.dumps(MyCaseClient().delete_call(call_id), indent=2)


# ── Folders ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_folder_documents(folder_id: int, per_page: int = 25) -> str:
    """List documents inside a specific folder."""
    return json.dumps(MyCaseClient().list_folder_documents(folder_id, per_page), indent=2)


@mcp.tool()
def list_folder_subfolders(folder_id: int) -> str:
    """List subfolders inside a specific folder."""
    return json.dumps(MyCaseClient().list_folder_subfolders(folder_id), indent=2)


@mcp.tool()
def create_case_subfolder(case_id: int, path: str) -> str:
    """Create a subfolder within a case's document folder. path is the folder name/path."""
    return json.dumps(MyCaseClient().create_case_subfolder(case_id, path), indent=2)


# ── Documents (upload + version management) ───────────────────────────────────

@mcp.tool()
def upload_document(filename: str, path: str, description: str | None = None,
                    assigned_date: str | None = None, staff_id: int | None = None) -> str:
    """Upload a new document to the firm. path is the file storage path/URL."""
    return json.dumps(MyCaseClient().upload_document(filename, path, description, assigned_date, staff_id), indent=2)


@mcp.tool()
def upload_case_document(case_id: int, filename: str, path: str,
                         description: str | None = None, assigned_date: str | None = None) -> str:
    """Upload a document directly to a case."""
    return json.dumps(MyCaseClient().upload_case_document(case_id, filename, path, description, assigned_date), indent=2)


@mcp.tool()
def list_all_document_versions() -> str:
    """List all document versions across the firm."""
    return json.dumps(MyCaseClient().list_all_document_versions(), indent=2)


@mcp.tool()
def upload_document_version(doc_id: int, path: str, filename: str | None = None) -> str:
    """Upload a new version of an existing document."""
    return json.dumps(MyCaseClient().upload_document_version(doc_id, path, filename), indent=2)


@mcp.tool()
def get_document_data(doc_id: int) -> str:
    """Get the download URL or data for a document's latest version."""
    return json.dumps(MyCaseClient().get_document_data(doc_id), indent=2)


@mcp.tool()
def get_document_version_data(doc_id: int, version_number: int) -> str:
    """Get the download URL or data for a specific document version."""
    return json.dumps(MyCaseClient().get_document_version_data(doc_id, version_number), indent=2)


@mcp.tool()
def delete_document_version(doc_id: int, version_number: int) -> str:
    """Delete a specific version of a document."""
    return json.dumps(MyCaseClient().delete_document_version(doc_id, version_number), indent=2)


# ── Webhooks ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_webhook_subscriptions() -> str:
    """List all active webhook subscriptions for this firm."""
    return json.dumps(MyCaseClient().list_webhook_subscriptions(), indent=2)


@mcp.tool()
def create_webhook_subscription(model: str, url: str, actions: list) -> str:
    """Create a webhook subscription. model: resource type (e.g. 'Case'). actions: ['created','updated','deleted']."""
    return json.dumps(MyCaseClient().create_webhook_subscription(model, url, actions), indent=2)


@mcp.tool()
def delete_webhook_subscription(subscription_id: int) -> str:
    """Delete a webhook subscription by ID."""
    return json.dumps(MyCaseClient().delete_webhook_subscription(subscription_id), indent=2)


# ── Entry points ──────────────────────────────────────────────────────────────

def main():
    mcp.run()
