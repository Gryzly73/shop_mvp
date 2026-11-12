import pytest
from pydantic import ValidationError

from app.infrastructure.settings import Settings


def _settings(**overrides: str) -> Settings:
    values = {
        "app_env": "development",
        "postgres_db": "shop",
        "postgres_user": "shop",
        "postgres_password": "change-me-postgres",
        "postgres_host": "postgres",
        "minio_root_user": "minio",
        "minio_root_password": "change-me-minio",
        "s3_endpoint": "http://minio:9000",
        "s3_bucket": "products",
        "public_media_url": "http://localhost/media/",
        "service_token": "change-me-service-token",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_development_allows_example_placeholders() -> None:
    assert _settings().app_env == "development"


def test_production_rejects_example_placeholders() -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        _settings(app_env="production")


def test_production_rejects_default_minio_user() -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        _settings(
            app_env="production",
            postgres_password="postgres-secret",
            minio_root_user="minioadmin",
            minio_root_password="minio-secret",
            service_token="service-secret",
            public_media_url="https://shop.example.com/media/",
        )


def test_production_requires_https_media_url() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        _settings(
            app_env="production",
            postgres_password="postgres-secret",
            minio_root_password="minio-secret",
            service_token="service-secret",
        )


def test_production_accepts_non_placeholder_secrets() -> None:
    settings = _settings(
        app_env="production",
        postgres_password="postgres-secret",
        minio_root_password="minio-secret",
        service_token="service-secret",
        public_media_url="https://shop.example.com/media/",
    )
    assert settings.app_env == "production"
