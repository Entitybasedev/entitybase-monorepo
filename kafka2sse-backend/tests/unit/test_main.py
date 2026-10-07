import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app, resume_offset_from, stamp_stream_position


class TestHealthEndpoint:
    def test_health_endpoint(self):
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data


class TestRootEndpoint:
    def test_root(self):
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200


class TestListTopicsEndpoint:
    @patch("src.main.Producer")
    def test_list_topics(self, mock_producer_cls):
        mock_instance = MagicMock()
        mock_metadata = MagicMock()
        mock_instance.list_topics.return_value = mock_metadata
        mock_producer_cls.return_value = mock_instance

        with TestClient(app) as client:
            response = client.get("/v1/topics")
            assert response.status_code == 200
            data = response.json()
            assert "topics" in data

class TestStampStreamPosition:
    """The topic position is recorded in the envelope, not only the SSE id.

    A producer cannot know its own Kafka offset before sending, so the payload
    arrives without one. A consumer that resumes on the EventStreams convention
    reads meta.offset and adds to it, which raised on the first batch it had
    otherwise ingested correctly.
    """

    @staticmethod
    def _msg(offset=7, partition=0, topic="incremental_rdf_diff"):
        # A record with plain fields, not a mock with methods: a mock answers
        # either shape, so it cannot tell attribute access from a call, and
        # calling a field of an int raises only against the real thing.
        return SimpleNamespace(offset=offset, partition=partition, topic=topic)

    def test_position_is_stamped_into_meta(self):
        value = stamp_stream_position(
            {"meta": {"dt": "2024-01-01T00:00:00Z"}}, self._msg()
        )
        assert value["meta"]["offset"] == 7
        assert value["meta"]["partition"] == 0
        assert value["meta"]["topic"] == "incremental_rdf_diff"

    def test_producers_own_position_is_kept(self):
        """Only fill in what is missing.

        A producer that knows where it sits - after a republish, say - should
        not have it overwritten by the offset of the message being relayed.
        """
        value = stamp_stream_position({"meta": {"offset": 3}}, self._msg(offset=99))
        assert value["meta"]["offset"] == 3

    def test_a_message_with_no_meta_is_left_alone(self):
        """Adding an empty meta would invent an envelope the producer did not send."""
        payload = {"entity_id": "Q1"}
        assert stamp_stream_position(payload, self._msg()) == {"entity_id": "Q1"}


class TestResumeOffsetFrom:
    """Last-Event-ID is how an SSE client says where it got to.

    sse-starlette does not read the header, so the route reads it here. It was
    ignored, so a client that reconnects was handed the topic from the start
    again - the same messages over and over, and for a follower that applies
    changes in batches, never a settled state to move on from.
    """

    def test_reads_the_offset_an_eventstreams_client_sends(self):
        header = json.dumps(
            [{"topic": "incremental_rdf_diff", "partition": 0, "offset": 42}]
        )
        assert resume_offset_from(header, "incremental_rdf_diff") == 42

    def test_reads_a_bare_offset(self):
        assert resume_offset_from("42", "incremental_rdf_diff") == 42

    def test_a_position_for_another_topic_is_not_ours(self):
        header = json.dumps([{"topic": "something_else", "offset": 42}])
        assert resume_offset_from(header, "incremental_rdf_diff") is None

    def test_absent_header_leaves_the_start_alone(self):
        assert resume_offset_from(None, "incremental_rdf_diff") is None
        assert resume_offset_from("", "incremental_rdf_diff") is None

    def test_unreadable_header_is_not_guessed_at(self):
        """Falling back to the start would silently replay the whole topic."""
        assert resume_offset_from("not json", "incremental_rdf_diff") is None

    def test_a_header_with_no_offset_is_not_guessed_at(self):
        header = json.dumps([{"topic": "incremental_rdf_diff", "partition": 0}])
        assert resume_offset_from(header, "incremental_rdf_diff") is None
