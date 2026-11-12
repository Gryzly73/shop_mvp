import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_image_storage, get_product_repository, get_session, get_settings
from app.api.schemas import ProductOut
from app.application.create_product import CreateProduct, InvalidTitleError
from app.infrastructure.repositories import SqlProductRepository
from app.infrastructure.settings import Settings
from app.infrastructure.storage_minio import MinioImageStorage

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
JPEG_CONTENT_TYPES = frozenset({"image/jpeg", "image/jpg"})


def _token_ok(provided: str | None, expected: str) -> bool:
    if not provided or not expected or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


@router.post("/internal/products")
async def create_product(
    title: Annotated[str, Form(min_length=1, max_length=500)],
    photo_file_unique_id: Annotated[str, Form(min_length=1, max_length=255)],
    file: Annotated[UploadFile, File()],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
    products: Annotated[SqlProductRepository, Depends(get_product_repository)],
    images: Annotated[MinioImageStorage, Depends(get_image_storage)],
    x_service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None,
) -> JSONResponse:
    if not _token_ok(x_service_token, settings.service_token):
        raise HTTPException(status_code=401, detail="invalid service token")

    content_type = (file.content_type or "").lower()
    if content_type not in JPEG_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="only JPEG images are supported")

    data = await file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="image is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image is too large")
    if len(data) < 3 or not data.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=422, detail="file is not a valid JPEG image")

    try:
        result = await CreateProduct(products, images).execute(
            title=title,
            photo_file_unique_id=photo_file_unique_id,
            image=data,
            content_type="image/jpeg",
        )
    except InvalidTitleError as exc:
        raise HTTPException(status_code=422, detail="title is empty") from exc

    try:
        await session.commit()
    except Exception:
        if result.created:
            try:
                await images.delete(result.product.image_key)
            except Exception:
                logger.exception(
                    "Failed to remove image %s after database commit failure",
                    result.product.image_key,
                )
        raise

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
