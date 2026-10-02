"""Mock classes for contract tests.

This module provides mock implementations of MysqlClient, S3Client, and StateHandler
for use in contract tests. These mocks simulate the real clients without requiring
external services (Vitess, S3).
"""

import json
import sys
from typing import Any, Literal
from unittest.mock import MagicMock

sys.path.insert(0, "src")


class MockHistoryEntry:
    def __init__(self, revision_id: int, created_at: str) -> None:
        self.revision_id = revision_id
        self.created_at = created_at


class MockConnectionManager:
    """Mock Vitess connection manager."""

    def __init__(self) -> None:
        self._revision_data_store: dict[int, dict] = {}
        self._cursor = MockCursor(revision_data_store=self._revision_data_store)
        self._connection = MagicMock()
        self._connection.cursor = lambda: self._cursor
    def acquire(self) -> MagicMock:
        return self._connection

    def release(self, connection: Any) -> None:
        pass

    @property
    def healthy_connection(self) -> bool:
        return True


class MockCursor:
    def __init__(
        self,
        revision_data_store: dict[int, dict] | None = None,
        mysql_client: Any = None,
    ) -> None:
        self._rows: list[tuple] = []
        self._revision_data_store = (
            revision_data_store if revision_data_store is not None else {}
        )
        self._mysql_client = mysql_client

    @property
    def cursor(self) -> "MockCursor":
        return self

    def execute(self, query: str, params: Any = None) -> None:
        q = " ".join(query.split())
        # Unknown queries produce no rows (fresh cursor state)
        self._rows = []
        if "INSERT INTO entity_revision_data" in q and params:
            self._revision_data_store[params[0]] = json.loads(params[1])
        elif "SELECT data FROM entity_revision_data" in q and params:
            row = self._revision_data_store.get(params[0])
            self._rows = [(json.dumps(row),)] if row else []
        elif "SELECT 1 FROM entity_revision_data" in q and params:
            self._rows = [(1,)] if params[0] in self._revision_data_store else []
        elif "SELECT content_hash FROM entity_revisions" in q and params:
            content_hash = self._lookup_content_hash(int(params[0]), int(params[1]))
            self._rows = [(content_hash,)] if content_hash else []

    def fetchone(self) -> tuple | None:
        if self._rows:
            return self._rows[0]
        return None

    def fetchall(self) -> list[tuple]:
        return self._rows

    def close(self) -> None:
        pass

    def _lookup_content_hash(self, internal_id: int, revision_id: int) -> int:
        """Resolve (internal_id, revision_id) to the stored content hash.

        Mirrors where MockMysqlClient.create_revision records hashes:
        pending revisions first, then hashes consumed by the S3 mock.
        """
        client = self._mysql_client
        if client is None:
            return 0
        entity_id = client.id_resolver.resolve_entity_id(internal_id)
        if not entity_id:
            return 0
        content_hash = client.get_pending_revisions().get((entity_id, revision_id))
        if content_hash:
            return int(content_hash)
        s3 = client._s3_client
        if s3 is not None:
            return int(s3._revision_hashes.get((entity_id, revision_id), 0))
        return 0

    def __enter__(self) -> "MockCursor":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        return False


class MockIdResolver:
    def __init__(self) -> None:
        self._entity_to_internal: dict[str, int] = {}
        self._internal_to_entity: dict[int, str] = {}
        self._next_internal_id = 1

    def resolve_id(self, entity_id: str) -> int:
        return self._entity_to_internal.get(entity_id, 0)

    def resolve_entity_id(self, internal_id: int) -> str | None:
        return self._internal_to_entity.get(internal_id)

    def entity_exists(self, entity_id: str) -> bool:
        return entity_id in self._entity_to_internal

    def register_entity(self, entity_id: str) -> int:
        if entity_id in self._entity_to_internal:
            return self._entity_to_internal[entity_id]
        internal_id = self._next_internal_id
        self._next_internal_id += 1
        self._entity_to_internal[entity_id] = internal_id
        self._internal_to_entity[internal_id] = entity_id
        return internal_id


class MockUserRepository:
    def __init__(self) -> None:
        self._registered: set[int] = set()
        self._ui_preferences: dict[int, dict] = {}
        self._credentials: dict[str, dict] = {}
        self._activities: list[dict] = []
        self._next_activity_id = 1

    def user_exists(self, user_id: int) -> bool:
        return user_id in self._registered

    def create_user(self, user_id: int) -> Any:
        self._registered.add(user_id)
        result = MagicMock()
        result.success = True
        result.error = None
        return result

    def log_user_activity(
        self,
        user_id: int,
        activity_type: Any,
        entity_id: str,
        revision_id: int = 0,
        change_type: Any = None,
        edit_summary: str = "",
    ) -> Any:
        """Record an activity row for the recent-changes endpoint."""
        entry = {
            "id": self._next_activity_id,
            "user_id": user_id,
            "activity_type": getattr(activity_type, "value", str(activity_type)),
            "change_type": getattr(change_type, "value", "") or "",
            "entity_id": entity_id,
            "revision_id": revision_id,
            "edit_summary": edit_summary,
            "created_at": "2026-01-01T00:00:00Z",
        }
        self._next_activity_id += 1
        self._activities.append(entry)
        result = MagicMock()
        result.success = True
        result.error = None
        return result

    def get_recent_changes(
        self,
        limit: int = 50,
        offset: int = 0,
        change_type: Any = None,
        exclude_imports: bool = False,
    ) -> list[dict]:
        rows = self._activities
        if change_type is not None:
            wanted = getattr(change_type, "value", change_type)
            rows = [row for row in rows if row["change_type"] == wanted]
        elif exclude_imports:
            rows = [row for row in rows if row["change_type"] != "entity_import"]
        # Newest first (id descending), then paginate
        ordered = sorted(rows, key=lambda row: row["id"], reverse=True)
        return ordered[offset : offset + limit]

    def get_ui_preferences(self, user_id: int) -> dict | None:
        return self._ui_preferences.get(user_id)

    def set_ui_preferences(self, user_id: int, preferences: dict) -> bool:
        self._ui_preferences[user_id] = preferences
        return True

    def create_credentials(
        self, user_id: int, username: str, password_hash: str
    ) -> Any:
        self._credentials[username] = {
            "user_id": user_id,
            "password_hash": password_hash,
        }
        result = MagicMock()
        result.success = True
        result.error = None
        return result

    def get_credentials_by_username(self, username: str) -> dict | None:
        return self._credentials.get(username)

    def get_next_user_id(self) -> int:
        if self._registered:
            return max(self._registered) + 1
        return 90001

    def list_users(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """List users with usernames, paginated by user ID."""
        ids = sorted(self._registered)
        page = ids[offset : offset + limit]
        username_by_user = {
            cred["user_id"]: name for name, cred in self._credentials.items()
        }
        return [
            {
                "user_id": uid,
                "username": username_by_user.get(uid, ""),
                "created_at": "",
                "last_activity": "",
            }
            for uid in page
        ]

    def is_watchlist_enabled(self, user_id: int) -> bool:
        return False

    def update_user_activity(self, user_id: int) -> MagicMock:
        result = MagicMock()
        result.success = True
        return result


class MockWatchlistRepository:
    def get_watches_for_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> MagicMock:
        result = MagicMock()
        result.success = True
        result.watches = []
        return result


class MockEntityRepository:
    def __init__(self, db_client: Any) -> None:
        self.db_client = db_client

    def list_entities_filtered(
        self,
        filter_request: Any,
    ) -> list[Any]:
        """Filter registered entities by type prefix, paginated."""
        prefix = {
            "item": "Q",
            "property": "P",
            "lexeme": "L",
            "entityschema": "E",
        }.get(getattr(filter_request, "entity_type", "") or "", "")

        registered = sorted(self.db_client.id_resolver._entity_to_internal, reverse=True)
        if prefix:
            registered = [eid for eid in registered if eid.startswith(prefix)]

        offset = filter_request.offset
        limit = filter_request.limit
        page = registered[offset : offset + limit]

        from models.data.rest_api.v1.entitybase.response import EntityListItem

        return [
            EntityListItem(
                entity_id=eid,
                head_revision_id=self.db_client.get_head(eid),
            )
            for eid in page
        ]

    def create_entity(self, entity_id: str) -> None:
        self.db_client.id_resolver.register_entity(entity_id)

    def delete_entity(self, entity_id: str) -> None:
        pass

    def delete(self, entity_id: str, revision_id: int) -> None:
        pass


class MockRevisionRepository:
    def get_revision(self, entity_id: int, revision_id: int) -> MagicMock | None:
        return None


class MockHeadRepository:
    def get_head_revision(self, entity_id: int) -> MagicMock | None:
        return None


class MockStatementRepository:
    def get_most_used(self, limit: int = 100) -> list[int]:
        return []


class MockMysqlClient:
    def __init__(self) -> None:
        self.id_resolver = MockIdResolver()
        self.connection_manager = MockConnectionManager()
        self.user_repository = MockUserRepository()
        self.watchlist_repository = MockWatchlistRepository()
        self.entity_repository = MockEntityRepository(db_client=self)
        self.revision_repository = MockRevisionRepository()
        self.head_repository = MockHeadRepository()
        self.statement_repository = MockStatementRepository()
        self._revision_data_store: dict[int, dict] = {}
        self._cursor = MockCursor(
            revision_data_store=self._revision_data_store, mysql_client=self
        )
        self._s3_client: Any = None
        self._pending_revisions: dict[tuple[str, int], int] = {}
        self._revisions: dict[str, list[int]] = {}

    def set_s3_client(self, s3_client: Any) -> None:
        self._s3_client = s3_client

    @property
    def cursor(self) -> "MockCursor":
        return self._cursor

    @property
    def healthy_connection(self) -> bool:
        return True

    def entity_exists(self, entity_id: str) -> bool:
        return self.id_resolver.entity_exists(entity_id)

    def register_entity(self, entity_id: str) -> None:
        self.id_resolver.register_entity(entity_id)

    def is_entity_deleted(self, entity_id: str) -> bool:
        return False

    def is_entity_locked(self, entity_id: str) -> bool:
        return False

    def get_head(self, entity_id: str) -> int:
        revisions = self._revisions.get(entity_id, [])
        return max(revisions) if revisions else 0

    def get_history(self, entity_id: str) -> list[Any]:
        return (
            [MockHistoryEntry(revision_id=1, created_at="2024-01-01T00:00:00Z")]
            if self.entity_exists(entity_id)
            else []
        )

    def get_entity_history(
        self, entity_id: str, limit: int = 20, offset: int = 0
    ) -> list[Any]:
        return self.get_history(entity_id)

    def get_backlinks(
        self, internal_id: int, limit: int = 100, offset: int = 0
    ) -> list[MagicMock]:
        return []

    def disconnect(self) -> None:
        pass

    def create_revision(
        self,
        entity_id: str,
        entity_data: Any,
        revision_id: int,
        content_hash: int,
        expected_revision_id: int = 0,
    ) -> bool:
        current_head = self.get_head(entity_id)
        # Mirror the real repository: expected_revision_id 0 skips the CAS check
        if expected_revision_id and current_head != expected_revision_id:
            return False
        self._pending_revisions[(entity_id, revision_id)] = content_hash
        if entity_id not in self._revisions:
            self._revisions[entity_id] = []
        self._revisions[entity_id].append(revision_id)
        return True

    def get_pending_revisions(self) -> dict[tuple[str, int], int]:
        return self._pending_revisions.copy()

    def clear_pending_revisions(self) -> None:
        self._pending_revisions.clear()

    def decrement_ref_count(self, hash_val: int) -> None:
        pass

    def get_ref_count(self, hash_val: int) -> int:
        return 0

    def delete_revision(self, entity_id: str, revision_id: int) -> None:
        pass


class MockS3ConnectionManager:
    @property
    def healthy_connection(self) -> bool:
        return True


class MockS3Client:
    def __init__(self) -> None:
        self.connection_manager = MockS3ConnectionManager()
        self._revisions: dict[int, dict[str, Any]] = {}
        self._revision_hashes: dict[tuple[str, int], int] = {}
        self._db_client: Any = None
        self._term_metadata: dict[int, tuple[str, str]] = {}  # hash -> (value, type)

    def set_db_client(self, db_client: Any) -> None:
        self._db_client = db_client

    @property
    def healthy_connection(self) -> bool:
        return True

    def read_revision(self, entity_id: str, revision_id: int) -> MagicMock:
        from models.data.infrastructure.s3 import S3RevisionData

        mock_revision = MagicMock(spec=S3RevisionData)
        default_revision: dict[str, Any] = {
            "revision_id": revision_id,
            "entity_type": "item",
            "type": "item",
            "id": entity_id,
            "edit": {
                "type": "manual-create",
                "user_id": 0,
                "summary": "test",
                "at": "2023-01-01T12:00:00Z",
            },
            "hashes": {
                "labels": {},
                "descriptions": {},
                "aliases": {},
                "sitelinks": {},
                "statements": [],
            },
            "labels_hashes": {},
            "descriptions_hashes": {},
            "aliases_hashes": {},
            "labels": {},
            "descriptions": {},
            "aliases": {},
            "statements": {},
            "sitelinks": {},
            "properties": [],
            "property_counts": {},
            "state": {
                "is_semi_protected": False,
                "is_locked": False,
                "is_archived": False,
                "is_dangling": False,
                "is_mass_edit_protected": False,
            },
        }
        key = (entity_id, revision_id)
        if key in self._revision_hashes:
            content_hash = self._revision_hashes[key]
            if content_hash in self._revisions:
                mock_revision.revision = self._revisions[content_hash].get(
                    "revision", {}
                )
            else:
                mock_revision.revision = default_revision
        else:
            mock_revision.revision = default_revision
        return mock_revision

    def read_full_revision(self, entity_id: str, revision_id: int) -> MagicMock:
        return self.read_revision(entity_id, revision_id)

    def disconnect(self) -> None:
        pass

    def store_revision(self, content_hash: int, revision_data: Any) -> None:
        self._revisions[content_hash] = (
            revision_data.model_dump(mode="json")
            if hasattr(revision_data, "model_dump")
            else revision_data
        )
        if self._db_client:
            pending_revisions = self._db_client.get_pending_revisions()
            for (entity_id, revision_id), hash_val in pending_revisions.items():
                self._revision_hashes[(entity_id, revision_id)] = hash_val
            self._db_client.clear_pending_revisions()

    def delete_statement(self, hash_val: int) -> None:
        pass

    def store_term_metadata(
        self, term: str, content_hash: int, content_type: str = "labels"
    ) -> None:
        self._term_metadata[content_hash] = (term, content_type)

    def store_sitelink_metadata(self, title: str, hash_value: int) -> None:
        self._term_metadata[hash_value] = (title, "sitelink")

    def load_metadata(self, metadata_type: str, content_hash: int) -> Any:
        if content_hash in self._term_metadata:
            value, _ = self._term_metadata[content_hash]
            from models.data.infrastructure.s3.load_response import StringLoadResponse

            return StringLoadResponse(data=value)
        return None


class MockValidator:
    """Mock validator for contract tests."""

    pass


def create_test_state_handler() -> "TestStateHandler":
    """Factory function to create a TestStateHandler instance."""
    return TestStateHandler()


class TestStateHandler:
    """Test StateHandler that uses mock clients.

    This class mimics the StateHandler interface but uses pre-configured
    mock clients instead of real Vitess/S3 connections.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self) -> None:
        self._db_client = MockMysqlClient()
        self._s3_client = MockS3Client()
        self._db_client.set_s3_client(self._s3_client)
        self._s3_client.set_db_client(self._db_client)
        self._validator = MockValidator()
        self._settings = MagicMock()
        self._mysql_config = MagicMock()
        self.cached_db_client: MockMysqlClient | None = None
        self.cached_s3_client: MockS3Client | None = None
        self.cached_enumeration_service: Any = None
        self.entity_change_stream_producer = None
        self.user_change_stream_producer = None
        self.entitydiff_stream_producer = None

    @property
    def settings(self) -> Any:
        return self._settings

    @property
    def db_client(self) -> MockMysqlClient:
        if self.cached_db_client is None:
            self.cached_db_client = self._db_client
        return self.cached_db_client

    @property
    def s3_client(self) -> MockS3Client:
        if self.cached_s3_client is None:
            self.cached_s3_client = self._s3_client
        return self.cached_s3_client

    @property
    def validator(self) -> Any:
        return self._validator

    @property
    def mysql_config(self) -> Any:
        return self._mysql_config

    def read_revision_data(self, entity_id: str, revision_id: int) -> Any:
        """Mimic StateHandler.read_revision_data using mock storage."""
        from models.data.infrastructure.s3 import S3RevisionData

        content_hash = self._db_client._pending_revisions.get(
            (entity_id, revision_id)
        ) or self._s3_client._revision_hashes.get((entity_id, revision_id))
        if content_hash is not None and content_hash in (
            self._db_client._revision_data_store
        ):
            return S3RevisionData.model_validate(
                self._db_client._revision_data_store[content_hash]
            )

        revision = self._s3_client.read_revision(entity_id, revision_id)
        return S3RevisionData.model_validate(
            {
                "schema": "1.0.0",
                "revision": revision.revision,
                "hash": 123456789,
                "created_at": "2023-01-01T12:00:00Z",
            }
        )

    @property
    def enumeration_service(self) -> Any:
        if self.cached_enumeration_service is None:
            from models.rest_api.entitybase.v1.services.enumeration_service import (
                EnumerationService,
            )

            class MockEnumerationServiceClass(EnumerationService):
                """Mock EnumerationService that inherits from real class."""

                _entity_counters: dict[str, int] = {}

                def __init__(self, **data: Any) -> None:
                    super().__init__(**data)
                    self._mock_mode = True

                def get_next_id(self, entity_type: str) -> int:
                    return 1

                def get_next_entity_id(self, entity_type: str) -> str:
                    """Get the next available entity ID for the given entity type."""
                    type_mapping = {
                        "item": "Q",
                        "property": "P",
                        "lexeme": "L",
                        "entityschema": "E",
                    }
                    if entity_type not in type_mapping:
                        from models.rest_api.utils import raise_validation_error

                        raise_validation_error(
                            f"Unsupported entity type: {entity_type}"
                        )
                    counter_key = f"{entity_type}_counter"
                    if counter_key not in self._entity_counters:
                        self._entity_counters[counter_key] = 1
                    entity_num = self._entity_counters[counter_key]
                    self._entity_counters[counter_key] += 1
                    return f"{type_mapping[entity_type]}{entity_num}"

                @property
                def range_manager(self) -> Any:
                    return MagicMock()

            self.cached_enumeration_service = MockEnumerationServiceClass(
                worker_id="test", db_client=self._db_client
            )
        return self.cached_enumeration_service

    def disconnect(self) -> None:
        if self._db_client:
            self._db_client.disconnect()
        if self._s3_client:
            self._s3_client.disconnect()
