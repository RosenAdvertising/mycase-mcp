#!/usr/bin/env python3
"""MyCase MCP Server — full MyCase API coverage via FastMCP."""

import json
from mcp.server.fastmcp import FastMCP
from .client import MyCaseClient

mcp = FastMCP(
    "mycase-mcp",
    instructions="Full access to MyCase practice management: cases, clients, companies, tasks, calendar, time entries, invoices, notes, documents, leads, messaging, and more.",
)


# ── Identity ──────────────────────────────────────────────────────────────────

@mcp.tool()
def who_am_i() -> str:
    """Get the currently authenticated staff member's profile."""
    return json.dumps(MyCaseClient().get_me(), indent=2)


@mcp.tool()
def get_firm() -> str:
    """Get this firm's profile and settings."""
    return json.dumps(MyCaseClient().get_firm(), indent=2)


@mcp.tool()
def list_staff(page_size: int = 50) -> str:
    """List all staff members in this firm."""
    return json.dumps(MyCaseClient().list_staff(page_size=page_size), indent=2)


@mcp.tool()
def get_staff_member(staff_id: int) -> str:
    """Get a staff member by ID."""
    return json.dumps(MyCaseClient().get_staff(staff_id), indent=2)


# ── Cases ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_cases(status: str = "", page_size: int = 25) -> str:
    """List cases. status: open | closed."""
    return json.dumps(MyCaseClient().list_cases(
        status=status or None, page_size=page_size), indent=2)


@mcp.tool()
def get_case(case_id: int) -> str:
    """Get a case by ID."""
    return json.dumps(MyCaseClient().get_case(case_id), indent=2)


@mcp.tool()
def create_case(name: str, description: str = "", status: str = "open",
                case_stage: str = "", practice_area: str = "") -> str:
    """Create a case. case_stage: must match an existing stage name. status: open | closed."""
    return json.dumps(MyCaseClient().create_case(
        name=name, description=description or None, status=status,
        case_stage=case_stage or None, practice_area=practice_area or None), indent=2)


@mcp.tool()
def update_case(case_id: int, name: str = "", status: str = "",
                description: str = "", case_stage: str = "") -> str:
    """Update a case's name, status, description, or stage."""
    fields = {}
    if name:
        fields["name"] = name
    if status:
        fields["status"] = status
    if description:
        fields["description"] = description
    if case_stage:
        fields["case_stage"] = case_stage
    return json.dumps(MyCaseClient().update_case(case_id, **fields), indent=2)


@mcp.tool()
def delete_case(case_id: int) -> str:
    """Delete a case by ID."""
    return json.dumps(MyCaseClient().delete_case(case_id), indent=2)


@mcp.tool()
def list_cases_for_client(client_id: int, page_size: int = 25) -> str:
    """List all cases associated with a client."""
    return json.dumps(MyCaseClient().list_cases_for_client(client_id, page_size=page_size), indent=2)


@mcp.tool()
def add_client_to_case(case_id: int, client_id: int, role: str = "") -> str:
    """Add a client to a case with an optional role."""
    return json.dumps(MyCaseClient().add_client_to_case(case_id, client_id, role=role or None), indent=2)


@mcp.tool()
def add_company_to_case(case_id: int, company_id: int, role: str = "") -> str:
    """Add a company to a case with an optional role."""
    return json.dumps(MyCaseClient().add_company_to_case(case_id, company_id, role=role or None), indent=2)


@mcp.tool()
def add_staff_to_case(case_id: int, staff_id: int) -> str:
    """Associate a staff member with a case."""
    return json.dumps(MyCaseClient().add_staff_to_case(case_id, staff_id), indent=2)


# ── Clients ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_clients(email: str = "", first_name: str = "", last_name: str = "",
                 cell_phone_number: str = "", updated_after: str = "",
                 page_size: int = 25) -> str:
    """List clients. Filter by email, first_name, last_name, cell_phone_number, or updated_after (ISO 8601)."""
    return json.dumps(MyCaseClient().list_clients(
        email=email or None, first_name=first_name or None, last_name=last_name or None,
        cell_phone_number=cell_phone_number or None, updated_after=updated_after or None,
        page_size=page_size), indent=2)


@mcp.tool()
def get_client(client_id: int) -> str:
    """Get a client by ID."""
    return json.dumps(MyCaseClient().get_client(client_id), indent=2)


@mcp.tool()
def create_client(first_name: str, last_name: str, email: str = "",
                  cell_phone_number: str = "") -> str:
    """Create a new client."""
    return json.dumps(MyCaseClient().create_client(
        first_name=first_name, last_name=last_name,
        email=email or None, cell_phone_number=cell_phone_number or None), indent=2)


@mcp.tool()
def update_client(client_id: int, first_name: str = "", last_name: str = "",
                  email: str = "", cell_phone_number: str = "") -> str:
    """Update a client's details."""
    fields = {}
    if first_name:
        fields["first_name"] = first_name
    if last_name:
        fields["last_name"] = last_name
    if email:
        fields["email"] = email
    if cell_phone_number:
        fields["cell_phone_number"] = cell_phone_number
    return json.dumps(MyCaseClient().update_client(client_id, **fields), indent=2)


@mcp.tool()
def delete_client(client_id: int) -> str:
    """Delete a client by ID."""
    return json.dumps(MyCaseClient().delete_client(client_id), indent=2)


@mcp.tool()
def list_client_notes(client_id: int, page_size: int = 25) -> str:
    """List all notes for a client."""
    return json.dumps(MyCaseClient().list_client_notes(client_id, page_size=page_size), indent=2)


@mcp.tool()
def list_client_message_threads(client_id: int, page_size: int = 25) -> str:
    """List all message threads for a client."""
    return json.dumps(MyCaseClient().list_client_message_threads(client_id, page_size=page_size), indent=2)


# ── Companies ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_companies(name: str = "", email: str = "", updated_after: str = "",
                   page_size: int = 25) -> str:
    """List companies. Filter by name, email, or updated_after (ISO 8601)."""
    return json.dumps(MyCaseClient().list_companies(
        name=name or None, email=email or None, updated_after=updated_after or None,
        page_size=page_size), indent=2)


@mcp.tool()
def get_company(company_id: int) -> str:
    """Get a company by ID."""
    return json.dumps(MyCaseClient().get_company(company_id), indent=2)


@mcp.tool()
def create_company(name: str, email: str = "", main_phone_number: str = "",
                   website: str = "") -> str:
    """Create a new company."""
    return json.dumps(MyCaseClient().create_company(
        name=name, email=email or None,
        main_phone_number=main_phone_number or None, website=website or None), indent=2)


@mcp.tool()
def update_company(company_id: int, name: str = "", email: str = "",
                   main_phone_number: str = "", website: str = "") -> str:
    """Update a company's details."""
    fields = {}
    if name:
        fields["name"] = name
    if email:
        fields["email"] = email
    if main_phone_number:
        fields["main_phone_number"] = main_phone_number
    if website:
        fields["website"] = website
    return json.dumps(MyCaseClient().update_company(company_id, **fields), indent=2)


@mcp.tool()
def delete_company(company_id: int) -> str:
    """Delete a company by ID."""
    return json.dumps(MyCaseClient().delete_company(company_id), indent=2)


@mcp.tool()
def add_client_to_company(company_id: int, client_id: int) -> str:
    """Associate a client with a company."""
    return json.dumps(MyCaseClient().add_client_to_company(company_id, client_id), indent=2)


# ── Tasks ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_tasks(updated_after: str = "", page_size: int = 25) -> str:
    """List tasks. updated_after: ISO 8601 datetime to filter recently changed tasks."""
    return json.dumps(MyCaseClient().list_tasks(
        updated_after=updated_after or None, page_size=page_size), indent=2)


@mcp.tool()
def create_task(name: str, priority: str, due_date: str, staff_id: int,
                case_id: int = 0, description: str = "") -> str:
    """Create a task. priority: Low | Medium | High. due_date: YYYY-MM-DD. staff_id is required."""
    return json.dumps(MyCaseClient().create_task(
        name=name, priority=priority, due_date=due_date, staff_id=staff_id,
        case_id=case_id or None, description=description or None), indent=2)


@mcp.tool()
def update_task(task_id: int, name: str = "", due_date: str = "",
                completed: str = "", priority: str = "") -> str:
    """Update a task. completed: 'true' or 'false' to set completion status. priority: Low | Medium | High."""
    fields = {}
    if name:
        fields["name"] = name
    if due_date:
        fields["due_date"] = due_date
    if completed.lower() in ("true", "false"):
        fields["completed"] = completed.lower() == "true"
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
                end_date: str = "", page_size: int = 25) -> str:
    """List calendar events. start_date/end_date: YYYY-MM-DD."""
    return json.dumps(MyCaseClient().list_events(
        case_id=case_id or None, start_date=start_date or None,
        end_date=end_date or None, page_size=page_size), indent=2)


@mcp.tool()
def create_event(name: str, start: str, end: str, staff_id: int,
                 case_id: int = 0, location_id: int = 0, description: str = "") -> str:
    """Create a calendar event. start/end: ISO 8601. staff_id is required. location_id: ID of a Location record."""
    return json.dumps(MyCaseClient().create_event(
        name=name, start=start, end=end, staff_id=staff_id,
        case_id=case_id or None, location_id=location_id or None,
        description=description or None), indent=2)


@mcp.tool()
def update_event(event_id: int, name: str = "", start: str = "",
                 end: str = "", location: str = "") -> str:
    """Update a calendar event."""
    fields = {}
    if name:
        fields["name"] = name
    if start:
        fields["start"] = start
    if end:
        fields["end"] = end
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
def list_time_entries(updated_after: str = "", page_size: int = 25) -> str:
    """List time entries. updated_after: ISO 8601 datetime to filter by last update."""
    return json.dumps(MyCaseClient().list_time_entries(
        updated_after=updated_after or None, page_size=page_size), indent=2)


@mcp.tool()
def get_time_entry(entry_id: int) -> str:
    """Get a specific time entry by ID."""
    return json.dumps(MyCaseClient().get_time_entry(entry_id), indent=2)


@mcp.tool()
def create_time_entry(case_id: int, staff_id: int, activity_name: str,
                      entry_date: str, rate: float, hours: float,
                      billable: bool = True, description: str = "") -> str:
    """Create a time entry. entry_date: YYYY-MM-DD. rate: dollars/hr. hours: decimal hours worked."""
    return json.dumps(MyCaseClient().create_time_entry(
        case_id=case_id, staff_id=staff_id, activity_name=activity_name,
        entry_date=entry_date, rate=rate, hours=hours,
        billable=billable, description=description or None), indent=2)


@mcp.tool()
def delete_time_entry(entry_id: int) -> str:
    """Delete a time entry by ID."""
    return json.dumps(MyCaseClient().delete_time_entry(entry_id), indent=2)


# ── Invoices ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_invoices(case_id: int = 0, status: str = "", page_size: int = 25) -> str:
    """List invoices. status: draft | sent | paid | overdue."""
    return json.dumps(MyCaseClient().list_invoices(
        case_id=case_id or None, status=status or None, page_size=page_size), indent=2)


@mcp.tool()
def record_invoice_payment(invoice_id: int, amount: float, date: str,
                           notes: str = "") -> str:
    """Record a payment against an invoice. date: YYYY-MM-DD (required)."""
    return json.dumps(MyCaseClient().record_invoice_payment(
        invoice_id=invoice_id, amount=amount, date=date, notes=notes or None), indent=2)


@mcp.tool()
def list_invoice_payments(page_size: int = 25, status: str = "", payable_id: str = "") -> str:
    """List invoice payments. status: pending|success|failure|error|timeout. payable_id: filter by invoice ID."""
    return json.dumps(MyCaseClient().list_invoice_payments(
        page_size=page_size, status=status or None, payable_id=payable_id or None), indent=2)


# ── Notes ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_note(note_id: int) -> str:
    """Get a note by ID."""
    return json.dumps(MyCaseClient().get_note(note_id), indent=2)


@mcp.tool()
def update_note(note_id: int, note: str = "", subject: str = "", date: str = "") -> str:
    """Update a note's body text, subject, or date. date: ISO 8601."""
    return json.dumps(MyCaseClient().update_note(
        note_id, note=note or None, subject=subject or None, date=date or None), indent=2)


@mcp.tool()
def delete_note(note_id: int) -> str:
    """Delete a note by ID."""
    return json.dumps(MyCaseClient().delete_note(note_id), indent=2)


@mcp.tool()
def list_case_notes(case_id: int, page_size: int = 25) -> str:
    """List all notes for a case."""
    return json.dumps(MyCaseClient().list_case_notes(case_id, page_size=page_size), indent=2)


@mcp.tool()
def create_case_note(case_id: int, note: str, subject: str, date: str) -> str:
    """Create a note on a case. All three fields (note body, subject, date ISO 8601) are required."""
    return json.dumps(MyCaseClient().create_case_note(case_id, note=note, subject=subject, date=date), indent=2)


@mcp.tool()
def create_client_note(client_id: int, note: str, subject: str, date: str) -> str:
    """Create a note on a client. All three fields (note body, subject, date ISO 8601) are required."""
    return json.dumps(MyCaseClient().create_client_note(client_id, note=note, subject=subject, date=date), indent=2)


@mcp.tool()
def create_company_note(company_id: int, note: str, subject: str, date: str) -> str:
    """Create a note on a company. All three fields (note body, subject, date ISO 8601) are required."""
    return json.dumps(MyCaseClient().create_company_note(company_id, note=note, subject=subject, date=date), indent=2)


# ── Documents ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_documents(case_id: int = 0, page_size: int = 25) -> str:
    """List documents, optionally filtered by case."""
    return json.dumps(MyCaseClient().list_documents(
        case_id=case_id or None, page_size=page_size), indent=2)


@mcp.tool()
def get_document(doc_id: int) -> str:
    """Get document metadata by ID."""
    return json.dumps(MyCaseClient().get_document(doc_id), indent=2)


@mcp.tool()
def update_document(doc_id: int, name: str = "", description: str = "") -> str:
    """Update a document's filename or description."""
    return json.dumps(MyCaseClient().update_document(
        doc_id, name=name or None, description=description or None), indent=2)


@mcp.tool()
def delete_document(doc_id: int) -> str:
    """Delete a document by ID."""
    return json.dumps(MyCaseClient().delete_document(doc_id), indent=2)


@mcp.tool()
def list_case_documents(case_id: int, page_size: int = 25) -> str:
    """List all documents for a case."""
    return json.dumps(MyCaseClient().list_case_documents(case_id, page_size=page_size), indent=2)


@mcp.tool()
def list_document_versions(doc_id: int) -> str:
    """List all versions of a document."""
    return json.dumps(MyCaseClient().list_document_versions(doc_id), indent=2)


@mcp.tool()
def get_case_folder(case_id: int) -> str:
    """Get the root document folder for a case."""
    return json.dumps(MyCaseClient().get_case_folder(case_id), indent=2)


@mcp.tool()
def upload_document(filename: str, path: str, description: str = "",
                    assigned_date: str = "", staff_id: int = 0) -> str:
    """Upload a new document. path is the file storage path/URL."""
    return json.dumps(MyCaseClient().upload_document(
        filename=filename, path=path, description=description or None,
        assigned_date=assigned_date or None, staff_id=staff_id or None), indent=2)


@mcp.tool()
def upload_case_document(case_id: int, filename: str, path: str,
                          description: str = "", assigned_date: str = "") -> str:
    """Upload a document directly to a case."""
    return json.dumps(MyCaseClient().upload_case_document(
        case_id=case_id, filename=filename, path=path,
        description=description or None, assigned_date=assigned_date or None), indent=2)


@mcp.tool()
def list_all_document_versions() -> str:
    """List all document versions across the firm."""
    return json.dumps(MyCaseClient().list_all_document_versions(), indent=2)


@mcp.tool()
def upload_document_version(doc_id: int) -> str:
    """Initiate a new version upload for an existing document. Returns upload instructions."""
    return json.dumps(MyCaseClient().upload_document_version(doc_id), indent=2)


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


# ── Leads ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_leads(status: str = "", page_size: int = 25) -> str:
    """List leads. status: new | contacted | qualified | converted | closed."""
    return json.dumps(MyCaseClient().list_leads(
        status=status or None, page_size=page_size), indent=2)


@mcp.tool()
def get_lead(lead_id: int) -> str:
    """Get a lead by ID."""
    return json.dumps(MyCaseClient().get_lead(lead_id), indent=2)


@mcp.tool()
def create_lead(first_name: str, last_name: str, email: str = "",
                cell_phone_number: str = "", referral_source_id: int = 0) -> str:
    """Create a new lead."""
    return json.dumps(MyCaseClient().create_lead(
        first_name=first_name, last_name=last_name,
        email=email or None, cell_phone_number=cell_phone_number or None,
        referral_source_id=referral_source_id or None), indent=2)


@mcp.tool()
def update_lead(lead_id: int, status: str = "", first_name: str = "",
                last_name: str = "", email: str = "") -> str:
    """Update a lead. status: new | contacted | qualified | converted | closed."""
    fields = {}
    if status:
        fields["status"] = status
    if first_name:
        fields["first_name"] = first_name
    if last_name:
        fields["last_name"] = last_name
    if email:
        fields["email"] = email
    return json.dumps(MyCaseClient().update_lead(lead_id, **fields), indent=2)


# ── Messaging ─────────────────────────────────────────────────────────────────

@mcp.tool()
def create_message_thread(subject: str, first_message_body: str,
                           sender_id: int = 0, client_ids: str = "",
                           staff_ids: str = "") -> str:
    """Create a message thread. client_ids/staff_ids: comma-separated IDs."""
    cids = [int(x.strip()) for x in client_ids.split(",") if x.strip()] if client_ids else None
    sids = [int(x.strip()) for x in staff_ids.split(",") if x.strip()] if staff_ids else None
    return json.dumps(MyCaseClient().create_message_thread(
        subject=subject, first_message_body=first_message_body,
        sender_id=sender_id or None, client_ids=cids, staff_ids=sids), indent=2)


@mcp.tool()
def create_case_message_thread(case_id: int, subject: str, first_message_body: str,
                                sender_id: int = 0, client_ids: str = "",
                                staff_ids: str = "") -> str:
    """Create a message thread on a case. client_ids/staff_ids: comma-separated IDs."""
    cids = [int(x.strip()) for x in client_ids.split(",") if x.strip()] if client_ids else None
    sids = [int(x.strip()) for x in staff_ids.split(",") if x.strip()] if staff_ids else None
    return json.dumps(MyCaseClient().create_case_message_thread(
        case_id=case_id, subject=subject, first_message_body=first_message_body,
        sender_id=sender_id or None, client_ids=cids, staff_ids=sids), indent=2)


@mcp.tool()
def post_message(thread_id: int, body: str, sender_id: int = 0) -> str:
    """Post a message to an existing message thread."""
    return json.dumps(MyCaseClient().post_message(
        thread_id, body_text=body, sender_id=sender_id or None), indent=2)


# ── Reference Data ────────────────────────────────────────────────────────────

@mcp.tool()
def list_case_stages() -> str:
    """List all case stages configured in this firm."""
    return json.dumps(MyCaseClient().list_case_stages(), indent=2)


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


@mcp.tool()
def list_case_roles() -> str:
    """List all case roles (e.g. plaintiff, defendant, attorney)."""
    return json.dumps(MyCaseClient().list_case_roles(), indent=2)


@mcp.tool()
def list_referral_sources() -> str:
    """List all referral sources configured in this firm."""
    return json.dumps(MyCaseClient().list_referral_sources(), indent=2)


@mcp.tool()
def create_referral_source(name: str) -> str:
    """Create a new referral source."""
    return json.dumps(MyCaseClient().create_referral_source(name), indent=2)


@mcp.tool()
def list_locations() -> str:
    """List all locations (courthouses, offices, etc.) in this firm."""
    return json.dumps(MyCaseClient().list_locations(), indent=2)


@mcp.tool()
def create_location(name: str, address1: str = "", city: str = "",
                    state: str = "", zip_code: str = "", country: str = "") -> str:
    """Create a new location."""
    return json.dumps(MyCaseClient().create_location(
        name=name, address1=address1 or None, city=city or None,
        state=state or None, zip_code=zip_code or None, country=country or None), indent=2)


@mcp.tool()
def update_location(location_id: int, name: str = "") -> str:
    """Update a location's name."""
    fields = {}
    if name:
        fields["name"] = name
    return json.dumps(MyCaseClient().update_location(location_id, **fields), indent=2)


@mcp.tool()
def delete_location(location_id: int) -> str:
    """Delete a location by ID."""
    return json.dumps(MyCaseClient().delete_location(location_id), indent=2)


@mcp.tool()
def list_people_groups() -> str:
    """List all people groups (contact categories) in this firm."""
    return json.dumps(MyCaseClient().list_people_groups(), indent=2)


@mcp.tool()
def create_people_group(name: str) -> str:
    """Create a new people group."""
    return json.dumps(MyCaseClient().create_people_group(name), indent=2)


@mcp.tool()
def update_people_group(group_id: int, name: str) -> str:
    """Rename a people group."""
    return json.dumps(MyCaseClient().update_people_group(group_id, name), indent=2)


@mcp.tool()
def delete_people_group(group_id: int) -> str:
    """Delete a people group by ID."""
    return json.dumps(MyCaseClient().delete_people_group(group_id), indent=2)


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


@mcp.tool()
def list_custom_fields() -> str:
    """List all custom fields configured in this firm."""
    return json.dumps(MyCaseClient().list_custom_fields(), indent=2)


@mcp.tool()
def create_custom_field(name: str, parent_type: str, field_type: str,
                         list_options: str = "") -> str:
    """Create a custom field. parent_type: Case|Client|Lead. field_type: text|date|list|checkbox|number. list_options: comma-separated option values for list type fields (e.g. 'Option A,Option B,Option C')."""
    opts = [v.strip() for v in list_options.split(",") if v.strip()] if list_options else None
    return json.dumps(MyCaseClient().create_custom_field(name, parent_type, field_type, opts), indent=2)


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


# ── Expenses ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_expenses(updated_after: str = "", page_size: int = 25) -> str:
    """List expense entries. updated_after: ISO 8601 datetime to filter by last update."""
    return json.dumps(MyCaseClient().list_expenses(
        updated_after=updated_after or None, page_size=page_size), indent=2)


@mcp.tool()
def get_expense(expense_id: int) -> str:
    """Get a specific expense entry by ID."""
    return json.dumps(MyCaseClient().get_expense(expense_id), indent=2)


@mcp.tool()
def create_expense(activity_name: str, cost: float, units: float = 1,
                   case_id: int = 0, staff_id: int = 0, description: str = "",
                   billable: bool = True, entry_date: str = "") -> str:
    """Create an expense entry. cost is per-unit cost. entry_date: YYYY-MM-DD."""
    return json.dumps(MyCaseClient().create_expense(
        activity_name=activity_name, cost=cost, units=units,
        case_id=case_id or None, staff_id=staff_id or None,
        description=description or None, billable=billable,
        entry_date=entry_date or None), indent=2)


@mcp.tool()
def delete_expense(expense_id: int) -> str:
    """Delete an expense entry by ID."""
    return json.dumps(MyCaseClient().delete_expense(expense_id), indent=2)


# ── Calls ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_calls(page_size: int = 25, updated_after: str = "") -> str:
    """List calls in the firm's call log. updated_after: ISO 8601."""
    return json.dumps(MyCaseClient().list_calls(
        page_size=page_size, updated_after=updated_after or None), indent=2)


@mcp.tool()
def create_call(called_at: str, caller_name: str = "", caller_phone_number: str = "",
                call_for_staff_id: int = 0, message: str = "", client_id: int = 0,
                lead_id: int = 0, call_type: str = "", resolved: bool = False) -> str:
    """Log a call. called_at: ISO 8601. call_type: inbound | outbound. call_for_staff_id: staff member the call is for."""
    return json.dumps(MyCaseClient().create_call(
        called_at=called_at, caller_name=caller_name or None,
        caller_phone_number=caller_phone_number or None,
        call_for_staff_id=call_for_staff_id or None,
        message=message or None, client_id=client_id or None,
        lead_id=lead_id or None, call_type=call_type or None,
        resolved=resolved), indent=2)


@mcp.tool()
def update_call(call_id: int, caller_name: str = "", caller_phone_number: str = "",
                call_for: str = "", message: str = "", call_type: str = "",
                resolved: str = "") -> str:
    """Update a call log entry. resolved: 'true' or 'false' to set resolved status."""
    resolved_val = None
    if resolved.lower() in ("true", "false"):
        resolved_val = resolved.lower() == "true"
    return json.dumps(MyCaseClient().update_call(
        call_id, caller_name=caller_name or None,
        caller_phone_number=caller_phone_number or None,
        call_for=call_for or None, message=message or None,
        call_type=call_type or None, resolved=resolved_val), indent=2)


@mcp.tool()
def delete_call(call_id: int) -> str:
    """Delete a call log entry by ID."""
    return json.dumps(MyCaseClient().delete_call(call_id), indent=2)


# ── Folders ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_folder_documents(folder_id: int, page_size: int = 25) -> str:
    """List documents inside a specific folder."""
    return json.dumps(MyCaseClient().list_folder_documents(folder_id, page_size=page_size), indent=2)


@mcp.tool()
def list_folder_subfolders(folder_id: int) -> str:
    """List subfolders inside a specific folder."""
    return json.dumps(MyCaseClient().list_folder_subfolders(folder_id), indent=2)


@mcp.tool()
def create_case_subfolder(case_id: int, path: str) -> str:
    """Create a subfolder within a case. path: relative path, e.g. 'Contracts/2026'."""
    return json.dumps(MyCaseClient().create_case_subfolder(case_id, path), indent=2)


# ── Webhooks ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_webhook_subscriptions() -> str:
    """List all active webhook subscriptions for this firm."""
    return json.dumps(MyCaseClient().list_webhook_subscriptions(), indent=2)


@mcp.tool()
def create_webhook_subscription(model: str, url: str, actions: str) -> str:
    """Create a webhook. model: resource type (case|client|company|event|lead|message). actions: comma-separated list of created|updated|deleted (e.g. 'created,updated')."""
    action_list = [a.strip() for a in actions.split(",") if a.strip()]
    return json.dumps(MyCaseClient().create_webhook_subscription(model, url, action_list), indent=2)


@mcp.tool()
def delete_webhook_subscription(subscription_id: int) -> str:
    """Delete a webhook subscription by ID."""
    return json.dumps(MyCaseClient().delete_webhook_subscription(subscription_id), indent=2)


# ── Entry points ──────────────────────────────────────────────────────────────

def main():
    mcp.run()
