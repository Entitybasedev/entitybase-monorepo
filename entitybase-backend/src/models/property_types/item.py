"""The wikibase-item property type: values are entity ids."""

from models.data.infrastructure.s3.enums import PropertyDatatype
from models.property_types.base import PropertyType, ValueKind

ITEM = PropertyType(
    id=PropertyDatatype.WIKIBASE_ITEM,
    label="Item",
    value_kind=ValueKind.ENTITY,
    value_label="Value item",
    value_placeholder="Q5",
)
