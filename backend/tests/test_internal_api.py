from collections.abc import AsyncIterator
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from app.api.deps import get_image_storage, get_product_repository, get_session, get_settings
from app.api.routes_internal import MAX_IMAGE_BYTES, router
from tests.fakes import FakeImageStorage, FakeProductRepository

SERVICE_TOKEN = "test-service-token"
JPEG = b"\xff\xd8\xffjpeg-data"


class FakeSession:
    def __init__(self, commit_error: Exception | None = None) -> None:
        self.commit_error = commit_error
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1
        if self.commit_error is not None:
            raise self.commit_error


def _client(
    *,
    session: FakeSession | None = None,
) -> tuple[TestClient, FakeSession, FakeProductRepository, FakeImageStorage]:
    app = FastAPI()
    app.include_router(router)
    fake_session = session or FakeSession()
    products = FakeProductRepository()
    images = FakeImageStorage()

    async def provide_session() -> AsyncIterator[FakeSession]:
        yield fake_session

    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(service_token=SERVICE_TOKEN)
    app.dependency_overrides[get_session] = provide_session
    app.dependency_overrides[get_product_repository] = lambda: products
    app.dependency_overrides[get_image_storage] = lambda: images
    return TestClient(app, raise_server_exceptions=False), fake_session, products, images


def _post(
    client: TestClient,
    *,
    title: str = "Кружка",
    photo_file_unique_id: str = "photo-1",
    image: bytes = JPEG,
    content_type: str = "image/jpeg",
    token: str | None = SERVICE_TOKEN,
) -> Response:
    headers = {"X-Service-Token": token} if token is not None else {}
    return client.post(
        "/internal/products",
        data={"title": title, "photo_file_unique_id": photo_file_unique_id},
        files={"file": ("photo.jpg", image, content_type)},
        headers=headers,
    )


def test_create_product_commits_and_returns_created() -> None:
    client, session, products, images = _client()

    response = _post(client)

    assert response.status_code == 201
    assert session.commits == 1
    assert len(products.items) == 1
    assert len(images.objects) == 1


def test_missing_or_invalid_service_token_is_rejected() -> None:
    client, session, products, images = _client()

    assert _post(client, token=None).status_code == 401
    assert _post(client, token="wrong").status_code == 401
    assert session.commits == 0
    assert products.items == {}
    assert images.objects == {}


def test_invalid_image_is_rejected() -> None:
    client, session, products, images = _client()

    assert _post(client, image=b"", content_type="image/jpeg").status_code == 422
    assert _post(client, image=b"not-jpeg", content_type="image/jpeg").status_code == 422
    assert _post(client, image=JPEG, content_type="image/png").status_code == 415
    assert session.commits == 0
    assert products.items == {}
    assert images.objects == {}


def test_oversized_image_is_rejected() -> None:
    client, session, products, images = _client()

    response = _post(client, image=b"\xff\xd8\xff" + b"x" * MAX_IMAGE_BYTES)

    assert response.status_code == 413
    assert session.commits == 0
    assert products.items == {}
    assert images.objects == {}


def test_form_field_limits_return_validation_error() -> None:
    client, session, products, images = _client()

    assert _post(client, title="x" * 501).status_code == 422
    assert _post(client, photo_file_unique_id="x" * 256).status_code == 422
    assert session.commits == 0
    assert products.items == {}
    assert images.objects == {}


def test_commit_failure_removes_uploaded_image() -> None:
    client, session, _products, images = _client(
        session=FakeSession(commit_error=RuntimeError("commit failed"))
    )

    response = _post(client)

    assert response.status_code == 500
    assert session.commits == 1
    assert images.objects == {}
