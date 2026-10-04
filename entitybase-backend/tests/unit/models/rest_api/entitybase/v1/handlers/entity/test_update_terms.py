"""Unit tests for EntityUpdateTermsMixin."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from models.rest_api.entitybase.v1.handlers.entity.update_terms import (
    EntityUpdateTermsMixin,
)


class TestEntityUpdateTermsMixin:
    """Unit tests for EntityUpdateTermsMixin._decrement_term_ref_count."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_vitess, mock_s3_client

    @patch("models.rest_api.entitybase.v1.handlers.entity.update_terms.TermsRepository")
    def test_decrement_term_ref_count_handles_none_data(
        self, mock_terms_repo_class
    ) -> None:
        """Test handling when result.data is None - treats as orphaned (deletes)."""
        mixin, mock_vitess, mock_s3 = self._create_mixin_with_mocks()

        mock_terms_repo = MagicMock()
        mock_terms_repo_class.return_value = mock_terms_repo
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = None
        mock_terms_repo.decrement_ref_count.return_value = mock_result

        mixin._decrement_term_ref_count(12345)

        mock_terms_repo.decrement_ref_count.assert_called_once_with(12345)

    @patch("models.rest_api.entitybase.v1.handlers.entity.update_terms.TermsRepository")
    def test_decrement_term_ref_count_deletes_when_zero(
        self, mock_terms_repo_class
    ) -> None:
        """Test that term is Vitess and S3 deleted when ref_count hits 0."""
        mixin, mock_vitess, mock_s3 = self._create_mixin_with_mocks()

        mock_terms_repo = MagicMock()
        mock_terms_repo_class.return_value = mock_terms_repo
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = 0
        mock_terms_repo.decrement_ref_count.return_value = mock_result

        mixin._decrement_term_ref_count(12345)

        mock_terms_repo.decrement_ref_count.assert_called_once_with(12345)
        mock_terms_repo.delete_term.assert_called_once_with(12345)
        mock_s3.delete_metadata.assert_called()

    @patch("models.rest_api.entitybase.v1.handlers.entity.update_terms.TermsRepository")
    def test_decrement_term_ref_count_handles_failure(
        self, mock_terms_repo_class
    ) -> None:
        """Test graceful failure handling when decrement fails."""
        mixin, mock_vitess, mock_s3 = self._create_mixin_with_mocks()

        mock_terms_repo = MagicMock()
        mock_terms_repo_class.return_value = mock_terms_repo
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "DB error"
        mock_terms_repo.decrement_ref_count.return_value = mock_result

        mixin._decrement_term_ref_count(12345)

        mock_terms_repo.decrement_ref_count.assert_called_once_with(12345)
        mock_terms_repo.delete_term.assert_not_called()
        mock_s3.delete_metadata.assert_not_called()

    @patch("models.rest_api.entitybase.v1.handlers.entity.update_terms.TermsRepository")
    def test_decrement_term_ref_count_deletes_all_metadata_types(
        self, mock_terms_repo_class
    ) -> None:
        """Test that all three metadata types are cleaned up when ref_count hits 0."""
        mixin, mock_vitess, mock_s3 = self._create_mixin_with_mocks()

        mock_terms_repo = MagicMock()
        mock_terms_repo_class.return_value = mock_terms_repo
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = 0
        mock_terms_repo.decrement_ref_count.return_value = mock_result

        mixin._decrement_term_ref_count(12345)

        assert mock_s3.delete_metadata.call_count == 3


class TestUpdateLabelErrors:
    """Unit tests for EntityUpdateTermsMixin.update_label error handling."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_state

    @pytest.mark.asyncio
    async def test_update_label_language_mismatch(self) -> None:
        """Test that language mismatch between request and path raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.entity.context import (
            TermUpdateContext,
        )
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        context = TermUpdateContext(language="en", language_code="de", value="Test")
        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.update_label("Q1", context, edit_headers)

        assert exc_info.value.status_code == 400
        assert "does not match" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_label_invalid_entity_id(self) -> None:
        """Test that invalid entity ID raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.entity.context import (
            TermUpdateContext,
        )
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        context = TermUpdateContext(language="en", language_code="en", value="Test")
        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.update_label("invalid", context, edit_headers)

        assert exc_info.value.status_code == 400
        assert "Invalid entity ID format" in exc_info.value.detail


class TestDeleteLabelErrors:
    """Unit tests for EntityUpdateTermsMixin.delete_label error handling."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_state

    @pytest.mark.asyncio
    async def test_delete_label_invalid_entity_id(self) -> None:
        """Test that invalid entity ID raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_label("invalid", "en", edit_headers)

        assert exc_info.value.status_code == 400
        assert "Invalid entity ID format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_label_entity_deleted(self) -> None:
        """Test that deleting label on deleted entity raises 410."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_label("Q1", "en", edit_headers)

        assert exc_info.value.status_code == 410
        assert "Entity deleted" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_label_entity_locked(self) -> None:
        """Test that deleting label on locked entity raises 423."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = False
        mock_state.db_client.is_entity_locked.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_label("Q1", "en", edit_headers)

        assert exc_info.value.status_code == 423
        assert "Entity locked" in exc_info.value.detail


class TestUpdateDescriptionErrors:
    """Unit tests for EntityUpdateTermsMixin.update_description error handling."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_state

    @pytest.mark.asyncio
    async def test_update_description_language_mismatch(self) -> None:
        """Test that language mismatch between request and path raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.entity.context import (
            TermUpdateContext,
        )
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        context = TermUpdateContext(language="en", language_code="de", value="Test")
        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.update_description("Q1", context, edit_headers)

        assert exc_info.value.status_code == 400
        assert "does not match" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_description_invalid_entity_id(self) -> None:
        """Test that invalid entity ID raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.entity.context import (
            TermUpdateContext,
        )
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        context = TermUpdateContext(language="en", language_code="en", value="Test")
        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.update_description("invalid", context, edit_headers)

        assert exc_info.value.status_code == 400
        assert "Invalid entity ID format" in exc_info.value.detail


class TestDeleteDescriptionErrors:
    """Unit tests for EntityUpdateTermsMixin.delete_description error handling."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_state

    @pytest.mark.asyncio
    async def test_delete_description_invalid_entity_id(self) -> None:
        """Test that invalid entity ID raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_description("invalid", "en", edit_headers)

        assert exc_info.value.status_code == 400
        assert "Invalid entity ID format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_description_entity_deleted(self) -> None:
        """Test that deleting description on deleted entity raises 410."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_description("Q1", "en", edit_headers)

        assert exc_info.value.status_code == 410
        assert "Entity deleted" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_description_entity_locked(self) -> None:
        """Test that deleting description on locked entity raises 423."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = False
        mock_state.db_client.is_entity_locked.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_description("Q1", "en", edit_headers)

        assert exc_info.value.status_code == 423
        assert "Entity locked" in exc_info.value.detail


class TestUpdateAliasesErrors:
    """Unit tests for EntityUpdateTermsMixin.update_aliases error handling."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_state

    @pytest.mark.asyncio
    async def test_update_aliases_invalid_entity_id(self) -> None:
        """Test that invalid entity ID raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.update_aliases("invalid", "en", ["alias"], edit_headers)

        assert exc_info.value.status_code == 400
        assert "Invalid entity ID format" in exc_info.value.detail


class TestAddAliasErrors:
    """Unit tests for EntityUpdateTermsMixin.add_alias error handling."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_state

    @pytest.mark.asyncio
    async def test_add_alias_invalid_entity_id(self) -> None:
        """Test that invalid entity ID raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.add_alias("invalid", "en", "alias", edit_headers)

        assert exc_info.value.status_code == 400
        assert "Invalid entity ID format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_add_alias_entity_deleted(self) -> None:
        """Test that adding alias to deleted entity raises 410."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.add_alias("Q1", "en", "alias", edit_headers)

        assert exc_info.value.status_code == 410
        assert "Entity deleted" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_add_alias_entity_locked(self) -> None:
        """Test that adding alias to locked entity raises 423."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = False
        mock_state.db_client.is_entity_locked.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.add_alias("Q1", "en", "alias", edit_headers)

        assert exc_info.value.status_code == 423
        assert "Entity locked" in exc_info.value.detail


class TestDeleteAliasesErrors:
    """Unit tests for EntityUpdateTermsMixin.delete_aliases error handling."""

    def _create_mixin_with_mocks(self):
        """Create a mixin with mocked dependencies."""
        mock_state = MagicMock()
        mock_vitess = MagicMock()
        mock_state.db_client = mock_vitess

        mock_s3_client = MagicMock()
        mock_state.s3_client = mock_s3_client

        mixin = EntityUpdateTermsMixin(state=mock_state)

        return mixin, mock_state

    @pytest.mark.asyncio
    async def test_delete_aliases_invalid_entity_id(self) -> None:
        """Test that invalid entity ID raises 400."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_aliases("invalid", "en", edit_headers)

        assert exc_info.value.status_code == 400
        assert "Invalid entity ID format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_aliases_entity_deleted(self) -> None:
        """Test that deleting aliases on deleted entity raises 410."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_aliases("Q1", "en", edit_headers)

        assert exc_info.value.status_code == 410
        assert "Entity deleted" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_aliases_entity_locked(self) -> None:
        """Test that deleting aliases on locked entity raises 423."""
        from fastapi import HTTPException
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders

        mixin, mock_state = self._create_mixin_with_mocks()
        mock_state.db_client.is_entity_deleted.return_value = False
        mock_state.db_client.is_entity_locked.return_value = True

        edit_headers = EditHeaders(x_edit_summary="test", x_user_id="0")

        with pytest.raises(HTTPException) as exc_info:
            await mixin.delete_aliases("Q1", "en", edit_headers)

        assert exc_info.value.status_code == 423
        assert "Entity locked" in exc_info.value.detail


class TestTermTransactionsRecordUserActivity:
    """Term transactions log user activity synchronously and must not await it.

    ``UserRepository.log_user_activity`` returns an OperationResult from a plain
    method, so awaiting it raises a TypeError after the revision is written and
    the endpoint answers 500 while the edit is actually saved.
    """

    def _setup(self, transaction_method: str):
        """Build the mixin plus a mocked UpdateTransaction for one helper."""
        from models.data.common import OperationResult
        from models.data.infrastructure.s3.enums import EntityType
        from models.data.rest_api.v1.entitybase.request import EntityChangeType
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders
        from models.rest_api.entitybase.v1.handlers.entity.update_terms import (
            TermTransactionContext,
        )

        mock_state = MagicMock()
        mock_state.db_client.get_head.return_value = 2
        mock_state.db_client.user_repository.log_user_activity.return_value = (
            OperationResult(success=True, data=1)
        )
        mixin = EntityUpdateTermsMixin(state=mock_state)

        tx = MagicMock()
        tx.create_revision_with_hashes = AsyncMock(
            return_value=MagicMock(revision_id=5)
        )
        tx.publish_event = AsyncMock()

        context = TermTransactionContext(
            entity_id="Q1",
            entity_type=EntityType.ITEM,
            updated_hashes={},
            existing_revision={},
            edit_headers=EditHeaders(x_edit_summary="test", x_user_id=4242),
        )
        helper = getattr(mixin, transaction_method)
        return helper, context, mock_state, tx

    @pytest.mark.asyncio
    async def test_term_delete_transaction_records_activity(self) -> None:
        """Deleting a term as a user logs the activity and commits."""
        helper, context, mock_state, tx = self._setup(
            "_execute_term_delete_transaction"
        )
        with patch(
            "models.rest_api.entitybase.v1.handlers.entity.update_transaction."
            "UpdateTransaction",
            return_value=tx,
        ):
            response = await helper(context)

        mock_state.db_client.user_repository.log_user_activity.assert_called_once()
        assert response.revision_id == 5
        tx.commit.assert_called_once()
        tx.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_term_add_transaction_records_activity(self) -> None:
        """Adding a term as a user logs the activity and commits."""
        helper, context, mock_state, tx = self._setup("_execute_term_add_transaction")
        with patch(
            "models.rest_api.entitybase.v1.handlers.entity.update_transaction."
            "UpdateTransaction",
            return_value=tx,
        ):
            response = await helper(context)

        mock_state.db_client.user_repository.log_user_activity.assert_called_once()
        assert response.revision_id == 5
        tx.commit.assert_called_once()
        tx.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_activity_log_does_not_fail_the_transaction(self) -> None:
        """A failed activity log is logged as a warning, not raised."""
        from models.data.common import OperationResult

        helper, context, mock_state, tx = self._setup(
            "_execute_term_delete_transaction"
        )
        mock_state.db_client.user_repository.log_user_activity.return_value = (
            OperationResult(success=False, error="DB error")
        )
        with patch(
            "models.rest_api.entitybase.v1.handlers.entity.update_transaction."
            "UpdateTransaction",
            return_value=tx,
        ):
            response = await helper(context)

        assert response.revision_id == 5

    @pytest.mark.asyncio
    async def test_anonymous_term_edit_skips_activity_log(self) -> None:
        """User id 0 is not an attributed edit, so nothing is logged."""
        from models.data.infrastructure.s3.enums import EntityType
        from models.data.rest_api.v1.entitybase.request.headers import EditHeaders
        from models.rest_api.entitybase.v1.handlers.entity.update_terms import (
            TermTransactionContext,
        )

        mock_state = MagicMock()
        mock_state.db_client.get_head.return_value = 2
        mixin = EntityUpdateTermsMixin(state=mock_state)
        tx = MagicMock()
        tx.create_revision_with_hashes = AsyncMock(
            return_value=MagicMock(revision_id=5)
        )
        tx.publish_event = AsyncMock()
        context = TermTransactionContext(
            entity_id="Q1",
            entity_type=EntityType.ITEM,
            updated_hashes={},
            existing_revision={},
            edit_headers=EditHeaders(x_edit_summary="test", x_user_id=0),
        )

        with patch(
            "models.rest_api.entitybase.v1.handlers.entity.update_transaction."
            "UpdateTransaction",
            return_value=tx,
        ):
            await mixin._execute_term_delete_transaction(context)

        mock_state.db_client.user_repository.log_user_activity.assert_not_called()
