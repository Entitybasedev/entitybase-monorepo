"""Unit tests for property datatype validation on entity creation."""

import pytest
from fastapi import HTTPException

from models.data.rest_api.v1.entitybase.request import EntityCreateRequest


class TestPropertyRequiresDatatype:
    """A property without a usable type cannot be created."""

    def test_missing_datatype_is_rejected(self):
        with pytest.raises(HTTPException) as error:
            EntityCreateRequest(type="property")

        assert error.value.status_code == 400
        assert "requires a datatype" in error.value.detail

    @pytest.mark.parametrize("datatype", ["wikibase-item", "string"])
    def test_supported_datatypes_are_accepted(self, datatype):
        request = EntityCreateRequest(type="property", datatype=datatype)

        assert request.datatype == datatype

    def test_unsupported_datatype_is_rejected(self):
        with pytest.raises(HTTPException) as error:
            EntityCreateRequest(type="property", datatype="external-id")

        assert error.value.status_code == 400
        assert "Unsupported datatype" in error.value.detail
        # The message lists what is supported
        assert "wikibase-item" in error.value.detail


class TestOtherTypesRejectDatatype:
    """A datatype only means something for a property."""

    def test_item_with_datatype_is_rejected(self):
        with pytest.raises(HTTPException) as error:
            EntityCreateRequest(type="item", datatype="string")

        assert error.value.status_code == 400
        assert "Only properties have a datatype" in error.value.detail

    def test_item_without_datatype_is_fine(self):
        assert EntityCreateRequest(type="item").datatype == ""

    def test_lexeme_with_datatype_is_rejected(self):
        with pytest.raises(HTTPException) as error:
            EntityCreateRequest(type="lexeme", datatype="wikibase-item")

        assert error.value.status_code == 400
