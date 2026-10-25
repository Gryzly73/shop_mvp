import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    return tuple(path for path in (".env", "../.env") if os.path.isfile(path))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_files() or None, extra="ignore")

    bot_token: str
    webhook_secret: str
    admin_ids: str
    public_base_url: str
    service_token: str
    backend_internal_url: str

    def admin_id_list(self) -> tuple[int, ...]:
        return tuple(int(part.strip()) for part in self.admin_ids.split(",") if part.strip())


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
