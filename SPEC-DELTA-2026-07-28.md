# MCP specification delta: 2025-11-25 to 2026-07-28

Research date: 2026-08-09. Sources are limited to the official MCP
specification and the official MCP Python SDK documentation.

## Current target and migration release

The repository currently targets MCP `2025-11-25`:

- `pyproject.toml` declares `mcp>=1.28.1,<2`, and `uv.lock` resolves MCP Python
  SDK 1.28.1.
- An installed-from-lock baseline reports SDK `1.28.1` and
  `LATEST_PROTOCOL_VERSION == "2025-11-25"`.
- `mycase_mcp/server.py` constructs v1 `FastMCP` and calls `mcp.run()` without
  overriding protocol negotiation or the default stdio transport.
- The repository has no protocol-version guard or MCP conformance tests. Its
  only file under `tests/` is an OpenAPI merge utility and pytest collects no
  tests.

The official changelog says `2026-07-28` follows `2025-11-25`
([spec changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).
The official v1-to-v2 guide identifies the high-level server rename and the
other required SDK API changes
([SDK migration guide](https://py.sdk.modelcontextprotocol.io/migration/)).
The proven fleet migration release is MCP Python SDK `2.0.0`, which implements
the modern revision while retaining legacy negotiation.

Verdicts below mean:

- **AFFECTS-US**: this server exposes or relies on the changed surface. The SDK
  may implement the wire behavior, but the migration must still pin, configure,
  or test it.
- **NOT-APPLICABLE**: the feature or direction is not implemented here. It will
  not be added merely because the new revision permits it.

## Protocol negotiation and lifecycle

| Normative change | Verdict | Why |
| --- | --- | --- |
| Protocol-level sessions and `Mcp-Session-Id` are removed for the modern revision; cross-call state must use explicit handles. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | The stdio server must accept independent modern requests. Application state is already limited to downstream MyCase OAuth credentials and HTTP-client instances; it does not depend on an MCP session. |
| `initialize` / `notifications/initialized` are removed for modern requests. Every request carries protocol version and client capabilities in `_meta`, with client/server identity metadata recommended. Version mismatch uses `UnsupportedProtocolVersionError`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | SDK v2's dual-era dispatcher must serve self-describing modern stdio requests while retaining legacy negotiation. |
| Servers MUST implement `server/discover`, advertising supported protocol versions, capabilities, and identity. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | This is required of every modern server. Discovery must report `2026-07-28` and this server's actual tools, resources, and prompts capabilities. |
| All results require `resultType`: `"complete"` for ordinary results or `"input_required"` for MRTR. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | Tool, resource, prompt, discovery, and list results are returned by this server. SDK v2 must serialize them as complete. |
| Server-initiated requests are replaced by Multi Round-Trip Requests (MRTR), using `InputRequiredResult`, `inputRequests`, and retry `inputResponses`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | No tool, resource, or prompt uses sampling, roots, elicitation, or any other server-to-client request. MRTR will not be added as a feature. |
| `ping`, `logging/setLevel`, and `notifications/roots/list_changed` are removed; log opt-in is now per request. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | The application implements none of these methods and emits no MCP logging notifications. Its operational output is ordinary stderr/application output. |
| Experimental core tasks move to the `io.modelcontextprotocol/tasks` extension and change methods. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | The server has no MCP task handlers or task-augmented tools. The MyCase `list_tasks` business tool is unrelated to the MCP Tasks extension. |

## Transports and notifications

| Normative change | Verdict | Why |
| --- | --- | --- |
| Streamable HTTP POST requests require `Mcp-Method`, plus `Mcp-Name` for named operations; `x-mcp-header` can map selected tool parameters to custom headers. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | Production exposes stdio only and no tool parameter opts into `x-mcp-header`. The migration suite will still exercise SDK v2's raw HTTP adapter to prevent a future transport from silently bypassing the required routing headers. |
| HTTP GET and `resources/subscribe` / `resources/unsubscribe` are replaced by opt-in `subscriptions/listen`; request-scoped notifications remain on their request stream. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | The high-level server advertises SDK-managed prompt/resource/tool list-change and resource-subscription capabilities. SDK v2 maps those declarations to the modern transport; no custom publisher or event bus is added. |
| SSE resumability and redelivery (`Last-Event-ID` and SSE event IDs) are removed. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | This stdio-only server configures neither an event store nor an HTTP resumption mechanism. |
| HTTP+SSE is formally deprecated. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | The server exposes stdio only. |

## Capabilities and extensions

| Normative change | Verdict | Why |
| --- | --- | --- |
| `ClientCapabilities` and `ServerCapabilities` gain an `extensions` field. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | `server/discover` exposes this shape. Because the migration adds no extension, discovery must not advertise one. |
| Roots, Sampling, and Logging are deprecated. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | None is declared or used. |
| Sampling `includeContext` values `"thisServer"` and `"allServers"` are deprecated. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | Sampling is not used. |

## Tools, resources, prompts, and cache semantics

| Normative change | Verdict | Why |
| --- | --- | --- |
| `tools/list`, `prompts/list`, `resources/list`, `resources/templates/list`, and `resources/read` results require `ttlMs` and `cacheScope`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | The server exposes 112 tools, three resources, and three prompts. The migration keeps conservative SDK defaults (`ttlMs: 0`, `cacheScope: private`) and tests every applicable category. |
| Servers SHOULD return `tools/list` in deterministic order. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | Registration order is stable; repeated discovery must return the same 112 names. |
| Tool schemas accept all JSON Schema 2020-12 keywords and `structuredContent` may be any JSON value, with bounds for references and composition. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | Decorators generate schemas for all tools. SDK v2 owns the revised schema models; tests must prove generated object schemas and schema-enforced bounded list limits remain valid. |
| Resource-not-found changes from `-32002` to JSON-RPC Invalid Params `-32602`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | The server exposes three static resources, so an unknown URI must return `-32602`. |
| URL-mode elicitation loses its completion notification and `elicitationId`; retry correlation uses application `requestState`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | The server performs no elicitation. |
| Generated JSON Schema models numeric minimum, maximum, and default values as numbers rather than integers. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#other-schema-changes) | **NOT-APPLICABLE** | The repository neither vendors the MCP schema nor validates directly against that generated meta-schema. SDK v2 absorbs the correction. |

## Authorization and security

| Normative change | Verdict | Why |
| --- | --- | --- |
| Authorization servers SHOULD return RFC 9207 `iss`; MCP clients MUST validate a present issuer before code redemption. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | mycase-mcp is not an MCP authorization server and does not perform MCP client authorization-code redemption. Its separate downstream MyCase OAuth flow is outside MCP transport authorization. |
| MCP clients performing Dynamic Client Registration must send an appropriate `application_type`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | This code does not dynamically register an MCP client. |
| Persisted MCP client credentials must be keyed to their authorization-server issuer and never reused at another issuer. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | The repository stores only downstream MyCase application credentials and tokens; it stores no MCP client registrations. |
| Dynamic Client Registration is deprecated in favor of Client ID Metadata Documents. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | The server neither hosts DCR nor acts as a dynamically registered MCP client. |

## Errors, metadata, and observability

| Normative change | Verdict | Why |
| --- | --- | --- |
| MCP reserves `-32020..-32099`; HeaderMismatch, MissingRequiredClientCapability, and UnsupportedProtocolVersion are `-32020`, `-32021`, and `-32022`; unknown methods use `-32601`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | SDK v2 dispatch must produce the modern codes. Raw-wire tests will cover header mismatch, unsupported version, unknown method, and resource Invalid Params. No operation requires a new optional client capability, so `-32021` is not manufactured solely for a test. |
| `_meta` formally carries W3C `traceparent`, `tracestate`, and `baggage`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | The server has no MCP `_meta` tracing integration. SDK propagation does not require application code. |

The changelog's governance and SEP workflow changes impose no runtime or wire
requirement. The new lifecycle is respected by not adopting deprecated Roots,
Sampling, Logging, HTTP+SSE, or DCR
([governance/process changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog#governance-and-process-updates)).

## SDK v2 migration surfaces in this repository

The official SDK migration guide maps to this code as follows:

- Rename `FastMCP` to `MCPServer`; decorators and synchronous handlers remain.
- Give the server an explicit version instead of reporting the v2 empty default.
- Keep `mcp.run()` as the stdio entry point. No constructor transport options
  exist here to move, while raw-wire tests configure an HTTP app at call time.
- Rely on SDK v2 models (now supplied through `mcp-types`) for snake-case Python
  fields and unchanged camel-case wire fields. The application constructs no MCP
  result model directly.
- Synchronous tool/resource/prompt functions now execute on worker threads. The
  existing primitives are synchronous and require no semantic rewrite.
- No low-level server, v1 client helper, SDK OAuth, context, elicitation,
  sampling, roots, or logging API is used, so those migration-guide sections are
  not applicable.
