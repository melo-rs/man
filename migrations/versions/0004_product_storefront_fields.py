"""Add storefront display fields to products.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "category", sa.VARCHAR(100), nullable=False, server_default="Produtos"
        ),
    )
    op.add_column(
        "products",
        sa.Column("unit", sa.VARCHAR(100), nullable=False, server_default="unidade"),
    )
    op.add_column(
        "products",
        sa.Column(
            "gallery_urls",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "options", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    for column in ("category", "unit", "gallery_urls", "options"):
        op.alter_column("products", column, server_default=None)


def downgrade() -> None:
    for column in ("options", "gallery_urls", "unit", "category"):
        op.drop_column("products", column)
