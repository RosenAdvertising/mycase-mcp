# mycase-mcp

MCP server for [MyCase](https://www.mycase.com/) — gives Claude full access to your law firm's MyCase account.

**112 tools. One setup command.**

## What It Does

- Read and manage cases, clients, contacts, and companies
- Create and update tasks, events, and calendar entries
- Log time entries, expenses, and manage invoices
- Access case notes, documents, folders, and custom fields
- Manage leads, lead intake, and referral sources
- Message thread access and call logging
- Webhooks, people groups, practice areas, and more

## Requirements

- Python 3.10+
- A MyCase developer app (see setup below)
- Claude Desktop or any MCP-compatible client

## Before You Start — Register the Redirect URI

The OAuth flow uses `http://127.0.0.1:8766/callback` as the redirect URI. **You must register this URI in your MyCase developer app settings before running setup.** Without it, authorization will fail.

If you don't have a MyCase developer app yet, contact MyCase support or your account manager to request API access.

## Installation

```bash
pip install mycase-mcp
```

## Setup (5 steps)

1. **Register redirect URI** in your MyCase app: `http://127.0.0.1:8766/callback`
2. **Run setup:**
   ```bash
   mycase-mcp-setup
   ```
   Enter your Client ID and Client Secret when prompted. Your browser will open for MyCase authorization.
3. **Verify:**
   ```bash
   mycase-mcp-verify
   ```
4. **Add to Claude Desktop config** (see below)
5. **Restart Claude Desktop**

## Claude Desktop Config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mycase": {
      "command": "mycase-mcp"
    }
  }
}
```

Restart Claude Desktop after saving the config.

## Troubleshooting

**"No code received" after authorizing in browser**
→ The redirect URI `http://127.0.0.1:8766/callback` is not registered in your MyCase app. Add it and try again.

**Token exchange failed (401)**
→ Double-check your Client ID and Client Secret. Re-run `mycase-mcp-setup`.

**"Missing credentials" on verify**
→ Run `mycase-mcp-setup` first. Credentials are saved to `~/.mycase-mcp/`.

**Claude doesn't see the mycase tools**
→ Make sure you restarted Claude Desktop after editing `claude_desktop_config.json`.

**429 Too Many Requests**
→ The server retries automatically (up to 3 times). If it persists, wait a moment and retry.

## Credentials Storage

- `~/.mycase-mcp/.env` — Client ID and Secret (mode 600)
- `~/.mycase-mcp/tokens.json` — Access/refresh tokens (mode 600)

Tokens are refreshed automatically on expiry.

## Tools

| Category | Tools |
|---|---|
| Identity | who_am_i, get_firm, list_staff, get_staff_member |
| Cases | list_cases, get_case, create_case, update_case, delete_case, list_cases_for_client, add_client_to_case, add_company_to_case, remove_client_from_case |
| Case Reference | list_case_stages, list_practice_areas, list_case_roles |
| Clients | list_clients, get_client, create_client, update_client |
| Companies | list_companies, get_company, create_company, update_company |
| Tasks | list_tasks, get_task, create_task, update_task |
| Events | list_events, get_event, create_event, update_event, delete_event |
| Time Entries | list_time_entries, get_time_entry, create_time_entry, update_time_entry, delete_time_entry |
| Expenses | list_expenses, get_expense, create_expense, update_expense, delete_expense |
| Invoices | list_invoices, get_invoice, create_invoice, update_invoice, delete_invoice, list_invoice_line_items, create_invoice_line_item, update_invoice_line_item, delete_invoice_line_item, record_invoice_payment, list_invoice_payments |
| Notes | list_notes, get_note, create_note, update_note, delete_note |
| Documents | list_documents, get_document, create_document, delete_document, list_document_versions, get_document_data, upload_document_version |
| Folders | list_folders, get_folder, create_folder, update_folder, delete_folder |
| Leads | list_leads, get_lead, create_lead, update_lead, delete_lead |
| Calls | list_calls, get_call, create_call, update_call, delete_call |
| Message Threads | list_message_threads, get_message_thread, create_message_thread, list_thread_messages, create_thread_message |
| Custom Fields | list_custom_fields, get_custom_field, create_custom_field, update_custom_field, delete_custom_field, list_custom_field_options, create_custom_field_option, delete_custom_field_option |
| Reference | list_locations, list_referral_sources, list_people_groups, get_people_group, create_people_group, update_people_group, delete_people_group, add_person_to_group, remove_person_from_group |
| Webhooks | list_webhooks, get_webhook, create_webhook, update_webhook, delete_webhook |

## License

MIT
