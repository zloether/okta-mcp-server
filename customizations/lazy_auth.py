"""Lazy authentication lifespan for the Okta MCP server.

Replaces the upstream lifespan that unconditionally triggers the device
authorization flow at startup. Authentication is deferred until the first
tool invocation; if a valid token already exists in the system keyring it
is reused without prompting the user.
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import jwt
import keyring
from loguru import logger
from mcp.server.fastmcp import FastMCP

from okta_mcp_server.server import OktaAppContext
from okta_mcp_server.utils.auth.auth_manager import SERVICE_NAME, OktaAuthManager
from okta_mcp_server.utils.scope_guard import prune_tools_by_scope

# Default token lifetime assumed by is_valid_token(); must match auth_manager.py.
_EXPIRY_DURATION = 3600


def _try_restore_token(manager: OktaAuthManager) -> None:
    """Restore token_timestamp from an existing keyring token if it is still valid.

    OktaAuthManager.is_valid_token() returns True when both:
      - a token exists in keyring, AND
      - time.time() - manager.token_timestamp < expiry_duration (default 3600 s)

    token_timestamp starts at 0 on a fresh manager, so is_valid_token() would
    always trigger re-auth even when keyring holds a live token.  This function
    decodes the JWT's `exp` claim and sets token_timestamp = exp - _EXPIRY_DURATION
    so that the age check mirrors actual token expiry.
    """
    token = keyring.get_password(SERVICE_NAME, "api_token")
    if not token:
        logger.debug("[lazy-auth] No existing token in keyring")
        return
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        exp = claims.get("exp", 0)
        if exp > time.time():
            manager.token_timestamp = int(exp) - _EXPIRY_DURATION
            logger.info(f"[lazy-auth] Reusing existing token, expires in {int(exp - time.time())}s")
        else:
            logger.info("[lazy-auth] Keyring token is expired; will authenticate on first tool call")
    except Exception as exc:
        logger.warning(f"[lazy-auth] Could not inspect keyring token: {exc}")


@asynccontextmanager
async def lazy_okta_lifespan(server: FastMCP) -> AsyncIterator[OktaAppContext]:  # noqa: RUF029
    """Lifespan that defers authentication until the first tool call.

    Replaces the upstream okta_authorisation_flow which unconditionally
    triggers the device authorization flow (or browserless flow) at startup.
    """
    logger.info("[lazy-auth] Server starting — authentication deferred until first tool call")
    manager = OktaAuthManager()
    _try_restore_token(manager)
    # prune_tools_by_scope reads manager.scopes (populated from OKTA_SCOPES env
    # var at init time) — no token needed.
    prune_tools_by_scope(server, manager)

    yield OktaAppContext(okta_auth_manager=manager)
