"""Integration fixtures for elasticsearch_indexer_worker.

These tests talk to the same stack as the backend integration suite, so they
need the database (and, for the dump workers, S3) running. Point them at it
with the same environment the backend uses - `entitybase-backend/test.env`
exports exactly that. Without it the tests skip instead of failing.
"""

import os
import pathlib
from typing import Any, Iterator

import pytest

BACKEND_ENV = pathlib.Path(__file__).resolve().parents[2] / "entitybase-backend/test.env"


def _load_env() -> None:
    """Load entitybase-backend/test.env if it exists and nothing is set."""
    if not BACKEND_ENV.exists() or os.getenv("DB_HOST"):
        return
    for line in BACKEND_ENV.read_text().splitlines():
        line = line.strip()
        if not line.startswith("export ") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_env()


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Skip the integration tests unless they are explicitly asked for.

    They need the database (and S3) running, so they only run with
    RUN_INTEGRATION=1, against the same stack as the backend suite.
    """
    if os.getenv("RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(
        reason="needs the stack; run with RUN_INTEGRATION=1"
    )
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture
def db_client() -> Iterator[Any]:
    """A real database client, from the same env the backend uses."""
    from models.infrastructure.db.client import MysqlClient

    client = MysqlClient()
    try:
        yield client
    finally:
        client.disconnect()


@pytest.fixture
def s3_client(db_client: Any) -> Iterator[Any]:
    """A real S3 client, for the workers that write dumps."""
    from models.config.settings import settings
    from models.infrastructure.s3.client import MyS3Client

    client = MyS3Client(config=settings.get_s3_config, db_client=db_client)
    try:
        yield client
    finally:
        client.disconnect()
