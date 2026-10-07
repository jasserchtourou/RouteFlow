from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# <repo>/.env, resolved from this file so it works regardless of the working directory.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Application configuration, read from environment variables (and the repo's .env)."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "RouteFlow"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_v1_prefix: str = "/api/v1"
    # Operational "today"/"yesterday" are calendar days in this zone (not UTC).
    business_timezone: str = "Europe/Berlin"
    # Accepts a comma-separated string ("a,b"); NoDecode stops pydantic-settings expecting JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    database_url: str = "postgresql+asyncpg://routeflow:change-me@localhost:5432/routeflow"
    # Separate database used only by the automated test-suite.
    test_database_url: str = (
        "postgresql+asyncpg://routeflow:change-me@localhost:5432/routeflow_test"
    )
    # Keeps a rolling schedule of truck visits so the 3D site view is alive in demos. Turn off
    # when real dock appointments are fed in.
    yard_simulation_enabled: bool = True
    db_pool_size: int = 10
    db_max_overflow: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
