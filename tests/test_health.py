"""Tests for health check endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_endpoint_returns_200(client):
    """Test that GET /health returns 200 status code."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_response_structure(client):
    """Test that health endpoint response has required fields."""
    response = client.get("/health")
    data = response.json()

    assert "status" in data
    assert "timestamp" in data
    assert "version" in data


def test_health_endpoint_status_value(client):
    """Test that health status is 'healthy'."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"


def test_health_endpoint_timestamp_format(client):
    """Test that timestamp is in ISO format."""
    response = client.get("/health")
    data = response.json()

    # Should not raise exception when parsing ISO format
    datetime.fromisoformat(data["timestamp"])


def test_health_endpoint_version_present(client):
    """Test that version is present and non-empty."""
    response = client.get("/health")
    data = response.json()

    assert data["version"]
    assert isinstance(data["version"], str)
