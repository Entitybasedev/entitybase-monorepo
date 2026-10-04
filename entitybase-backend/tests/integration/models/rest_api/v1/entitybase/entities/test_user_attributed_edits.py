"""Integration tests for edits made by an attributed (logged-in) user.

Endpoints that record user activity call
``UserRepository.log_user_activity``, which is synchronous. These tests all
send a non-zero ``X-User-ID`` so that code path is actually taken: the edit
must succeed and return the updated entity, not fail halfway through with a
500 after the revision was already written.
"""

import logging
import sys

sys.path.insert(0, "src")

import pytest
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)

USER_ID = "4242"


async def create_lexeme(client: AsyncClient) -> str:
    """Create a lexeme and return its ID."""
    response = await client.post(
        "/v1/entities/lexemes",
        json={
            "type": "lexeme",
            "language": "Q1860",
            "lexicalCategory": "Q1084",
            "lemmas": {"en": {"language": "en", "value": "answer"}},
        },
        headers={"X-Edit-Summary": "create", "X-User-ID": USER_ID},
    )
    assert response.status_code == 200
    return str(response.json()["id"])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_sense_as_user() -> None:
    """Adding a sense as a user stores the sense instead of failing."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        lexeme_id = await create_lexeme(client)

        response = await client.post(
            f"/v1/entities/lexemes/{lexeme_id}/senses",
            json={"glosses": {"en": {"language": "en", "value": "a gloss"}}},
            headers={"X-Edit-Summary": "add sense", "X-User-ID": USER_ID},
        )
        assert response.status_code == 200

        senses = await client.get(f"/v1/entities/lexemes/{lexeme_id}/senses")
        assert senses.status_code == 200
        assert [s["glosses"]["en"]["value"] for s in senses.json()["senses"]] == [
            "a gloss"
        ]
        logger.info("✓ POST sense as user passed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_form_as_user() -> None:
    """Adding a form as a user stores the form instead of failing."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        lexeme_id = await create_lexeme(client)

        response = await client.post(
            f"/v1/entities/lexemes/{lexeme_id}/forms",
            json={
                "representations": {"en": {"language": "en", "value": "answers"}},
                "grammaticalFeatures": ["Q110786"],
            },
            headers={"X-Edit-Summary": "add form", "X-User-ID": USER_ID},
        )
        assert response.status_code == 200

        forms = await client.get(f"/v1/entities/lexemes/{lexeme_id}/forms")
        assert forms.status_code == 200
        stored = forms.json()["forms"][0]
        assert stored["representations"]["en"]["value"] == "answers"
        assert stored["grammaticalFeatures"] == ["Q110786"]
        logger.info("✓ POST form as user passed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_label_as_user() -> None:
    """Deleting a label as a user removes it instead of failing."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/v1/entities/items",
            headers={"X-Edit-Summary": "create", "X-User-ID": USER_ID},
        )
        assert create_response.status_code == 200
        entity_id = create_response.json()["data"]["entity_id"]

        added = await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "A label"},
            headers={"X-Edit-Summary": "add label", "X-User-ID": USER_ID},
        )
        assert added.status_code == 200

        response = await client.delete(
            f"/v1/entities/{entity_id}/labels/en",
            headers={"X-Edit-Summary": "delete label", "X-User-ID": USER_ID},
        )
        assert response.status_code == 200

        remaining = await client.get(f"/v1/entities/{entity_id}/labels/en")
        assert remaining.status_code == 404
        logger.info("✓ DELETE label as user passed")