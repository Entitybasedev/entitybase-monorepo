"""Registry of supported property types.

One module per type, listed in PROPERTY_TYPES below. The API serves this
registry, so supporting another property type needs no change outside this
package: add a PropertyDatatype member, add a module, register it here.
"""

from models.data.infrastructure.s3.enums import PropertyDatatype
from models.property_types import item, string
from models.property_types.base import PropertyType, ValueKind

PROPERTY_TYPES: dict[PropertyDatatype, PropertyType] = {
    item.ITEM.id: item.ITEM,
    string.STRING.id: string.STRING,
}


def supported_property_types() -> list[PropertyType]:
    """The property types a property may be created with, in display order."""
    return list(PROPERTY_TYPES.values())


def get_property_type(datatype: str) -> PropertyType:
    """The descriptor for a datatype.

    Raises ValueError for an unsupported datatype, which the request validator
    turns into a 400.
    """
    try:
        return PROPERTY_TYPES[PropertyDatatype(datatype)]
    except (KeyError, ValueError) as e:
        raise ValueError(
            f"Unsupported datatype '{datatype}'. Supported: "
            f"{', '.join(d.value for d in PROPERTY_TYPES)}"
        ) from e


__all__ = [
    "PROPERTY_TYPES",
    "PropertyType",
    "ValueKind",
    "get_property_type",
    "supported_property_types",
]
