"""General entity operations for Wikibase v1 API."""

from fastapi import APIRouter, HTTPException

from models.rest_api.entitybase.response import EntitiesResponse
from models.rest_api.entitybase.response import StatementsResponse

router = APIRouter()


@router.get("/entities")
async def get_entities() -> EntitiesResponse:
    """Search entities - stub"""
    raise HTTPException(status_code=501, detail="Not implemented")


# Statements


@router.get("/statements")
async def get_statements() -> StatementsResponse:
    """Get statements - stub"""
    raise HTTPException(status_code=501, detail="Not implemented")
