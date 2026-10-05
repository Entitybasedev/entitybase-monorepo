"""Request model for entity creation."""

from typing import Self

from pydantic import Field, model_validator

from models.data.infrastructure.s3.enums import EditType, EntityType
from models.property_types import get_property_type
from models.rest_api.utils import raise_validation_error
from models.data.rest_api.v1.entitybase.request.entity.entity_request_base import (
    EntityRequestBase,
)


class EntityCreateRequest(EntityRequestBase):
    """Request model for entity creation."""

    type: str = Field(..., description="Entity type (item, property, lexeme)")
    edit_type: EditType = Field(
        default=EditType.UNSPECIFIED,
        description="Classification of edit type",
    )

    @model_validator(mode="after")
    def validate_datatype(self) -> Self:
        """A property is created with a supported datatype; nothing else has one.

        Only creation takes a datatype: an edit keeps the one the property was
        created with, so it is not part of an update payload.
        """
        if self.type == EntityType.PROPERTY.value:
            if not self.datatype:
                raise_validation_error(
                    "A property requires a datatype, e.g. wikibase-item or string",
                    status_code=400,
                )
            try:
                get_property_type(self.datatype)
            except ValueError as e:
                raise_validation_error(str(e), status_code=400)
        elif self.datatype:
            raise_validation_error(
                f"Only properties have a datatype, got type '{self.type}'",
                status_code=400,
            )
        return self
