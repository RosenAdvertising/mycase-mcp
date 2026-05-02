#!/usr/bin/env python3
"""MyCase API v1 client. Handles OAuth tokens, auto-refresh, and all API operations."""

import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

BASE_URL = "https://api.mycase.com/api/v1"
AUTH_URL = "https://auth.mycase.com/oauth/authorize"
TOKEN_URL = "https://auth.mycase.com/oauth/token"
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

    @property
    def access_token(self):
        return self.tokens.get("access_token", "")

    @property
    def refresh_token(self):
        return self.tokens.get("refresh_token", "")

    def refresh(self):
        if not self.refresh_token:
            raise RuntimeError("No refresh token. Run: mycase-mcp-setup")
        resp = requests.post(TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        })
        if resp.status_code == 200:
            new_tokens = resp.json()
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = self.refresh_token
            new_tokens["refreshed_at"] = datetime.now(timezone.utc).isoformat()
            self.save(new_tokens)
            return new_tokens
        raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text}")


class MyCaseClient:
    def __init__(self):
        self.tm = TokenManager()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.tm.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(self, method, path, params=None, json_body=None, retry=True):
        url = f"{BASE_URL}/{path.lstrip('/')}"
        resp = self.session.request(method, url, params=params, json=json_body)

        if resp.status_code == 401 and retry:
            self.tm.refresh()
            self.session.headers["Authorization"] = f"Bearer {self.tm.access_token}"
            return self._request(method, path, params=params, json_body=json_body, retry=False)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 10))
            print(f"Rate limited. Waiting {retry_after}s...", file=sys.stderr)
            time.sleep(retry_after)
            return self._request(method, path, params=params, json_body=json_body, retry=retry)

        if resp.status_code == 204:
            return {"success": True}

        if not resp.ok:
            raise RuntimeError(f"MyCase API error {resp.status_code}: {resp.text[:400]}")

        return resp.json()

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

    def list_staff(self, per_page=50):
        return self.get("/staff", {"per_page": per_page})

    def get_staff(self, staff_id):
        return self.get(f"/staff/{staff_id}")

    # ── Cases ─────────────────────────────────────────────────────────────────

    def list_cases(self, status=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if status:
            params["status"] = status
        return self.get("/cases", params)

    def get_case(self, case_id):
        return self.get(f"/cases/{case_id}")

    def create_case(self, name, description=None, status="open", case_stage_id=None):
        body = {"case": {"name": name, "status": status}}
        if description:
            body["case"]["description"] = description
        if case_stage_id:
            body["case"]["case_stage_id"] = case_stage_id
        return self.post("/cases", body)

    def update_case(self, case_id, **fields):
        return self.put(f"/cases/{case_id}", {"case": fields})

    def delete_case(self, case_id):
        return self.delete(f"/cases/{case_id}")

    def list_cases_for_client(self, client_id, per_page=25):
        return self.get(f"/clients/{client_id}/cases", {"per_page": per_page})

    def add_client_to_case(self, case_id, client_id, role=None):
        body = {"data": {"id": client_id}}
        if role:
            body["data"]["role"] = role
        return self.post(f"/cases/{case_id}/relationships/clients", body)

    def add_company_to_case(self, case_id, company_id, role=None):
        body = {"data": {"id": company_id}}
        if role:
            body["data"]["role"] = role
        return self.post(f"/cases/{case_id}/relationships/companies", body)

    def add_staff_to_case(self, case_id, staff_id, role=None):
        body = {"data": {"id": staff_id}}
        if role:
            body["data"]["role"] = role
        return self.post(f"/cases/{case_id}/relationships/staff", body)

    # ── Clients (People) ──────────────────────────────────────────────────────

    def list_clients(self, query=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if query:
            params["q"] = query
        return self.get("/clients", params)

    def get_client(self, client_id):
        return self.get(f"/clients/{client_id}")

    def create_client(self, first_name, last_name, email=None, phone=None):
        body = {"client": {"first_name": first_name, "last_name": last_name}}
        if email:
            body["client"]["email"] = email
        if phone:
            body["client"]["phone"] = phone
        return self.post("/clients", body)

    def update_client(self, client_id, **fields):
        return self.put(f"/clients/{client_id}", {"client": fields})

    def delete_client(self, client_id):
        return self.delete(f"/clients/{client_id}")

    # ── Companies ─────────────────────────────────────────────────────────────

    def list_companies(self, query=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if query:
            params["q"] = query
        return self.get("/companies", params)

    def get_company(self, company_id):
        return self.get(f"/companies/{company_id}")

    def create_company(self, name, email=None, phone=None, website=None):
        body = {"company": {"name": name}}
        if email:
            body["company"]["email"] = email
        if phone:
            body["company"]["phone"] = phone
        if website:
            body["company"]["website"] = website
        return self.post("/companies", body)

    def update_company(self, company_id, **fields):
        return self.put(f"/companies/{company_id}", {"company": fields})

    def delete_company(self, company_id):
        return self.delete(f"/companies/{company_id}")

    def add_client_to_company(self, company_id, client_id):
        return self.post(f"/companies/{company_id}/relationships/clients", {"data": {"id": client_id}})

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def list_tasks(self, case_id=None, assignee_id=None, status=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if case_id:
            params["case_id"] = case_id
        if assignee_id:
            params["assignee_id"] = assignee_id
        if status:
            params["status"] = status
        return self.get("/tasks", params)

    def create_task(self, name, case_id=None, due_date=None, description=None, priority=None):
        body = {"task": {"name": name}}
        if case_id:
            body["task"]["case_id"] = case_id
        if due_date:
            body["task"]["due_date"] = due_date
        if description:
            body["task"]["description"] = description
        if priority:
            body["task"]["priority"] = priority
        return self.post("/tasks", body)

    def update_task(self, task_id, **fields):
        return self.put(f"/tasks/{task_id}", {"task": fields})

    def delete_task(self, task_id):
        return self.delete(f"/tasks/{task_id}")

    def assign_task_to_staff(self, task_id, staff_id):
        return self.post(f"/tasks/{task_id}/relationships/staff", {"data": {"id": staff_id}})

    # ── Events / Calendar ─────────────────────────────────────────────────────

    def list_events(self, case_id=None, start_date=None, end_date=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if case_id:
            params["case_id"] = case_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self.get("/events", params)

    def create_event(self, name, start_at, end_at, case_id=None, location=None, description=None):
        body = {"event": {"name": name, "start_at": start_at, "end_at": end_at}}
        if case_id:
            body["event"]["case_id"] = case_id
        if location:
            body["event"]["location"] = location
        if description:
            body["event"]["description"] = description
        return self.post("/events", body)

    def update_event(self, event_id, **fields):
        return self.put(f"/events/{event_id}", {"event": fields})

    def delete_event(self, event_id):
        return self.delete(f"/events/{event_id}")

    def add_staff_to_event(self, event_id, staff_id):
        return self.post(f"/events/{event_id}/relationships/staff", {"data": {"id": staff_id}})

    # ── Time Entries ──────────────────────────────────────────────────────────

    def list_time_entries(self, case_id=None, staff_id=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if case_id:
            params["case_id"] = case_id
        if staff_id:
            params["staff_id"] = staff_id
        return self.get("/time_entries", params)

    def get_time_entry(self, entry_id):
        return self.get(f"/time_entries/{entry_id}")

    def create_time_entry(self, case_id, duration_in_seconds, note=None, date=None, rate=None):
        body = {"time_entry": {"case_id": case_id, "duration_in_seconds": duration_in_seconds}}
        if note:
            body["time_entry"]["note"] = note
        if date:
            body["time_entry"]["date"] = date
        if rate:
            body["time_entry"]["rate"] = rate
        return self.post("/time_entries", body)

    def delete_time_entry(self, entry_id):
        return self.delete(f"/time_entries/{entry_id}")

    # ── Invoices ──────────────────────────────────────────────────────────────

    def list_invoices(self, case_id=None, status=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if case_id:
            params["case_id"] = case_id
        if status:
            params["status"] = status
        return self.get("/invoices", params)

    def delete_invoice(self, invoice_id):
        return self.delete(f"/invoices/{invoice_id}")

    def record_invoice_payment(self, invoice_id, amount, date=None, note=None):
        body = {"payment": {"amount": amount}}
        if date:
            body["payment"]["date"] = date
        if note:
            body["payment"]["note"] = note
        return self.post(f"/invoices/{invoice_id}/payments", body)

    def list_invoice_payments(self, per_page=25, page=1):
        return self.get("/invoice_payments", {"per_page": per_page, "page": page})

    # ── Notes ─────────────────────────────────────────────────────────────────

    def get_note(self, note_id):
        return self.get(f"/notes/{note_id}")

    def update_note(self, note_id, body_text=None, subject=None):
        payload = {}
        if body_text:
            payload["body"] = body_text
        if subject:
            payload["subject"] = subject
        return self.put(f"/notes/{note_id}", {"note": payload})

    def delete_note(self, note_id):
        return self.delete(f"/notes/{note_id}")

    def list_case_notes(self, case_id, per_page=25):
        return self.get(f"/cases/{case_id}/notes", {"per_page": per_page})

    def create_case_note(self, case_id, body_text, subject=None):
        payload = {"note": {"body": body_text}}
        if subject:
            payload["note"]["subject"] = subject
        return self.post(f"/cases/{case_id}/notes", payload)

    def list_client_notes(self, client_id, per_page=25):
        return self.get(f"/clients/{client_id}/notes", {"per_page": per_page})

    def create_client_note(self, client_id, body_text, subject=None):
        payload = {"note": {"body": body_text}}
        if subject:
            payload["note"]["subject"] = subject
        return self.post(f"/clients/{client_id}/notes", payload)

    def create_company_note(self, company_id, body_text, subject=None):
        payload = {"note": {"body": body_text}}
        if subject:
            payload["note"]["subject"] = subject
        return self.post(f"/companies/{company_id}/notes", payload)

    # ── Documents ─────────────────────────────────────────────────────────────

    def list_documents(self, case_id=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if case_id:
            params["case_id"] = case_id
        return self.get("/documents", params)

    def get_document(self, doc_id):
        return self.get(f"/documents/{doc_id}")

    def update_document(self, doc_id, name=None, description=None):
        payload = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        return self.put(f"/documents/{doc_id}", {"document": payload})

    def delete_document(self, doc_id):
        return self.delete(f"/documents/{doc_id}")

    def list_document_versions(self, doc_id):
        return self.get(f"/documents/{doc_id}/versions")

    def list_case_documents(self, case_id, per_page=25):
        return self.get(f"/cases/{case_id}/documents", {"per_page": per_page})

    def get_case_folder(self, case_id):
        return self.get(f"/cases/{case_id}/folder")

    # ── Leads ─────────────────────────────────────────────────────────────────

    def list_leads(self, status=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if status:
            params["status"] = status
        return self.get("/leads", params)

    def get_lead(self, lead_id):
        return self.get(f"/leads/{lead_id}")

    def create_lead(self, first_name, last_name, email=None, phone=None, referral_source_id=None):
        body = {"lead": {"first_name": first_name, "last_name": last_name}}
        if email:
            body["lead"]["email"] = email
        if phone:
            body["lead"]["phone"] = phone
        if referral_source_id:
            body["lead"]["referral_source_id"] = referral_source_id
        return self.post("/leads", body)

    def update_lead(self, lead_id, **fields):
        return self.put(f"/leads/{lead_id}", {"lead": fields})

    # ── Message Threads ───────────────────────────────────────────────────────

    def create_message_thread(self, subject, participant_ids):
        body = {"message_thread": {"subject": subject, "participant_ids": participant_ids}}
        return self.post("/message_threads", body)

    def create_case_message_thread(self, case_id, subject, participant_ids):
        body = {"message_thread": {"subject": subject, "participant_ids": participant_ids}}
        return self.post(f"/cases/{case_id}/message_threads", body)

    def list_client_message_threads(self, client_id, per_page=25):
        return self.get(f"/clients/{client_id}/message_threads", {"per_page": per_page})

    def post_message(self, thread_id, body_text):
        return self.post(f"/message_threads/{thread_id}/messages", {"message": {"body": body_text}})

    # ── Reference Data ────────────────────────────────────────────────────────

    def list_case_stages(self, per_page=50):
        return self.get("/case_stages", {"per_page": per_page})

    def list_case_roles(self):
        return self.get("/case_roles")

    def list_referral_sources(self, per_page=50):
        return self.get("/referral_sources", {"per_page": per_page})

    def list_locations(self, per_page=50):
        return self.get("/locations", {"per_page": per_page})

    def list_people_groups(self, per_page=50):
        return self.get("/people_groups", {"per_page": per_page})

    def list_custom_fields(self, per_page=50):
        return self.get("/custom_fields", {"per_page": per_page})

    def create_custom_field(self, name, parent_type, field_type, list_options=None):
        body = {"custom_field": {"name": name, "parent_type": parent_type, "field_type": field_type}}
        if list_options:
            body["custom_field"]["list_options"] = list_options
        return self.post("/custom_fields", body)

    def get_custom_field(self, field_id):
        return self.get(f"/custom_fields/{field_id}")

    def delete_custom_field(self, field_id):
        return self.delete(f"/custom_fields/{field_id}")

    def list_custom_field_options(self, field_id):
        return self.get(f"/custom_fields/{field_id}/list_options")

    def create_custom_field_option(self, field_id, option_value):
        return self.post(f"/custom_fields/{field_id}/list_options", {"list_options": [option_value]})

    def update_custom_field_option(self, field_id, key, option_value):
        return self.put(f"/custom_fields/{field_id}/list_options/{key}", {"option_value": option_value})

    def delete_custom_field_option(self, field_id, key):
        return self.delete(f"/custom_fields/{field_id}/list_options/{key}")

    # ── Case Stages CRUD ──────────────────────────────────────────────────────

    def create_case_stage(self, name):
        return self.post("/case_stages", {"case_stage": {"name": name}})

    def update_case_stage(self, stage_id, name):
        return self.put(f"/case_stages/{stage_id}", {"case_stage": {"name": name}})

    def delete_case_stage(self, stage_id):
        return self.delete(f"/case_stages/{stage_id}")

    # ── Locations CRUD ────────────────────────────────────────────────────────

    def create_location(self, name, address1=None, city=None, state=None, zip_code=None, country=None):
        body = {"location": {"name": name}}
        if any([address1, city, state, zip_code, country]):
            body["location"]["address"] = {k: v for k, v in {
                "address1": address1, "city": city, "state": state,
                "zip_code": zip_code, "country": country
            }.items() if v}
        return self.post("/locations", body)

    def update_location(self, location_id, **fields):
        return self.put(f"/locations/{location_id}", {"location": fields})

    def delete_location(self, location_id):
        return self.delete(f"/locations/{location_id}")

    # ── People Groups CRUD ────────────────────────────────────────────────────

    def create_people_group(self, name):
        return self.post("/people_groups", {"people_group": {"name": name}})

    def update_people_group(self, group_id, name):
        return self.put(f"/people_groups/{group_id}", {"people_group": {"name": name}})

    def delete_people_group(self, group_id):
        return self.delete(f"/people_groups/{group_id}")

    # ── Practice Areas ────────────────────────────────────────────────────────

    def list_practice_areas(self, per_page=50):
        return self.get("/practice_areas", {"per_page": per_page})

    def create_practice_area(self, name):
        return self.post("/practice_areas", {"practice_area": {"name": name}})

    def update_practice_area(self, area_id, name):
        return self.put(f"/practice_areas/{area_id}", {"practice_area": {"name": name}})

    def delete_practice_area(self, area_id):
        return self.delete(f"/practice_areas/{area_id}")

    # ── Referral Sources CRUD ─────────────────────────────────────────────────

    def create_referral_source(self, name):
        return self.post("/referral_sources", {"referral_source": {"name": name}})

    # ── Expenses ──────────────────────────────────────────────────────────────

    def list_expenses(self, case_id=None, staff_id=None, per_page=25, page=1):
        params = {"per_page": per_page, "page": page}
        if case_id:
            params["filter[case_id]"] = case_id
        if staff_id:
            params["filter[staff_id]"] = staff_id
        return self.get("/expenses", params)

    def get_expense(self, expense_id):
        return self.get(f"/expenses/{expense_id}")

    def create_expense(self, activity_name, cost, units=1, case_id=None, staff_id=None,
                       description=None, billable=True, entry_date=None):
        body = {"expense": {"activity_name": activity_name, "cost": cost, "units": units, "billable": billable}}
        if case_id:
            body["expense"]["case"] = {"id": case_id}
        if staff_id:
            body["expense"]["staff"] = {"id": staff_id}
        if description:
            body["expense"]["description"] = description
        if entry_date:
            body["expense"]["entry_date"] = entry_date
        return self.post("/expenses", body)

    def delete_expense(self, expense_id):
        return self.delete(f"/expenses/{expense_id}")

    # ── Calls ─────────────────────────────────────────────────────────────────

    def list_calls(self, per_page=25, updated_after=None):
        params = {"per_page": per_page}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self.get("/calls", params)

    def create_call(self, called_at, caller_name=None, caller_phone_number=None,
                    call_for=None, message=None, client_id=None, lead_id=None,
                    call_type=None, resolved=None):
        body = {"call": {"called_at": called_at}}
        if caller_name:
            body["call"]["caller_name"] = caller_name
        if caller_phone_number:
            body["call"]["caller_phone_number"] = caller_phone_number
        if call_for:
            body["call"]["call_for"] = call_for
        if message:
            body["call"]["message"] = message
        if client_id:
            body["call"]["client"] = {"id": client_id}
        if lead_id:
            body["call"]["lead"] = {"id": lead_id}
        if call_type:
            body["call"]["call_type"] = call_type
        if resolved is not None:
            body["call"]["resolved"] = resolved
        return self.post("/calls", body)

    def update_call(self, call_id, **fields):
        return self.put(f"/calls/{call_id}", {"call": fields})

    def delete_call(self, call_id):
        return self.delete(f"/calls/{call_id}")

    # ── Folders ───────────────────────────────────────────────────────────────

    def list_folder_documents(self, folder_id, per_page=25):
        return self.get(f"/folders/{folder_id}/documents", {"per_page": per_page})

    def list_folder_subfolders(self, folder_id):
        return self.get(f"/folders/{folder_id}/subfolders")

    def create_case_subfolder(self, case_id, path):
        return self.post(f"/cases/{case_id}/subfolders", {"folder": {"path": path}})

    # ── Documents (upload + version management) ───────────────────────────────

    def upload_document(self, filename, path, description=None, assigned_date=None, staff_id=None):
        body = {"document": {"filename": filename, "path": path}}
        if description:
            body["document"]["description"] = description
        if assigned_date:
            body["document"]["assigned_date"] = assigned_date
        if staff_id:
            body["document"]["staff"] = {"id": staff_id}
        return self.post("/documents", body)

    def upload_case_document(self, case_id, filename, path, description=None, assigned_date=None):
        body = {"document": {"filename": filename, "path": path}}
        if description:
            body["document"]["description"] = description
        if assigned_date:
            body["document"]["assigned_date"] = assigned_date
        return self.post(f"/cases/{case_id}/documents", body)

    def list_all_document_versions(self):
        return self.get("/document_versions")

    def upload_document_version(self, doc_id, path, filename=None):
        body = {"document": {"path": path}}
        if filename:
            body["document"]["filename"] = filename
        return self.post(f"/documents/{doc_id}/versions", body)

    def get_document_data(self, doc_id):
        return self.get(f"/documents/{doc_id}/data")

    def get_document_version_data(self, doc_id, version_number):
        return self.get(f"/documents/{doc_id}/versions/{version_number}/data")

    def delete_document_version(self, doc_id, version_number):
        return self.delete(f"/documents/{doc_id}/versions/{version_number}")

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def list_webhook_subscriptions(self):
        return self.get("/webhooks/subscriptions")

    def create_webhook_subscription(self, model, url, actions):
        return self.post("/webhooks/subscriptions", {"webhook": {"model": model, "url": url, "actions": actions}})

    def delete_webhook_subscription(self, subscription_id):
        return self.delete(f"/webhooks/subscriptions/{subscription_id}")
