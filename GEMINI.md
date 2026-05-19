# okta-mcp-server

See **[AGENTS.md](AGENTS.md)** for the full project reference: architecture, customization system, tool authoring patterns, testing, and coding conventions.

## Quick orientation

- **Do not modify `src/okta_mcp_server/`** — all changes go in `customizations/` and are declared in `customizations/manifest.yaml`
- **Entry point:** `uv run python custom_server.py`
- **Tool decorator order:** `@mcp.tool()` → `@require_scopes()` → `@validate_ids()`
- **New scopes:** every new tool must be added to `TOOL_SCOPE_REGISTRY` in `src/okta_mcp_server/utils/scope_registry.py`
- **Tests:** `uv run pytest`
- **Lint:** `uv run ruff check . && uv run ruff format .`
