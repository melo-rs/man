"""Create database-backed authentication sessions.

Revision ID: 0003
Revises: 5bcef2dc1018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "5bcef2dc1018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("token_hash", name=op.f("auth_sessions_pkey")),
    )


def downgrade() -> None:
    op.drop_table("auth_sessions")
