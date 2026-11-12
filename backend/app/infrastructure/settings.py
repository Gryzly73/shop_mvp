import os
from typing import Literal, Self
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    return tuple(path for path in (".env", "../.env") if os.path.isfile(path))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_files() or None, extra="ignore")

    app_env: Literal["development", "production"] = "development"
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int = 5432
    database_url: str | None = None

    minio_root_user: str
    minio_root_password: str
    s3_endpoint: str
    s3_bucket: str
    public_media_url: str
    service_token: str

    @model_validator(mode="after")
    def reject_production_placeholders(self) -> Self:
        if self.app_env == "production":
            secrets = (
                self.postgres_password,
                self.minio_root_password,
                self.service_token,
            )
            if any(not value or value.startswith("change-me") for value in secrets):
                raise ValueError("production secrets must not use placeholder values")
            if not self.minio_root_user or self.minio_root_user == "minioadmin":
                raise ValueError("production secrets must not use placeholder values")
            if not self.public_media_url.startswith("https://"):
                raise ValueError("PUBLIC_MEDIA_URL must use HTTPS in production")
        return self

    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        database = quote_plus(self.postgres_db)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database}"
        )


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
