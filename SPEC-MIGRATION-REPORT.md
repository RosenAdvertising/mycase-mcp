# MCP 2026-07-28 migration report

## Result

`mycase-mcp` now targets MCP `2026-07-28`, up from `2025-11-25`. The direct
Python SDK dependency changed from `mcp>=1.28.1,<2` (locked to 1.28.1) to the
exact fleet migration release `mcp==2.0.0`. The refreshed lock includes the SDK
v2 dependency split, including `mcp-types==2.0.0`.

The authoritative repository-specific change classification and official
sources are in [`SPEC-DELTA-2026-07-28.md`](SPEC-DELTA-2026-07-28.md).

No deployment, live MyCase account, credential store, or remote Git repository
was touched. Nothing was pushed.

## Implementation

- Replaced v1 `FastMCP` with SDK v2 `MCPServer`, preserving the default stdio
  entry point, 112 tools, three resources, and three prompts.
- Added an explicit server version and retained SDK v2's dual-era support:
  modern clients negotiate `2026-07-28`, while legacy mode still negotiates
  `2025-11-25`.
- Kept downstream MyCase OAuth credentials, token persistence, synchronous API
  client behavior, resources, prompts, and existing write operations.
- Kept conservative SDK cache defaults (`ttlMs: 0`, `cacheScope: private`) and
  added no MCP session state, extension, MRTR feature, or custom notification
  bus.
- Added a protocol guard and raw-wire modern HTTP tests even though the shipped
  entry point remains stdio-only.
- Added an explicit core Ruff policy for the declared Python 3.10 floor.

## AFFECTS-US handling

| Change | Handling |
| --- | --- |
| Stateless modern protocol and removal of modern initialize | SDK v2 dual-era dispatcher; discovery/sessionless and modern/legacy client regressions. |
| Required `server/discover` | Exact version, identity, capabilities, cache fields, and result type asserted. |
| Required `resultType` | Complete results asserted for discovery, lists, resource reads, and a tool call. |
| HTTP routing headers | Raw requests carry `Mcp-Protocol-Version`, `Mcp-Method`, and `Mcp-Name`; method/name omission and mismatch return `-32020`. |
| Modern subscription/listen mapping | SDK-managed prompt/resource/tool declarations preserved without adding a publisher or custom bus. |
| Capability extensions | Discovery proves no unused extension is advertised. |
| Required cache hints | Private, zero-TTL hints asserted for every list/read category. |
| Deterministic tools | Two independent listings return the same 112 tool names. |
| JSON Schema 2020-12 | All generated schemas remain objects; every collection tool has schema-enforced bounds. |
| Resource not found | Unknown resource regression asserts Invalid Params `-32602`. |
| Reserved modern errors | Header mismatch `-32020`, unsupported version `-32022`, and unknown method `-32601` asserted. |

## Canary sibling checks

- **A — FIXED/CLEAN:** all 31 `list_*` tools now expose a `limit` constrained
  to 1–200. The client sends it as MyCase's documented `page_size` where that
  parameter exists and locally caps plain-list or enveloped responses, so a
  vendor over-delivery cannot exceed the requested total. There was no
  auto-pagination. The retained vendor OpenAPI history contains no collection
  `sort` or `order` query parameter, so no unsupported control was invented.
- **B — FIXED:** local OAuth callback rejections now emit a PII-free reason for
  unexpected path, missing code/state, or state mismatch. Existing CLI
  validation failures already emit a user-facing reason or raise a bounded
  error rather than silently denying an MCP request.
- **C — FIXED / PATTERN-N-A:** this repository serves only a loopback OAuth GET
  callback, not an origin-guarded browser form or a CSP-restricted cross-origin
  authorization handoff. Applying `Sec-Fetch-Site: same-origin` would reject the
  legitimate cross-site OAuth redirect. The applicable hardening was added:
  OAuth state binding plus `default-src 'none'`, `frame-ancestors 'none'`,
  `base-uri 'none'`, `form-action 'none'`, `no-referrer`, `nosniff`, and
  `no-store` response headers.
- **D — FIXED/CLEAN:** the verifier no longer prints the authenticated person's
  name; the secret prompt no longer echoes; the authorization URL is not
  printed; and API/OAuth error bodies are not copied into exceptions or setup
  output. A regression uses private name/email markers and proves they do not
  reach output. No `sub`, email, or person-name value reaches application log
  calls in the final sweep.

## Verification

Baseline, installed from the original lock:

- SDK 1.28.1, latest protocol `2025-11-25`.
- `pytest -q`: 0 tests collected (0/0, pytest exit 5).
- Ruff: 12 pre-existing findings.

Final, installed from the refreshed lock:

- `uv run --frozen pytest -q`: **19 passed**.
- `tests/test_spec_2026_07_28.py`: **9 passed**.
- List-control and security regressions: **10 passed**.
- `uv run --frozen python tests/spec_check.py`: **PASS (`2026-07-28`)**.
- `uv run --frozen ruff check .`: **all checks passed**.
- Package and test compilation: passed.
- Stdio entry point with EOF: started and exited successfully.

No live MyCase account test was performed because the migration requires no
credentials. Vendor request methods and parameters were verified offline; live
account behavior remains method-verified-only.

## Git sandbox and handoff

The runtime permits worktree writes but rejects this repository's `.git` writes
with `index.lock: Operation not permitted`. The required commits were created
on `spec-2026-07-28` in the authorized alternate Git database. A portable bundle
containing the complete branch history is exported to the fan-out scratchpad
and must be imported into a writable clone. The scratchpad handoff report
contains its exact path, verification result, and complete `git log --oneline`.
