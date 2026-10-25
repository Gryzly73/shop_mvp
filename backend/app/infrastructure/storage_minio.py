from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.config import Config


class MinioImageStorage:
    def __init__(
        self,
        *,
        session: aioboto3.Session,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        public_media_url: str,
    ) -> None:
        self._session = session
        self._endpoint_url = endpoint_url
        self._bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key
        self._public_media_url = (
            public_media_url if public_media_url.endswith("/") else f"{public_media_url}/"
        )

    def public_url(self, key: str) -> str:
        return f"{self._public_media_url}{key}"

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        async with self._client() as client:
            await client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

    async def delete(self, key: str) -> None:
        async with self._client() as client:
            await client.delete_object(Bucket=self._bucket, Key=key)

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[Any]:
        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        ) as client:
            yield client
