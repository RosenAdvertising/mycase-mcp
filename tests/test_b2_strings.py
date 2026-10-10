"""The mycase://security-notes resource text agrees with the README."""

from __future__ import annotations

import asyncio

from mcp import Client

from mycase_mcp import server


def _read_security_notes() -> str:
    async def read() -> str:
        async with Client(server.mcp, cache=None) as client:
            result = await client.read_resource("mycase://security-notes")
        return result.contents[0].text

    return asyncio.run(read())


def test_security_notes_name_the_oauth_credentials_the_server_reads() -> None:
    text = _read_security_notes()
    # client.py loads MYCASE_CLIENT_ID and MYCASE_CLIENT_SECRET; MYCASE_API_TOKEN is never read.
    assert "MYCASE_CLIENT_ID" in text
    assert "MYCASE_CLIENT_SECRET" in text
    assert "MYCASE_API_TOKEN" not in text
    assert "tokens.json" in text


def test_security_notes_state_the_credential_read_order_the_code_uses() -> None:
    text = _read_security_notes()
    # credentials.load_into_environ skips any key already set in the process environment,
    # then reads the keyring, then the .env file.
    assert "Read order: process environment, then the OS keyring" in text
    assert "then `~/.mycase-mcp/.env`" in text
    assert "Resolution order: process env → `~/.mycase-mcp/.env`" not in text
    assert "MYCASE_MCP_USE_KEYRING=0" in text
    assert "0600" in text


def test_security_notes_describe_the_http_mode_warning_and_settings() -> None:
    text = _read_security_notes()
    assert "stdio is the default" in text
    assert "MYCASE_MCP_TRANSPORT=streamable-http" in text
    assert "no authentication and no TLS" in text
    assert "127.0.0.1" in text
    assert "MYCASE_MCP_ALLOWED_HOSTS" in text
    assert "MYCASE_MCP_ALLOWED_ORIGINS" in text
    assert "not against direct callers" in text
    assert "MYCASE_ALLOWED_DESTINATION_HOSTS" in text


def test_security_notes_keep_the_tool_classification() -> None:
    text = _read_security_notes()
    assert "Read-only (safe)" in text
    assert "delete_case" in text
