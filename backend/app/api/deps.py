from collections.abc import AsyncIterator
from typing import Annotated

import aioboto3
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories import SqlProductRepository
from app.infrastructure.settings import Settings
from app.infrastructure.storage_minio import MinioImageStorage


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_product_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SqlProductRepository:
    return SqlProductRepository(session)


def get_image_storage(request: Request) -> MinioImageStorage:
    settings = get_settings(request)
    s3_session: aioboto3.Session = request.app.state.s3_session
    return MinioImageStorage(
        session=s3_session,
        endpoint_url=settings.s3_endpoint,
        bucket=settings.s3_bucket,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        public_media_url=settings.public_media_url,
    )
