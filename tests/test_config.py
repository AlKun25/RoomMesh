"""Tests for application configuration."""

import pytest

from src.config import Settings


def test_settings_defaults():
    """Test that settings have correct default values.

    ``_env_file=None`` ignores the project ``.env`` so this exercises the
    in-code defaults rather than whatever the local ``.env`` happens to set.
    """
    settings = Settings(_env_file=None)
    assert settings.scans_dir == "./scans"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.debug is False


def test_settings_from_env(monkeypatch):
    """Test that settings load from environment variables."""
    monkeypatch.setenv("SCANS_DIR", "/custom/scans")
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings()
    assert settings.scans_dir == "/custom/scans"
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.debug is True


def test_settings_type_validation():
    """Test that settings validate types correctly."""
    with pytest.raises(ValueError):
        Settings(port="invalid")


def test_settings_partial_env(monkeypatch):
    """Test that settings work with partial environment variables."""
    monkeypatch.setenv("HOST", "192.168.1.1")

    settings = Settings()
    assert settings.host == "192.168.1.1"
    assert settings.scans_dir == "./scans"  # Uses default
    assert settings.port == 8000  # Uses default
