# AI Coding Agent Reference — okta-mcp-server

This is the primary reference for AI coding assistants working in this repository.
Read this before making any changes.

---

## Project Overview

An MCP (Model Context Protocol) server that exposes Okta's Admin Management APIs to LLMs like Claude.
Enables AI agents to manage Okta organizations through natural language — users, groups, applications,
policies, device assurance, brands/themes, and system logs.

- **Version:** 1.1.0
- **Python:** ≥ 3.13
- **Package manager:** uv
- **MCP framework:** FastMCP (`mcp[cli]>=1.26.0`)
- **Okta SDK:** `okta==3.4.1`
- **License:** Apache 2.0 (forked from https://github.com/okta/okta-mcp-server)

---

## Repository Structure

```
okta-mcp-server/
├── src/okta_mcp_server/           # Upstream source — do not modify directly (see Customization System)
│   ├── __init__.py                # Entry point: calls server.main()
│   ├── server.py                  # FastMCP instance, lifespan/auth flow, get_scope_status tool
│   ├── tools/
│   │   ├── applications/          # App CRUD + activate/deactivate
│   │   ├── customization/
│   │   │   ├── brands/            # Brand management
│   │   │   ├── custom_domains/    # Custom domain management
│   │   │   ├── custom_pages/      # Sign-in/error page customization
│   │   │   ├── custom_templates/  # Email template customization
│   │   │   ├── email_domains/     # Email domain management
│   │   │   └── themes/            # Theme management
│   │   ├── device_assurance/      # Device assurance policy CRUD
│   │   ├── groups/                # Group CRUD + membership
│   │   ├── policies/              # Policy + policy rule CRUD
│   │   ├── system_logs/           # System log query + login failure analysis
│   │   └── users/                 # User CRUD + CSV export
│   └── utils/
│       ├── auth/auth_manager.py   # OktaAuthManager: Device Auth Grant + Private Key JWT
│       ├── client.py              # get_okta_client() factory
│       ├── elicitation.py         # MCP elicitation for destructive ops
│       ├── messages.py            # Elicitation message templates
│       ├── pagination.py          # Pagination helpers (handles Okta SDK v2/v3 response formats)
│       ├── scope_guard.py         # @require_scopes decorator + prune_tools_by_scope()
│       ├── scope_registry.py      # TOOL_SCOPE_REGISTRY — single source of truth: tool → scope
│       ├── scope_stubs.py         # Stub tools shown when a scope is missing
│       └── validation.py          # @validate_ids, @validate_os_version_params decorators
├── customizations/                # All local changes live here — never in src/
│   ├── manifest.yaml              # Inventory of every customization (machine + human readable)
│   ├── tools/                     # New tool modules (add_tool entries)
│   └── overrides/                 # Replacement tool modules (override_tool entries)
├── tests/
│   ├── conftest.py                # Shared fixtures: FakeOktaAuthManager, elicitation contexts
│   ├── elicitation/               # Elicitation flow tests per domain
│   └── test_*.py                  # Feature tests
├── custom_server.py               # Custom entry point — use instead of okta-mcp-server
├── UPSTREAM.md                    # Upstream repo URL, last-synced tag, sync process
├── pyproject.toml                 # Project metadata + dependencies
├── Dockerfile / docker-compose.yml
└── .ruff.toml                     # Ruff linter configuration
```

---

## How to Run

### Local (development)

```bash
uv sync                          # install dependencies

# Upstream server (no customizations applied)
uv run okta-mcp-server

# Custom server (reads customizations/manifest.yaml and applies all entries)
uv run python custom_server.py
```

**Always use `custom_server.py` in this fork.**

### Docker

```bash
cp .env.example .env
# Edit .env with your Okta credentials
docker-compose up -d
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OKTA_ORG_URL` | Yes | Okta org URL, e.g. `https://mycompany.okta.com` |
| `OKTA_CLIENT_ID` | Yes | Client ID of the Okta API Services application |
| `OKTA_SCOPES` | Yes | Space-separated OAuth 2.0 scopes, e.g. `okta.users.read okta.groups.manage` |
| `OKTA_PRIVATE_KEY` | JWT only | PEM private key with newlines as `\n` |
| `OKTA_KEY_ID` | JWT only | Key ID for the private key |
| `OKTA_LOG_FILE` | No | Path for structured JSON log output |
| `OKTA_LOG_LEVEL` | No | Log level (default: `INFO`) |

### Authentication Modes

**Device Authorization Grant** (default — interactive browser):
Set `OKTA_ORG_URL`, `OKTA_CLIENT_ID`, `OKTA_SCOPES`. On first run a browser tab opens for login.
Token is stored in the system keyring and refreshed automatically.

**Private Key JWT** (headless/Docker):
Set all of the above plus `OKTA_PRIVATE_KEY` and `OKTA_KEY_ID`. No browser interaction required.
In Docker, `PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring` is set for file-based storage.

---

## Architecture

### Entry Points

| How to invoke | File | Notes |
|---------------|------|-------|
| `uv run okta-mcp-server` | `src/okta_mcp_server/__init__.py` → `server.main()` | Upstream only, no customizations |
| `uv run python custom_server.py` | `custom_server.py` | Applies manifest customizations |

### Request Lifecycle

1. `custom_server.py:main()` sets up logging, reads `customizations/manifest.yaml`, imports all upstream tool modules
2. Customizations are applied: overrides are removed and re-registered; removals are dropped; additions are imported
3. `mcp.run()` starts the FastMCP server
4. On the first MCP connection, the lifespan (`okta_authorisation_flow` in `server.py`) fires:
   - `OktaAuthManager.authenticate()` runs the configured auth flow
   - `prune_tools_by_scope()` removes any tool whose required scope is absent from the token
5. Each tool call: `@require_scopes` checks the token → tool body executes → Okta SDK API call

### Core Objects

**`mcp`** — FastMCP singleton defined at module level in `server.py`. All tool modules (upstream and custom) import it from there:
```python
from okta_mcp_server.server import mcp
```

**`OktaAppContext`** — dataclass holding the auth manager; injected via the lifespan. Access it inside a tool:
```python
manager = ctx.request_context.lifespan_context.okta_auth_manager
client = await get_okta_client(manager)
```

**`OktaAuthManager`** — manages token lifecycle (stored in system keyring, auto-refreshed). Tools never call it directly beyond the pattern above.

**`TOOL_SCOPE_REGISTRY`** — dict in `scope_registry.py` mapping every tool function name to its required OAuth scope. Used by both `prune_tools_by_scope()` at startup and by tests.

---

## Customization System

**Do not modify files in `src/okta_mcp_server/`.** All changes go in `customizations/` and are declared in `customizations/manifest.yaml`. This keeps upstream merges conflict-free — when a new upstream release arrives, only `src/` files need reconciliation and the customizations directory is untouched.

### manifest.yaml Entry Types

| Type | Effect | Required extra fields |
|------|--------|-----------------------|
| `add_tool` | Registers a new tool not present upstream | `file` |
| `override_tool` | Removes the upstream registration, loads replacement | `file` |
| `remove_tool` | Drops an upstream tool from the FastMCP registry | — |
| `config_change` | Server-level config change (apply in `custom_server.py`) | `value` |

### All entry fields

```yaml
- id: "add-001"              # unique ID — increment per type prefix (add, ov, rm, cfg)
  type: add_tool             # add_tool | override_tool | remove_tool | config_change
  name: "my_tool"            # exact Python function name
  file: "customizations/tools/my_tool.py"   # required for add_tool and override_tool
  description: "What this tool does"        # human-readable summary
  reason: "Why this change was made"        # motivation
  added_date: "2026-05-16"   # ISO date
```

### Adding a New Tool

1. Create `customizations/tools/my_tool.py` following the Tool Authoring Pattern below
2. Add an `add_tool` entry to `customizations/manifest.yaml`
3. If the tool requires a new OAuth scope, add it to `TOOL_SCOPE_REGISTRY` in `src/okta_mcp_server/utils/scope_registry.py`

### Overriding an Existing Tool

1. Create `customizations/overrides/my_override.py` with the replacement function (same function name as upstream)
2. Add an `override_tool` entry to `customizations/manifest.yaml`
3. At startup, `custom_server.py` removes the upstream registration via `mcp._tool_manager.remove_tool(name)` before importing the override module

### Removing a Tool

Add a `remove_tool` entry — no file needed. `custom_server.py` calls `mcp._tool_manager.remove_tool(name)` after all upstream imports.

### Syncing Upstream

See `UPSTREAM.md` for the full process. In brief:
1. Review the upstream release changelog
2. Check `customizations/manifest.yaml`: do any `override_tool` entries need updating given upstream changes?
3. Copy changed files from the upstream release into `src/okta_mcp_server/`
4. Run `uv run pytest`
5. Update `UPSTREAM.md` with the new tag, commit hash, and date

---

## Tool Authoring Pattern

Every tool — whether in `src/` (upstream) or `customizations/` (local) — follows this pattern:

```python
from loguru import logger
from mcp.server.fastmcp import Context

from okta_mcp_server.server import mcp
from okta_mcp_server.utils.client import get_okta_client
from okta_mcp_server.utils.scope_guard import require_scopes
from okta_mcp_server.utils.validation import validate_ids


@mcp.tool()
@require_scopes("okta.resource.read", error_return_type="list")
@validate_ids("resource_id")
async def my_tool(ctx: Context, resource_id: str) -> list:
    """LLM-visible description. Be explicit about parameters and return shape.

    Parameters:
        resource_id: The Okta resource ID.

    Returns:
        List of result dicts, or [{"error": "..."}] on failure.
    """
    manager = ctx.request_context.lifespan_context.okta_auth_manager
    client = await get_okta_client(manager)

    resource, _, err = await client.get_resource(resource_id)
    if err:
        logger.error(f"Error fetching resource {resource_id}: {err}")
        return [{"error": str(err)}]

    return [{"id": resource.id, "profile": resource.profile.__dict__}]
```

### Decorator Order (always follow this)

```python
@mcp.tool()          # 1. register with FastMCP
@require_scopes(…)   # 2. scope enforcement
@validate_ids(…)     # 3. input validation (apply to any ID parameters)
async def tool_name(ctx: Context, …):
```

### Return Types

- Read tools return `dict` or `list`
- On error, always return `{"error": str(err)}` (or `[{"error": …}]` for list tools) — never raise from a tool
- Match `error_return_type` on `@require_scopes` to the tool's actual return type

### Destructive Operations (Elicitation)

Tools that delete or deactivate must request user confirmation via elicitation:

```python
from okta_mcp_server.utils.elicitation import DeleteConfirmation, elicit_or_fallback
from okta_mcp_server.utils.messages import DELETE_USER

outcome = await elicit_or_fallback(ctx, DELETE_USER.format(user_id=user_id), DeleteConfirmation)
if not outcome.confirmed:
    return outcome.fallback_response
# safe to proceed
```

`elicit_or_fallback` handles both clients that support MCP elicitation and those that don't (fallback to a two-step confirmation tool pattern).

### Input Validation

Apply `@validate_ids("param_name")` to any parameter passed as an Okta API ID. This prevents path traversal and SSRF attacks by rejecting IDs containing `..`, `/`, `\`, `?`, `#`, or URL-encoded variants.

For OS version strings, use `@validate_os_version_params`.

---

## OAuth Scope Registry

`src/okta_mcp_server/utils/scope_registry.py` contains `TOOL_SCOPE_REGISTRY`, the complete tool → scope mapping. When adding a tool in `customizations/`, add its entry here so scope pruning and the `get_scope_status` tool work correctly.

| Scope | Covers |
|-------|--------|
| `okta.users.read` / `.manage` | Users |
| `okta.groups.read` / `.manage` | Groups |
| `okta.apps.read` / `.manage` | Applications |
| `okta.policies.read` / `.manage` | Policies + rules |
| `okta.deviceAssurance.read` / `.manage` | Device assurance policies |
| `okta.logs.read` | System logs |
| `okta.brands.read` / `.manage` | Brands, themes, custom pages |
| `okta.templates.read` / `.manage` | Email templates |
| `okta.domains.read` / `.manage` | Custom domains |
| `okta.emailDomains.read` / `.manage` | Email domains |

Scope convention: `okta.<resource>.read` for GET operations; `okta.<resource>.manage` for POST/PUT/DELETE.

---

## Testing

### Run Tests

```bash
uv run pytest                              # all tests
uv run pytest tests/test_users.py -v      # single file
uv run pytest -k "test_create_user" -v    # by name
```

### Test Structure

- `tests/conftest.py` — shared fixtures for all tests
- `tests/elicitation/` — elicitation flow tests (accept / decline / cancel / MCP fallback)
- `tests/test_*.py` — feature tests per domain

### Key Fixtures (conftest.py)

```python
FakeOktaAuthManager        # mock auth manager with configurable .scopes string
FakeLifespanContext        # wraps FakeOktaAuthManager for ctx injection
mock_okta_client           # mock Okta SDK client

# Pre-built MCP Context objects for elicitation scenarios:
ctx_elicit_accept_true     # user confirms (confirm=True)
ctx_elicit_accept_false    # user submits with confirm=False (treated as decline)
ctx_elicit_decline         # user explicitly declines
ctx_elicit_cancel          # user cancels the elicitation dialog
ctx_no_elicitation         # client without elicitation support (tests fallback path)
ctx_elicit_exception       # elicitation raises an unexpected exception
```

### Writing a Test for a Custom Tool

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_tool(mock_okta_client, ctx_elicit_accept_true):
    mock_okta_client.get_resource = AsyncMock(return_value=(fake_resource, None, None))
    with patch("okta_mcp_server.utils.client.OktaClient", return_value=mock_okta_client):
        result = await my_tool(ctx=ctx_elicit_accept_true, resource_id="abc123")
    assert result[0]["id"] == "abc123"
```

---

## Coding Conventions

- **Python 3.13+** — use modern syntax: `X | Y` unions, `match`, built-in generics (`list[str]` not `List[str]`)
- **Linter/formatter:** Ruff — config in `.ruff.toml`; line length 119; double-quoted strings
- **Run before committing:** `uv run ruff check . && uv run ruff format .`
- **Async:** all tools are `async def`; Okta SDK calls use `await`
- **Comments:** write none by default. Only add a comment when the WHY is non-obvious (a hidden constraint, a subtle invariant, a workaround). Never comment WHAT the code does.
- **Docstrings on tools:** mandatory and LLM-visible. Include parameter descriptions, return shape, and any important behavioral notes. The LLM reads these to decide how to call the tool.
- **Logging:** `from loguru import logger`. Use `INFO` for significant operations, `DEBUG` for parameter values, `ERROR` for API failures.
- **Imports:** standard library → third party → local; sorted by Ruff's isort rules.

---

## CI/CD

| System | Config | Purpose |
|--------|--------|---------|
| CircleCI | `.circleci/config.yml` | Build, test (`uv run pytest`), Snyk dependency scan, Reverse Labs malware scan |
| GitHub Actions | `.github/workflows/ruff-check.yml` | Ruff lint + format check on pull requests |
| Bacon (Okta internal) | `.bacon.yml` | Build, test, SCA scan on mainline |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]>=1.26.0,<2.0.0` | Model Context Protocol framework (FastMCP) |
| `okta==3.4.1` | Official Okta Python SDK |
| `loguru>=0.7.3` | Structured logging |
| `requests>=2.32.4` | HTTP client (auth flows) |
| `keyring>=25.6.0` + `keyrings.alt>=5.0.0` | Secure token storage |
| `flatdict>=4.1.0` | Flatten/unflatten nested dicts |
| `pyyaml>=6.0` | Parse `customizations/manifest.yaml` |
| `ruff>=0.11.13` | Linter + formatter |
| `pytest` + `pytest-asyncio` | Test framework (dev only) |
