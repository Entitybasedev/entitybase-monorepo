"""Property creation endpoints for Entitybase v1 API."""

import logging

from fastapi import APIRouter, Request

from models.data.common import OperationResult
from models.data.infrastructure.s3.enums import EntityType
from models.data.rest_api.v1.entitybase.request import EntityCreateRequest
from models.data.rest_api.v1.entitybase.request.headers import EditHeadersType
from models.data.rest_api.v1.entitybase.response import (
    EntityIdResult,
    PropertyDatatypeInfo,
    PropertyDatatypesResponse,
)
from models.property_types import supported_property_types
from models.rest_api.entitybase.v1.handlers.entity.property import PropertyCreateHandler
from models.rest_api.utils import raise_validation_error

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/property-datatypes", response_model=PropertyDatatypesResponse)
async def list_property_datatypes() -> PropertyDatatypesResponse:
    """List the property types a property can be created with.

    The UI builds its type picker and its per-type value inputs from this, so
    adding a supported type needs no frontend change.
    """
    return PropertyDatatypesResponse(
        datatypes=[
            PropertyDatatypeInfo(
                id=property_type.id,
                label=property_type.label,
                value_kind=property_type.value_kind,
                value_label=property_type.value_label,
                value_placeholder=property_type.value_placeholder,
            )
            for property_type in supported_property_types()
        ]
    )


@router.post("/entities/properties", response_model=OperationResult[EntityIdResult])
async def create_property(
    request: EntityCreateRequest,
    req: Request,
    headers: EditHeadersType,
) -> OperationResult[EntityIdResult]:
    """Create a new property entity.

    The body carries the datatype and the label; the type is always property.
    """
    logger.info("🔍 ENDPOINT: Received POST request to create property")

    if request.type != EntityType.PROPERTY.value:
        raise_validation_error(
            f"This endpoint creates properties, got type '{request.type}'",
            status_code=400,
        )

    try:
        state = req.app.state.state_handler
        validator = req.app.state.state_handler.validator
        enumeration_service = req.app.state.state_handler.enumeration_service

        entity_request = request.model_copy(update={"type": EntityType.PROPERTY.value})

        handler = PropertyCreateHandler(
            state=state, enumeration_service=enumeration_service
        )
        logger.debug("🔍 ENDPOINT: Handler created, calling create_entity")

        result = await handler.create_entity(
            entity_request, edit_headers=headers, validator=validator
        )
        logger.info(f"🔍 ENDPOINT: Property creation successful: {result.id}")

        return OperationResult(
            success=True,
            data=EntityIdResult(entity_id=result.id, revision_id=result.revision_id),
        )

    except Exception as e:
        logger.error(f"🔍 ENDPOINT: Create property failed: {e}", exc_info=True)
        raise
