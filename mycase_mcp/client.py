#!/usr/bin/env python3
"""MyCase API v1 client. Handles OAuth tokens, auto-refresh, and all API operations."""

import json
import math
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote

import requests
from mcp.server.mcpserver.exceptions import ToolError

from mycase_mcp import credentials

BASE_URL = "https://external-integrations.mycase.com/v1"
AUTH_URL = "https://auth.mycase.com/login_sessions/new"
TOKEN_URL = "https://auth.mycase.com/tokens"
CONFIG_DIR = Path.home() / ".mycase-mcp"

# Resolve credentials through the pluggable store (OS keyring -> .env file).
credentials.load_into_environ(["MYCASE_CLIENT_ID", "MYCASE_CLIENT_SECRET"])

CLIENT_ID = os.environ.get("MYCASE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("MYCASE_CLIENT_SECRET", "")


def _path_id(value, parameter: str) -> str:
    """Validate a plain identifier before URL quoting or any HTTP request."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (str, int))
        or str(value) in {".", ".."}
        or re.fullmatch(r"[A-Za-z0-9._~-]+", str(value)) is None
    ):
        raise PathValidationError(parameter)
    return quote(str(value), safe="")


class MyCaseToolError(ToolError, RuntimeError):
    """An anticipated failure with a reviewed, client-safe message."""


class PathValidationError(MyCaseToolError):
    """Only the reviewed identifier form crosses the public error boundary."""

    def __init__(self, parameter: str):
        super().__init__(
            f"Invalid argument '{parameter}': use a non-empty plain identifier "
            "(ASCII letters, digits, -, _, ., ~); not . or .."
        )


class MissingCredentialsError(MyCaseToolError):
    def __init__(self, reason: str = ""):
        super().__init__(
            "MyCase is not configured. Run mycase-mcp-setup to connect your account "
            "and configure the required OAuth credentials, then restart mycase-mcp."
        )


class ReauthorizationRequiredError(MyCaseToolError):
    def __init__(self, reason: str = ""):
        super().__init__(
            "The MyCase authorization expired or was rejected. "
            "Run mycase-mcp-setup to reauthorize the account."
        )


class AccessDeniedError(MyCaseToolError):
    def __init__(self):
        super().__init__(
            "MyCase access denied: the connected account lacks permission for this action (or the authorization expired; re-run mycase-mcp-setup if so)."
        )


class TransportOutcomeUnknownError(MyCaseToolError):
    def __init__(self, method):
        super().__init__(
            f"MyCase {method} request outcome is unknown. Check whether it completed before retrying."
        )


_VENDOR_REASONS = {
    "invalid_request": "request rejected",
    "invalid_grant": "authorization rejected",
    "not_found": "record not found",
    "forbidden": "access denied",
    "rate_limited": "rate limited",
    "invalid_response": "response was not valid JSON",
}


class VendorHTTPError(MyCaseToolError):
    def __init__(self, status: int, code: str = ""):
        self.status = status
        self.code = code if isinstance(code, str) and code in _VENDOR_REASONS else ""
        reason = _VENDOR_REASONS.get(self.code, "request failed")
        if status == 403:
            message = "MyCase access denied: the connected account lacks permission for this action (or the authorization expired; re-run mycase-mcp-setup if so)."
        elif status == 404 or self.code == "not_found":
            message = (
                f"The requested MyCase record was not found (HTTP {status}). "
                "Check the record ID."
            )
        else:
            message = f"MyCase API returned HTTP {status}: {reason}."
        super().__init__(message)


class RateLimitedError(MyCaseToolError):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)
        super().__init__(
            f"MyCase rate limit reached. Retry after {self.retry_after} seconds."
        )


def _safe_retry_after(resp, default=10):
    try:
        value = Decimal(str(resp.headers.get("Retry-After", default)))
        if not value.is_finite() or value.adjusted() > 308:
            return default
        value = math.ceil(value)
    except (TypeError, ValueError, OverflowError, InvalidOperation):
        return default
    return max(1, value)


def _atomic_token_write(path, tokens):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tokens-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(tokens, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _vendor_code(resp):
    try:
        body = resp.json()
    except (ValueError, TypeError):
        return ""
    if isinstance(body, dict):
        error = body.get("error")
        candidates = [body.get("code"), error]
        if isinstance(error, dict):
            candidates.append(error.get("code"))
        for code in candidates:
            if isinstance(code, str) and code in _VENDOR_REASONS:
                return code
    return ""


def _retry_after_seconds(resp, default=10):
    return _safe_retry_after(resp, default)


def _json_response(resp):
    try:
        return resp.json()
    except ValueError:
        raise VendorHTTPError(resp.status_code, "invalid_response") from None


def _cap_list_response(payload, limit):
    """Return at most ``limit`` collection records without changing envelopes."""
    if isinstance(payload, list):
        return payload[:limit]
    if isinstance(payload, dict):
        capped = dict(payload)
        for key in ("data", "items", "list_options"):
            values = payload.get(key)
            if isinstance(values, list):
                capped[key] = values[:limit]
                break
        return capped
    return payload


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
        _atomic_token_write(self.token_file, tokens)

    @property
    def access_token(self):
        return self.tokens.get("access_token", "")

    @property
    def refresh_token(self):
        return self.tokens.get("refresh_token", "")

    def refresh(self):
        if not self.refresh_token:
            raise ReauthorizationRequiredError()
        if not CLIENT_ID or not CLIENT_SECRET:
            raise MissingCredentialsError("client_credentials")
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                allow_redirects=False,
                timeout=30,
            )
        except (requests.Timeout, requests.ConnectionError):
            raise TransportOutcomeUnknownError("POST token refresh") from None
        if resp.status_code == 200:
            new_tokens = _json_response(resp)
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = self.refresh_token
            new_tokens["refreshed_at"] = datetime.now(timezone.utc).isoformat()
            self.save(new_tokens)
            return new_tokens
        if resp.status_code in (400, 401):
            raise ReauthorizationRequiredError()
        if resp.status_code == 403:
            raise AccessDeniedError()
        if resp.status_code == 429:
            raise RateLimitedError(_safe_retry_after(resp))
        raise VendorHTTPError(resp.status_code, _vendor_code(resp))


class MyCaseClient:
    def __init__(self):
        self.tm = TokenManager()
        if not self.tm.access_token and not self.tm.refresh_token:
            raise MissingCredentialsError("oauth_tokens")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.tm.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self,
        method,
        path,
        params=None,
        json_body=None,
        retry=True,
        _rate_retries=0,
        _retry_sleep=0,
    ):
        url = f"{BASE_URL}/{path.lstrip('/')}"
        try:
            resp = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                allow_redirects=False,
                timeout=30,
            )
        except (requests.Timeout, requests.ConnectionError):
            if method.upper() != "GET":
                raise TransportOutcomeUnknownError(method.upper()) from None
            raise

        if resp.status_code == 401 and retry:
            self.tm.refresh()
            self.session.headers["Authorization"] = f"Bearer {self.tm.access_token}"
            return self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                retry=False,
                _rate_retries=_rate_retries,
                _retry_sleep=_retry_sleep,
            )

        if resp.status_code == 429 and _rate_retries < 3:
            retry_after = _retry_after_seconds(resp)
            if _retry_sleep + retry_after > 60:
                raise RateLimitedError(_safe_retry_after(resp))
            time.sleep(retry_after)
            return self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                retry=retry,
                _rate_retries=_rate_retries + 1,
                _retry_sleep=_retry_sleep + retry_after,
            )

        if resp.status_code == 429:
            raise RateLimitedError(_safe_retry_after(resp))

        if resp.status_code == 403:
            raise AccessDeniedError()
        if resp.status_code == 401:
            raise ReauthorizationRequiredError()

        # 202 Accepted = queued, no body (e.g. POST /calls)
        if resp.status_code == 202:
            return {"accepted": True}

        # 204 No Content
        if resp.status_code == 204:
            return {"success": True}

        if not 200 <= resp.status_code < 300:
            raise VendorHTTPError(resp.status_code, _vendor_code(resp))

        return _json_response(resp)

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None):
        return self._request("POST", path, json_body=body)

    def put(self, path, body=None):
        return self._request("PUT", path, json_body=body)

    def delete(self, path):
        return self._request("DELETE", path)

    def _list(self, path, page_size=25, params=None, *, send_page_size=True):
        """Fetch one MyCase collection page and enforce a total response cap."""
        query = dict(params or {})
        if send_page_size:
            query["page_size"] = page_size
        payload = self.get(path, query or None)
        return _cap_list_response(payload, page_size)

    # ── Identity ──────────────────────────────────────────────────────────────

    def get_me(self):
        return self.get("/me")

    def get_firm(self):
        return self.get("/firm")

    def list_staff(self, page_size=50):
        return self._list("/staff", page_size)

    def get_staff(self, staff_id):
        return self.get(f"/staff/{_path_id(staff_id, 'staff_id')}")

    # ── Cases ─────────────────────────────────────────────────────────────────

    def list_cases(self, status=None, page_size=25):
        params = {}
        if status:
            params["filter[status]"] = status
        return self._list("/cases", page_size, params)

    def get_case(self, case_id):
        return self.get(f"/cases/{_path_id(case_id, 'case_id')}")

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
        return self.put(f"/cases/{_path_id(case_id, 'case_id')}", fields)

    def delete_case(self, case_id):
        return self.delete(f"/cases/{_path_id(case_id, 'case_id')}")

    def list_cases_for_client(self, client_id, page_size=25):
        return self._list(
            f"/clients/{_path_id(client_id, 'client_id')}/cases", page_size
        )

    def add_client_to_case(self, case_id, client_id, role=None):
        entry = {"id": client_id}
        if role:
            entry["role"] = role
        return self.post(
            f"/cases/{_path_id(case_id, 'case_id')}/relationships/clients",
            {"clients": [entry]},
        )

    def add_company_to_case(self, case_id, company_id, role=None):
        entry = {"id": company_id}
        if role:
            entry["role"] = role
        return self.post(
            f"/cases/{_path_id(case_id, 'case_id')}/relationships/companies",
            {"companies": [entry]},
        )

    def add_staff_to_case(self, case_id, staff_id):
        return self.post(
            f"/cases/{_path_id(case_id, 'case_id')}/relationships/staff",
            {"staff": [{"id": staff_id}]},
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
        params = {}
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
        return self._list("/clients", page_size, params)

    def get_client(self, client_id):
        return self.get(f"/clients/{_path_id(client_id, 'client_id')}")

    def create_client(self, first_name, last_name, email=None, cell_phone_number=None):
        body = {"first_name": first_name, "last_name": last_name}
        if email:
            body["email"] = email
        if cell_phone_number:
            body["cell_phone_number"] = cell_phone_number
        return self.post("/clients", body)

    def update_client(self, client_id, **fields):
        return self.put(f"/clients/{_path_id(client_id, 'client_id')}", fields)

    def delete_client(self, client_id):
        return self.delete(f"/clients/{_path_id(client_id, 'client_id')}")

    # ── Companies ─────────────────────────────────────────────────────────────

    def list_companies(self, name=None, email=None, updated_after=None, page_size=25):
        params = {}
        if name:
            params["filter[name]"] = name
        if email:
            params["filter[email]"] = email
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self._list("/companies", page_size, params)

    def get_company(self, company_id):
        return self.get(f"/companies/{_path_id(company_id, 'company_id')}")

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
        return self.put(f"/companies/{_path_id(company_id, 'company_id')}", fields)

    def delete_company(self, company_id):
        return self.delete(f"/companies/{_path_id(company_id, 'company_id')}")

    def add_client_to_company(self, company_id, client_id):
        return self.post(
            f"/companies/{_path_id(company_id, 'company_id')}/relationships/clients",
            {"clients": [{"id": client_id}]},
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def list_tasks(self, updated_after=None, page_size=25):
        params = {}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self._list("/tasks", page_size, params)

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
        return self.put(f"/tasks/{_path_id(task_id, 'task_id')}", fields)

    def delete_task(self, task_id):
        return self.delete(f"/tasks/{_path_id(task_id, 'task_id')}")

    def assign_task_to_staff(self, task_id, staff_id):
        return self.post(
            f"/tasks/{_path_id(task_id, 'task_id')}/relationships/staff",
            {"staff": [{"id": staff_id}]},
        )

    # ── Events ────────────────────────────────────────────────────────────────

    def list_events(self, case_id=None, start_date=None, end_date=None, page_size=25):
        params = {}
        if case_id:
            params["filter[case_id]"] = case_id
        if start_date:
            params["filter[start_date]"] = start_date
        if end_date:
            params["filter[end_date]"] = end_date
        return self._list("/events", page_size, params)

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
        return self.put(f"/events/{_path_id(event_id, 'event_id')}", fields)

    def delete_event(self, event_id):
        return self.delete(f"/events/{_path_id(event_id, 'event_id')}")

    def add_staff_to_event(self, event_id, staff_id):
        return self.post(
            f"/events/{_path_id(event_id, 'event_id')}/relationships/staff",
            {"staff": [{"id": staff_id}]},
        )

    # ── Time Entries ──────────────────────────────────────────────────────────

    def list_time_entries(self, updated_after=None, page_size=25):
        params = {}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self._list("/time_entries", page_size, params)

    def get_time_entry(self, entry_id):
        return self.get(f"/time_entries/{_path_id(entry_id, 'entry_id')}")

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
        return self.delete(f"/time_entries/{_path_id(entry_id, 'entry_id')}")

    # ── Invoices ──────────────────────────────────────────────────────────────

    def list_invoices(self, case_id=None, status=None, page_size=25):
        params = {}
        if case_id:
            params["filter[case_id]"] = case_id
        if status:
            params["filter[status]"] = status
        return self._list("/invoices", page_size, params)

    def delete_invoice(self, invoice_id):
        return self.delete(f"/invoices/{_path_id(invoice_id, 'invoice_id')}")

    def record_invoice_payment(self, invoice_id, amount, date, notes=None):
        body = {"amount": amount, "date": date}
        if notes:
            body["notes"] = notes
        return self.post(
            f"/invoices/{_path_id(invoice_id, 'invoice_id')}/payments", body
        )

    def list_invoice_payments(self, page_size=25, status=None, payable_id=None):
        params = {}
        if status:
            params["filter[status]"] = status
        if payable_id:
            params["filter[payable_id]"] = payable_id
        return self._list("/invoice_payments", page_size, params)

    # ── Notes ─────────────────────────────────────────────────────────────────

    def get_note(self, note_id):
        return self.get(f"/notes/{_path_id(note_id, 'note_id')}")

    def update_note(self, note_id, note=None, subject=None, date=None):
        body = {}
        if note:
            body["note"] = note
        if subject:
            body["subject"] = subject
        if date:
            body["date"] = date
        return self.put(f"/notes/{_path_id(note_id, 'note_id')}", body)

    def delete_note(self, note_id):
        return self.delete(f"/notes/{_path_id(note_id, 'note_id')}")

    def list_case_notes(self, case_id, page_size=25):
        return self._list(f"/cases/{_path_id(case_id, 'case_id')}/notes", page_size)

    def create_case_note(self, case_id, note, subject, date):
        return self.post(
            f"/cases/{_path_id(case_id, 'case_id')}/notes",
            {"note": note, "subject": subject, "date": date},
        )

    def list_client_notes(self, client_id, page_size=25):
        return self._list(
            f"/clients/{_path_id(client_id, 'client_id')}/notes", page_size
        )

    def create_client_note(self, client_id, note, subject, date):
        return self.post(
            f"/clients/{_path_id(client_id, 'client_id')}/notes",
            {"note": note, "subject": subject, "date": date},
        )

    def create_company_note(self, company_id, note, subject, date):
        return self.post(
            f"/companies/{_path_id(company_id, 'company_id')}/notes",
            {"note": note, "subject": subject, "date": date},
        )

    # ── Documents ─────────────────────────────────────────────────────────────

    def list_documents(self, case_id=None, page_size=25):
        params = {}
        if case_id:
            params["filter[case_id]"] = case_id
        return self._list("/documents", page_size, params)

    def get_document(self, doc_id):
        return self.get(f"/documents/{_path_id(doc_id, 'doc_id')}")

    def update_document(self, doc_id, name=None, description=None):
        body = {}
        if name:
            body["filename"] = name
        if description:
            body["description"] = description
        return self.put(f"/documents/{_path_id(doc_id, 'doc_id')}", body)

    def delete_document(self, doc_id):
        return self.delete(f"/documents/{_path_id(doc_id, 'doc_id')}")

    def list_document_versions(self, doc_id, page_size=25):
        return self._list(
            f"/documents/{_path_id(doc_id, 'doc_id')}/versions",
            page_size,
            send_page_size=False,
        )

    def list_case_documents(self, case_id, page_size=25):
        return self._list(f"/cases/{_path_id(case_id, 'case_id')}/documents", page_size)

    def get_case_folder(self, case_id):
        return self.get(f"/cases/{_path_id(case_id, 'case_id')}/folder")

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
        return self.post(f"/cases/{_path_id(case_id, 'case_id')}/documents", body)

    def list_all_document_versions(self, page_size=25):
        return self._list("/document_versions", page_size)

    def upload_document_version(self, doc_id):
        return self.post(f"/documents/{_path_id(doc_id, 'doc_id')}/versions")

    def get_document_data(self, doc_id):
        return self.get(f"/documents/{_path_id(doc_id, 'doc_id')}/data")

    def get_document_version_data(self, doc_id, version_number):
        return self.get(
            f"/documents/{_path_id(doc_id, 'doc_id')}/versions/{_path_id(version_number, 'version_number')}/data"
        )

    def delete_document_version(self, doc_id, version_number):
        return self.delete(
            f"/documents/{_path_id(doc_id, 'doc_id')}/versions/{_path_id(version_number, 'version_number')}"
        )

    # ── Leads ─────────────────────────────────────────────────────────────────

    def list_leads(self, status=None, page_size=25):
        params = {}
        if status:
            params["filter[status]"] = status
        return self._list("/leads", page_size, params)

    def get_lead(self, lead_id):
        return self.get(f"/leads/{_path_id(lead_id, 'lead_id')}")

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
        return self.put(f"/leads/{_path_id(lead_id, 'lead_id')}", fields)

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
        return self.post(f"/cases/{_path_id(case_id, 'case_id')}/message_threads", body)

    def list_client_message_threads(self, client_id, page_size=25):
        return self._list(
            f"/clients/{_path_id(client_id, 'client_id')}/message_threads", page_size
        )

    def post_message(self, thread_id, body_text, sender_id=None):
        body = {"body": body_text}
        if sender_id:
            body["sender"] = {"id": sender_id}
        return self.post(
            f"/message_threads/{_path_id(thread_id, 'thread_id')}/messages", body
        )

    # ── Reference Data ────────────────────────────────────────────────────────

    def list_case_stages(self, page_size=50):
        return self._list("/case_stages", page_size)

    def create_case_stage(self, name):
        return self.post("/case_stages", {"name": name})

    def update_case_stage(self, stage_id, name):
        return self.put(
            f"/case_stages/{_path_id(stage_id, 'stage_id')}", {"name": name}
        )

    def delete_case_stage(self, stage_id):
        return self.delete(f"/case_stages/{_path_id(stage_id, 'stage_id')}")

    def list_case_roles(self, page_size=50):
        return self._list("/case_roles", page_size)

    def list_referral_sources(self, page_size=50):
        return self._list("/referral_sources", page_size)

    def create_referral_source(self, name):
        return self.post("/referral_sources", {"name": name})

    def list_locations(self, page_size=50):
        return self._list("/locations", page_size)

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
        return self.put(f"/locations/{_path_id(location_id, 'location_id')}", fields)

    def delete_location(self, location_id):
        return self.delete(f"/locations/{_path_id(location_id, 'location_id')}")

    def list_people_groups(self, page_size=50):
        return self._list("/people_groups", page_size)

    def create_people_group(self, name):
        return self.post("/people_groups", {"name": name})

    def update_people_group(self, group_id, name):
        return self.put(
            f"/people_groups/{_path_id(group_id, 'group_id')}", {"name": name}
        )

    def delete_people_group(self, group_id):
        return self.delete(f"/people_groups/{_path_id(group_id, 'group_id')}")

    def list_practice_areas(self, page_size=50):
        return self._list("/practice_areas", page_size)

    def create_practice_area(self, name):
        return self.post("/practice_areas", {"name": name})

    def update_practice_area(self, area_id, name):
        return self.put(
            f"/practice_areas/{_path_id(area_id, 'area_id')}", {"name": name}
        )

    def delete_practice_area(self, area_id):
        return self.delete(f"/practice_areas/{_path_id(area_id, 'area_id')}")

    def list_custom_fields(self, page_size=50):
        return self._list("/custom_fields", page_size)

    def create_custom_field(self, name, parent_type, field_type, list_options=None):
        body = {"name": name, "parent_type": parent_type, "field_type": field_type}
        if list_options:
            body["list_options"] = [{"option_value": v} for v in list_options]
        return self.post("/custom_fields", body)

    def get_custom_field(self, field_id):
        return self.get(f"/custom_fields/{_path_id(field_id, 'field_id')}")

    def delete_custom_field(self, field_id):
        return self.delete(f"/custom_fields/{_path_id(field_id, 'field_id')}")

    def list_custom_field_options(self, field_id, page_size=25):
        return self._list(
            f"/custom_fields/{_path_id(field_id, 'field_id')}/list_options",
            page_size,
            send_page_size=False,
        )

    def create_custom_field_option(self, field_id, option_value):
        return self.post(
            f"/custom_fields/{_path_id(field_id, 'field_id')}/list_options",
            {"list_options": [{"option_value": option_value}]},
        )

    def update_custom_field_option(self, field_id, key, option_value):
        return self.put(
            f"/custom_fields/{_path_id(field_id, 'field_id')}/list_options/{_path_id(key, 'key')}",
            {"option_value": option_value},
        )

    def delete_custom_field_option(self, field_id, key):
        return self.delete(
            f"/custom_fields/{_path_id(field_id, 'field_id')}/list_options/{_path_id(key, 'key')}"
        )

    # ── Expenses ──────────────────────────────────────────────────────────────

    def list_expenses(self, updated_after=None, page_size=25):
        params = {}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self._list("/expenses", page_size, params)

    def get_expense(self, expense_id):
        return self.get(f"/expenses/{_path_id(expense_id, 'expense_id')}")

    def create_expense(
        self,
        activity_name,
        cost,
        units: float = 1,
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
        return self.delete(f"/expenses/{_path_id(expense_id, 'expense_id')}")

    # ── Calls ─────────────────────────────────────────────────────────────────

    def list_calls(self, page_size=25, updated_after=None):
        params = {}
        if updated_after:
            params["filter[updated_after]"] = updated_after
        return self._list("/calls", page_size, params)

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
        return self.put(f"/calls/{_path_id(call_id, 'call_id')}", body)

    def delete_call(self, call_id):
        return self.delete(f"/calls/{_path_id(call_id, 'call_id')}")

    # ── Folders ───────────────────────────────────────────────────────────────

    def list_folder_documents(self, folder_id, page_size=25):
        return self._list(
            f"/folders/{_path_id(folder_id, 'folder_id')}/documents", page_size
        )

    def list_folder_subfolders(self, folder_id, page_size=25):
        return self._list(
            f"/folders/{_path_id(folder_id, 'folder_id')}/subfolders", page_size
        )

    def create_case_subfolder(self, case_id, path):
        return self.post(
            f"/cases/{_path_id(case_id, 'case_id')}/subfolders", {"path": path}
        )

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def list_webhook_subscriptions(self, page_size=25):
        return self._list(
            "/webhooks/subscriptions",
            page_size,
            send_page_size=False,
        )

    def create_webhook_subscription(self, model, url, actions):
        return self.post(
            "/webhooks/subscriptions", {"model": model, "url": url, "actions": actions}
        )

    def delete_webhook_subscription(self, subscription_id):
        return self.delete(
            f"/webhooks/subscriptions/{_path_id(subscription_id, 'subscription_id')}"
        )
