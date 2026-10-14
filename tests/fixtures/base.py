from collections.abc import AsyncGenerator
from typing import Any, Literal

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.types import Receive, Scope, Send

from man.app import app as man_app
from man.postgres import AsyncSession, get_db_session


class HTTPClient(httpx.AsyncClient):
    """
    Test client that mimics production behavior by clearing session before requests.

    Each HTTP request gets a fresh database session. This client
    simulates that by expunging all objects from the test session before each
    request, catching lazy='raise' errors that would otherwise pass in tests.
    """

    def __init__(self, session: AsyncSession, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._session = session

    async def request(self, *args: Any, **kwargs: Any) -> httpx.Response:
        """Expunge session before each request to simulate production."""
        self._session.expunge_all()
        return await super().request(*args, **kwargs)


@pytest.fixture
async def app(session: AsyncSession) -> AsyncGenerator[FastAPI]:
    man_app.dependency_overrides[get_db_session] = lambda: session
    yield man_app
    man_app.dependency_overrides.pop(get_db_session)


@pytest.fixture(scope="session", autouse=True)
def anyio_backend() -> Literal["asyncio"]:
    return "asyncio"


@pytest.fixture
async def client(
    app: FastAPI,
    session: AsyncSession,
) -> AsyncGenerator[HTTPClient]:
    sessionmaker = async_sessionmaker(bind=session.bind, expire_on_commit=False)

    async def app_with_state(scope: Scope, receive: Receive, send: Send) -> None:
        scope.setdefault("state", {}).update(async_sessionmaker=sessionmaker)
        await app(scope, receive, send)

    async with HTTPClient(
        session=session,
        transport=httpx.ASGITransport(app=app_with_state),
        base_url="http://test",
    ) as client:
        yield client
