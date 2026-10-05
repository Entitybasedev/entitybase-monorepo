"""Unit tests for the property type registry.

The point of the package is that everything about one property type lives in
one module, so these tests keep it honest: no datatype may exist without a
descriptor, and no descriptor may exist without a datatype.
"""

from models.data.infrastructure.s3.enums import PropertyDatatype
from models.property_types import (
    PROPERTY_TYPES,
    ValueKind,
    get_property_type,
    supported_property_types,
)


class TestRegistry:
    """Every supported datatype is described, and nothing else is."""

    def test_every_datatype_has_a_descriptor(self):
        missing = [d for d in PropertyDatatype if d not in PROPERTY_TYPES]

        assert missing == []

    def test_every_descriptor_has_a_datatype(self):
        unknown = [
            t.id for t in PROPERTY_TYPES.values() if t.id not in PropertyDatatype
        ]

        assert unknown == []

    def test_descriptors_are_unique(self):
        assert len(PROPERTY_TYPES) == len(supported_property_types())

    def test_supported_types_are_the_expected_ones(self):
        ids = [t.id for t in supported_property_types()]

        assert ids == [PropertyDatatype.WIKIBASE_ITEM, PropertyDatatype.STRING]


class TestGetPropertyType:
    """Looking a type up by its wire id."""

    def test_returns_the_descriptor(self):
        descriptor = get_property_type("string")

        assert descriptor.label == "String"
        assert descriptor.value_kind == ValueKind.TEXT

    def test_rejects_an_unsupported_datatype(self):
        import pytest

        with pytest.raises(ValueError, match="Unsupported datatype 'external-id'"):
            get_property_type("external-id")

    def test_rejects_an_empty_datatype(self):
        import pytest

        with pytest.raises(ValueError, match="Unsupported datatype"):
            get_property_type("")


class TestDescriptors:
    """A descriptor carries everything the UI needs to render the type."""

    def test_item_type_is_entity_valued(self):
        descriptor = get_property_type("wikibase-item")

        assert descriptor.value_kind == ValueKind.ENTITY
        assert descriptor.value_placeholder == "Q5"

    def test_every_descriptor_has_a_value_label_and_placeholder(self):
        for descriptor in supported_property_types():
            assert descriptor.value_label
            assert descriptor.value_placeholder
            assert descriptor.label
