from sqlalchemy import INT, TEXT
from sqlalchemy.dialects.postgresql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from man.kit.db.models import RecordModel


class Product(RecordModel):
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(TEXT, nullable=False)
    price: Mapped[int] = mapped_column(INT, nullable=False)
