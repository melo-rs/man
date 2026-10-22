from fastapi import Depends, Request

from man.auth.service import SESSION_COOKIE, auth
from man.exceptions import Unauthorized
from man.kit.utils import utc_now
from man.models.auth_session import AuthSession
from man.postgres import AsyncSession, get_db_session


async def require_authentication(
    request: Request, session: AsyncSession = Depends(get_db_session)
) -> None:
    token = request.cookies.get(SESSION_COOKIE)

    if not token or len(token) > 128:
        raise Unauthorized()

    auth_session = await session.get(AuthSession, auth.hash_session_token(token))

    if auth_session is None or auth_session.expires_at <= utc_now():
        raise Unauthorized()
