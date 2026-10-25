"""products table

Revision ID: 0001_products
Revises:
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_products"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("image_key", sa.String(length=1024), nullable=False),
        sa.Column("photo_file_unique_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("photo_file_unique_id", name="uq_products_photo_file_unique_id"),
    )


def downgrade() -> None:
    op.drop_table("products")
