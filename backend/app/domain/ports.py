from typing import Protocol

from app.domain.product import Product


class ProductRepository(Protocol):
    async def add_if_absent(self, product: Product) -> Product:
        """Insert the product. If photo_file_unique_id already exists, return that row."""

    async def list(self) -> list[Product]:
        """Return stored products."""


class ImageStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store image bytes under key."""

    def public_url(self, key: str) -> str:
        """Build the public URL for a stored key."""

    async def delete(self, key: str) -> None:
        """Remove an object. Used to drop an upload that lost an idempotency race."""
