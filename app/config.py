"""
Configuration settings for the AMT Backend application.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "AMT Backend"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # Database
    database_url: str = Field(
        default="sqlite:///./amt_backend.db",
        env="DATABASE_URL"
    )

    # Redis (for Celery)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )

    # File Storage
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(
        default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    allowed_audio_formats: list[str] = Field(
        default=["wav", "mp3", "flac", "m4a", "ogg"],
        env="ALLOWED_AUDIO_FORMATS"
    )

    # Audio Processing
    sample_rate: int = Field(default=44100, env="SAMPLE_RATE")
    max_audio_duration: int = Field(
        default=600, env="MAX_AUDIO_DURATION")  # 10 minutes

    # Security
    secret_key: str = Field(env="SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
