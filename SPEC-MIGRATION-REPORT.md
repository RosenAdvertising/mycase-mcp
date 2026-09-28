# MCP 2026-07-28 migration

This server targets MCP protocol revision `2026-07-28`. Its Python requirement
is `mcp>=2.2,<3`; `uv.lock` resolves both `mcp` and its companion `mcp-types`
to `2.2.0`. The protocol change classification and source links are in
[SPEC-DELTA-2026-07-28.md](SPEC-DELTA-2026-07-28.md).

## Server and protocol behavior

- The server uses SDK `MCPServer` with version `0.1.0`. Its shipped entry point
  runs over stdio. It declares 112 tools, three resources, and three prompts.
- SDK discovery and modern requests support `2026-07-28`; legacy client mode
  can still negotiate `2025-11-25`.
- Modern discovery, list, read, and tool results use `resultType: complete`.
  Cacheable list and read results retain private, zero-TTL SDK defaults.
- The test suite exercises modern HTTP routing in process, including required
  protocol, method, and name headers, unsupported versions, missing resources,
  and unknown methods. The product does not configure an HTTP entry point.
- Collection tools expose a bounded `limit` (1–200). The client forwards it as
  `page_size` where supported and caps returned collections locally. It does
  not add automatic pagination or an unsupported sort control.
- The local OAuth callback checks state and sends restrictive response headers.
  Setup and verification avoid printing secrets or authenticated person details.

## Reproduce local checks

Use the repository's locked virtual environment and fake credentials. Disable
keyring lookup so these checks do not consult a user's credential store. The
suite uses stubbed vendor clients, an in-process MCP HTTP transport, and a
loopback OAuth callback.

```bash
MYCASE_CLIENT_ID=offline-test MYCASE_CLIENT_SECRET=offline-test MYCASE_MCP_USE_KEYRING=0 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests
.venv/bin/ruff check mycase_mcp/__init__.py mycase_mcp/client.py mycase_mcp/server.py mycase_mcp/setup/oauth_flow.py mycase_mcp/setup/verify.py tests/spec_check.py tests/test_list_tool_controls.py tests/test_security_regressions.py tests/test_spec_2026_07_28.py
MYCASE_CLIENT_ID=offline-test MYCASE_CLIENT_SECRET=offline-test MYCASE_MCP_USE_KEYRING=0 .venv/bin/python tests/spec_check.py
uv lock --check --offline
```

These checks cover local SDK and protocol behavior. Live MyCase OAuth and API
responses, deployed transports, and other Python/platform combinations are
outside their scope. One header helper assertion checks the helper's own
output; separate HTTP request tests exercise server routing errors.

## Open product decision

MCP 2.2.0 masks messages from tool exceptions other than `ToolError` or
`ResourceError`, so clients receive a generic tool failure for those cases.
Retaining the masking limits information leakage; explicitly safe `ToolError`
messages could give clients more actionable feedback. Toby should decide the
policy. Existing tool exception handling remains unchanged.
