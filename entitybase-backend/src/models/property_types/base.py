"""Property type descriptors.

Each supported property type gets a module here describing how values of that
type are entered and stored, so everything relating to one type can be found by
reading one file. The registry in __init__ maps datatypes to descriptors and is
what the API serves, so adding a type is: add a member to PropertyDatatype, add
a module here, register it.
"""

from enum import Enum

from pydantic import BaseModel, Field

from models.data.infrastructure.s3.enums import PropertyDatatype


class ValueKind(str, Enum):
    """How a value of this property type is supplied."""

    ENTITY = "entity"
    TEXT = "text"


class PropertyType(BaseModel):
    """Everything the API and the UI need to know about one property type."""

    id: PropertyDatatype
    label: str = Field(..., description="Human-readable name, e.g. Item")
    value_kind: ValueKind = Field(
        ..., description="How a value is entered: an entity id, or free text"
    )
    value_label: str = Field(default="Value", description="Label for the value input")
    value_placeholder: str = Field(
        default="", description="Placeholder for the value input, e.g. Q5"
    )
