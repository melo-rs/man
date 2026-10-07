from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from man.postgres import AsyncSession, get_db_session

router = APIRouter(tags=["health"], include_in_schema=False)


@router.get("/healthz")
async def healthz(
    session: AsyncSession = Depends(get_db_session),
):
    try:
        await session.execute(select(1))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=503, detail="Postgres is not available") from e

    return {"status": "ok"}
