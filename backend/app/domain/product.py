from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Product:
    id: UUID
    title: str
    image_key: str
    photo_file_unique_id: str
    created_at: datetime
