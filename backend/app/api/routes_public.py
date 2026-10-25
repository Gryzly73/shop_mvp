from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_image_storage, get_product_repository, get_session
from app.api.schemas import ProductOut
from app.application.list_products import ListProducts
from app.infrastructure.repositories import SqlProductRepository
from app.infrastructure.storage_minio import MinioImageStorage

router = APIRouter()


@router.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/api/products", response_model=list[ProductOut])
async def list_products(
    products: Annotated[SqlProductRepository, Depends(get_product_repository)],
    images: Annotated[MinioImageStorage, Depends(get_image_storage)],
) -> list[ProductOut]:
    items = await ListProducts(products).execute()
    return [
        ProductOut(
            id=item.id,
            title=item.title,
            image_url=images.public_url(item.image_key),
            created_at=item.created_at,
        )
        for item in items
    ]
