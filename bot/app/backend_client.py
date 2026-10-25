import httpx


class BackendClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str,
        service_token: str,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token

    async def create_product(
        self,
        *,
        title: str,
        photo_file_unique_id: str,
        image: bytes,
        content_type: str = "image/jpeg",
    ) -> bool:
        response = await self._client.post(
            f"{self._base_url}/internal/products",
            data={
                "title": title,
                "photo_file_unique_id": photo_file_unique_id,
            },
            files={"file": ("photo.jpg", image, content_type)},
            headers={"X-Service-Token": self._service_token},
        )
        response.raise_for_status()
        return response.status_code == 201
