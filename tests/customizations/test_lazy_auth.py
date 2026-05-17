"""Tests for the lazy authentication lifespan (customizations/lazy_auth.py)."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from customizations.lazy_auth import _EXPIRY_DURATION, _try_restore_token, lazy_okta_lifespan

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_jwt(exp: int) -> str:
    """Return a minimal JWT whose decoded claims contain the given exp."""
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "test", "exp": exp}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


@dataclass
class FakeManager:
    token_timestamp: int = 0
    scopes: str = "openid profile email offline_access"

    async def is_valid_token(self) -> bool:
        return True

    async def authenticate(self) -> None:
        pass

    def clear_tokens(self) -> None:
        pass


# ---------------------------------------------------------------------------
# _try_restore_token
# ---------------------------------------------------------------------------


class TestTryRestoreToken:
    def test_no_token_in_keyring_leaves_timestamp_zero(self):
        manager = FakeManager()
        with patch("customizations.lazy_auth.keyring.get_password", return_value=None):
            _try_restore_token(manager)
        assert manager.token_timestamp == 0

    def test_valid_token_sets_timestamp_from_exp(self):
        manager = FakeManager()
        future_exp = int(time.time()) + 1800  # 30 min from now
        token = _make_jwt(future_exp)
        with patch("customizations.lazy_auth.keyring.get_password", return_value=token):
            _try_restore_token(manager)
        assert manager.token_timestamp == future_exp - _EXPIRY_DURATION

    def test_expired_token_leaves_timestamp_zero(self):
        manager = FakeManager()
        past_exp = int(time.time()) - 60
        token = _make_jwt(past_exp)
        with patch("customizations.lazy_auth.keyring.get_password", return_value=token):
            _try_restore_token(manager)
        assert manager.token_timestamp == 0

    def test_malformed_token_leaves_timestamp_zero(self):
        manager = FakeManager()
        with patch("customizations.lazy_auth.keyring.get_password", return_value="not.a.jwt"):
            _try_restore_token(manager)  # must not raise
        assert manager.token_timestamp == 0

    def test_timestamp_tracks_expiry_boundary(self):
        """token_timestamp = exp - _EXPIRY_DURATION means is_valid_token()'s age
        check (time.time() - token_timestamp < _EXPIRY_DURATION) flips False
        exactly when the token expires."""
        manager = FakeManager()
        future_exp = int(time.time()) + 500
        token = _make_jwt(future_exp)
        with patch("customizations.lazy_auth.keyring.get_password", return_value=token):
            _try_restore_token(manager)
        age_at_expiry = future_exp - manager.token_timestamp
        assert age_at_expiry == _EXPIRY_DURATION


# ---------------------------------------------------------------------------
# lazy_okta_lifespan
# ---------------------------------------------------------------------------


class TestLazyOktaLifespan:
    @pytest.mark.asyncio
    async def test_yields_okta_app_context_with_manager(self):
        fake_manager = FakeManager()
        fake_server = MagicMock()

        with (
            patch("customizations.lazy_auth.OktaAuthManager", return_value=fake_manager),
            patch("customizations.lazy_auth._try_restore_token"),
            patch("customizations.lazy_auth.prune_tools_by_scope"),
        ):
            async with lazy_okta_lifespan(fake_server) as ctx:
                assert ctx.okta_auth_manager is fake_manager

    @pytest.mark.asyncio
    async def test_calls_try_restore_token_and_prune(self):
        fake_manager = FakeManager()
        fake_server = MagicMock()

        with (
            patch("customizations.lazy_auth.OktaAuthManager", return_value=fake_manager),
            patch("customizations.lazy_auth._try_restore_token") as mock_restore,
            patch("customizations.lazy_auth.prune_tools_by_scope") as mock_prune,
        ):
            async with lazy_okta_lifespan(fake_server):
                pass

        mock_restore.assert_called_once_with(fake_manager)
        mock_prune.assert_called_once_with(fake_server, fake_manager)

    @pytest.mark.asyncio
    async def test_clears_tokens_on_exit(self):
        fake_manager = FakeManager()
        cleared = []
        fake_manager.clear_tokens = lambda: cleared.append(True)
        fake_server = MagicMock()

        with (
            patch("customizations.lazy_auth.OktaAuthManager", return_value=fake_manager),
            patch("customizations.lazy_auth._try_restore_token"),
            patch("customizations.lazy_auth.prune_tools_by_scope"),
        ):
            async with lazy_okta_lifespan(fake_server):
                pass

        assert cleared == [True]

    @pytest.mark.asyncio
    async def test_clears_tokens_even_on_exception(self):
        fake_manager = FakeManager()
        cleared = []
        fake_manager.clear_tokens = lambda: cleared.append(True)
        fake_server = MagicMock()

        with (
            patch("customizations.lazy_auth.OktaAuthManager", return_value=fake_manager),
            patch("customizations.lazy_auth._try_restore_token"),
            patch("customizations.lazy_auth.prune_tools_by_scope"),
        ):
            with pytest.raises(RuntimeError):
                async with lazy_okta_lifespan(fake_server):
                    raise RuntimeError("tool blew up")

        assert cleared == [True]
