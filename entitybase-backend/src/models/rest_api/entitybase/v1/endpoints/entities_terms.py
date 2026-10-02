"""Per-language all-terms endpoint for Entitybase v1 API (label, description, aliases)."""

import logging

from fastapi import APIRouter, HTTPException, Request

from models.data.infrastructure.s3.enums import MetadataType
from models.data.rest_api.v1.entitybase.response import TermsForLanguageResponse
from models.rest_api.entitybase.v1.handlers.entity.read import EntityReadHandler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/entities/{entity_id}/terms/{language_code}",
    response_model=TermsForLanguageResponse,
)
async def get_entity_terms(
    entity_id: str, language_code: str, req: Request
) -> TermsForLanguageResponse:
    """Get the label, description and aliases of an entity for one language."""
    logger.info(f"Getting terms for entity {entity_id}, language {language_code}")
    state = req.app.state.state_handler
    handler = EntityReadHandler(state=state)
    response = handler.get_entity(entity_id)

    hashes = response.entity_data.revision.get("hashes", {})
    label_hash = hashes.get("labels", {}).get(language_code)
    description_hash = hashes.get("descriptions", {}).get(language_code)
    alias_hashes = hashes.get("aliases", {}).get(language_code, [])

    if label_hash is None and description_hash is None and not alias_hashes:
        raise HTTPException(
            status_code=404,
            detail=f"Terms not found for entity {entity_id}, language {language_code}",
        )

    label = ""
    if label_hash is not None:
        label_data = state.s3_client.load_metadata(MetadataType.LABELS, int(label_hash))
        if label_data is not None:
            label = str(label_data.data)

    description = ""
    if description_hash is not None:
        description_data = state.s3_client.load_metadata(
            MetadataType.DESCRIPTIONS, int(description_hash)
        )
        if description_data is not None:
            description = str(description_data.data)

    aliases: list[str] = []
    for alias_hash in alias_hashes:
        alias_data = state.s3_client.load_metadata(
            MetadataType.ALIASES, int(alias_hash)
        )
        if alias_data and alias_data.data:
            aliases.append(str(alias_data.data))

    logger.debug(
        f"Terms for entity {entity_id}/{language_code}: "
        f"label={bool(label)}, description={bool(description)}, "
        f"aliases={len(aliases)}"
    )
    return TermsForLanguageResponse(
        language=language_code,
        label=label,
        description=description,
        aliases=aliases,
    )
