import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.product import Product
from app.infrastructure.models import ProductModel


class SqlProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, product: Product) -> Product:
        stmt = (
            pg_insert(ProductModel)
            .values(
                id=product.id,
                title=product.title,
                image_key=product.image_key,
                photo_file_unique_id=product.photo_file_unique_id,
                created_at=product.created_at,
            )
            .on_conflict_do_nothing(index_elements=["photo_file_unique_id"])
            .returning(ProductModel)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            found = await self._session.execute(
                select(ProductModel).where(
                    ProductModel.photo_file_unique_id == product.photo_file_unique_id
                )
            )
            row = found.scalar_one()
        return _to_product(row)

    async def list(self) -> list[Product]:
        result = await self._session.execute(
            select(ProductModel).order_by(
                ProductModel.created_at.desc(),
                ProductModel.id.desc(),
            )
        )
        return [_to_product(row) for row in result.scalars().all()]


def _to_product(row: ProductModel) -> Product:
    product_id: uuid.UUID = row.id
    created_at: datetime = row.created_at
    return Product(
        id=product_id,
        title=row.title,
        image_key=row.image_key,
        photo_file_unique_id=row.photo_file_unique_id,
        created_at=created_at,
    )
