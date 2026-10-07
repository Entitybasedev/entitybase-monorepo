"""Incremental RDF worker for processing entity changes and generating RDF diffs."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional, cast

from pydantic import Field
from rdflib import Graph

from models.config.settings import settings
from models.data.infrastructure.stream.consumer import EntityChangeEventData
from models.infrastructure.stream.consumer import StreamConsumerClient
from models.infrastructure.stream.producer import StreamProducerClient
from models.infrastructure.db.client import MysqlClient
from models.infrastructure.s3.client import MyS3Client
from models.rest_api.entitybase.v1.services.rdf_service import (
    serialize_entity_to_turtle,
)
from models.workers.worker import Worker
from incremental_rdf_worker.rdf_change_builder import (
    EventConfig,
    RDFChangeEventBuilder,
)

logger = logging.getLogger(__name__)


class IncrementalRDFWorker(Worker):
    """Worker that consumes entity change events and generates incremental RDF diffs.

    This worker:
    1. Consumes entity change events from entitybase.entity_change Kafka topic
    2. Looks up revision metadata in MySQL to get content hashes
    3. Fetches the stored revision for both the old and the new revision
    4. Serializes both revisions to Turtle and diffs the triples
    5. Publishes RDF change events to incremental_rdf_diff Kafka topic
    """

    db_client: Optional[MysqlClient] = Field(default=None, exclude=True)
    # Resolves the content hashes a stored revision points at. Built with the
    # database client so it falls back to the database for content when no
    # object store is configured, which is how the stack runs.
    content_client: Optional[Any] = Field(default=None, exclude=True)
    consumer: Optional[StreamConsumerClient] = Field(default=None, exclude=True)
    producer: Optional[StreamProducerClient] = Field(default=None, exclude=True)
    worker_enabled: bool = Field(default=False, exclude=True)

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup/shutdown."""
        try:
            if not self.worker_enabled:
                logger.info("IncrementalRDFWorker disabled by configuration")
                yield
                return

            logger.info("Starting IncrementalRDFWorker")

            await self._initialize_clients()

            logger.info("IncrementalRDFWorker started successfully")

            yield
        except Exception as e:
            logger.error(f"Failed to start IncrementalRDFWorker: {e}")
            raise
        finally:
            await self._cleanup_clients()
            logger.info("IncrementalRDFWorker stopped")

    async def _initialize_clients(self) -> None:
        """Initialize Kafka consumer, producer and database clients."""
        kafka_brokers = self._get_kafka_brokers()

        if kafka_brokers:
            await self._initialize_kafka(kafka_brokers)
        else:
            logger.warning(
                "Kafka not configured, worker will not be able to consume/produce events"
            )

        await self._initialize_storage_clients()

    def _get_kafka_brokers(self) -> list[str]:
        """Get Kafka brokers from settings."""
        if not settings.kafka_bootstrap_servers:
            return []
        return [
            b.strip() for b in settings.kafka_bootstrap_servers.split(",") if b.strip()
        ]

    async def _initialize_kafka(self, kafka_brokers: list[str]) -> None:
        """Initialize Kafka consumer and producer."""
        from models.data.config.stream_consumer import StreamConsumerConfig

        consumer_config = StreamConsumerConfig(
            brokers=kafka_brokers,
            topic=settings.kafka_entitychange_json_topic,
            group_id=settings.incremental_rdf_consumer_group,
        )
        self.consumer = StreamConsumerClient(config=consumer_config)
        await self.consumer.start()
        logger.info(
            f"Kafka consumer started: topic={settings.kafka_entitychange_json_topic}, "
            f"group={settings.incremental_rdf_consumer_group}"
        )

        producer_config = settings.get_incremental_rdf_stream_config
        self.producer = StreamProducerClient(config=producer_config)
        await self.producer.start()
        logger.info(
            f"Kafka producer started: topic={settings.kafka_incremental_rdf_topic}"
        )

    async def _initialize_storage_clients(self) -> None:
        """Initialize the database client and the content client.

        Both are needed. The database holds the revision document and, when no
        object store is configured, the deduplicated content it points at; the
        content client is what turns the hashes in a revision back into text.
        """
        if not self.worker_enabled:
            return

        mysql_config = settings.get_mysql_config
        if mysql_config.host and mysql_config.port:
            self.db_client = MysqlClient(config=mysql_config)
            logger.info("Database client initialized")
        else:
            logger.warning(
                "Database not configured, worker cannot fetch revision metadata"
            )
            return

        try:
            # db_client is what lets content resolve from the database when
            # there is no object store. Without it every hash is unresolvable
            # and the worker emits empty diffs.
            self.content_client = MyS3Client(
                config=settings.get_s3_config, db_client=self.db_client
            )
            logger.info("Content client initialized")
        except Exception as e:
            logger.warning(f"Content client unavailable: {e}")

    async def _cleanup_clients(self) -> None:
        """Clean up all clients."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        if self.db_client and self.db_client.connection_manager:
            self.db_client.connection_manager.disconnect()
        logger.debug("All clients cleaned up")

    async def run(self) -> None:
        """Run the consumer loop."""
        if not self.consumer:
            logger.warning("Consumer not started, cannot run")
            return

        try:
            async for event in self.consumer.consume_events():
                await self.process_message(event)
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            raise

    async def process_message(self, message: EntityChangeEventData) -> None:
        """Process a single entity change event message."""
        try:
            entity_id = message.entity_id
            revision_id = message.revision_id
            from_revision_id = message.from_revision_id
            change_type = message.change_type

            if not entity_id or not revision_id:
                logger.warning(
                    f"Invalid event message: missing required fields {message}"
                )
                return

            logger.info(
                f"Processing {change_type} event for {entity_id}: "
                f"rev {revision_id} (from_rev: {from_revision_id})"
            )

            await self._process_entity_change(
                entity_id=entity_id,
                to_revision_id=revision_id,
                from_revision_id=from_revision_id,
                change_type=change_type,
            )

        except Exception as e:
            logger.error(f"Error processing message {message}: {e}")

    async def _process_entity_change(
        self,
        entity_id: str,
        to_revision_id: int,
        from_revision_id: Optional[int],
        change_type: str,
    ) -> None:
        """Process an entity change and generate RDF diff."""
        if change_type == "delete":
            await self._handle_entity_deletion(entity_id, to_revision_id)
            return

        old_entity_data = await self._fetch_previous_entity_data(
            entity_id, from_revision_id
        )
        new_entity_data = await self._fetch_entity_data(entity_id, to_revision_id)

        operation, rdf_added, rdf_removed = self._compute_diff_and_rdf(
            entity_id, old_entity_data, new_entity_data
        )
        await self._publish_rdf_change_event(
            entity_id, to_revision_id, operation, rdf_added, rdf_removed
        )

    async def _fetch_previous_entity_data(
        self, entity_id: str, from_revision_id: Optional[int]
    ) -> Optional[dict[str, Any]]:
        """Fetch previous entity data if a from_revision_id is provided."""
        if from_revision_id and from_revision_id > 0:
            return await self._fetch_entity_data(entity_id, from_revision_id)
        return None

    def _compute_diff_and_rdf(
        self,
        entity_id: str,
        old_entity_data: Optional[dict],
        new_entity_data: Optional[dict],
    ) -> tuple[str, str, str]:
        """Return the operation, the triples to add and the triples to remove.

        A creation has nothing to compare against, so its payload is the whole
        entity. It used to be an empty string, which is why every creation on
        the stream carried no RDF at all.
        """
        if new_entity_data is None:
            return "import", "", ""

        new_triples = self._revision_triples(entity_id, new_entity_data)

        if old_entity_data is None:
            return "import", self._to_turtle(new_triples), ""

        old_triples = self._revision_triples(entity_id, old_entity_data)
        added = new_triples - old_triples
        removed = old_triples - new_triples
        return "diff", self._to_turtle(added), self._to_turtle(removed)

    def _revision_triples(self, entity_id: str, revision: dict[str, Any]) -> set[str]:
        """The triples one stored revision describes.

        The revision keeps its terms as content hashes, so it is serialized by
        the same path the .ttl endpoint uses: the hashes are resolved and the
        result is real RDF. Reading the revision's fields directly produced
        nothing, because it has no `entity` key and its labels are numbers.
        """
        if self.content_client is None:
            logger.warning("No content client; cannot resolve revision hashes")
            return set()

        turtle = serialize_entity_to_turtle(entity_id, revision, self.content_client)
        return self._parse_triples(turtle)

    @staticmethod
    def _parse_triples(turtle: str) -> set[str]:
        """Read a Turtle document into N-Triples lines.

        Diffing needs a comparable form: the two revisions are written
        independently, so their prefixes and formatting differ even where the
        triples are identical. N-Triples lines are canonical, so equal triples
        compare equal.
        """
        if not turtle.strip():
            return set()
        try:
            graph = Graph()
            graph.parse(data=turtle, format="turtle")
            return {
                line
                for line in graph.serialize(format="nt").splitlines()
                if line.strip()
            }
        except Exception as e:
            logger.warning(f"Could not parse Turtle: {e}")
            return set()

    @staticmethod
    def _to_turtle(triples: set[str]) -> str:
        """Render N-Triples lines as a Turtle document."""
        if not triples:
            return ""
        return "\n".join(sorted(triples)) + "\n"

    async def _publish_rdf_change_event(
        self,
        entity_id: str,
        rev_id: int,
        operation: str,
        rdf_added: str,
        rdf_removed: str = "",
    ) -> None:
        """Publish RDF change event to Kafka."""
        event_config = EventConfig(
            entity_id=entity_id,
            rev_id=rev_id,
            operation=operation,
            rdf_added_data=rdf_added,
            rdf_deleted_data=rdf_removed,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        event_data = RDFChangeEventBuilder.build(event_config)

        if self.producer:
            await self.producer.publish(event_data)
            logger.info(f"Published RDF change event for {entity_id} rev {rev_id}")

    async def _fetch_entity_data(
        self, entity_id: str, revision_id: int
    ) -> Optional[dict[str, Any]]:
        """Fetch entity data for a given revision from MariaDB."""
        if not self.db_client:
            logger.error("DB client not initialized")
            return None

        try:
            from models.infrastructure.db.repositories.revision import RevisionRepository
            from models.infrastructure.db.repositories.revision_data import RevisionDataRepository
            from models.data.infrastructure.s3.revision_data import S3RevisionData

            internal_id = self.db_client.id_resolver.resolve_id(entity_id)  # type: ignore[union-attr]
            if not internal_id:
                return None

            revision_repo = RevisionRepository(db_client=self.db_client)
            content_hash = revision_repo.get_content_hash(internal_id, revision_id)
            if content_hash == 0:
                return None

            data_repo = RevisionDataRepository(db_client=self.db_client)
            data = data_repo.load(content_hash)
            if data is None:
                return None

            revision = S3RevisionData.model_validate(data)
            return cast("dict[str, Any] | None", revision.revision)
        except Exception as e:
            logger.error(
                f"Failed to fetch entity data for {entity_id} rev {revision_id}: {e}"
            )
            return None

    async def _handle_entity_deletion(self, entity_id: str, revision_id: int) -> None:
        """Handle entity deletion by publishing a delete event."""
        event_config = EventConfig(
            entity_id=entity_id,
            rev_id=revision_id,
            operation="delete",
            rdf_added_data="",
            rdf_deleted_data="",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        event_data = RDFChangeEventBuilder.build(event_config)

        if self.producer:
            await self.producer.publish(event_data)
            logger.info(f"Published delete event for {entity_id}")


async def main() -> None:
    """Main entry point for the IncrementalRDFWorker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    worker = IncrementalRDFWorker(
        worker_id=f"incremental-rdf-{id(main)}",
        worker_enabled=settings.incremental_rdf_enabled,
    )

    async with worker.lifespan():
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
