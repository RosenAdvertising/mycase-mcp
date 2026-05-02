#!/usr/bin/env python3
"""Post-setup smoke test — verifies auth and basic API access."""

import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".mycase-mcp"


def check_config():
    env_file = CONFIG_DIR / ".env"
    token_file = CONFIG_DIR / "tokens.json"

    if not env_file.exists():
        print(f"✗ Missing credentials: {env_file}")
        print("  Run: mycase-mcp-setup")
        return False

    if not token_file.exists():
        print(f"✗ Missing tokens: {token_file}")
        print("  Run: mycase-mcp-setup")
        return False

    print(f"✓ Config found: {CONFIG_DIR}")
    return True


def check_api():
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from mycase_mcp.client import MyCaseClient

        client = MyCaseClient()
        me = client.get_me()
        name = me.get("full_name") or me.get("name") or "unknown"
        print(f"✓ Authenticated as: {name}")

        cases = client.list_cases(page_size=5)
        count = len(cases) if isinstance(cases, list) else len(cases.get("data", []))
        print(f"✓ Cases accessible: {count} returned (limit 5)")

        return True
    except Exception as e:
        print(f"✗ API check failed: {e}")
        return False


def main():
    print("=== mycase-mcp Verification ===\n")
    ok = check_config() and check_api()
    if ok:
        print("\n✓ All checks passed. mycase-mcp is ready.")
    else:
        print("\n✗ Setup incomplete. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
