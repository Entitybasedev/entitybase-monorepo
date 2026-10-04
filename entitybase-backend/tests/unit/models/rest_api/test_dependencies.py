"""Unit tests for the current-user route dependencies."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from models.rest_api.dependencies import (
    AUTH_USER_ID_SCOPE_KEY,
    current_user_id,
    require_self,
)


def request_with(user_id: int | None) -> MagicMock:
    """A request whose scope carries (or lacks) an authenticated user id."""
    req = MagicMock()
    scope = {} if user_id is None else {AUTH_USER_ID_SCOPE_KEY: user_id}
    req.scope = scope
    return req


class TestCurrentUserId:
    """current_user_id reads the id the middleware decoded from the token."""

    def test_returns_the_authenticated_user(self):
        assert current_user_id(request_with(42)) == 42

    def test_requires_a_token(self):
        with pytest.raises(HTTPException) as error:
            current_user_id(request_with(None))
        assert error.value.status_code == 401

    def test_ignores_a_client_supplied_header(self):
        """Only the token decides who the caller is.

        The X-User-ID header is absent from the scope on purpose: a client can
        send it, and it must never be mistaken for an authenticated identity.
        """
        req = request_with(42)
        assert "x-user-id" not in req.scope
        assert current_user_id(req) == 42


class TestRequireSelf:
    """require_self rejects acting on another user's data."""

    def test_allows_the_owner(self):
        assert require_self(42, request_with(42)) == 42

    def test_rejects_another_user(self):
        with pytest.raises(HTTPException) as error:
            require_self(42, request_with(99))
        assert error.value.status_code == 403

    def test_rejects_anonymous_callers(self):
        with pytest.raises(HTTPException) as error:
            require_self(42, request_with(None))
        assert error.value.status_code == 401
