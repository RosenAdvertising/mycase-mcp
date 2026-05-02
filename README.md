# mycase-mcp

MCP server for [MyCase](https://www.mycase.com/) — gives Claude full access to your law firm's MyCase account.

**45+ tools. One setup command.**

## What It Does

- Read and manage cases, clients, contacts, and companies
- Create and update tasks, events, and calendar entries
- Log time entries and manage invoices
- Access case notes, documents, and folders
- Manage leads and lead intake
- Message thread access
- Reference data: case stages, roles, custom fields, locations

## Requirements

- Python 3.10+
- A MyCase developer app (contact MyCase for API access)
- Claude Desktop or any MCP-compatible client

## Installation

```bash
pip install mycase-mcp
```

## Setup

```bash
mycase-mcp-setup
```

This opens your browser for OAuth authorization and saves credentials to `~/.mycase-mcp/`.

## Verify

```bash
mycase-mcp-verify
```

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

## Tools

| Category | Tools |
|---|---|
| Identity | get_me, get_firm, list_staff, get_staff |
| Cases | list_cases, get_case, create_case, update_case, list_case_contacts, add_case_contact, remove_case_contact, list_case_events, list_case_tasks, list_case_notes |
| Clients | list_clients, get_client, create_client, update_client, list_client_cases, list_client_contacts, add_client_contact |
| Companies | list_companies, get_company, create_company, update_company, list_company_cases, list_company_contacts |
| Tasks | list_tasks, get_task, create_task, update_task, complete_task |
| Events | list_events, get_event, create_event, update_event, delete_event, list_case_events |
| Time Entries | list_time_entries, get_time_entry, create_time_entry, update_time_entry |
| Invoices | list_invoices, get_invoice, list_invoice_payments |
| Notes | list_notes, get_note, create_note, update_note, list_case_notes, list_client_notes, list_lead_notes |
| Documents | list_documents, get_document, list_case_documents, get_case_folder, list_folder_contents, get_folder, list_document_versions |
| Leads | list_leads, get_lead, create_lead, update_lead |
| Messaging | list_message_threads, get_message_thread, list_thread_messages |
| Reference | list_case_stages, list_case_roles, list_referral_sources, list_locations, list_people_groups, list_custom_fields |

## License

MIT
