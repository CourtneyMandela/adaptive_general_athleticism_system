from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGAS_",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+psycopg://agas:agas@localhost:5432/agas"
    cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
