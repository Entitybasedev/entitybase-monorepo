"""Shared mocks for kafka2sse contract tests.

Contract tests assert HTTP response shapes without real kafka/valkey
services, mirroring the entitybase-backend contract test style.
"""

from unittest.mock import MagicMock, patch

import pytest
from confluent_kafka import KafkaError, KafkaException


def make_cluster_metadata(topics: dict[str, int] | None = None) -> MagicMock:
    """Build a confluent-kafka ClusterMetadata-like mock.

    topics maps topic name -> partition count.
    """
    metadata = MagicMock()
    metadata.topics = {}
    for name, partition_count in (topics or {}).items():
        topic_meta = MagicMock()
        topic_meta.partitions = {i: MagicMock() for i in range(partition_count)}
        metadata.topics[name] = topic_meta
    return metadata


@pytest.fixture
def mock_producer():
    """Patch src.main.Producer so /health and /v1/topics need no broker.

    By default reports one user-facing topic. Tests may reconfigure
    list_topics return value or side_effect.
    """
    with patch("src.main.Producer") as producer_cls:
        producer = producer_cls.return_value
        producer.list_topics.return_value = make_cluster_metadata(
            {"entity_change": 1}
        )
        yield producer


@pytest.fixture
def mock_consumer():
    """Patch confluent_kafka.Consumer so /v1/streams/{t}/metadata needs no broker."""
    with patch("confluent_kafka.Consumer") as consumer_cls:
        consumer = consumer_cls.return_value
        consumer.list_topics.return_value = make_cluster_metadata(
            {"entity_change": 1}
        )
        consumer.get_watermark_offsets.return_value = (0, 5)
        yield consumer


@pytest.fixture
def api_prefix() -> str:
    return ""


@pytest.fixture
def kafka_transport_error():
    """Exception used to simulate an unreachable broker."""
    return KafkaException(
        KafkaError(KafkaError._TRANSPORT, "mock transport failure")
    )
