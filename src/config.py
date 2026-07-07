"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    scans_dir: str = "./scans"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    mdns_enabled: bool = True
    mdns_service_name: str = "macbook"


settings = Settings()
