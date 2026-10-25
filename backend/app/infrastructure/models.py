import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class ProductModel(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("photo_file_unique_id", name="uq_products_photo_file_unique_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    image_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    photo_file_unique_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
