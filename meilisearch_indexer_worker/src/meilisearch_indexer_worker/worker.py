"""Meilisearch indexer worker.

Keeps the Meilisearch entity index in step with the database: it consumes
entity change events, rebuilds the search document of the changed entity from
its stored revision and indexes it (or removes it, when the entity is gone).

The worker reads the revision and its terms straight from MariaDB - it never
calls the API.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from pydantic import Field

from models.config.settings import settings
from models.data.infrastructure.meilisearch import MeilisearchDocument
from models.data.infrastructure.s3.enums import MetadataType
from models.data.infrastructure.stream.consumer import EntityChangeEventData
from models.data.rest_api.v1.entitybase.response import WorkerHealthCheckResponse
from models.infrastructure.db.client import MysqlClient
from models.infrastructure.db.repositories.revision import RevisionRepository
from models.infrastructure.db.repositories.revision_data import RevisionDataRepository
from models.infrastructure.s3.client import MyS3Client
from models.infrastructure.stream.consumer import StreamConsumerClient
from models.services.meilisearch import (
    MeilisearchClient,
    RevisionRef,
    build_document,
    entity_type_from_id,
)
from models.workers.worker import Worker

logger = logging.getLogger(__name__)

ENTITY_TYPES = ["item", "property", "lexeme"]
HEALTH_PORT = 8009

# How long to wait before reconnecting to the entity change stream
CONSUMER_RETRY_SECONDS = 5

# Change types that mean the entity is gone and must leave the index
DELETE_CHANGE_TYPES = ["soft_delete", "hard_delete"]


class MeilisearchIndexerWorker(Worker):
    """Indexes entity changes into Meilisearch."""

    db_client: Any = Field(default=None, exclude=True)
    s3_client: Any = Field(default=None, exclude=True)
    revision_repository: Any = Field(default=None, exclude=True)
    revision_data_repository: Any = Field(default=None, exclude=True)
    consumer: Any = Field(default=None, exclude=True)
    search_client: Any = Field(default=None, exclude=True)
    reindex_on_start: bool = Field(default=False)
    indexed_count: int = 0

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None, None]:
        """Set up the database and Meilisearch clients for the worker lifespan."""
        logger.info("Initializing Meilisearch indexer worker")

        self.db_client = MysqlClient(config=settings.get_mysql_config)
        self.s3_client = MyS3Client(
            config=settings.get_s3_config, db_client=self.db_client
        )
        self.revision_repository = RevisionRepository(db_client=self.db_client)
        self.revision_data_repository = RevisionDataRepository(db_client=self.db_client)

        self.search_client = MeilisearchClient(
            host=settings.meilisearch_host,
            port=settings.meilisearch_port,
            api_key=settings.meilisearch_api_key,
            index_name=settings.meilisearch_index,
        )
        if not self.search_client.connect():
            raise RuntimeError(
                f"Could not connect to Meilisearch at {self.search_client.url}"
            )

        yield

        await self.cleanup()
        logger.info("Meilisearch indexer worker stopped")

    async def cleanup(self) -> None:
        """Close the consumer and the Meilisearch connection."""
        if self.consumer is not None:
            await self.consumer.stop()
            self.consumer = None
        if self.search_client is not None:
            self.search_client.close()
        if self.db_client is not None and self.db_client.connection_manager:
            self.db_client.connection_manager.disconnect()

    async def start(self) -> None:
        """Index everything that exists, then follow the change stream."""
        if not settings.meilisearch_enabled:
            logger.info("Meilisearch indexer worker disabled by configuration")
            return

        logger.info(f"Starting Meilisearch indexer worker {self.worker_id}")

        async with self.lifespan():
            self.running = True

            if self.reindex_on_start:
                await self.reindex_all()

            await self.start_consumer()
            try:
                await self.run()
            finally:
                self.running = False

    async def start_consumer(self) -> None:
        """Subscribe to the entity change topic."""
        brokers = [
            broker.strip()
            for broker in (settings.kafka_bootstrap_servers or "").split(",")
            if broker.strip()
        ]
        if not brokers:
            raise RuntimeError("No Kafka brokers configured")

        from models.data.config.stream_consumer import StreamConsumerConfig

        self.consumer = StreamConsumerClient(
            config=StreamConsumerConfig(
                brokers=brokers,
                topic=settings.kafka_entitychange_json_topic,
                group_id=settings.meilisearch_consumer_group,
            )
        )
        await self.consumer.start()
        logger.info(
            f"Consuming {settings.kafka_entitychange_json_topic} as {settings.meilisearch_consumer_group}"
        )

    async def run(self) -> None:
        """Consume entity changes and index them, until stopped.

        The stream is the worker's lifeline: if consuming breaks, the worker
        reconnects and carries on instead of sitting there healthy but blind.
        """
        if self.consumer is None:
            logger.warning("No consumer, nothing to do")
            return

        while self.running:
            try:
                async for event in self.consumer.consume_events():
                    await self.process_message(event)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Entity change stream broke, retrying: {e}")
                await asyncio.sleep(CONSUMER_RETRY_SECONDS)

    async def process_message(self, message: EntityChangeEventData) -> None:
        """Index or remove one entity, based on the change it describes."""
        try:
            entity_id = message.entity_id
            if not entity_id:
                logger.warning(f"Skipping event without an entity ID: {message}")
                return

            if message.change_type in DELETE_CHANGE_TYPES:
                self.delete_entity(entity_id)
                return

            self.index_entity(entity_id, message.revision_id)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # One bad event must not cost us the rest of the stream
            logger.error(f"Could not handle {message}: {e}")

    def index_entity(self, entity_id: str, revision_id: int = 0) -> bool:
        """Index one entity from its stored revision.

        Args:
            entity_id: the entity ID, e.g. Q42.
            revision_id: the revision to index; the head revision when 0.

        Returns:
            True when the entity is now indexed.
        """
        document = self.build_entity_document(entity_id, revision_id)
        if document is None:
            return False

        if self.search_client.index_document(entity_id, document):
            self.indexed_count += 1
            logger.info(f"Indexed {entity_id} (revision {document.lastrevid})")
            return True
        return False

    def delete_entity(self, entity_id: str) -> bool:
        """Remove one entity from the index."""
        if self.search_client.delete_document(entity_id):
            logger.info(f"Removed {entity_id} from the index")
            return True
        return False

    def build_entity_document(
        self, entity_id: str, revision_id: int = 0
    ) -> MeilisearchDocument | None:
        """Build the search document of an entity from the database.

        Args:
            entity_id: the entity ID, e.g. Q42.
            revision_id: the revision to read; the head revision when 0.

        Returns:
            The document, or None when the entity or its revision is gone.
        """
        try:
            if revision_id == 0:
                revision_id = self.db_client.get_head(entity_id)
            if revision_id == 0:
                logger.debug(f"{entity_id} has no head revision, skipping")
                return None

            internal_id = self.db_client.id_resolver.resolve_id(entity_id)
            if not internal_id:
                logger.debug(f"{entity_id} does not exist, skipping")
                return None

            content_hash = self.revisions.get_content_hash(internal_id, revision_id)
            if content_hash == 0:
                logger.debug(f"No revision data for {entity_id}, skipping")
                return None

            revision_data = self.revision_data.load(content_hash)
            if revision_data is None:
                logger.debug(f"Revision {revision_id} of {entity_id} is gone, skipping")
                return None

            document = build_document(
                RevisionRef(
                    entity_id=entity_id,
                    entity_type=entity_type_from_id(entity_id),
                    lastrevid=revision_id,
                    modified=revision_data.get("created_at", ""),
                ),
                revision_data.get("revision", {}),
                self.load_term,
            )
            return document
        except Exception as e:
            logger.error(f"Could not build the search document for {entity_id}: {e}")
            return None

    @property
    def revisions(self) -> RevisionRepository:
        """The revision repository, built on first use."""
        if self.revision_repository is None:
            self.revision_repository = RevisionRepository(db_client=self.db_client)
        return self.revision_repository

    @property
    def revision_data(self) -> RevisionDataRepository:
        """The revision data repository, built on first use."""
        if self.revision_data_repository is None:
            self.revision_data_repository = RevisionDataRepository(
                db_client=self.db_client
            )
        return self.revision_data_repository

    def load_term(self, metadata_type: MetadataType, content_hash: int) -> str | None:
        """Load the text of one content-addressed term."""
        metadata = self.s3_client.load_metadata(metadata_type, content_hash)
        if metadata is None:
            return None
        return str(metadata.data)

    async def reindex_all(self, batch_size: int = 500) -> int:
        """Index every entity that exists, whatever its revision.

        The index starts empty, so entities created before the worker was
        running would otherwise stay invisible to search.

        Returns:
            How many entities were indexed.
        """
        logger.info("Reindexing all entities into Meilisearch")
        indexed = 0

        for entity_type in ENTITY_TYPES:
            offset = 0
            while True:
                entity_ids = self.db_client.list_entities_by_type(
                    entity_type, limit=batch_size, offset=offset
                )
                if not entity_ids:
                    break
                for entity_id in entity_ids:
                    if self.index_entity(entity_id):
                        indexed += 1
                offset += len(entity_ids)

        logger.info(f"Reindexed {indexed} entities")
        return indexed

    def health_check(self) -> WorkerHealthCheckResponse:
        """Report whether the worker is running."""
        return WorkerHealthCheckResponse(
            status="healthy" if self.running else "starting",
            worker_id=self.worker_id,
            range_status={},
        )


async def run_server(app: Any) -> None:
    """Serve the worker health endpoint."""
    import uvicorn

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("WORKER_PORT", str(HEALTH_PORT))),
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    """Run the indexer worker and its health endpoint."""
    logging.basicConfig(
        level=settings.get_log_level(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    from fastapi import FastAPI

    worker = MeilisearchIndexerWorker(
        worker_id="meilisearch-indexer",
        reindex_on_start=(
            os.getenv("MEILISEARCH_REINDEX_ON_START", "false").lower() == "true"
        ),
    )

    app = FastAPI(response_model_by_alias=True)

    @app.get("/health")
    def health() -> WorkerHealthCheckResponse:
        return worker.health_check()

    await asyncio.gather(run_server(app), worker.start())


if __name__ == "__main__":
    asyncio.run(main())