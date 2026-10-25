from app.domain.ports import ProductRepository
from app.domain.product import Product


class ListProducts:
    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    async def execute(self) -> list[Product]:
        return await self._products.list()
