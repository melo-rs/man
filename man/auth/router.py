from fastapi import APIRouter, Depends, Response

from man.auth.schemas import LoginRequest
from man.auth.service import SESSION_COOKIE, SESSION_DURATION, auth
from man.config import settings
from man.postgres import AsyncSession, get_db_session

router = APIRouter()


@router.post("/login", status_code=204)
async def login(
    credentials: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> Response:
    token = await auth.create_session(session, credentials.password)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        path="/v1",
        secure=settings.is_production(),
        httponly=True,
        samesite="lax",
    )
    return response
