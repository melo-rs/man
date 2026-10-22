from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BOOLEAN,
    INT,
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
)
from sqlalchemy import (
    UUID as SQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from man.kit.db.models import RecordModel


class Offer(RecordModel):
    __tablename__ = "offers"

    __table_args__ = (
        CheckConstraint(
            "promo_price > 0",
            name="promo_price_positive",
        ),
        CheckConstraint(
            "ends_at > starts_at",
            name="ends_after_start",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        SQLUUID,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    promo_price: Mapped[int] = mapped_column(
        INT,
        nullable=False,
    )

    starts_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    ends_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        BOOLEAN,
        nullable=False,
        default=True,
    )
