from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGAS_",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+psycopg://agas:agas@localhost:5432/agas"
    auth_mode: Literal["development", "external"] = "development"
    development_auth_issuer: str = "urn:agas:development"
    cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )

    @model_validator(mode="after")
    def reject_development_auth_in_production(self) -> Settings:
        if (
            self.environment.casefold() in {"production", "prod"}
            and self.auth_mode == "development"
        ):
            raise ValueError("production environments cannot use development authentication")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
