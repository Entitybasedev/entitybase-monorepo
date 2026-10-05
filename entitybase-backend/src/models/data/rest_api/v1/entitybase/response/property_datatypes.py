"""Response models for the supported property types."""

from pydantic import BaseModel, Field

from models.data.infrastructure.s3.enums import PropertyDatatype
from models.property_types.base import ValueKind


class PropertyDatatypeInfo(BaseModel):
    """One property type this wiki supports."""

    id: PropertyDatatype = Field(..., description="Datatype id, e.g. wikibase-item")
    label: str = Field(..., description="Human-readable name, e.g. Item")
    value_kind: ValueKind = Field(
        ..., description="How a value is entered: entity or text"
    )
    value_label: str = Field(..., description="Label for the value input")
    value_placeholder: str = Field(
        default="", description="Placeholder for the value input"
    )


class PropertyDatatypesResponse(BaseModel):
    """The property types a property may be created with."""

    datatypes: list[PropertyDatatypeInfo] = Field(
        ...,
        description=(
            "Supported property types, in the order they should be offered. "
            "The UI renders whatever this returns, so supporting another type "
            "is a backend-only change."
        ),
    )