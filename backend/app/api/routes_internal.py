import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import get_image_storage, get_product_repository, get_settings
from app.api.schemas import ProductOut
from app.application.create_product import CreateProduct, InvalidTitleError
from app.infrastructure.repositories import SqlProductRepository
from app.infrastructure.settings import Settings
from app.infrastructure.storage_minio import MinioImageStorage

router = APIRouter()


def _token_ok(provided: str | None, expected: str) -> bool:
    if not provided or not expected or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


@router.post("/internal/products")
async def create_product(
    title: Annotated[str, Form()],
    photo_file_unique_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    settings: Annotated[Settings, Depends(get_settings)],
    products: Annotated[SqlProductRepository, Depends(get_product_repository)],
    images: Annotated[MinioImageStorage, Depends(get_image_storage)],
    x_service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None,
) -> JSONResponse:
    if not _token_ok(x_service_token, settings.service_token):
        raise HTTPException(status_code=401, detail="invalid service token")

    data = await file.read()
    try:
        result = await CreateProduct(products, images).execute(
            title=title,
            photo_file_unique_id=photo_file_unique_id,
            image=data,
            content_type=file.content_type or "image/jpeg",
        )
    except InvalidTitleError as exc:
        raise HTTPException(status_code=422, detail="title is empty") from exc

    body = ProductOut(
        id=result.product.id,
        title=result.product.title,
        image_url=images.public_url(result.product.image_key),
        created_at=result.product.created_at,
    )
    return JSONResponse(
        status_code=201 if result.created else 200,
        content=body.model_dump(mode="json"),
    )
