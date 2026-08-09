#!/usr/bin/env python3
"""CI-friendly guard for the MCP protocol revision targeted by this repo."""

from __future__ import annotations

from mcp.types import LATEST_PROTOCOL_VERSION
from mcp_types.version import MODERN_PROTOCOL_VERSIONS


EXPECTED_MCP_PROTOCOL_VERSION = "2026-07-28"


def main() -> int:
    errors: list[str] = []
    if LATEST_PROTOCOL_VERSION != EXPECTED_MCP_PROTOCOL_VERSION:
        errors.append(
            "installed SDK latest protocol is "
            f"{LATEST_PROTOCOL_VERSION!r}, expected "
            f"{EXPECTED_MCP_PROTOCOL_VERSION!r}"
        )
    if MODERN_PROTOCOL_VERSIONS != (EXPECTED_MCP_PROTOCOL_VERSION,):
        errors.append(
            f"modern protocol set is {MODERN_PROTOCOL_VERSIONS!r}, expected "
            f"({EXPECTED_MCP_PROTOCOL_VERSION!r},)"
        )

    if errors:
        for error in errors:
            print(f"Spec check: FAIL: {error}")
        return 1
    print(f"Spec check: PASS ({EXPECTED_MCP_PROTOCOL_VERSION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
