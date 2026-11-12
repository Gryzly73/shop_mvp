import pytest
from pydantic import ValidationError

from app.settings import Settings


def _settings(**overrides: str) -> Settings:
    values = {
        "app_env": "development",
        "bot_token": "123456:replace-with-botfather-token",
        "webhook_secret": "change-me-webhook-secret",
        "admin_ids": "123456789",
        "public_base_url": "http://localhost",
        "service_token": "change-me-service-token",
        "backend_internal_url": "http://backend:8000",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_development_allows_example_placeholders() -> None:
    assert _settings().app_env == "development"


def test_production_rejects_example_placeholders() -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        _settings(app_env="production")


def test_production_rejects_example_admin_ids() -> None:
    with pytest.raises(ValidationError, match="ADMIN_IDS"):
        _settings(
            app_env="production",
            bot_token="123456:real-token",
            webhook_secret="webhook-secret",
            service_token="service-secret",
            public_base_url="https://shop.example.com",
        )


def test_production_requires_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        _settings(
            app_env="production",
            bot_token="123456:real-token",
            webhook_secret="webhook-secret",
            service_token="service-secret",
            admin_ids="42",
        )


def test_production_accepts_real_configuration() -> None:
    settings = _settings(
        app_env="production",
        bot_token="123456:real-token",
        webhook_secret="webhook-secret",
        service_token="service-secret",
        admin_ids="42",
        public_base_url="https://shop.example.com",
    )
    assert settings.app_env == "production"
