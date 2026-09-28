import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app


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