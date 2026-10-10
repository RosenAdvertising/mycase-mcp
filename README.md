# MyCase MCP server

[![CI](https://github.com/RosenAdvertising/mycase-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/RosenAdvertising/mycase-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP 2026-07-28](https://img.shields.io/badge/MCP-2026--07--28-7C3AED.svg)](https://modelcontextprotocol.io)
[![PyPI version](https://img.shields.io/pypi/v/mycase-mcp.svg)](https://pypi.org/project/mycase-mcp/)

Connect Claude and other MCP clients to MyCase to manage cases, clients, tasks, billing and documents.

MyCase MCP server is a [Model Context Protocol](https://modelcontextprotocol.io) server for [MyCase](https://www.mycase.com/), the legal practice management platform. It registers 112 tools that read and write MyCase data. It runs over stdio by default, for desktop clients such as Claude Desktop, and offers an opt-in stateless Streamable HTTP mode that implements MCP specification 2026-07-28. MyCase credentials stay on the machine that runs the server: they come from the setup command and your operating system's keyring, or from environment variables, never from the client.

## Features

- **Cases**: list, read, create, update and delete cases, and attach clients, companies and staff.
- **Clients and companies**: list, read, create, update and delete clients and companies, with their notes.
- **Tasks and events**: create, update and delete tasks and calendar events, and assign staff.
- **Time and billing**: log time entries and expenses, list invoices and record invoice payments.
- **Documents and notes**: upload, read, update and delete documents and versions, browse case folders, and write case, client and company notes.
- **Leads and messaging**: list, read, create and update leads, manage referral sources, start message threads, post messages and log calls.
- **Firm setup**: manage custom fields, case stages, locations, people groups, practice areas and webhook subscriptions.

## Tools

The server registers 112 tools. They cover identity, cases, clients, companies, tasks, events, time entries, invoices and payments, expenses, notes, documents and folders, leads, calls, messaging, custom fields, case stages and roles, locations, referral sources, people groups, practice areas and webhooks. Tools that submit a URL accept only hosts approved in `MYCASE_ALLOWED_DESTINATION_HOSTS` (see [Webhook destination allowlist](#webhook-destination-allowlist)).

<details>
<summary>All 112 tools</summary>

- `add_client_to_case`
- `add_client_to_company`
- `add_company_to_case`
- `add_staff_to_case`
- `add_staff_to_event`
- `assign_task_to_staff`
- `create_call`
- `create_case`
- `create_case_message_thread`
- `create_case_note`
- `create_case_stage`
- `create_case_subfolder`
- `create_client`
- `create_client_note`
- `create_company`
- `create_company_note`
- `create_custom_field`
- `create_custom_field_option`
- `create_event`
- `create_expense`
- `create_lead`
- `create_location`
- `create_message_thread`
- `create_people_group`
- `create_practice_area`
- `create_referral_source`
- `create_task`
- `create_time_entry`
- `create_webhook_subscription`
- `delete_call`
- `delete_case`
- `delete_case_stage`
- `delete_client`
- `delete_company`
- `delete_custom_field`
- `delete_custom_field_option`
- `delete_document`
- `delete_document_version`
- `delete_event`
- `delete_expense`
- `delete_location`
- `delete_note`
- `delete_people_group`
- `delete_practice_area`
- `delete_task`
- `delete_time_entry`
- `delete_webhook_subscription`
- `get_case`
- `get_case_folder`
- `get_client`
- `get_company`
- `get_custom_field`
- `get_document`
- `get_document_data`
- `get_document_version_data`
- `get_expense`
- `get_firm`
- `get_lead`
- `get_note`
- `get_staff_member`
- `get_time_entry`
- `list_all_document_versions`
- `list_calls`
- `list_case_documents`
- `list_case_notes`
- `list_case_roles`
- `list_case_stages`
- `list_cases`
- `list_cases_for_client`
- `list_client_message_threads`
- `list_client_notes`
- `list_clients`
- `list_companies`
- `list_custom_field_options`
- `list_custom_fields`
- `list_document_versions`
- `list_documents`
- `list_events`
- `list_expenses`
- `list_folder_documents`
- `list_folder_subfolders`
- `list_invoice_payments`
- `list_invoices`
- `list_leads`
- `list_locations`
- `list_people_groups`
- `list_practice_areas`
- `list_referral_sources`
- `list_staff`
- `list_tasks`
- `list_time_entries`
- `list_webhook_subscriptions`
- `post_message`
- `record_invoice_payment`
- `update_call`
- `update_case`
- `update_case_stage`
- `update_client`
- `update_company`
- `update_custom_field_option`
- `update_document`
- `update_event`
- `update_lead`
- `update_location`
- `update_note`
- `update_people_group`
- `update_practice_area`
- `update_task`
- `upload_case_document`
- `upload_document`
- `upload_document_version`
- `who_am_i`

</details>

### Prompts and resources

The server also registers three prompts and three read-only resources.

| Prompt | What it does |
| --- | --- |
| `case_status_briefing` | Morning briefing of open cases, overdue tasks and pending invoices. |
| `intake_new_client` | Intake workflow for a new client: create the client record, the case and the first task. Takes a `case_description`. |
| `billing_cycle_review` | Review unbilled time and outstanding invoices for billing cycle close. |

| Resource | What it holds |
| --- | --- |
| `mycase://case_stages` | The case stages configured in your MyCase firm. |
| `mycase://practice_areas` | The practice areas configured in your MyCase firm. |
| `mycase://security-notes` | Security notes for this server, as Markdown. |

## Requirements

- Python 3.10 or later
- A MyCase developer app with an OAuth Client ID and Client Secret
- An MCP client such as Claude Desktop

## Installation

Install [uv](https://docs.astral.sh/uv/), then clone the repository and install its locked dependencies:

```bash
git clone https://github.com/RosenAdvertising/mycase-mcp.git
cd mycase-mcp
uv sync --locked
```

Releases are also published to PyPI: `pip install mycase-mcp` installs version 0.2.0, which predates the HTTP mode described below. Install from source to use HTTP mode.

## Configuration

Register `http://127.0.0.1:8766/callback` as a redirect URI in your MyCase developer app settings before you run setup. Authorization fails without it. If you do not have a MyCase developer app yet, contact MyCase support or your account manager to request API access.

Run the guided OAuth setup from your clone of the repository:

```bash
uv run --locked mycase-mcp-setup
```

Enter your Client ID and Client Secret when prompted. Your browser opens for MyCase authorization, and setup listens on port 8766 for the redirect. Setup saves the credentials to your operating system's keyring (or the file fallback described under [Credential storage](#credential-storage)) and the OAuth tokens to `~/.mycase-mcp/tokens.json`.

Verify the connection:

```bash
uv run --locked mycase-mcp-verify
```

Verify resolves your credentials through the configured secret store, including keyring-only installations, signs in to MyCase, and reads your profile and up to five cases.

The server reads these environment variables. A variable set in the process environment takes precedence over a stored value.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `MYCASE_CLIENT_ID` | Yes | Stored value from setup | MyCase OAuth client ID. |
| `MYCASE_CLIENT_SECRET` | Yes | Stored value from setup | MyCase OAuth client secret. |
| `MYCASE_MCP_USE_KEYRING` | No | `1` | Set to `0` (or `false`, `no`, `off`) to skip the OS keyring and use the `.env` file fallback. |
| `MYCASE_ALLOWED_DESTINATION_HOSTS` | Only for tools that submit a URL | unset | Comma-separated hostnames approved as webhook destinations (see [Webhook destination allowlist](#webhook-destination-allowlist)). |

## Usage with Claude Desktop

Add the server to Claude Desktop's configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "mycase": {
      "command": "uv",
      "args": ["run", "--locked", "--directory", "/absolute/path/to/mycase-mcp", "mycase-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/mycase-mcp` with the path of your clone. Restart Claude Desktop after saving. Any other stdio MCP client uses the same command and arguments.

## HTTP mode

Stdio is the default. Set `MYCASE_MCP_TRANSPORT=streamable-http` to serve the stateless Streamable HTTP transport from MCP specification 2026-07-28 at `/mcp`. Each request stands alone: no initialization handshake and no `Mcp-Session-Id`. Clients on earlier protocol versions are served on the same endpoint.

> **Security: this endpoint has no authentication and no TLS.** Anyone who can reach the port can run every tool, including write and delete tools, with this server's vendor credentials. Keep the default loopback bind (`127.0.0.1`), or put the server behind an authenticating TLS proxy on a private network. `MYCASE_MCP_ALLOWED_HOSTS` and `MYCASE_MCP_ALLOWED_ORIGINS` protect against browser DNS rebinding, not against direct callers. A proxy in front of it needs connection and idle timeouts: a legacy-style `GET /mcp` with `Accept: text/event-stream` holds a stream open until the client disconnects.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MYCASE_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http`. A set but empty value selects `stdio`. |
| `MYCASE_MCP_HOST` | `127.0.0.1` | Bind address. `127.0.0.1`, `localhost` and `::1` use the SDK's built-in Host and Origin checks; any other value requires `MYCASE_MCP_ALLOWED_HOSTS`. |
| `PORT` | `8080` | Port; must be an integer. |
| `MYCASE_MCP_ALLOWED_HOSTS` | unset | Comma-separated `Host` header values accepted on a non-loopback bind, such as `mcp.example.com:8080` or `mcp.example.com:*`. |
| `MYCASE_MCP_ALLOWED_ORIGINS` | unset | Comma-separated `Origin` values accepted on a non-loopback bind, such as `https://client.example.com`. Requests without an `Origin` header are accepted; with this unset on a non-loopback bind, a request that carries an `Origin` header is rejected. |

MyCase credentials come from the same configuration as stdio (see [Configuration](#configuration)), never from the request.

```bash
MYCASE_MCP_TRANSPORT=streamable-http PORT=8080 uv run --locked mycase-mcp
```

Point the MCP client at `http://127.0.0.1:8080/mcp`.

## Error handling

A failed tool call returns an MCP error result (`isError`) with a fixed message. The server never passes a MyCase response body, a request URL or a credential back to the client.

| Situation | What the tool returns |
| --- | --- |
| Setup missing or incomplete | "MyCase is not configured. Run mycase-mcp-setup to connect your account and configure the required OAuth credentials, then restart mycase-mcp." |
| HTTP 401 (after one automatic token refresh) | "The MyCase authorization expired or was rejected. Run mycase-mcp-setup to reauthorize the account." |
| HTTP 403 | "MyCase access denied: the connected account lacks permission for this action (or the authorization expired; re-run mycase-mcp-setup if so)." |
| HTTP 404 | "The requested MyCase record was not found (HTTP 404). Check the record ID." |
| HTTP 429 | "MyCase rate limit reached. Retry after N seconds." N comes from the `Retry-After` header, or is 10 when the header is missing or unusable. |
| Other HTTP error statuses | "MyCase API returned HTTP 500: request failed." The reason is one fixed phrase chosen from the error code in the MyCase response: request rejected, authorization rejected, record not found, access denied, rate limited, response was not valid JSON, or request failed for any other code. |
| Timeout on a read | "MyCase request timed out. Retry shortly." |
| Connection failure on a read | "Could not connect to MyCase. Check connectivity and retry." |
| Timeout or connection failure on a write | "MyCase POST request outcome is unknown. Check whether it completed before retrying." (the method is POST, PUT or DELETE as appropriate) |
| Invalid arguments | A message that names the argument and the shape it expects, such as "Invalid argument 'limit': expected integer between 1 and 200." or "Supply at least one update field." |
| Destination URL or document path refused | "Destination refused: configure MYCASE_ALLOWED_DESTINATION_HOSTS with trusted comma-separated exact hostnames or .example.com for a domain and its subdomains; the URL host must match." or "Invalid document path: use a safe relative MyCase folder/name ..." |
| Anything else | `Error executing tool <name>` with no detail. |

Every MyCase request has a 30-second timeout and redirects are not followed. On HTTP 401 the server refreshes the OAuth access token once and repeats the request. On HTTP 429 it waits for the `Retry-After` period and retries up to 3 times, as long as the waits together stay within 60 seconds; otherwise it returns the rate-limit message. Other failures are not retried.

Missing credentials do not stop the server from starting: each tool call reports them. At startup the server exits with a message and a non-zero status when `MYCASE_MCP_TRANSPORT` is neither `stdio` nor `streamable-http`, when `PORT` is not an integer, or when a non-loopback `MYCASE_MCP_HOST` is set without `MYCASE_MCP_ALLOWED_HOSTS`.

## Troubleshooting

**Setup prints "Did not receive authorization code"**
→ The redirect URI `http://127.0.0.1:8766/callback` is not registered in your MyCase app. Add it and run `uv run --locked mycase-mcp-setup` again.

**Setup prints "Token exchange failed (401)"**
→ Check your Client ID and Client Secret, then run setup again.

**Verify prints "Missing MyCase client credentials" or "Missing tokens"**
→ Run `uv run --locked mycase-mcp-setup` first. Tokens are saved to `~/.mycase-mcp/tokens.json`; the Client ID and Client Secret go to your operating system's keyring (see [Credential storage](#credential-storage)).

**Claude does not show the MyCase tools**
→ Restart Claude Desktop after editing `claude_desktop_config.json`, and check that the path in the configuration points at your clone.

**429 Too Many Requests**
→ The server retries automatically (up to 3 times, see [Error handling](#error-handling)). If it persists, wait a moment and retry.

## Credential storage

By default credentials are stored in your operating system's native secret store
via the cross-platform [`keyring`](https://github.com/jaraco/keyring) library:

| OS      | Backend                                  |
| ------- | ---------------------------------------- |
| macOS   | Keychain                                 |
| Windows | Credential Manager                       |
| Linux   | Secret Service (GNOME Keyring / KWallet) |

Keyring entries use the service name `mycase-mcp`.

**File fallback.** On a host with no keyring backend (e.g. a headless Linux box
without Secret Service), or if you set `MYCASE_MCP_USE_KEYRING=0`, credentials
fall back to a `~/.mycase-mcp/.env` file with `0600` permissions.

On Windows, the file is stored in the user's profile and protected by Windows'
default per-user access rules. On POSIX, files are created with `0600` permissions
and writes fail closed if private permissions cannot be established.

**Read order.** A credential already present in the server process environment takes precedence, including one set in your MCP client's configuration. Otherwise the server checks the OS keyring, then the `.env` file. If you change credentials after the server has loaded them, restart the MCP server to reload the new values.

OAuth tokens are stored separately at `~/.mycase-mcp/tokens.json` (mode 600) and
refreshed automatically on expiry.

## Document paths

`upload_document` and `upload_case_document` take a relative MyCase folder/name,
including the document name, such as `example_folder1/example_folder2/example_name`.
This is the example in both the [case document schema](https://mycaseapi.stoplight.io/docs/mycase-api-documentation/rh7lgmsrahr9d-document-request)
and [firm document schema](https://mycaseapi.stoplight.io/docs/mycase-api-documentation/zlvjohvugwzvt-document-request).
MyCase creates missing folders and returns a separate upload URL; see the
[document creation reference](https://mycaseapi.stoplight.io/docs/mycase-api-documentation/5f9d31af2e726-create-a-document-for-a-case).

Paths may contain ASCII letters, digits, spaces, `_`, `-`, `.`, parentheses and
`/` between segments, up to 1024 characters total and 255 per segment. All URLs
(including HTTPS and hostname/path forms), absolute paths, empty or dot segments,
leading/trailing segment spaces or dots, backslashes, percent encodings, Unicode
and control characters are refused before requests. A filename alone, such as
`report.pdf`, is valid.

## Webhook destination allowlist

Set `MYCASE_ALLOWED_DESTINATION_HOSTS` in the server process environment, for example
`MYCASE_ALLOWED_DESTINATION_HOSTS=hooks.example.com,.callbacks.example.com`.
Entries are exact hostnames; a leading dot permits that domain and its subdomains.
Matching ignores case and a trailing dot and uses IDNA normalization. Empty or
unset configuration refuses webhook registration before any request. This prevents
model-supplied URLs from sending firm data to arbitrary destinations, including
private-address hostname services and unlisted redirectors. Only administrators
can configure this setting; tools cannot change it. List only trusted hosts whose
DNS and redirect behavior you control. The existing HTTPS, userinfo, fragment,
port, local-name, non-global-IP and encoded/Unicode-host checks still apply.
Explicit destination keys in nested objects receive the same validation; unrelated
keys are not matched by substring. No DNS lookup or destination fetch is performed.

## Testing

The test suite runs offline and needs no MyCase account: MyCase API calls are replaced with test doubles. It covers the error messages tools return, argument validation, bounded list controls, path identifiers and document paths, the webhook destination allowlist, the OAuth setup callback and credential storage including private file permissions, logging that omits personal data, the setup and verify command help, MCP specification 2026-07-28 behavior, and the Streamable HTTP transport including Host and Origin checks and stateless requests.

```bash
uv sync --locked
uv run --locked pytest -q
```

CI runs the suite on every push and pull request to `main`.

## License

MIT. See [LICENSE](LICENSE).
