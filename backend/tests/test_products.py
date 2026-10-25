import pytest

from app.application.create_product import CreateProduct, InvalidTitleError
from app.application.list_products import ListProducts
from tests.fakes import FakeImageStorage, FakeProductRepository


def _usecase() -> tuple[CreateProduct, FakeProductRepository, FakeImageStorage]:
    products = FakeProductRepository()
    images = FakeImageStorage()
    return CreateProduct(products, images), products, images


async def test_create_product_stores_title_and_image() -> None:
    usecase, products, images = _usecase()

    result = await usecase.execute(
        title="  Кружка  ",
        photo_file_unique_id="file-1",
        image=b"jpeg-bytes",
    )

    assert result.created is True
    assert result.product.title == "Кружка"
    assert result.product.photo_file_unique_id == "file-1"
    assert result.product.image_key.startswith("products/")
    assert result.product.image_key.endswith(".jpg")
    assert images.objects[result.product.image_key] == b"jpeg-bytes"
    assert images.content_types[result.product.image_key] == "image/jpeg"
    assert images.public_url(result.product.image_key) == (
        f"http://localhost/media/{result.product.image_key}"
    )
    assert await products.list() == [result.product]


async def test_empty_title_is_rejected_without_upload() -> None:
    usecase, products, images = _usecase()

    with pytest.raises(InvalidTitleError):
        await usecase.execute(title="   ", photo_file_unique_id="file-1", image=b"jpeg-bytes")

    assert await products.list() == []
    assert images.objects == {}


async def test_duplicate_photo_file_unique_id_keeps_one_record() -> None:
    usecase, products, images = _usecase()

    first = await usecase.execute(
        title="Кружка",
        photo_file_unique_id="file-1",
        image=b"first",
    )
    second = await usecase.execute(
        title="Другое имя",
        photo_file_unique_id="file-1",
        image=b"second",
    )

    assert second.created is False
    assert second.product == first.product
    assert await products.list() == [first.product]
    assert images.objects == {first.product.image_key: b"first"}


async def test_list_products_returns_stored_records() -> None:
    usecase, products, _images = _usecase()
    await usecase.execute(title="Первый", photo_file_unique_id="file-1", image=b"a")
    await usecase.execute(title="Второй", photo_file_unique_id="file-2", image=b"b")

    listed = await ListProducts(products).execute()

    assert {item.title for item in listed} == {"Первый", "Второй"}
