"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "CloudGaming"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://cloudgaming:cloudgaming@localhost:5432/cloudgaming"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Streaming
    stun_server: str = "stun:stun.l.google.com:19302"
    turn_server: str = ""
    turn_username: str = ""
    turn_password: str = ""
    max_bitrate: int = 6000
    default_resolution: str = "1080p"
    default_fps: int = 60

    # Docker
    docker_network: str = "cloud-gaming-net"
    game_container_cpu_limit: float = 4.0
    game_container_memory_limit: str = "8g"
    game_container_image: str = "cloud-gaming/game-node:latest"

    # GPU
    gpu_enabled: bool = False
    gpu_driver: str = "nvidia"

    # Session
    max_sessions_per_user: int = 1
    session_timeout_minutes: int = 120
    idle_timeout_minutes: int = 15

    # Monitoring
    prometheus_port: int = 9090

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
