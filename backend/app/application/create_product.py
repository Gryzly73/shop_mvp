from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.ports import ImageStorage, ProductRepository
from app.domain.product import Product


class InvalidTitleError(Exception):
    """Title is missing or blank."""


@dataclass(frozen=True, slots=True)
class CreateProductResult:
    product: Product
    created: bool


class CreateProduct:
    def __init__(self, products: ProductRepository, images: ImageStorage) -> None:
        self._products = products
        self._images = images

    async def execute(
        self,
        *,
        title: str,
        photo_file_unique_id: str,
        image: bytes,
        content_type: str = "image/jpeg",
    ) -> CreateProductResult:
        cleaned = title.strip()
        if not cleaned:
            raise InvalidTitleError("title is empty")

        image_id = uuid4()
        product = Product(
            id=uuid4(),
            title=cleaned,
            image_key=f"products/{image_id}.jpg",
            photo_file_unique_id=photo_file_unique_id,
            created_at=datetime.now(UTC),
        )
        await self._images.put(product.image_key, image, content_type)
        try:
            stored = await self._products.add_if_absent(product)
        except Exception:
            await self._images.delete(product.image_key)
            raise
        if stored.image_key != product.image_key:
            await self._images.delete(product.image_key)
            return CreateProductResult(product=stored, created=False)
        return CreateProductResult(product=stored, created=True)
