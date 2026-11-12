import httpx


class BackendRequestError(Exception):
    """Backend rejected the request with a permanent 4xx response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"backend returned {status_code}: {detail}")


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
        if response.status_code in {200, 201}:
            return response.status_code == 201
        if 400 <= response.status_code < 500:
            raise BackendRequestError(response.status_code, _detail(response))
        response.raise_for_status()
        raise AssertionError(f"unexpected backend status {response.status_code}")


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return response.text
