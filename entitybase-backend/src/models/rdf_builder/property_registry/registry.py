"""Property registry for RDF building."""

from pydantic import BaseModel, ConfigDict

from models.rdf_builder.ontology.datatypes import property_shape
from models.rdf_builder.property_registry.models import PropertyShape


class PropertyRegistry(BaseModel):
    properties: dict[str, PropertyShape]

    model_config = ConfigDict(frozen=True)

    def shape(self, pid: str) -> PropertyShape:
        try:
            return self.properties[pid]
        except KeyError:
            raise KeyError(f"Property {pid} not in registry")

    def shape_or_derived(self, pid: str, datatype: str = "") -> PropertyShape:
        """The shape for a property, derived from the datatype if it is unknown.

        The registry is optional and stays empty unless PROPERTY_REGISTRY_PATH
        points at one, so a strict lookup here would turn every entity with a
        statement into a 500 the moment the property is not in it. Derive the
        shape from the datatype instead: what is lost is the property's own
        label and ontology block, not the statement itself.
        """
        if pid in self.properties:
            return self.properties[pid]
        return property_shape(pid, datatype or "string")