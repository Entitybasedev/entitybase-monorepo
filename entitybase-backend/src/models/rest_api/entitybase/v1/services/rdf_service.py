"""RDF serialization service."""

from typing import Any

from models.json_parser import parse_entity
from models.rest_api.entitybase.v1.services.normalization import EntityNormalizer
from models.rdf_builder.property_registry.registry import PropertyRegistry


def serialize_entity_to_turtle(
    entity_id: str,
    revision: dict[str, Any],
    s3_client: Any,
    property_registry: PropertyRegistry | None = None,
) -> str:
    """Convert one stored revision to a Turtle document.

    The stored revision keeps terms as content hashes and statements as a flat
    list of hashes, so it cannot be serialized as it stands: RDF needs the text.
    Resolve it first, exactly as the .njson endpoint does, rather than teaching
    the RDF writer about storage.

    The resolved statements are regrouped into Wikibase's `claims` shape
    (property -> statements) because that is what the shared entity parser
    reads. Grouping is lossless here: the parser flattens it straight back out,
    and the property is re-read from each statement's mainsnak anyway.
    """
    from models.rdf_builder.converter import EntityConverter

    document = EntityNormalizer(s3_client).normalize(entity_id, revision)
    claims: dict[str, list[Any]] = {}
    for statement in document.get("statements") or []:
        prop = (statement.get("mainsnak") or {}).get("property", "")
        claims.setdefault(prop, []).append(statement)

    entity = parse_entity({**document, "claims": claims})
    converter = EntityConverter(
        property_registry=property_registry or PropertyRegistry(properties={}),
        enable_deduplication=True,
    )
    return str(converter.convert_to_string(entity))
