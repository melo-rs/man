from collections.abc import AsyncIterator
from typing import Literal

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from starlette.types import Receive, Scope, Send

from man.app import create_app
from man.kit.db.postgres import AsyncSessionMaker


@pytest.fixture(scope="session")
def anyio_backend() -> Literal["asyncio"]:
    return "asyncio"


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(
    app: FastAPI,
    connection: AsyncConnection,
    session: AsyncSession,
    sessionmaker: AsyncSessionMaker,
) -> AsyncIterator[httpx.AsyncClient]:
    async def app_with_state(scope: Scope, receive: Receive, send: Send) -> None:
        # Finish fixture setup before opening another savepoint on this connection.
        # Clearing the identity map also prevents assertions from reading stale objects.
        await session.commit()
        session.expunge_all()
        scope.setdefault("state", {}).update(
            async_engine=connection.engine,
            async_sessionmaker=sessionmaker,
        )
        await app(scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_with_state),
        base_url="http://test",
    ) as client:
        yield client
