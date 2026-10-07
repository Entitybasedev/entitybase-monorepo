"""Unit tests for incremental_rdf_worker and rdf_change_builder."""

import re
from pathlib import Path

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from models.config.settings import settings
from models.data.infrastructure.stream.consumer import EntityChangeEventData
from incremental_rdf_worker.rdf_change_builder import (
    EventConfig,
    eventstreams_timestamp,
    RDFChangeEvent,
    RDFChangeEventBuilder,
    RDFDataField,
)
from incremental_rdf_worker.worker import (
    IncrementalRDFWorker,
)


class TestIncrementalRDFWorker:
    """Unit tests for IncrementalRDFWorker class."""

    def test_worker_initialization(self):
        """Test worker initialization."""
        worker = IncrementalRDFWorker(worker_id="test-worker", worker_enabled=False)
        assert worker.worker_id == "test-worker"
        assert worker.worker_enabled is False
        assert worker.db_client is None
        assert worker.consumer is None
        assert worker.producer is None

    def test_no_s3_client(self):
        """The worker holds no S3 client: it never reads object storage.

        It used to, assigned and never used, and initialising it failed on a
        config field that does not exist - which stopped the worker starting at
        all. Asserting the field is gone keeps it from creeping back.
        """
        worker = IncrementalRDFWorker(worker_id="test-worker", worker_enabled=False)
        assert not hasattr(worker, "s3_client")

    def test_get_kafka_brokers_empty(self):
        """Test getting kafka brokers when not configured."""
        with patch(
            "incremental_rdf_worker.worker.settings"
        ) as mock_settings:
            mock_settings.kafka_bootstrap_servers = None
            worker = IncrementalRDFWorker(worker_enabled=False)
            brokers = worker._get_kafka_brokers()
            assert brokers == []

    def test_get_kafka_brokers_with_servers(self):
        """Test getting kafka brokers when configured."""
        with patch(
            "incremental_rdf_worker.worker.settings"
        ) as mock_settings:
            mock_settings.kafka_bootstrap_servers = "broker1:9092, broker2:9092"
            worker = IncrementalRDFWorker(worker_enabled=False)
            brokers = worker._get_kafka_brokers()
            assert brokers == ["broker1:9092", "broker2:9092"]

    @pytest.mark.asyncio
    async def test_lifespan_disabled_worker(self):
        """Test lifespan when worker is disabled."""
        worker = IncrementalRDFWorker(worker_enabled=False)
        async with worker.lifespan():
            pass

    @pytest.mark.asyncio
    async def test_process_message_invalid_no_entity_id(self):
        """Test processing message with missing entity_id."""
        worker = IncrementalRDFWorker(worker_enabled=False)
        message = EntityChangeEventData(
            id="",
            rev=123,
            from_rev=None,
            type="update",
            at="2024-01-01T00:00:00Z",
            user="test",
            summary="test",
        )
        await worker.process_message(message)

    @pytest.mark.asyncio
    async def test_process_message_invalid_no_revision_id(self):
        """Test processing message with missing revision_id."""
        worker = IncrementalRDFWorker(worker_enabled=False)
        message = EntityChangeEventData(
            id="Q42",
            rev=0,
            from_rev=None,
            type="update",
            at="2024-01-01T00:00:00Z",
            user="test",
            summary="test",
        )
        await worker.process_message(message)

    @pytest.mark.asyncio
    async def test_published_event_carries_the_rdf(self):
        """The published event must contain the RDF the diff produced.

        End to end through process_message, because the pieces were tested
        apart: the diff was right and the event was still empty, which is the
        same empty graph as never having computed a diff at all.
        """
        worker = self._worker_with_content()
        worker.producer = MagicMock()
        worker.producer.publish = AsyncMock()
        worker._fetch_previous_entity_data = AsyncMock(return_value=None)
        worker._fetch_entity_data = AsyncMock(
            return_value={"id": "Q42", "hashes": {"labels": {"en": 1}}}
        )
        turtle = (
            "<http://wikiba.se/ontology#Q42> "
            "<http://www.w3.org/2000/01/rdf-schema#label> \"Test\" .\n"
        )

        with patch(
            "incremental_rdf_worker.worker.serialize_entity_to_turtle",
            return_value=turtle,
        ):
            await worker.process_message(
                EntityChangeEventData(
                    id="Q42",
                    rev=123,
                    from_rev=None,
                    type="update",
                    at="2024-01-01T00:00:00Z",
                    user="test",
                    summary="test",
                )
            )

        worker.producer.publish.assert_awaited_once()
        published = worker.producer.publish.await_args[0][0]
        assert "Q42" in published.rdf_added_data.data
        assert "Test" in published.rdf_added_data.data
        assert published.rdf_added_data.mime_type == "text/turtle"
        assert published.rdf_deleted_data is None

    @pytest.mark.asyncio
    async def test_published_event_carries_removals(self):
        """A statement that went away has to be published as a removal.

        Publishing only additions would leave the old triples in the graph
        forever, with no way for a consumer to know they were meant to go.
        """
        worker = self._worker_with_content()
        worker.producer = MagicMock()
        worker.producer.publish = AsyncMock()
        worker._fetch_previous_entity_data = AsyncMock(return_value=None)
        worker._fetch_entity_data = AsyncMock(
            return_value={"id": "Q42", "revision_id": 2}
        )
        turtle_by_revision = {
            1: (
                "<http://wikiba.se/ontology#Q42> "
                "<http://www.w3.org/2000/01/rdf-schema#label> \"Old\" .\n"
            ),
            2: (
                "<http://wikiba.se/ontology#Q42> "
                "<http://www.w3.org/2000/01/rdf-schema#label> \"New\" .\n"
            ),
        }
        worker._fetch_previous_entity_data = AsyncMock(
            return_value={"id": "Q42", "revision_id": 1}
        )

        with patch(
            "incremental_rdf_worker.worker.serialize_entity_to_turtle",
            side_effect=lambda _id, revision, _client, *a, **kw: (
                turtle_by_revision[revision["revision_id"]]
            ),
        ):
            await worker.process_message(
                EntityChangeEventData(
                    id="Q42",
                    rev=2,
                    from_rev=1,
                    type="update",
                    at="2024-01-01T00:00:00Z",
                    user="test",
                    summary="test",
                )
            )

        published = worker.producer.publish.await_args[0][0]
        assert '"New"' in published.rdf_added_data.data
        assert '"Old"' in published.rdf_deleted_data.data

    @pytest.mark.asyncio
    async def test_process_message_delete(self):
        """Test processing delete message."""
        worker = IncrementalRDFWorker(worker_enabled=False)
        worker.producer = MagicMock()
        worker.producer.publish = AsyncMock()

        message = EntityChangeEventData(
            id="Q42",
            rev=123,
            from_rev=None,
            type="delete",
            at="2024-01-01T00:00:00Z",
            user="test",
            summary="test",
        )
        await worker.process_message(message)

        worker.producer.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_no_consumer(self):
        """Test run when consumer is not initialized."""
        worker = IncrementalRDFWorker(worker_enabled=False)
        await worker.run()

    @staticmethod
    def _worker_with_content():
        """A worker whose serializer is stubbed out per test.

        The content client only has to be present: _revision_triples checks it
        before serializing, and the serializer is patched, so anything will do.
        """
        worker = IncrementalRDFWorker(worker_enabled=False)
        worker.content_client = object()
        return worker

    def test_creation_publishes_the_whole_entity(self):
        """A creation has nothing to compare against, so it carries everything.

        It used to carry an empty string, so every creation on the stream said
        an entity had arrived and then described none of it - which is how the
        graph stayed empty while the stream looked busy.
        """
        worker = self._worker_with_content()
        turtle = (
            "<http://wikiba.se/ontology#Q42> "
            "<http://www.w3.org/2000/01/rdf-schema#label> \"Test\" .\n"
        )
        with patch(
            "incremental_rdf_worker.worker.serialize_entity_to_turtle",
            return_value=turtle,
        ):
            operation, added, removed = worker._compute_diff_and_rdf(
                "Q42", None, {"id": "Q42", "hashes": {"labels": {"en": 1}}}
            )
        assert operation == "import"
        assert "Q42" in added
        assert "Test" in added
        assert removed == ""

    def test_edit_publishes_only_what_changed(self):
        """An edit publishes the triples that differ, in both directions.

        Publishing the whole new entity would be wrong: it cannot express a
        removal, and QLever would never learn that a statement went away.
        """
        worker = self._worker_with_content()
        old = (
            "<http://wikiba.se/ontology#Q42> "
            "<http://www.w3.org/2000/01/rdf-schema#label> \"Old\" .\n"
        )
        new = (
            "<http://wikiba.se/ontology#Q42> "
            "<http://www.w3.org/2000/01/rdf-schema#label> \"New\" .\n"
        )
        # Keyed on the revision rather than returned in order, so the test
        # states which revision is which instead of relying on which one the
        # diff happens to serialize first.
        turtle_by_revision = {1: old, 2: new}
        with patch(
            "incremental_rdf_worker.worker.serialize_entity_to_turtle",
            side_effect=lambda _id, revision, _client, *a, **kw: (
                turtle_by_revision[revision["revision_id"]]
            ),
        ):
            operation, added, removed = worker._compute_diff_and_rdf(
                "Q42",
                {"id": "Q42", "revision_id": 1},
                {"id": "Q42", "revision_id": 2},
            )
        assert operation == "diff"
        assert '"New"' in added and '"Old"' not in added
        assert '"Old"' in removed and '"New"' not in removed

    def test_unchanged_revision_produces_no_triples(self):
        """Reindexing the same revision changes nothing, and says so.

        Rather than republishing the whole entity as if it were an edit.
        """
        worker = self._worker_with_content()
        turtle = (
            "<http://wikiba.se/ontology#Q42> "
            "<http://www.w3.org/2000/01/rdf-schema#label> \"Same\" .\n"
        )
        with patch(
            "incremental_rdf_worker.worker.serialize_entity_to_turtle",
            side_effect=[turtle, turtle],
        ):
            _, added, removed = worker._compute_diff_and_rdf(
                "Q42", {"id": "Q42", "revision_id": 1}, {"id": "Q42", "revision_id": 2}
            )
        assert added == ""
        assert removed == ""

    def test_formatting_differences_are_not_changes(self):
        """Two spellings of the same triples are the same triples.

        The revisions are serialized independently, so prefixes and whitespace
        differ between them even when nothing about the entity changed. Diffing
        the raw text would report every entity as edited on every revision.
        """
        worker = self._worker_with_content()
        spelled_one = (
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            "<http://wikiba.se/ontology#Q42> rdfs:label \"Same\" .\n"
        )
        spelled_two = (
            "<http://wikiba.se/ontology#Q42> "
            "<http://www.w3.org/2000/01/rdf-schema#label>   \"Same\"  .\n"
        )
        turtle_by_revision = {1: spelled_one, 2: spelled_two}
        with patch(
            "incremental_rdf_worker.worker.serialize_entity_to_turtle",
            side_effect=lambda _id, revision, _client, *a, **kw: (
                turtle_by_revision[revision["revision_id"]]
            ),
        ):
            _, added, removed = worker._compute_diff_and_rdf(
                "Q42", {"id": "Q42", "revision_id": 1}, {"id": "Q42", "revision_id": 2}
            )
        assert added == ""
        assert removed == ""

    def test_unresolvable_hashes_publish_nothing_rather_than_guessing(self):
        """Without a content client the hashes cannot be read, so nothing is sent.

        An empty payload is a claim that the entity has no RDF. Guessing at one
        would put triples in the graph that no revision ever described.
        """
        worker = IncrementalRDFWorker(worker_enabled=False)
        assert worker.content_client is None
        operation, added, removed = worker._compute_diff_and_rdf(
            "Q42", None, {"id": "Q42", "hashes": {"labels": {"en": 1}}}
        )
        assert operation == "import"
        assert added == ""
        assert removed == ""

    def test_missing_new_revision_publishes_nothing(self):
        """A change whose new revision cannot be read publishes no RDF."""
        worker = IncrementalRDFWorker(worker_enabled=False)
        operation, added, removed = worker._compute_diff_and_rdf(
            "Q42", {"id": "Q42"}, None
        )
        assert operation == "import"
        assert added == ""
        assert removed == ""


class TestRDFDataField:
    """Test RDFDataField model."""

    def test_rdf_data_field_creation(self):
        """Test creating an RDFDataField."""
        field = RDFDataField(data="<test> a <test> .")
        assert field.data == "<test> a <test> ."
        assert field.mime_type == "text/turtle"

    def test_rdf_data_field_custom_mime_type(self):
        """Test creating an RDFDataField with custom mime type."""
        field = RDFDataField(data="<test>", mime_type="application/ld+json")
        assert field.data == "<test>"
        assert field.mime_type == "application/ld+json"


class TestRDFChangeEvent:
    """Test RDFChangeEvent model."""

    def test_rdf_change_event_diff_operation(self):
        """Test creating an RDFChangeEvent for diff operation."""
        event = RDFChangeEvent(
            dt="2024-01-01T00:00:00Z",
            entity_id="Q42",
            meta={"domain": "wikidata.org", "stream": "test"},
            operation="diff",
            rev_id=123,
            rdf_added_data=RDFDataField(data="<added>"),
            rdf_deleted_data=RDFDataField(data="<removed>"),
            sequence=0,
            sequence_length=1,
        )
        assert event.entity_id == "Q42"
        assert event.operation == "diff"
        assert event.rev_id == 123
        assert event.rdf_added_data is not None
        assert event.rdf_deleted_data is not None

    def test_rdf_change_event_import_operation(self):
        """Test creating an RDFChangeEvent for import operation."""
        event = RDFChangeEvent(
            dt="2024-01-01T00:00:00Z",
            entity_id="Q42",
            meta={"domain": "wikidata.org", "stream": "test"},
            operation="import",
            rev_id=123,
            rdf_added_data=RDFDataField(data="<full data>"),
            sequence=0,
            sequence_length=1,
        )
        assert event.operation == "import"
        assert event.rdf_added_data is not None
        assert event.rdf_deleted_data is None

    def test_rdf_change_event_delete_operation(self):
        """Test creating an RDFChangeEvent for delete operation."""
        event = RDFChangeEvent(
            dt="2024-01-01T00:00:00Z",
            entity_id="Q42",
            meta={"domain": "wikidata.org", "stream": "test"},
            operation="delete",
            rev_id=123,
            sequence=0,
            sequence_length=1,
        )
        assert event.operation == "delete"
        assert event.rdf_added_data is None
        assert event.rdf_deleted_data is None


class TestRDFChangeEventBuilder:
    """Test RDFChangeEventBuilder."""

    @pytest.mark.parametrize(
        "written",
        [
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:00:00.123456+00:00",
            "2024-01-01T00:00:00",
        ],
    )
    def test_eventstreams_timestamp_is_whole_seconds_ending_in_z(self, written):
        """The date in meta has to be readable by the consumer that follows it.

        It strips fractional seconds with a pattern anchored on Z and parses
        what is left as "%Y-%m-%dT%H:%M:%SZ". The timestamp this worker writes
        matches neither part, and a consumer that cannot read the date drops
        every message.
        """
        rendered = eventstreams_timestamp(written)

        assert rendered == "2024-01-01T00:00:00Z"
        # Exactly what the consumer does with it, so the two cannot drift apart.
        stripped = re.sub(r"\.\d*Z$", "Z", rendered)
        assert datetime.strptime(stripped, "%Y-%m-%dT%H:%M:%SZ")

    def test_meta_carries_the_envelope_a_consumer_reads(self):
        """topic, partition and dt all belong in meta, and it is where they go.

        A consumer following the EventStreams convention looks for the topic
        there to decide a message is its own, and the date there to order it.
        Carried anywhere else - or absent - and it skips the message without
        saying why.
        """
        event = RDFChangeEventBuilder.build(
            EventConfig(
                entity_id="Q42",
                rev_id=1,
                operation="import",
                rdf_added_data="<added> .",
                rdf_deleted_data="",
                timestamp="2024-01-01T00:00:00.987654+00:00",
            )
        )

        assert event.meta["topic"] == "incremental_rdf_diff"
        assert event.meta["partition"] == 0
        assert event.meta["dt"] == "2024-01-01T00:00:00Z"
        assert event.meta["request_id"]

    def test_build_diff_event(self):
        """Test building a diff event."""
        config = EventConfig(
            entity_id="Q42",
            rev_id=123,
            operation="diff",
            rdf_added_data="<added> .",
            rdf_deleted_data="<removed> .",
            timestamp="2024-01-01T00:00:00Z",
        )
        event = RDFChangeEventBuilder.build(config)

        assert event.entity_id == "Q42"
        assert event.rev_id == 123
        assert event.operation == "diff"
        assert event.rdf_added_data is not None
        assert event.rdf_added_data.data == "<added> ."
        assert event.rdf_deleted_data is not None
        assert event.rdf_deleted_data.data == "<removed> ."

    def test_build_import_event(self):
        """Test building an import event."""
        config = EventConfig(
            entity_id="Q42",
            rev_id=123,
            operation="import",
            rdf_added_data="<full rdf> .",
            rdf_deleted_data="",
            timestamp="2024-01-01T00:00:00Z",
        )
        event = RDFChangeEventBuilder.build(config)

        assert event.operation == "import"
        assert event.rdf_added_data is not None
        assert event.rdf_deleted_data is None

    def test_build_delete_event(self):
        """Test building a delete event."""
        config = EventConfig(
            entity_id="Q42",
            rev_id=123,
            operation="delete",
            rdf_added_data="",
            rdf_deleted_data="",
            timestamp="2024-01-01T00:00:00Z",
        )
        event = RDFChangeEventBuilder.build(config)

        assert event.operation == "delete"
        assert event.rdf_added_data is None
        assert event.rdf_deleted_data is None

    def test_build_with_custom_domain(self):
        """Test building an event with custom domain."""
        config = EventConfig(
            entity_id="Q42",
            rev_id=123,
            operation="diff",
            rdf_added_data="<test> .",
            rdf_deleted_data="",
            timestamp="2024-01-01T00:00:00Z",
            domain="test.wikidata.org",
        )
        event = RDFChangeEventBuilder.build(config)

        assert event.meta["domain"] == "test.wikidata.org"

    def test_build_with_request_id(self):
        """Test building an event with custom request ID."""
        config = EventConfig(
            entity_id="Q42",
            rev_id=123,
            operation="diff",
            rdf_added_data="<test> .",
            rdf_deleted_data="",
            timestamp="2024-01-01T00:00:00Z",
            request_id="custom-request-123",
        )
        event = RDFChangeEventBuilder.build(config)

        assert event.meta["request_id"] == "custom-request-123"


class TestSettingsContract:
    """Every settings attribute and config field the worker reads must exist.

    The worker crashed five times before it started once, each time on an
    attribute that was never there: kafka_incremental_rdf_topic,
    get_incremental_rdf_stream_config, incremental_rdf_enabled,
    incremental_rdf_consumer_group, and s3_config.endpoint. None was caught,
    because every test constructed the worker with worker_enabled=False and
    so never reached the code that reads them.

    This reads them off the source instead, so a rename shows up here rather
    than in a container.
    """

    WORKER_SOURCE = (
        Path(__file__).parent.parent
        / "src"
        / "incremental_rdf_worker"
        / "worker.py"
    )

    def test_settings_attributes_exist(self):
        source = self.WORKER_SOURCE.read_text()
        # digits included: get_s3_config truncates to get_s without them
        used = set(re.findall(r"settings\.([a-zA-Z_0-9]+)", source))

        assert used, "no settings attributes found; the pattern probably changed"
        missing = sorted(a for a in used if not hasattr(settings, a))
        assert not missing, f"worker reads settings the Settings class lacks: {missing}"

    def test_config_fields_exist(self):
        """Config objects are checked field by field, not just by name.

        get_s3_config existed, so the settings check passed, while the field the
        worker then read off it did not. One level deeper is what was missing.
        """
        source = self.WORKER_SOURCE.read_text()
        checked = 0
        for variable, config_getter in re.findall(
            r"(\w+_config) = settings\.(get_\w+)", source
        ):
            config = getattr(settings, config_getter)
            used = set(re.findall(rf"{variable}\.([a-zA-Z_]+)", source))
            for field in used:
                checked += 1
                assert hasattr(config, field), (
                    f"{variable} ({config_getter}) has no field {field!r}; "
                    f"fields are {sorted(config.model_fields)}"
                )
        assert checked, "no config fields found; the pattern probably changed"
