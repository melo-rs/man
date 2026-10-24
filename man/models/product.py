from sqlalchemy import INT, TEXT
from sqlalchemy.dialects.postgresql import JSONB, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from man.kit.db.models import RecordModel


class Product(RecordModel):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(TEXT, nullable=False)
    price: Mapped[int] = mapped_column(INT, nullable=False)
    thumb_url: Mapped[str] = mapped_column(TEXT, nullable=False)
    category: Mapped[str] = mapped_column(
        VARCHAR(100), nullable=False, default="Produtos"
    )
    unit: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, default="unidade")
    gallery_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    options: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    option_prices: Mapped[dict[str, int]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
