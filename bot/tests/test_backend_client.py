import httpx
import pytest

from app.backend_client import BackendClient, BackendRequestError


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


async def test_create_product_posts_multipart_and_treats_201_as_created() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://backend:8000/internal/products"
        assert request.headers["X-Service-Token"] == "svc"
        body = request.content
        assert "Кружка".encode() in body
        assert b"file-1" in body
        assert b"jpeg-bytes" in body
        return httpx.Response(201, json={"id": "new"})

    async with _client(httpx.MockTransport(handler)) as http:
        created = await BackendClient(
            http,
            base_url="http://backend:8000/",
            service_token="svc",
        ).create_product(
            title="Кружка",
            photo_file_unique_id="file-1",
            image=b"jpeg-bytes",
        )

    assert created is True


async def test_create_product_treats_200_as_duplicate() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "old"})

    async with _client(httpx.MockTransport(handler)) as http:
        created = await BackendClient(
            http,
            base_url="http://backend:8000",
            service_token="svc",
        ).create_product(
            title="Кружка",
            photo_file_unique_id="file-1",
            image=b"jpeg-bytes",
        )

    assert created is False


async def test_create_product_raises_client_error_on_4xx() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "title is empty"})

    async with _client(httpx.MockTransport(handler)) as http:
        client = BackendClient(http, base_url="http://backend:8000", service_token="svc")
        with pytest.raises(BackendRequestError) as exc_info:
            await client.create_product(
                title="Кружка",
                photo_file_unique_id="file-1",
                image=b"jpeg-bytes",
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "title is empty"


async def test_create_product_raises_on_backend_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    async with _client(httpx.MockTransport(handler)) as http:
        client = BackendClient(http, base_url="http://backend:8000", service_token="svc")
        with pytest.raises(httpx.HTTPStatusError):
            await client.create_product(
                title="Кружка",
                photo_file_unique_id="file-1",
                image=b"jpeg-bytes",
            )
