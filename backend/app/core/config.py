from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Quant Platform"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+psycopg://quant:quant@postgres:5432/quant"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    tickflow_api_key: str = ""
    strategy_storage_dir: Path = Path("/app/storage/strategies")
    sandbox_image: str = "quant-platform-strategy-sandbox:latest"
    sandbox_timeout_seconds: int = 60

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "quant-platform@example.local"
    smtp_to: str = ""

    default_commission_rate: float = 0.0003
    default_stamp_tax_rate: float = 0.001
    default_slippage_rate: float = 0.0002

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.strategy_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()

