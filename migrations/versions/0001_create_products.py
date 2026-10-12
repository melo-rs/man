"""Create products.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("name", sa.VARCHAR(255), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=False),
        sa.Column("price", sa.INT(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("products_pkey")),
    )
    op.create_index(op.f("ix_products_created_at"), "products", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_products_created_at"), table_name="products")
    op.drop_table("products")
