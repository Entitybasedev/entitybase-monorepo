"""Unit tests for update_lexeme."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from models.data.common import OperationResult
from models.data.rest_api.v1.entitybase.request.entity.lexeme_update_request import (
    LexemeUpdateRequest,
)
from models.data.rest_api.v1.entitybase.request.headers import EditHeaders
from models.rest_api.entitybase.v1.handlers.entity.update_lexeme import (
    EntityUpdateLexemeMixin,
)

MODULE = "models.rest_api.entitybase.v1.handlers.entity.update_lexeme"


def _mixin_with_state() -> tuple[EntityUpdateLexemeMixin, MagicMock]:
    """Build the mixin with a state whose activity log is synchronous."""
    state = MagicMock()
    state.db_client.entity_exists.return_value = True
    state.db_client.is_entity_deleted.return_value = False
    state.db_client.is_entity_locked.return_value = False
    state.db_client.get_head.return_value = 3
    # The real repository method is synchronous and returns an OperationResult,
    # which cannot be awaited - awaiting it used to fail the whole edit
    state.db_client.user_repository.log_user_activity.return_value = OperationResult(
        success=True, data=1
    )
    return EntityUpdateLexemeMixin(state=state), state


def _update_request() -> LexemeUpdateRequest:
    return LexemeUpdateRequest(
        id="L42",
        type="lexeme",
        lemmas={"en": {"language": "en", "value": "answer"}},
        senses=[],
        forms=[],
    )


def _edit_headers() -> EditHeaders:
    return EditHeaders(**{"X-User-ID": 4242, "X-Edit-Summary": "add sense"})


def _transaction_mock() -> MagicMock:
    tx = MagicMock()
    tx.process_lexeme_terms = MagicMock()
    tx.process_statements = MagicMock(return_value=MagicMock())
    tx.create_revision = AsyncMock(return_value=MagicMock(revision_id=4))
    tx.publish_event = AsyncMock()
    tx.commit = MagicMock()
    tx.rollback = MagicMock()
    return tx


class TestUpdateLexeme:
    """The lexeme update path used by the form and sense endpoints."""

    @pytest.mark.asyncio
    @patch(f"{MODULE}.PreparedRequestData")
    @patch(f"{MODULE}.UpdateTransaction")
    async def test_records_user_activity_without_awaiting_it(
        self, mock_tx_class: MagicMock, mock_prepared: MagicMock
    ) -> None:
        """An edit by a real user is recorded and the edit still succeeds."""
        mixin, state = _mixin_with_state()
        tx = _transaction_mock()
        mock_tx_class.return_value = tx
        mock_prepared.model_validate.side_effect = lambda data: data

        result = await mixin.update_lexeme("L42", _update_request(), _edit_headers())

        state.db_client.user_repository.log_user_activity.assert_called_once()
        assert result.revision_id == 4
        tx.commit.assert_called_once()
        tx.rollback.assert_not_called()

    @pytest.mark.asyncio
    @patch(f"{MODULE}.PreparedRequestData")
    @patch(f"{MODULE}.UpdateTransaction")
    async def test_failed_activity_log_does_not_fail_the_edit(
        self, mock_tx_class: MagicMock, mock_prepared: MagicMock
    ) -> None:
        """A failed activity log is a warning, not a failed edit."""
        mixin, state = _mixin_with_state()
        state.db_client.user_repository.log_user_activity.return_value = (
            OperationResult(success=False, error="DB error")
        )
        mock_tx_class.return_value = _transaction_mock()
        mock_prepared.model_validate.side_effect = lambda data: data

        result = await mixin.update_lexeme("L42", _update_request(), _edit_headers())

        assert result.revision_id == 4

    @pytest.mark.asyncio
    @patch(f"{MODULE}.PreparedRequestData")
    @patch(f"{MODULE}.UpdateTransaction")
    async def test_anonymous_edit_skips_activity_log(
        self, mock_tx_class: MagicMock, mock_prepared: MagicMock
    ) -> None:
        """User id 0 is not an attributed edit, so nothing is logged."""
        mixin, state = _mixin_with_state()
        mock_tx_class.return_value = _transaction_mock()
        mock_prepared.model_validate.side_effect = lambda data: data
        headers = EditHeaders(**{"X-User-ID": 0, "X-Edit-Summary": "import"})

        await mixin.update_lexeme("L42", _update_request(), headers)

        state.db_client.user_repository.log_user_activity.assert_not_called()

    @pytest.mark.asyncio
    @patch(f"{MODULE}.UpdateTransaction")
    async def test_rejects_non_lexeme_id(self, mock_tx_class: MagicMock) -> None:
        """A non-lexeme id is rejected before anything is written."""
        mixin, state = _mixin_with_state()
        mock_tx_class.return_value = _transaction_mock()

        with pytest.raises(HTTPException) as error:
            await mixin.update_lexeme("Q42", _update_request(), _edit_headers())

        assert error.value.status_code == 400
        mock_tx_class.assert_not_called()
