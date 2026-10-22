import hashlib
import secrets
from datetime import timedelta

from man.config import settings
from man.exceptions import Unauthorized
from man.kit.utils import utc_now
from man.models.auth_session import AuthSession
from man.postgres import AsyncSession

SESSION_DURATION = timedelta(days=30)
SESSION_COOKIE = "man_session"


class AuthService:
    @staticmethod
    def hash_session_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_session(self, session: AsyncSession, password: str) -> str:
        configured_password = settings.PASSWORD.get_secret_value()
        if not configured_password:
            raise RuntimeError("MAN_PASSWORD must be configured")
        if not secrets.compare_digest(
            password.encode("utf-8"), configured_password.encode("utf-8")
        ):
            raise Unauthorized("Invalid credentials")

        token = secrets.token_urlsafe(32)
        created_at = utc_now()
        session.add(
            AuthSession(
                token_hash=self.hash_session_token(token),
                created_at=created_at,
                expires_at=created_at + SESSION_DURATION,
            )
        )
        await session.flush()
        return token


auth = AuthService()
