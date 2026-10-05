"""The string property type: values are free text."""

from models.data.infrastructure.s3.enums import PropertyDatatype
from models.property_types.base import PropertyType, ValueKind

STRING = PropertyType(
    id=PropertyDatatype.STRING,
    label="String",
    value_kind=ValueKind.TEXT,
    value_label="Value",
    value_placeholder="a short text",
)
