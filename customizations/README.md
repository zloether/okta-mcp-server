# Running the Customized Server

This directory contains all local changes layered on top of the upstream
[okta-mcp-server](https://github.com/okta/okta-mcp-server). The entry point
is `custom_server.py` at the repo root — it loads the upstream tools and applies
the customizations in `manifest.yaml` without modifying anything in `src/`.

## Prerequisites

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Okta credentials (see [Authentication](#authentication) below)

Install dependencies:

```bash
uv sync
```

## Running from the command line

```bash
uv run python custom_server.py
```

Optional environment variables:

| Variable | Default | Description |
|---|---|---|
| `OKTA_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OKTA_LOG_FILE` | _(stderr only)_ | Path to write JSON log output |

## Connecting an MCP client

Replace `uv run okta-mcp-server` (the upstream entry point) with
`uv run python custom_server.py` in whichever client config you're using.

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "okta-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/okta-mcp-server",
        "python",
        "custom_server.py"
      ],
      "env": {
        "OKTA_ORG_URL": "<OKTA_ORG_URL>",
        "OKTA_CLIENT_ID": "<OKTA_CLIENT_ID>",
        "OKTA_SCOPES": "<OKTA_SCOPES>",
        "OKTA_PRIVATE_KEY": "<PRIVATE_KEY_IF_NEEDED>",
        "OKTA_KEY_ID": "<KEY_ID_IF_NEEDED>"
      }
    }
  }
}
```

### VS Code

`.vscode/mcp.json` (or user `settings.json` under `"mcp"`):

```json
{
  "servers": {
    "okta-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/okta-mcp-server",
        "python",
        "custom_server.py"
      ],
      "env": {
        "OKTA_ORG_URL": "<OKTA_ORG_URL>",
        "OKTA_CLIENT_ID": "<OKTA_CLIENT_ID>",
        "OKTA_SCOPES": "<OKTA_SCOPES>",
        "OKTA_PRIVATE_KEY": "<PRIVATE_KEY_IF_NEEDED>",
        "OKTA_KEY_ID": "<KEY_ID_IF_NEEDED>"
      }
    }
  }
}
```

### Other MCP clients

Use the same pattern — `command: uv`, args `["run", "--directory", "/path/to/okta-mcp-server", "python", "custom_server.py"]` — with the env vars above.

## Authentication

The server supports the same two auth methods as upstream. See the
[upstream README](../README.md#authenticate-with-okta) for setup steps.

**Device Authorization Grant** — interactive browser login; good for local use.
Set `OKTA_CLIENT_ID`, `OKTA_ORG_URL`, and `OKTA_SCOPES`.

**Private Key JWT** — browserless; good for automated or headless environments.
Set `OKTA_CLIENT_ID`, `OKTA_ORG_URL`, `OKTA_SCOPES`, `OKTA_PRIVATE_KEY`, and `OKTA_KEY_ID`.

## How customizations are applied

At startup `custom_server.py` reads `manifest.yaml` and applies each entry in order:

| Type | Effect |
|---|---|
| `add_tool` | Loads a new tool from `customizations/tools/` |
| `override_tool` | Removes the upstream tool and loads a replacement from `customizations/overrides/` |
| `remove_tool` | Drops an upstream tool entirely |
| `config_change` | Applies a server-level config change |

See [AGENTS.md](../AGENTS.md) for instructions on adding or modifying customizations.
