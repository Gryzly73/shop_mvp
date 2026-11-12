import os
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    return tuple(path for path in (".env", "../.env") if os.path.isfile(path))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_files() or None, extra="ignore")

    app_env: Literal["development", "production"] = "development"
    bot_token: str
    webhook_secret: str
    admin_ids: str
    public_base_url: str
    service_token: str
    backend_internal_url: str

    @model_validator(mode="after")
    def validate_production_configuration(self) -> Self:
        if self.app_env == "production":
            secrets = (self.bot_token, self.webhook_secret, self.service_token)
            if any(
                not value or value.startswith(("change-me", "123456:replace")) for value in secrets
            ):
                raise ValueError("production secrets must not use placeholder values")
            if not self.admin_id_list() or self.admin_id_list() == (123456789,):
                raise ValueError("production ADMIN_IDS must not use placeholder values")
            if not self.public_base_url.startswith("https://"):
                raise ValueError("PUBLIC_BASE_URL must use HTTPS in production")
        return self

    def admin_id_list(self) -> tuple[int, ...]:
        return tuple(int(part.strip()) for part in self.admin_ids.split(",") if part.strip())


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
