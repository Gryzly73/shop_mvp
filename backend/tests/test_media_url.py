import aioboto3

from app.infrastructure.storage_minio import MinioImageStorage


def test_public_url_joins_media_base_and_key() -> None:
    storage = MinioImageStorage(
        session=aioboto3.Session(),
        endpoint_url="http://minio:9000",
        bucket="products",
        access_key="minioadmin",
        secret_key="change-me-minio",
        public_media_url="http://localhost/media/",
    )

    assert storage.public_url("products/abc.jpg") == "http://localhost/media/products/abc.jpg"
