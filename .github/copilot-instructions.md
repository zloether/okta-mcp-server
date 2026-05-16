# GitHub Copilot Instructions — okta-mcp-server

See **[AGENTS.md](../AGENTS.md)** in the repository root for the full reference.

## Critical rules

- **Never modify `src/okta_mcp_server/`** — this is the upstream source. All changes go in `customizations/` and must be declared in `customizations/manifest.yaml`.
- **Entry point:** `uv run python custom_server.py`
- **Tool decorator order:** `@mcp.tool()` → `@require_scopes()` → `@validate_ids()`
- **New tools need a scope entry** in `src/okta_mcp_server/utils/scope_registry.py`
- **Error returns:** never raise from a tool — return `{"error": str(err)}` or `[{"error": …}]`
- **No comments** unless the WHY is non-obvious
- **Lint:** `uv run ruff check . && uv run ruff format .`
- **Tests:** `uv run pytest`
