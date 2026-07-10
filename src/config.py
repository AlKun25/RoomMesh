"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    scans_dir: str = "./scans"
    # Target rate at which incoming video frames are saved to disk. The phone
    # streams at its camera frame rate; we decimate to this rate so the SfM
    # pipeline gets useful coverage without storing every redundant frame.
    frame_save_fps: float = 4.0
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    mdns_enabled: bool = True
    mdns_service_name: str = "macbook"


settings = Settings()
