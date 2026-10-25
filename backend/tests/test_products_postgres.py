import asyncio
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager

from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from alembic import command
from app.application.create_product import CreateProduct
from app.infrastructure.models import ProductModel
from app.infrastructure.repositories import SqlProductRepository
from tests.fakes import FakeImageStorage


def _async_url(container: PostgresContainer) -> str:
    _scheme, rest = container.get_connection_url().split("://", 1)
    return f"postgresql+asyncpg://{rest}"


@contextmanager
def _database_url(url: str) -> Iterator[None]:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


def test_duplicate_photo_file_unique_id_inserts_one_row() -> None:
    if sys.platform == "win32":
        os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

    with PostgresContainer("postgres:16-alpine", driver=None) as postgres:
        url = _async_url(postgres)
        with _database_url(url):
            command.upgrade(Config("alembic.ini"), "head")
            asyncio.run(_insert_duplicate(url))


async def _insert_duplicate(url: str) -> None:
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    images = FakeImageStorage()
    try:
        async with factory() as session:
            first = await CreateProduct(SqlProductRepository(session), images).execute(
                title="Кружка",
                photo_file_unique_id="same-file",
                image=b"first-image",
            )
            await session.commit()

        async with factory() as session:
            second = await CreateProduct(SqlProductRepository(session), images).execute(
                title="Другое имя",
                photo_file_unique_id="same-file",
                image=b"second-image",
            )
            await session.commit()
            count = await session.scalar(select(func.count()).select_from(ProductModel))

        assert first.created is True
        assert second.created is False
        assert second.product.id == first.product.id
        assert second.product.title == "Кружка"
        assert count == 1
        assert images.objects == {first.product.image_key: b"first-image"}
    finally:
        await engine.dispose()
