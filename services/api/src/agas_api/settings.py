from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
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
    external_auth_issuer: AnyHttpUrl | None = None
    external_auth_audience: str | None = None
    external_auth_jwks_url: AnyHttpUrl | None = None
    external_auth_algorithms: tuple[
        Literal["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"], ...
    ] = Field(default=("RS256",), min_length=1)
    external_auth_leeway_seconds: int = Field(default=30, ge=0, le=300)
    external_auth_jwks_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    external_auth_jwks_cache_seconds: int = Field(default=300, ge=30, le=3600)
    cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def select_psycopg_driver(cls, value: object) -> object:
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+psycopg://", 1)
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def validate_authentication_configuration(self) -> Settings:
        if self.external_auth_audience is not None:
            self.external_auth_audience = self.external_auth_audience.strip()
            if not self.external_auth_audience:
                raise ValueError("external authentication audience cannot be blank")
        production = self.environment.casefold() in {"production", "prod"}
        if production and self.auth_mode == "development":
            raise ValueError("production environments cannot use development authentication")
        if production:
            issuer = self.external_auth_issuer
            jwks_url = self.external_auth_jwks_url
            if issuer is None or jwks_url is None or not self.external_auth_audience:
                raise ValueError(
                    "production external authentication requires issuer, audience, and JWKS URL"
                )
            if issuer.scheme != "https" or jwks_url.scheme != "https":
                raise ValueError("production external authentication endpoints must use HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
