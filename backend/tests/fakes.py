from app.domain.product import Product


class FakeProductRepository:
    def __init__(self) -> None:
        self.items: dict[str, Product] = {}

    async def add_if_absent(self, product: Product) -> Product:
        existing = self.items.get(product.photo_file_unique_id)
        if existing is not None:
            return existing
        self.items[product.photo_file_unique_id] = product
        return product

    async def list(self) -> list[Product]:
        return sorted(self.items.values(), key=lambda item: item.created_at, reverse=True)


class FakeImageStorage:
    def __init__(self, base_url: str = "http://localhost/media/") -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.base_url = base_url

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data
        self.content_types[key] = content_type

    def public_url(self, key: str) -> str:
        return f"{self.base_url}{key}"

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)
        self.content_types.pop(key, None)
