"""
Custom MCP server entry point.

Wraps the upstream Okta MCP server and applies customizations defined in
customizations/manifest.yaml without modifying any files in src/.

Usage:
    uv run python custom_server.py

Customization types applied at startup:
    add_tool      — loads modules from customizations/tools/
    override_tool — removes the upstream registration, loads replacement from customizations/overrides/
    remove_tool   — removes the upstream tool from the FastMCP registry
    config_change — applied directly in _apply_config_changes() below
"""

import importlib
import os
import sys
from pathlib import Path

import yaml
from loguru import logger

# Repo root must be on sys.path so customizations/ is importable as a package.
sys.path.insert(0, str(Path(__file__).parent))

LOG_FILE = os.environ.get("OKTA_LOG_FILE")
MANIFEST_PATH = Path(__file__).parent / "customizations" / "manifest.yaml"


def _load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f) or {}


def _by_type(manifest: dict, ctype: str) -> list[dict]:
    return [c for c in manifest.get("customizations", []) if c.get("type") == ctype]


def _file_to_module(file_path: str) -> str:
    """Convert 'customizations/tools/my_tool.py' -> 'customizations.tools.my_tool'."""
    return file_path.replace("/", ".").removesuffix(".py")


def _remove_tool(mcp, name: str) -> bool:
    try:
        mcp._tool_manager.remove_tool(name)
        return True
    except Exception as exc:
        logger.warning(f"[custom] Could not remove tool '{name}': {exc}")
        return False


def main():
    logger.remove()

    if LOG_FILE:
        logger.add(
            LOG_FILE,
            mode="w",
            level=os.environ.get("OKTA_LOG_LEVEL", "INFO"),
            retention="5 days",
            enqueue=True,
            serialize=True,
        )

    logger.add(
        sys.stderr,
        level=os.environ.get("OKTA_LOG_LEVEL", "INFO"),
        format="{time} {level} {message}",
        serialize=True,
    )

    logger.info("Starting custom Okta MCP Server")

    manifest = _load_manifest()
    override_entries = _by_type(manifest, "override_tool")
    remove_entries = _by_type(manifest, "remove_tool")
    add_entries = _by_type(manifest, "add_tool")

    logger.info(
        f"[custom] Manifest: "
        f"{len(add_entries)} addition(s), "
        f"{len(override_entries)} override(s), "
        f"{len(remove_entries)} removal(s)"
    )

    # --- Load all upstream tools (same order as server.py:main) ---
    from okta_mcp_server.tools.applications import applications  # noqa: F401, I001
    from okta_mcp_server.tools.customization.brands import brands  # noqa: F401
    from okta_mcp_server.tools.customization.custom_domains import custom_domains  # noqa: F401
    from okta_mcp_server.tools.customization.custom_pages import custom_pages  # noqa: F401
    from okta_mcp_server.tools.customization.custom_templates import custom_templates  # noqa: F401
    from okta_mcp_server.tools.customization.email_domains import email_domains  # noqa: F401
    from okta_mcp_server.tools.customization.themes import themes  # noqa: F401
    from okta_mcp_server.tools.device_assurance import device_assurance  # noqa: F401
    from okta_mcp_server.tools.groups import groups  # noqa: F401
    from okta_mcp_server.tools.policies import policies  # noqa: F401
    from okta_mcp_server.tools.system_logs import login_failures  # noqa: F401
    from okta_mcp_server.tools.system_logs import system_logs  # noqa: F401
    from okta_mcp_server.tools.users import users  # noqa: F401
    from okta_mcp_server.utils import scope_stubs  # noqa: F401

    # mcp is imported after tool modules so all upstream registrations are complete.
    from okta_mcp_server.server import mcp

    # --- Replace upstream lifespan with lazy authentication ---
    from mcp.server.fastmcp.server import lifespan_wrapper
    from customizations.lazy_auth import lazy_okta_lifespan

    mcp._mcp_server.lifespan = lifespan_wrapper(mcp, lazy_okta_lifespan)
    logger.info("[custom] Replaced upstream lifespan with lazy authentication")

    # --- Overrides: remove upstream registration, load replacement ---
    for entry in override_entries:
        tool_name = entry["name"]
        if _remove_tool(mcp, tool_name):
            logger.info(f"[custom] Removed upstream '{tool_name}' for override")
        importlib.import_module(_file_to_module(entry["file"]))
        logger.info(f"[custom] Override loaded: '{tool_name}' <- {entry['file']}")

    # --- Removals: drop tools entirely ---
    for entry in remove_entries:
        if _remove_tool(mcp, entry["name"]):
            logger.info(f"[custom] Removed tool: '{entry['name']}'")

    # --- Additions: register new tools ---
    for entry in add_entries:
        importlib.import_module(_file_to_module(entry["file"]))
        logger.info(f"[custom] Addition loaded: '{entry['name']}' <- {entry['file']}")

    mcp.run()


if __name__ == "__main__":
    main()
