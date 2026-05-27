#!/usr/bin/env python3
"""MyCase API v1 client. Handles OAuth tokens, auto-refresh, and all API operations."""

import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

BASE_URL = "https://external-integrations.mycase.com/v1"
AUTH_URL = "https://auth.mycase.com/login_sessions/new"
TOKEN_URL = "https://auth.mycase.com/tokens"
CONFIG_DIR = Path.home() / ".mycase-mcp"


def _load_env():
    env_file = CONFIG_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


_load_env()

CLIENT_ID = os.environ.get("MYCASE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("MYCASE_CLIENT_SECRET", "")


def _retry_after_seconds(resp, default=10):
    try:
        return int(resp.headers.get("Retry-After", default))
    except (TypeError, ValueError):
        return default


def _json_response(resp):
    try:
        return resp.json()
    except ValueError:
        raise RuntimeError(
            f"MyCase API returned non-JSON response ({resp.status_code}): "
            f"{resp.text[:200]}"
        )


class TokenManager:
    def __init__(self):
        self.token_file = CONFIG_DIR / "tokens.json"
        self.tokens = self._load()

    def _load(self):
        if self.token_file.exists():
            with open(self.token_file) as f:
                return json.load(f)
        return {}

    def save(self, tokens):
        self.tokens = tokens
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, "w") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.token_file, 0o600)

    @property
    def access_token(self):
        return self.tokens.get("access_token", "")

    @property
    def refresh_token(self):
        return self.tokens.get("refresh_token", "")

    def refresh(self):
        if not self.refresh_token:
            raise RuntimeError("No refresh token. Run: mycase-mcp-setup")
        if not CLIENT_ID or not CLIENT_SECRET:
            raise RuntimeError(
                "MYCASE_CLIENT_ID and MYCASE_CLIENT_SECRET are required. Run: mycase-mcp-setup"
            )
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        if resp.status_code == 200:
            new_tokens = _json_response(resp)
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = self.refresh_token
            new_tokens["refreshed_at"] = datetime.now(timezone.utc).isoformat()
            self.save(new_tokens)
            return new_tokens
        raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text}")


class MyCaseClient:
    def __init__(self):
        self.tm = TokenManager()
        if not self.tm.access_token and not self.tm.refresh_token:
            raise RuntimeError("No MyCase OAuth tokens found. Run: mycase-mcp-setup")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.tm.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self, method, path, params=None, json_body=None, retry=True, _rate_retries=0
    ):
        url = f"{BASE_URL}/{path.lstrip('/')}"
        resp = self.session.request(
            method, url, params=params, json=json_body, allow_redirects=False
        )

        if resp.status_code == 401 and retry:
            self.tm.refresh()
            self.session.headers["Authorization"] = f"Bearer {self.tm.access_token}"
            return self._request(
                method, path, params=params, json_body=json_body, retry=False
            )

        if resp.status_code == 429 and _rate_retries < 3:
            retry_after = _retry_after_seconds(resp)
            print(f"Rate limited. Waiting {retry_after}s...", file=sys.stderr)
            time.sleep(retry_after)
            return self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                retry=retry,
                _rate_retries=_rate_retries + 1,
            )

        # 202 Accepted = queued, no body (e.g. POST /calls)
        if resp.status_code == 202:
            return {"accepted": True}

        # 204 No Content
        if resp.status_code == 204:
            return {"success": True}

        # 302 = signed download URL in Location header (document data endpoints)
        if resp.status_code == 302:
            return {"download_url": resp.headers.get("Location")}

        if not resp.ok:
            raise RuntimeError(
                f"MyCase API error {resp.status_code}: {resp.text[:400]}"
            )

        return _json_response(resp)

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None):
        return self._request("POST", path, json_body=body)

    def put(self, path, body=None):
        return self._request("PUT", path, json_body=body)

    def delete(self, path):
        return self._request("DELETE", path)

    # ── Identity ──────────────────────────────────────────────────────────────

    def get_me(self):
        return self.get("/me")

    def get_firm(self):
        return self.get("/firm")

    def list_staff(self, page_size=50):
        return self.get("/staff", {"page_size": page_size})

    def get_staff(self, staff_id):
        return self.get(f"/staff/{staff_id}")

    # ── Cases ─────────────────────────────────────────────────────────────────

    def list_cases(self, status=None, page_size=25):
        params = {"page_size": page_size}
        if status:
            params["filter[status]"] = status
        return self.get("/cases", params)

    def get_case(self, case_id):
        return self.get(f"/cases/{case_id}")

    def create_case(
        self, name, description=None, status="open", case_stage=None, practice_area=None
    ):
        body = {"name": name, "status": status}
        if description:
            body["description"] = description
        if case_stage:
            body["case_stage"] = case_stage
        if practice_area:
            body["practice_area"] = practice_area
        return self.post("/cases", body)

    def update_case(self, case_id, **fields):
        return self.put(f"/cases/{case_id}", fields)

    def delete_case(self, case_id):
        return self.delete(f"/cases/{case_id}")

    def list_cases_for_client(self, client_id, page_size=25):
        return self.get(f"/clients/{client_id}/cases", {"page_size": page_size})

    def add_client_to_case(self, case_id, client_id, role=None):
        entry = {"id": client_id}
        if role:
            entry["role"] = role
        return self.post(
            f"/cases/{case_id}/relationships/clients", {"clients": [entry]}
        )

    def add_company_to_case(self, case_id, company_id, role=None):
        entry = {"id": company_id}
        if role:
            entry["role"] = role
        return self.post(
            f"/cases/{case_id}/relationships/companies", {"companies": [entry]}
        )

    def add_staff_to_case(self, case_id, staff_id):
        return self.post(
            f"/cases/{case_id}/relationships/staff", {"staff": [{"id": staff_id}]}
        )

    # ── Clients ───────────────────────────────────────────────────────────────

    def list_clients(
        self,
        email=None,
        first_name=None,
        last_name=None,
        cell_phone_number=None,
        updated_after=None,
        page_size=25,
    ):
        params = {"page_size": page_size}
        if email:
            params["filter[email]"] = email
        if first_name:
            params["filter[first_name]"] = first_name
        if last_name:
            params["filter[last_name]"] = last_name
        if cell_phone_number:
            params["filter[cell_phone_number]"] = cell_phone_number
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self.get("/clients", params)

    def get_client(self, client_id):
        return self.get(f"/clients/{client_id}")

    def create_client(self, first_name, last_name, email=None, cell_phone_number=None):
        body = {"first_name": first_name, "last_name": last_name}
        if email:
            body["email"] = email
        if cell_phone_number:
            body["cell_phone_number"] = cell_phone_number
        return self.post("/clients", body)

    def update_client(self, client_id, **fields):
        return self.put(f"/clients/{client_id}", fields)

    def delete_client(self, client_id):
        return self.delete(f"/clients/{client_id}")

    # ── Companies ─────────────────────────────────────────────────────────────

    def list_companies(self, name=None, email=None, updated_after=None, page_size=25):
        params = {"page_size": page_size}
        if name:
            params["filter[name]"] = name
        if email:
            params["filter[email]"] = email
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self.get("/companies", params)

    def get_company(self, company_id):
        return self.get(f"/companies/{company_id}")

    def create_company(self, name, email=None, main_phone_number=None, website=None):
        body = {"name": name}
        if email:
            body["email"] = email
        if main_phone_number:
            body["main_phone_number"] = main_phone_number
        if website:
            body["website"] = website
        return self.post("/companies", body)

    def update_company(self, company_id, **fields):
        return self.put(f"/companies/{company_id}", fields)

    def delete_company(self, company_id):
        return self.delete(f"/companies/{company_id}")

    def add_client_to_company(self, company_id, client_id):
        return self.post(
            f"/companies/{company_id}/relationships/clients",
            {"clients": [{"id": client_id}]},
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def list_tasks(self, updated_after=None, page_size=25):
        params = {"page_size": page_size}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self.get("/tasks", params)

    def create_task(
        self, name, priority, due_date, staff_id, case_id=None, description=None
    ):
        body = {
            "name": name,
            "priority": priority,
            "due_date": due_date,
            "staff": [{"id": staff_id}],
        }
        if case_id:
            body["case"] = {"id": case_id}
        if description:
            body["description"] = description
        return self.post("/tasks", body)

    def update_task(self, task_id, **fields):
        return self.put(f"/tasks/{task_id}", fields)

    def delete_task(self, task_id):
        return self.delete(f"/tasks/{task_id}")

    def assign_task_to_staff(self, task_id, staff_id):
        return self.post(
            f"/tasks/{task_id}/relationships/staff", {"staff": [{"id": staff_id}]}
        )

    # ── Events ────────────────────────────────────────────────────────────────

    def list_events(self, case_id=None, start_date=None, end_date=None, page_size=25):
        params = {"page_size": page_size}
        if case_id:
            params["filter[case_id]"] = case_id
        if start_date:
            params["filter[start_date]"] = start_date
        if end_date:
            params["filter[end_date]"] = end_date
        return self.get("/events", params)

    def create_event(
        self,
        name,
        start,
        end,
        staff_id,
        case_id=None,
        location_id=None,
        description=None,
    ):
        body = {"name": name, "start": start, "end": end, "staff": [{"id": staff_id}]}
        if case_id:
            body["case"] = {"id": case_id}
        if location_id:
            body["location"] = {"id": location_id}
        if description:
            body["description"] = description
        return self.post("/events", body)

    def update_event(self, event_id, **fields):
        return self.put(f"/events/{event_id}", fields)

    def delete_event(self, event_id):
        return self.delete(f"/events/{event_id}")

    def add_staff_to_event(self, event_id, staff_id):
        return self.post(
            f"/events/{event_id}/relationships/staff", {"staff": [{"id": staff_id}]}
        )

    # ── Time Entries ──────────────────────────────────────────────────────────

    def list_time_entries(self, updated_after=None, page_size=25):
        params = {"page_size": page_size}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self.get("/time_entries", params)

    def get_time_entry(self, entry_id):
        return self.get(f"/time_entries/{entry_id}")

    def create_time_entry(
        self,
        case_id,
        staff_id,
        activity_name,
        entry_date,
        rate,
        hours,
        billable=True,
        description=None,
    ):
        body = {
            "activity_name": activity_name,
            "entry_date": entry_date,
            "rate": rate,
            "hours": hours,
            "billable": billable,
            "case": {"id": case_id},
            "staff": {"id": staff_id},
        }
        if description:
            body["description"] = description
        return self.post("/time_entries", body)

    def delete_time_entry(self, entry_id):
        return self.delete(f"/time_entries/{entry_id}")

    # ── Invoices ──────────────────────────────────────────────────────────────

    def list_invoices(self, case_id=None, status=None, page_size=25):
        params = {"page_size": page_size}
        if case_id:
            params["filter[case_id]"] = case_id
        if status:
            params["filter[status]"] = status
        return self.get("/invoices", params)

    def delete_invoice(self, invoice_id):
        return self.delete(f"/invoices/{invoice_id}")

    def record_invoice_payment(self, invoice_id, amount, date, notes=None):
        body = {"amount": amount, "date": date}
        if notes:
            body["notes"] = notes
        return self.post(f"/invoices/{invoice_id}/payments", body)

    def list_invoice_payments(self, page_size=25, status=None, payable_id=None):
        params = {"page_size": page_size}
        if status:
            params["filter[status]"] = status
        if payable_id:
            params["filter[payable_id]"] = payable_id
        return self.get("/invoice_payments", params)

    # ── Notes ─────────────────────────────────────────────────────────────────

    def get_note(self, note_id):
        return self.get(f"/notes/{note_id}")

    def update_note(self, note_id, note=None, subject=None, date=None):
        body = {}
        if note:
            body["note"] = note
        if subject:
            body["subject"] = subject
        if date:
            body["date"] = date
        return self.put(f"/notes/{note_id}", body)

    def delete_note(self, note_id):
        return self.delete(f"/notes/{note_id}")

    def list_case_notes(self, case_id, page_size=25):
        return self.get(f"/cases/{case_id}/notes", {"page_size": page_size})

    def create_case_note(self, case_id, note, subject, date):
        return self.post(
            f"/cases/{case_id}/notes", {"note": note, "subject": subject, "date": date}
        )

    def list_client_notes(self, client_id, page_size=25):
        return self.get(f"/clients/{client_id}/notes", {"page_size": page_size})

    def create_client_note(self, client_id, note, subject, date):
        return self.post(
            f"/clients/{client_id}/notes",
            {"note": note, "subject": subject, "date": date},
        )

    def create_company_note(self, company_id, note, subject, date):
        return self.post(
            f"/companies/{company_id}/notes",
            {"note": note, "subject": subject, "date": date},
        )

    # ── Documents ─────────────────────────────────────────────────────────────

    def list_documents(self, case_id=None, page_size=25):
        params = {"page_size": page_size}
        if case_id:
            params["filter[case_id]"] = case_id
        return self.get("/documents", params)

    def get_document(self, doc_id):
        return self.get(f"/documents/{doc_id}")

    def update_document(self, doc_id, name=None, description=None):
        body = {}
        if name:
            body["filename"] = name
        if description:
            body["description"] = description
        return self.put(f"/documents/{doc_id}", body)

    def delete_document(self, doc_id):
        return self.delete(f"/documents/{doc_id}")

    def list_document_versions(self, doc_id):
        return self.get(f"/documents/{doc_id}/versions")

    def list_case_documents(self, case_id, page_size=25):
        return self.get(f"/cases/{case_id}/documents", {"page_size": page_size})

    def get_case_folder(self, case_id):
        return self.get(f"/cases/{case_id}/folder")

    def upload_document(
        self, filename, path, description=None, assigned_date=None, staff_id=None
    ):
        body = {"filename": filename, "path": path}
        if description:
            body["description"] = description
        if assigned_date:
            body["assigned_date"] = assigned_date
        if staff_id:
            body["staff"] = {"id": staff_id}
        return self.post("/documents", body)

    def upload_case_document(
        self, case_id, filename, path, description=None, assigned_date=None
    ):
        body = {"filename": filename, "path": path}
        if description:
            body["description"] = description
        if assigned_date:
            body["assigned_date"] = assigned_date
        return self.post(f"/cases/{case_id}/documents", body)

    def list_all_document_versions(self):
        return self.get("/document_versions")

    def upload_document_version(self, doc_id):
        return self.post(f"/documents/{doc_id}/versions")

    def get_document_data(self, doc_id):
        return self.get(f"/documents/{doc_id}/data")

    def get_document_version_data(self, doc_id, version_number):
        return self.get(f"/documents/{doc_id}/versions/{version_number}/data")

    def delete_document_version(self, doc_id, version_number):
        return self.delete(f"/documents/{doc_id}/versions/{version_number}")

    # ── Leads ─────────────────────────────────────────────────────────────────

    def list_leads(self, status=None, page_size=25):
        params = {"page_size": page_size}
        if status:
            params["filter[status]"] = status
        return self.get("/leads", params)

    def get_lead(self, lead_id):
        return self.get(f"/leads/{lead_id}")

    def create_lead(
        self,
        first_name,
        last_name,
        email=None,
        cell_phone_number=None,
        referral_source_id=None,
    ):
        body = {"first_name": first_name, "last_name": last_name}
        if email:
            body["email"] = email
        if cell_phone_number:
            body["cell_phone_number"] = cell_phone_number
        if referral_source_id:
            body["referral_source_reference"] = {"id": referral_source_id}
        return self.post("/leads", body)

    def update_lead(self, lead_id, **fields):
        return self.put(f"/leads/{lead_id}", fields)

    # ── Message Threads ───────────────────────────────────────────────────────

    def create_message_thread(
        self,
        subject,
        first_message_body,
        sender_id=None,
        client_ids=None,
        staff_ids=None,
    ):
        body = {"subject": subject, "first_message_body": first_message_body}
        if sender_id:
            body["sender"] = {"id": sender_id}
        if client_ids:
            body["client_recipients"] = [{"id": i} for i in client_ids]
        if staff_ids:
            body["staff_recipients"] = [{"id": i} for i in staff_ids]
        return self.post("/message_threads", body)

    def create_case_message_thread(
        self,
        case_id,
        subject,
        first_message_body,
        sender_id=None,
        client_ids=None,
        staff_ids=None,
    ):
        body = {"subject": subject, "first_message_body": first_message_body}
        if sender_id:
            body["sender"] = {"id": sender_id}
        if client_ids:
            body["client_recipients"] = [{"id": i} for i in client_ids]
        if staff_ids:
            body["staff_recipients"] = [{"id": i} for i in staff_ids]
        return self.post(f"/cases/{case_id}/message_threads", body)

    def list_client_message_threads(self, client_id, page_size=25):
        return self.get(
            f"/clients/{client_id}/message_threads", {"page_size": page_size}
        )

    def post_message(self, thread_id, body_text, sender_id=None):
        body = {"body": body_text}
        if sender_id:
            body["sender"] = {"id": sender_id}
        return self.post(f"/message_threads/{thread_id}/messages", body)

    # ── Reference Data ────────────────────────────────────────────────────────

    def list_case_stages(self, page_size=50):
        return self.get("/case_stages", {"page_size": page_size})

    def create_case_stage(self, name):
        return self.post("/case_stages", {"name": name})

    def update_case_stage(self, stage_id, name):
        return self.put(f"/case_stages/{stage_id}", {"name": name})

    def delete_case_stage(self, stage_id):
        return self.delete(f"/case_stages/{stage_id}")

    def list_case_roles(self):
        return self.get("/case_roles")

    def list_referral_sources(self, page_size=50):
        return self.get("/referral_sources", {"page_size": page_size})

    def create_referral_source(self, name):
        return self.post("/referral_sources", {"name": name})

    def list_locations(self, page_size=50):
        return self.get("/locations", {"page_size": page_size})

    def create_location(
        self, name, address1=None, city=None, state=None, zip_code=None, country=None
    ):
        body = {"name": name}
        if any([address1, city, state, zip_code, country]):
            body["address"] = {
                k: v
                for k, v in {
                    "address1": address1,
                    "city": city,
                    "state": state,
                    "zip_code": zip_code,
                    "country": country,
                }.items()
                if v
            }
        return self.post("/locations", body)

    def update_location(self, location_id, **fields):
        return self.put(f"/locations/{location_id}", fields)

    def delete_location(self, location_id):
        return self.delete(f"/locations/{location_id}")

    def list_people_groups(self, page_size=50):
        return self.get("/people_groups", {"page_size": page_size})

    def create_people_group(self, name):
        return self.post("/people_groups", {"name": name})

    def update_people_group(self, group_id, name):
        return self.put(f"/people_groups/{group_id}", {"name": name})

    def delete_people_group(self, group_id):
        return self.delete(f"/people_groups/{group_id}")

    def list_practice_areas(self, page_size=50):
        return self.get("/practice_areas", {"page_size": page_size})

    def create_practice_area(self, name):
        return self.post("/practice_areas", {"name": name})

    def update_practice_area(self, area_id, name):
        return self.put(f"/practice_areas/{area_id}", {"name": name})

    def delete_practice_area(self, area_id):
        return self.delete(f"/practice_areas/{area_id}")

    def list_custom_fields(self, page_size=50):
        return self.get("/custom_fields", {"page_size": page_size})

    def create_custom_field(self, name, parent_type, field_type, list_options=None):
        body = {"name": name, "parent_type": parent_type, "field_type": field_type}
        if list_options:
            body["list_options"] = [{"option_value": v} for v in list_options]
        return self.post("/custom_fields", body)

    def get_custom_field(self, field_id):
        return self.get(f"/custom_fields/{field_id}")

    def delete_custom_field(self, field_id):
        return self.delete(f"/custom_fields/{field_id}")

    def list_custom_field_options(self, field_id):
        return self.get(f"/custom_fields/{field_id}/list_options")

    def create_custom_field_option(self, field_id, option_value):
        return self.post(
            f"/custom_fields/{field_id}/list_options",
            {"list_options": [{"option_value": option_value}]},
        )

    def update_custom_field_option(self, field_id, key, option_value):
        return self.put(
            f"/custom_fields/{field_id}/list_options/{key}",
            {"option_value": option_value},
        )

    def delete_custom_field_option(self, field_id, key):
        return self.delete(f"/custom_fields/{field_id}/list_options/{key}")

    # ── Expenses ──────────────────────────────────────────────────────────────

    def list_expenses(self, updated_after=None, page_size=25):
        params = {"page_size": page_size}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self.get("/expenses", params)

    def get_expense(self, expense_id):
        return self.get(f"/expenses/{expense_id}")

    def create_expense(
        self,
        activity_name,
        cost,
        units=1,
        case_id=None,
        staff_id=None,
        description=None,
        billable=True,
        entry_date=None,
    ):
        body = {
            "activity_name": activity_name,
            "cost": cost,
            "units": units,
            "billable": billable,
        }
        if case_id:
            body["case"] = {"id": case_id}
        if staff_id:
            body["staff"] = {"id": staff_id}
        if description:
            body["description"] = description
        if entry_date:
            body["entry_date"] = entry_date
        return self.post("/expenses", body)

    def delete_expense(self, expense_id):
        return self.delete(f"/expenses/{expense_id}")

    # ── Calls ─────────────────────────────────────────────────────────────────

    def list_calls(self, page_size=25, updated_after=None):
        params = {"page_size": page_size}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self.get("/calls", params)

    def create_call(
        self,
        called_at,
        caller_name=None,
        caller_phone_number=None,
        call_for_staff_id=None,
        message=None,
        client_id=None,
        lead_id=None,
        call_type=None,
        resolved=None,
    ):
        body = {"called_at": called_at}
        if caller_name:
            body["caller_name"] = caller_name
        if caller_phone_number:
            body["caller_phone_number"] = caller_phone_number
        if call_for_staff_id:
            body["call_for"] = {"id": call_for_staff_id}
        if message:
            body["message"] = message
        if client_id:
            body["client"] = {"id": client_id}
        if lead_id:
            body["lead"] = {"id": lead_id}
        if call_type:
            body["call_type"] = call_type
        if resolved is not None:
            body["resolved"] = resolved
        return self.post("/calls", body)

    def update_call(
        self,
        call_id,
        caller_name=None,
        caller_phone_number=None,
        call_for=None,
        message=None,
        call_type=None,
        resolved=None,
    ):
        body = {}
        if caller_name is not None:
            body["caller_name"] = caller_name
        if caller_phone_number is not None:
            body["caller_phone_number"] = caller_phone_number
        if call_for is not None:
            body["call_for"] = call_for
        if message is not None:
            body["message"] = message
        if call_type is not None:
            body["call_type"] = call_type
        if resolved is not None:
            body["resolved"] = resolved
        return self.put(f"/calls/{call_id}", body)

    def delete_call(self, call_id):
        return self.delete(f"/calls/{call_id}")

    # ── Folders ───────────────────────────────────────────────────────────────

    def list_folder_documents(self, folder_id, page_size=25):
        return self.get(f"/folders/{folder_id}/documents", {"page_size": page_size})

    def list_folder_subfolders(self, folder_id):
        return self.get(f"/folders/{folder_id}/subfolders")

    def create_case_subfolder(self, case_id, path):
        return self.post(f"/cases/{case_id}/subfolders", {"path": path})

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def list_webhook_subscriptions(self):
        return self.get("/webhooks/subscriptions")

    def create_webhook_subscription(self, model, url, actions):
        return self.post(
            "/webhooks/subscriptions", {"model": model, "url": url, "actions": actions}
        )

    def delete_webhook_subscription(self, subscription_id):
        return self.delete(f"/webhooks/subscriptions/{subscription_id}")
