#!/usr/bin/env python3
"""One-command OAuth setup for mycase-mcp.
Opens the browser, captures the callback, exchanges the code, saves tokens.

Credentials (Client ID, Client Secret) are stored securely via the OS keyring
(macOS Keychain / Windows Credential Manager / Linux Secret Service), falling
back to a 0600 ``.env`` file when no keyring backend is available or
``MYCASE_MCP_USE_KEYRING=0`` is set.
"""

import json
import hmac
import logging
import os
import secrets
import sys
import webbrowser
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from mycase_mcp import credentials

REDIRECT_URI = "http://127.0.0.1:8766/callback"
AUTH_URL = "https://auth.mycase.com/login_sessions/new"
TOKEN_URL = "https://auth.mycase.com/tokens"
CONFIG_DIR = Path.home() / ".mycase-mcp"

_auth_code: str | None = None
_oauth_state: str | None = None
logger = logging.getLogger(__name__)

_CALLBACK_CSP = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


class _CallbackHandler(BaseHTTPRequestHandler):
    def _send_page(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Security-Policy", _CALLBACK_CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global _auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        reason = ""
        if parsed.path != "/callback":
            reason = "unexpected_path"
        elif not params.get("code"):
            reason = "authorization_code_missing"
        elif not params.get("state") or _oauth_state is None:
            reason = "oauth_state_missing"
        elif not hmac.compare_digest(params["state"][0], _oauth_state):
            reason = "oauth_state_mismatch"

        if reason:
            logger.warning("OAuth callback rejected: %s", reason)
            self._send_page(
                400,
                b"<h2>Authorization could not be completed. Retry setup.</h2>",
            )
            return

        _auth_code = params["code"][0]
        self._send_page(
            200,
            b"<h2>Authorization complete. You can close this tab.</h2>",
        )

    def log_message(self, *args):
        pass


def main():
    global _auth_code, _oauth_state
    _auth_code = None
    _oauth_state = secrets.token_urlsafe(32)
    print("=== mycase-mcp OAuth Setup ===\n")

    client_id = input("MyCase Client ID: ").strip()
    client_secret = getpass("MyCase Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Client ID and Secret are required.")
        sys.exit(1)

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "state": _oauth_state,
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    print("\nOpening browser for MyCase authorization...")
    if not webbrowser.open(auth_url):
        logger.error("OAuth browser launch failed")
        print("Error: Could not open a browser. Retry setup from a desktop session.")
        sys.exit(1)

    server = HTTPServer(("127.0.0.1", 8766), _CallbackHandler)
    print("Waiting for MyCase to redirect back (port 8766)...")
    server.handle_request()
    server.server_close()

    if not _auth_code:
        print("Error: Did not receive authorization code.")
        sys.exit(1)

    print("Exchanging code for tokens...")
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": _auth_code,
            "redirect_uri": REDIRECT_URI,
        },
    )

    if resp.status_code != 200:
        print(f"Token exchange failed ({resp.status_code}).")
        sys.exit(1)

    tokens = resp.json()

    backend = credentials.set_secret("MYCASE_CLIENT_ID", client_id)
    credentials.set_secret("MYCASE_CLIENT_SECRET", client_secret)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    token_file = CONFIG_DIR / "tokens.json"
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(token_file, 0o600)

    if backend == "keyring":
        print(
            f"\n✓ Credentials saved to the OS keyring ({credentials.storage_backend()})."
        )
    else:
        print(f"\n✓ Credentials saved to {credentials.ENV_FILE} (0600).")
    print(f"✓ Tokens saved to {token_file}")
    print("\nRun 'mycase-mcp-verify' to test the connection.")


if __name__ == "__main__":
    main()
