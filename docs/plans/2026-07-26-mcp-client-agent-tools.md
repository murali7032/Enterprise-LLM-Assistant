---
title: MCP client for agent tools
date: 2026-07-26
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

# MCP Client for Agent Tools

## Goal Capsule

**Objective:** Make this platform an MCP **client** that discovers tools from configured external MCP servers and exposes them through the existing agent tool path (`ToolRouter` → `AgentService`), without changing `ChatService` RAG/chat behavior.

**Authority:** Session-settled scope (user chose option 1: client → Agent/ToolRouter). Prefer existing Clean Architecture patterns over LangChain.

**Stop when:** Agents can list and call at least one remote MCP tool via `/api/v1/agents/run`, with config-driven enablement, tests, and docs. Do not build an MCP server that exposes this platform outward.

**Execution profile:** Feature-bearing, test-backed units; keep ChatService untouched.

---

## Product Contract

### Summary

External MCP servers (filesystem, GitHub, etc.) run as separate processes. This app connects to them, adapts their tools onto the existing `Tool` interface, and lets the agent planner/executor use them like local tools.

### Problem Frame

The platform already has RAG, LLM service, and in-process agent tools, but no way to consume the growing ecosystem of MCP servers. Wiring MCP into ChatService would mix retrieval Q&A with tool execution; the agent stack already owns tools.

### Requirements

#### Capability — MCP client

- R1. The platform acts as an MCP **client** only (v1); it does not expose itself as an MCP server.
- R2. Operators can configure one or more MCP servers (command/args/env for stdio; optional URL for HTTP later) via env/settings without code changes.
- R3. On startup (or first agent use), the client connects, initializes, and discovers remote tools.
- R4. Discovered tools are available to `AgentService` through `ToolRouter` with stable, collision-safe names.

#### Capability — Agent integration

- R5. `POST /api/v1/agents/run` can invoke MCP-backed tools the same way it invokes local tools (`weather`, `sql`, etc.).
- R6. Planner prompts include enough tool metadata (name + short description) for MCP tools to be selectable.
- R7. Tool argument mapping supports MCP JSON schemas: planner `input` may be a plain string (local tools) or a JSON object/string (MCP tools).

#### Capability — Safety and operability

- R8. If MCP is disabled or no servers are configured, agent behavior is unchanged (local tools only).
- R9. Connection or call failures surface as tool execution errors, not process crashes; failed servers do not block app boot for chat/RAG.
- R10. Secrets for MCP server env (tokens) come from process env / config, not hardcoded values.

### Actors

- A1. Platform operator — configures MCP servers in `.env` / deploy manifests.
- A2. Authenticated agent user — calls `/api/v1/agents/run` with a goal that may need remote tools.
- A3. External MCP server process — provides tools over stdio (v1).

### Flows

- F1. **Happy path:** App starts → MCP client connects configured stdio server → lists tools → registers adapters on `ToolRouter` → agent plans `action=<mcp_tool>` → executor calls tool → observation returned.
- F2. **Disabled path:** `MCP_ENABLED=false` or empty config → no MCP connections → local tools only.
- F3. **Partial failure:** One of N servers fails to start → log warning, register tools from healthy servers, continue.

### Acceptance Examples

- AE1. With a demo/filesystem MCP server configured, goal `"list files in the docs folder"` results in an agent step whose action is an MCP tool name and a non-empty observation.
- AE2. With MCP disabled, existing weather-agent tests still pass and `list_tools` contains only local tools.
- AE3. Chat `/api/v1/chat` behavior and code path remain unchanged (no MCP dependency injected into `ChatService`).

### Success Criteria

- Agents can use at least one external MCP tool end-to-end in local docker/dev.
- Zero changes required in `app/services/chat_service.py` for v1.
- Tests cover adapter mapping, router registration, and disabled/fallback behavior.

### Scope Boundaries

**In scope**
- MCP client (stdio transport first)
- Config + DI wiring into `ToolRouter` / `AgentService`
- Tool adapter + naming + JSON arg parsing
- Planner prompt enrichment for tool descriptions
- Docs (`.env.example`, short README section)
- Unit/integration tests with a fake or in-process MCP double

**Out of scope**
- Exposing this platform as an MCP server
- Wiring MCP into `ChatService`
- LangChain / LangGraph
- Full multi-tenant per-user MCP credentials UI
- Streaming HTTP/SSE MCP transport (defer; design config shape so it can be added)

### Dependencies

- Official Python MCP SDK (`mcp` package) — pin a **stable** release suitable for production; avoid unpinned v2 alpha unless team explicitly accepts churn.
- External MCP server binary/script available in the environment for manual/e2e verification (e.g. a small local demo server or `@modelcontextprotocol/server-filesystem`).

### Outstanding Questions

- Q1 (deferred): Which first production MCP server to document as the default example (filesystem vs GitHub vs custom)? Implementer may pick filesystem for local demos.
- Q2 (deferred): HTTP/SSE transport timing — after stdio v1 proves out.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **Client, not server** `(session-settled: user-directed — chosen over "also expose MCP server": v1 focuses on consuming external tools)`.
- KTD2. **Integrate at Agent/ToolRouter, not ChatService** `(session-settled: user-directed — chosen over ChatService wiring: tools already belong to the agent loop; ChatService stays RAG/LLM)`.
- KTD3. **Adapter pattern over new agent runtime** — wrap each MCP tool as `app.tools.base.Tool` so `Executor` / `ToolRouter` stay unchanged in control flow.
- KTD4. **Collision-safe names** — register as `{server_id}__{tool_name}` (double underscore) so multiple servers cannot clobber local tools or each other.
- KTD5. **Keep `Tool.execute(query: str)`** — for MCP tools, treat `query` as either a raw string mapped to a single primary arg **or** a JSON object string matching the tool’s input schema; document the convention in the adapter. Avoid a breaking interface change in v1; optional `input_schema` property may be added on `Tool` for planner prompts.
- KTD6. **Lazy-tolerant lifecycle** — discover/register during FastAPI lifespan startup when enabled; failures are non-fatal to the API process (chat/RAG still serve).
- KTD7. **No LangChain** — use official `mcp` SDK + thin wrappers, consistent with prior architecture stance in `docs/INTERVIEW_GUIDE.md`.

### High-Level Design

```
Configured MCP servers (env JSON)
        │
        ▼
McpClientManager (connect / list_tools / call_tool / aclose)
        │
        ▼
McpTool adapters (Tool interface)
        │
        ▼
ToolRouter (local tools + MCP tools)
        │
        ▼
Executor → AgentService → POST /api/v1/agents/run

ChatService ── unchanged ──► LLMService / RAG
```

**Config shape (directional, not final schema):**

```json
[
  {
    "id": "fs",
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    "env": {}
  }
]
```

Loaded from `MCP_SERVERS_JSON` (string) with `MCP_ENABLED` bool gate.

### Assumptions

- Agent planner already returns JSON `{thought, action, input}`; MCP tools reuse `action` = registered name and `input` = args payload.
- Local tools remain registered and take precedence only if names collide — naming scheme in KTD4 should prevent collisions with short local names.
- Operators can install Node/Python MCP server CLIs in the runtime environment when they enable MCP.

### Constraints

- Preserve Clean Architecture: routers thin, services/agents own orchestration, SDK confined to `app/mcp/` (or `app/clients/mcp_client.py` + `app/tools/mcp_tool.py`).
- Do not require MCP for CI unit tests — use fakes/mocks; optional marked e2e test if a server is present.
- App boot must succeed with MCP enabled but misconfigured (degraded tools).

### Sequencing

1. U1 — Config + client manager skeleton  
2. U2 — Tool adapter + ToolRouter registration  
3. U3 — Lifespan wiring + planner metadata  
4. U4 — Tests, docs, demo config  

### Research Inputs

- Existing tool path: `app/tools/base.py`, `app/agents/tool_router.py`, `app/agents/executor.py`, `app/agents/agent_service.py`, `app/dependencies.py` (`get_tool_router`)
- Planner prompt currently lists **names only** (`app/prompt/prompt_builder.py` `build_agent_prompt`) — needs description enrichment for MCP usefulness
- Official MCP Python client: `ClientSession` + `stdio_client` / `StdioServerParameters` ([MCP build-client docs](https://modelcontextprotocol.io/docs/develop/build-client.md))
- Prefer stable `mcp` SDK pin; note upstream v2 pre-release churn as of mid-2026

---

## Implementation Units

### U1. MCP settings and client manager

**Goal:** Load MCP config and provide connect / list_tools / call_tool / shutdown.

**Requirements:** R1, R2, R3, R8, R9, R10

**Files:**
- `app/core/config.py` (add `MCP_ENABLED`, `MCP_SERVERS_JSON`)
- `app/mcp/__init__.py` (new)
- `app/mcp/models.py` (new — pydantic server config)
- `app/mcp/client_manager.py` (new)
- `.env.example`
- `requirements.txt` (add pinned `mcp` + any required peer deps)
- `tests/test_mcp_client_manager.py` (new)

**Approach:**
- Parse `MCP_SERVERS_JSON` into a list of server configs (`id`, `transport`, `command`, `args`, `env`).
- `McpClientManager` owns sessions per server id; stdio only in v1.
- Methods: `async start()`, `list_remote_tools()`, `call_tool(server_id, tool_name, arguments)`, `async aclose()`.
- On per-server failure: log and skip that server.

**Test scenarios:**
- Disabled / empty JSON → manager starts with zero sessions.
- Invalid JSON → clear config error or empty+log (pick one; document; prefer fail-soft empty with warning).
- Fake session double → `list_remote_tools` returns expected names; `call_tool` forwards arguments.

**Verification:** `pytest tests/test_mcp_client_manager.py -q`

---

### U2. MCP Tool adapter and ToolRouter composition

**Goal:** Expose remote tools as `Tool` instances with safe names.

**Requirements:** R4, R5, R7

**Files:**
- `app/tools/mcp_tool.py` (new)
- `app/tools/base.py` (optional: add `description` already exists; optional `input_schema` property with default `None`)
- `app/dependencies.py` (compose local + MCP tools in `get_tool_router` or a builder used by lifespan)
- `tests/test_mcp_tool.py` (new)
- `tests/test_agents.py` (extend: MCP tool in router used by stub planner)

**Approach:**
- `McpTool(server_id, remote_name, description, manager, input_schema)` with `name` property `{server_id}__{remote_name}`.
- `execute(query)`: if query looks like JSON object, `json.loads` → arguments; else wrap as `{"query": query}` or map to first required string property when schema is trivial — document chosen rule in code comment + tests.
- Builder: `build_tools(manager) -> list[Tool]` merges Weather/SQL/K8s/Shell + MCP adapters.
- Keep `get_tool_router` rebuildable after discovery (may need to drop `@lru_cache` or cache a mutable holder refreshed at lifespan).

**Test scenarios:**
- Name formatting `{id}__{tool}`.
- JSON input parses to MCP `arguments` dict.
- Plain string input uses documented fallback mapping.
- Unknown tool still raises `ToolExecutionException`.
- Stub planner calling an MCP-named tool returns observation from fake manager.

**Verification:** `pytest tests/test_mcp_tool.py tests/test_agents.py -q`

---

### U3. Lifespan wiring and planner tool metadata

**Goal:** Start/stop MCP with the app; give the planner descriptions.

**Requirements:** R3, R5, R6, R9

**Files:**
- `app/main.py` (lifespan: start manager, rebuild tool router / agent deps, aclose on shutdown)
- `app/dependencies.py`
- `app/agents/tool_router.py` (optional `list_tool_specs()` → `[{name, description}]`)
- `app/agents/agent_service.py` / `app/agents/planner.py` / `app/prompt/prompt_builder.py` (pass descriptions into prompt)
- `tests/test_agent_prompt_tools.py` (new) or extend existing prompt tests

**Approach:**
- Use FastAPI lifespan context to `await manager.start()` when enabled.
- After discovery, replace/update the tool list used by `AgentService`.
- Update `build_agent_prompt` to include `name: description` lines (local tools already have `description`).
- Ensure chat routes do not import MCP manager.

**Test scenarios:**
- Prompt includes MCP tool description text when specs provided.
- Agent loop still finishes with local-only tools when MCP list empty.
- Shutdown calls manager `aclose` (unit test with mock).

**Verification:** `pytest tests/test_agent_prompt_tools.py tests/test_agents.py -q`

---

### U4. Docs and operator example

**Goal:** Operators know how to enable MCP and verify with agents.

**Requirements:** R2, R8, R10, AE1–AE3

**Files:**
- `README.md` (short MCP section under Features / Agents)
- `.env.example` (`MCP_ENABLED`, `MCP_SERVERS_JSON` sample)
- Optional: `docs/mcp.md` only if README would become too long — prefer README first

**Approach:**
- Document architecture (client → ToolRouter, not ChatService).
- Provide one copy-paste stdio example (filesystem or a tiny local demo).
- Note security: MCP tools inherit the privileges of the server process.

**Test scenarios:**
- Manual checklist in Definition of Done (no automated UI test required).

**Verification:** Doc review + dry-run config parse in unit tests from U1.

---

## Verification Contract

**Commands:**
- `pytest tests/test_mcp_client_manager.py tests/test_mcp_tool.py tests/test_agents.py -q`
- `pytest tests/test_agent_prompt_tools.py -q` (once added)
- Broader regression: `pytest -q` (or project’s usual CI subset)

**Quality gates:**
- ChatService files unchanged in the PR diff.
- No LangChain dependency added.
- MCP optional: default `MCP_ENABLED=false`.

**Manual smoke (local):**
1. Enable MCP with a demo server.
2. `POST /api/v1/agents/run` with a goal that requires the remote tool.
3. Confirm steps include `{server}__{tool}` action and useful observation.
4. Disable MCP; confirm chat and local agent tools still work.

---

## Definition of Done

**Global**
- [ ] R1–R10 satisfied or explicitly deferred with note
- [ ] U1–U4 complete with listed tests green
- [ ] ChatService untouched
- [ ] README + `.env.example` updated
- [ ] Manual smoke optional but recommended before merge

**Per unit**
- U1: manager start/list/call/close covered by fakes
- U2: adapter naming + arg mapping + router composition covered
- U3: lifespan + planner descriptions covered
- U4: operator docs present

---

## Appendix

### Architecture reminder (why not ChatService)

`ChatService` builds prompts with optional RAG context and calls `LLMService`. It has no tool loop. `AgentService` already runs plan → execute → observe. MCP tools are remote executors; they belong on that loop.

### Do you need an MCP server running?

Yes — **externally**. You configure and run (or let the client spawn via stdio) one or more MCP **server** processes. This app does not replace them; it **calls** them. When `MCP_ENABLED=false`, no server is needed.
