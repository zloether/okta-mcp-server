# okta-mcp-server

See **[AGENTS.md](AGENTS.md)** for the full project reference: architecture, customization system, tool authoring patterns, testing, and coding conventions.

## Quick orientation

- **Do not modify `src/okta_mcp_server/`** — all changes go in `customizations/` and are declared in `customizations/manifest.yaml`
- **Entry point:** `uv run python custom_server.py` (not `okta-mcp-server`)
- **Run tests:** `uv run pytest`
- **Lint:** `uv run ruff check . && uv run ruff format .`
