import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from man.config import settings
from tests.fixtures.database import Database

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_health_with_real_postgres(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_health_database_error_response(
    client: AsyncClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "sqlalchemy.ext.asyncio.AsyncSession.execute",
        side_effect=SQLAlchemyError("database unavailable"),
    )
    response = await client.get("/healthz")
    assert response.status_code == 503
    assert response.json() == {"detail": "Postgres is not available"}


def test_real_application_lifespan(
    app: FastAPI,
    initialize_test_database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "POSTGRES_DATABASE", initialize_test_database.name)
    with TestClient(app) as client:
        assert (
            client.app_state["async_engine"].url.database
            == initialize_test_database.name
        )
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
