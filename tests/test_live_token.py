"""
test_live_token.py
==================
Tests for LiveToken: str-protocol compliance, HTTP library integration,
auto-refresh behaviour, and security (masked repr).
"""
from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from shopify_auth_adapter._live_token import LiveToken


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_live_token(value: str = "test_token_abc") -> LiveToken:
    """Return a LiveToken backed by a mock manager that returns *value*."""
    manager = MagicMock()
    manager.get_token.return_value = value
    return LiveToken(manager)


def make_live_token_sequence(*values: str) -> LiveToken:
    """Return a LiveToken whose get_token() returns each value in sequence."""
    manager = MagicMock()
    manager.get_token.side_effect = list(values)
    return LiveToken(manager)


# ---------------------------------------------------------------------------
# isinstance checks
# ---------------------------------------------------------------------------


class TestLiveTokenIsStrSubclass:
    def test_is_instance_of_str(self):
        lt = make_live_token()
        assert isinstance(lt, str)

    def test_is_instance_of_live_token(self):
        lt = make_live_token()
        assert isinstance(lt, LiveToken)

    def test_isinstance_check_passes_for_http_libs(self):
        """Simulate the isinstance(value, str) check done by requests/httpx."""
        lt = make_live_token("tok")
        assert isinstance(lt, str) is True  # passes library guard


# ---------------------------------------------------------------------------
# Core behaviour: delegates to manager.get_token()
# ---------------------------------------------------------------------------


class TestLiveTokenDelegation:
    def test_str_returns_current_token(self):
        lt = make_live_token("my_token")
        assert str(lt) == "my_token"

    def test_encode_returns_current_token_bytes(self):
        lt = make_live_token("my_token")
        assert lt.encode("latin-1") == b"my_token"
        assert lt.encode("utf-8") == b"my_token"

    def test_encode_called_per_invocation(self):
        """encode() must call get_token() each time — not cache the result."""
        lt = make_live_token_sequence("first_token", "second_token")
        assert lt.encode("latin-1") == b"first_token"
        assert lt.encode("latin-1") == b"second_token"

    def test_format_returns_current_token(self):
        lt = make_live_token("tok_abc")
        assert f"{lt}" == "tok_abc"
        assert format(lt, "") == "tok_abc"

    def test_addition_with_str(self):
        lt = make_live_token("Bearer ")
        result = lt + "my_token"
        assert result == "Bearer my_token"
        assert isinstance(result, str)

    def test_right_addition_with_str(self):
        lt = make_live_token("_suffix")
        result = "prefix" + lt
        assert result == "prefix_suffix"

    def test_equality_with_matching_str(self):
        lt = make_live_token("abc")
        assert lt == "abc"

    def test_inequality_with_different_str(self):
        lt = make_live_token("abc")
        assert lt != "xyz"

    def test_length(self):
        lt = make_live_token("hello")
        assert len(lt) == 5

    def test_bool_true_for_non_empty(self):
        lt = make_live_token("tok")
        assert bool(lt) is True

    def test_bool_false_for_empty(self):
        lt = make_live_token("")
        assert bool(lt) is False

    def test_contains(self):
        lt = make_live_token("shpat_abc123")
        assert "abc" in lt

    def test_startswith(self):
        lt = make_live_token("Bearer tok")
        assert lt.startswith("Bearer")

    def test_endswith(self):
        lt = make_live_token("my_token_xyz")
        assert lt.endswith("xyz")

    def test_upper(self):
        lt = make_live_token("abc")
        assert lt.upper() == "ABC"

    def test_lower(self):
        lt = make_live_token("ABC")
        assert lt.lower() == "abc"

    def test_strip(self):
        lt = make_live_token("  tok  ")
        assert lt.strip() == "tok"

    def test_split(self):
        lt = make_live_token("a,b,c")
        assert lt.split(",") == ["a", "b", "c"]

    def test_replace(self):
        lt = make_live_token("hello world")
        assert lt.replace("world", "shopify") == "hello shopify"

    def test_iteration(self):
        lt = make_live_token("abc")
        assert list(lt) == ["a", "b", "c"]

    def test_getitem(self):
        lt = make_live_token("hello")
        assert lt[0] == "h"
        assert lt[-1] == "o"
        assert lt[1:3] == "el"


# ---------------------------------------------------------------------------
# Auto-refresh behaviour
# ---------------------------------------------------------------------------


class TestLiveTokenAutoRefresh:
    def test_refreshes_when_manager_returns_new_token(self):
        """
        If the TokenManager returns a new token (because the old one expired
        and was refreshed internally), encode() should return the new value.
        """
        lt = make_live_token_sequence("old_token", "old_token", "new_token")
        assert lt.encode("utf-8") == b"old_token"
        assert lt.encode("utf-8") == b"old_token"
        assert lt.encode("utf-8") == b"new_token"

    def test_get_token_called_on_each_encode(self):
        manager = MagicMock()
        manager.get_token.return_value = "tok"
        lt = LiveToken(manager)
        for _ in range(5):
            lt.encode("utf-8")
        assert manager.get_token.call_count == 5

    def test_get_token_called_on_each_str(self):
        manager = MagicMock()
        manager.get_token.return_value = "tok"
        lt = LiveToken(manager)
        for _ in range(3):
            str(lt)
        assert manager.get_token.call_count == 3


# ---------------------------------------------------------------------------
# HTTP header simulation
# ---------------------------------------------------------------------------


class TestLiveTokenInHttpHeaders:
    def test_used_as_requests_header_value(self):
        """
        Simulate what requests/http.client does: check hasattr 'encode',
        then call .encode('latin-1').
        """
        lt = make_live_token("my_shopify_token")
        header_value = lt
        # Simulate http.client.putheader logic
        if hasattr(header_value, "encode"):
            encoded = header_value.encode("latin-1")
        else:
            encoded = header_value
        assert encoded == b"my_shopify_token"

    def test_used_as_httpx_header_value(self):
        """
        Simulate what httpx does: call v.encode('latin-1') directly.
        """
        lt = make_live_token("httpx_token_123")
        # httpx builds headers with: (k.encode('latin-1'), v.encode('latin-1'))
        assert lt.encode("latin-1") == b"httpx_token_123"

    def test_isinstance_str_check_passes(self):
        """
        requests checks isinstance(value, str) before encoding.
        LiveToken must pass.
        """
        lt = make_live_token("tok")
        assert isinstance(lt, str)

    def test_header_dict_stores_live_token(self):
        """The LiveToken object should survive being stored in a plain dict."""
        lt = make_live_token("shopify_abc")
        headers = {"X-Shopify-Access-Token": lt}
        stored = headers["X-Shopify-Access-Token"]
        # Encoding the stored value must still return the current token bytes
        assert stored.encode("latin-1") == b"shopify_abc"


# ---------------------------------------------------------------------------
# Security – repr never exposes the token
# ---------------------------------------------------------------------------


class TestLiveTokenSecurity:
    def test_repr_is_masked(self):
        lt = make_live_token("SUPER_SECRET_TOKEN")
        r = repr(lt)
        assert "SUPER_SECRET_TOKEN" not in r
        assert "<masked>" in r

    def test_repr_does_not_call_get_token(self):
        manager = MagicMock()
        manager.get_token.return_value = "tok"
        lt = LiveToken(manager)
        repr(lt)
        manager.get_token.assert_not_called()

    def test_live_token_not_str_equal_to_placeholder(self):
        """The empty placeholder baked into the str parent must not leak."""
        lt = make_live_token("real_token")
        # The baked-in str value is "" — LiveToken must NOT report equality with it
        assert lt != ""

    def test_hash_based_on_current_token(self):
        lt = make_live_token("consistent_token")
        assert hash(lt) == hash("consistent_token")


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestLiveTokenConstruction:
    def test_no_api_call_at_construction(self):
        """LiveToken.__new__ must not call get_token() (lazy init)."""
        manager = MagicMock()
        LiveToken(manager)
        manager.get_token.assert_not_called()

    def test_manager_stored_correctly(self):
        manager = MagicMock()
        lt = LiveToken(manager)
        assert lt._manager is manager
