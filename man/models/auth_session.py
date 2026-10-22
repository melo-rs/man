from datetime import datetime

from sqlalchemy import CHAR, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from man.kit.db.models import Model


class AuthSession(Model):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
