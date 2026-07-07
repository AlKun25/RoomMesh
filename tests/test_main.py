"""Tests for the main application module."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_app_can_be_imported():
    """Test that app can be imported successfully."""
    from src.main import app as imported_app

    assert imported_app is not None


def test_app_instantiation():
    """Test that FastAPI app is properly instantiated."""
    assert app is not None
    assert app.title == "RoomMesh"


def test_app_has_health_router(client):
    """Test that health router is registered."""
    response = client.get("/health")
    assert response.status_code == 200


def test_app_openapi_schema(client):
    """Test that OpenAPI schema can be accessed."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "RoomMesh"
    assert "paths" in schema
    assert "/health" in schema["paths"]
