"""Integration tests for FastAPI app with mDNS."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.main import app


class TestAppWithMdns:
    """Test FastAPI app integration with mDNS."""

    @pytest.fixture
    def client(self):
        """Create a test client for the app."""
        return TestClient(app)

    def test_app_starts_with_mdns_enabled(self, client) -> None:
        """Test that app starts successfully with mDNS enabled."""
        # Make a request to verify the app is running
        response = client.get("/health")
        assert response.status_code == 200

    def test_app_starts_with_mdns_disabled(self) -> None:
        """Test that app starts successfully with mDNS disabled."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.mdns_enabled = False
            mock_settings.host = "127.0.0.1"
            mock_settings.port = 8000
            mock_settings.debug = False
            mock_settings.scans_dir = "./scans"
            mock_settings.mdns_service_name = "macbook"

            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200

    def test_mdns_settings_configured(self) -> None:
        """Test that mDNS settings are properly configured."""
        assert hasattr(settings, "mdns_enabled")
        assert hasattr(settings, "mdns_service_name")
        assert settings.mdns_service_name == "macbook"

    def test_mdns_config_from_env(self) -> None:
        """Test that mDNS config can be loaded from environment."""
        # The defaults should work
        assert settings.mdns_enabled is True
        assert settings.mdns_service_name == "macbook"

    def test_app_has_correct_metadata(self) -> None:
        """Test that app has correct title and description."""
        assert app.title == "RoomMesh"
        assert "room/mesh networking" in app.description.lower()

    def test_app_openapi_schema_generated(self) -> None:
        """Test that OpenAPI schema is properly generated."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "RoomMesh"
