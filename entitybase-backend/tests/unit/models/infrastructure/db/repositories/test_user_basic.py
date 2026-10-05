"""Unit tests for UserRepository - basic CRUD operations."""

import pytest
from unittest.mock import MagicMock, call

from models.infrastructure.db.repositories.user import UserRepository


class TestUserRepositoryBasic:
    """Unit tests for UserRepository basic operations."""

    def test_create_user_success(self):
        """Test successful user creation."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.create_user(123)

        assert result.success is True
        mock_cursor.execute.assert_called_once()

    def test_create_user_database_error(self):
        """Test user creation with database error."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.create_user(123)

        assert result.success is False
        assert "DB error" in result.error

    def test_create_user_success_new(self):
        """Test successful user creation for new user."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.create_user(123)

        assert result.success is True

    def test_user_exists_true(self):
        """Test user exists when found."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = (1,)
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.user_exists(123)

        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "SELECT 1 FROM users WHERE user_id = %s", (123,)
        )

    def test_user_exists_false(self):
        """Test user does not exist."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.user_exists(123)

        assert result is False

    def test_user_exists_database_error(self):
        """Test user exists with database error."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        with pytest.raises(Exception):
            repo.user_exists(123)

    def test_get_user_found(self):
        """Test getting existing user."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = (123, "2023-01-01", {"theme": "dark"})
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.get_user(123)

        assert result is not None
        assert result.user_id == 123
        assert result.preferences == {"theme": "dark"}

    def test_get_user_not_found(self):
        """Test getting non-existent user."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.get_user(123)

        assert result is None

    def test_get_user_database_error(self):
        """Test get user with database error."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        with pytest.raises(Exception):
            repo.get_user(123)

    def test_get_user_invalid_data(self):
        """Test get user with invalid data raises validation error."""
        from fastapi import HTTPException

        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = (123, "2023-01-01", "invalid_json")
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        with pytest.raises(HTTPException) as exc_info:
            repo.get_user(123)

        assert exc_info.value.status_code == 400
        assert "Invalid user data" in exc_info.value.detail

    def test_delete_user_success(self):
        """Test successful user deletion."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 1
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.delete_user(123)

        assert result.success is True
        mock_cursor.execute.assert_any_call(
            "DELETE FROM users WHERE user_id = %s", (123,)
        )

    def test_delete_user_also_removes_credentials(self):
        """Credentials are keyed by user id, so they go with the account.

        The id allocator hands out MAX(user_id) + 1, so a leftover credential
        row blocks a later registration of that id.
        """
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 1
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        repo.delete_user(123)

        mock_cursor.execute.assert_any_call(
            "DELETE FROM user_credentials WHERE user_id = %s", (123,)
        )

    def test_delete_user_not_found_leaves_credentials_alone(self):
        """A missing account is not an error to fix by deleting credentials."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 0
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        repo.delete_user(123)

        executed = [call.args[0] for call in mock_cursor.execute.call_args_list]
        assert all("user_credentials" not in sql for sql in executed)

    def test_delete_user_not_found(self):
        """Test deleting non-existent user."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 0
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.delete_user(123)

        assert result.success is False
        assert "User not found" in result.error

    def test_delete_user_invalid_id(self):
        """Test deleting with invalid ID."""
        mock_db_client = MagicMock()

        repo = UserRepository(db_client=mock_db_client)

        result = repo.delete_user(0)

        assert result.success is False
        assert "Invalid user ID" in result.error

    def test_delete_user_database_error(self):
        """Test deleting user with database error."""
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_db_client.cursor = mock_cursor

        repo = UserRepository(db_client=mock_db_client)

        result = repo.delete_user(123)

        assert result.success is False
        assert "DB error" in result.error


class TestCredentialsExist:
    """An id counts as taken when a credentials row remains for it."""

    def _repo(self, row):
        mock_db_client = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = row
        mock_db_client.cursor = mock_cursor
        return UserRepository(db_client=mock_db_client), mock_cursor

    def test_reports_existing_credentials(self):
        repo, cursor = self._repo((1,))

        assert repo.credentials_exist(123) is True
        assert "FROM user_credentials" in cursor.execute.call_args.args[0]

    def test_reports_missing_credentials(self):
        repo, _ = self._repo(None)

        assert repo.credentials_exist(123) is False

    def test_database_error_is_not_taken(self):
        repo, _ = self._repo(None)
        repo.db_client.cursor.__enter__.side_effect = Exception("DB error")

        assert repo.credentials_exist(123) is False
