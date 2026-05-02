#!/usr/bin/env python3
"""One-command OAuth setup for mycase-mcp.
Opens the browser, captures the callback, exchanges the code, saves tokens.
"""

import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests

REDIRECT_URI = "http://127.0.0.1:8766/callback"
AUTH_URL = "https://auth.mycase.com/oauth/authorize"
TOKEN_URL = "https://auth.mycase.com/oauth/token"
CONFIG_DIR = Path.home() / ".mycase-mcp"

_auth_code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorization complete. You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>No code received. Check MyCase app settings.</h2>")

    def log_message(self, *args):
        pass


def main():
    print("=== mycase-mcp OAuth Setup ===\n")

    client_id = input("MyCase Client ID: ").strip()
    client_secret = input("MyCase Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Client ID and Secret are required.")
        sys.exit(1)

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    print(f"\nOpening browser for MyCase authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("127.0.0.1", 8766), _CallbackHandler)
    print("Waiting for MyCase to redirect back (port 8766)...")
    server.handle_request()

    if not _auth_code:
        print("Error: Did not receive authorization code.")
        sys.exit(1)

    print("Exchanging code for tokens...")
    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": _auth_code,
        "redirect_uri": REDIRECT_URI,
    })

    if resp.status_code != 200:
        print(f"Token exchange failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    tokens = resp.json()

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    env_file = CONFIG_DIR / ".env"
    with open(env_file, "w") as f:
        f.write(f"MYCASE_CLIENT_ID={client_id}\n")
        f.write(f"MYCASE_CLIENT_SECRET={client_secret}\n")
    os.chmod(env_file, 0o600)

    token_file = CONFIG_DIR / "tokens.json"
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(token_file, 0o600)

    print(f"\n✓ Credentials saved to {env_file}")
    print(f"✓ Tokens saved to {token_file}")
    print("\nRun 'mycase-mcp-verify' to test the connection.")


if __name__ == "__main__":
    main()
