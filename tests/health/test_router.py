import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from man.health.router import healthz


@pytest.mark.anyio
async def test_database_failure_becomes_service_unavailable(
    mocker: MockerFixture,
) -> None:
    session = mocker.AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError("database unavailable")
    with pytest.raises(HTTPException) as exc:
        await healthz(session)
    assert exc.value.status_code == 503
    assert exc.value.detail == "Postgres is not available"
