from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid7

import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from man.auth.service import SESSION_COOKIE, SESSION_DURATION, auth
from man.config import settings
from man.files.service import files
from man.kit.utils import utc_now
from man.models import AuthSession
from man.postgres import AsyncSession

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


async def test_login_creates_a_30_day_database_session(
    client: AsyncClient, session: AsyncSession
) -> None:
    before = utc_now()
    response = await client.post(
        "/v1/login", json={"password": settings.PASSWORD.get_secret_value()}
    )
    after = utc_now()

    assert response.status_code == 204
    assert response.content == b""
    cookie = response.cookies[SESSION_COOKIE]
    assert cookie
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()
    assert (
        f"Max-Age={int(SESSION_DURATION.total_seconds())}"
        in response.headers["set-cookie"]
    )
    assert "password" not in response.text.lower()

    auth_session = await session.get(AuthSession, auth.hash_session_token(cookie))
    assert auth_session is not None
    assert before <= auth_session.created_at <= after
    assert auth_session.expires_at == auth_session.created_at + timedelta(days=30)
    assert cookie != auth_session.token_hash


async def test_wrong_password_does_not_create_a_session(client: AsyncClient) -> None:
    response = await client.post("/v1/login", json={"password": "wrong-password"})
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


async def test_login_allows_credentialed_configured_frontend(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/v1/login",
        headers={"Origin": "http://localhost:3000"},
        json={"password": settings.PASSWORD.get_secret_value()},
    )
    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/v1/products", None),
        ("GET", "/v1/offers", None),
        ("POST", "/v1/files", {"mime_type": "image/png"}),
    ],
)
async def test_resource_endpoints_require_login(
    client: AsyncClient, method: str, path: str, payload: dict[str, str] | None
) -> None:
    client.cookies.clear()
    response = await client.request(method, path, json=payload)
    assert response.status_code == 401


async def test_forged_session_cookie_is_rejected(client: AsyncClient) -> None:
    client.cookies.set(SESSION_COOKIE, "made-up-token", path="/v1")
    response = await client.get("/v1/products")
    assert response.status_code == 401


async def test_health_endpoint_remains_public(client: AsyncClient) -> None:
    client.cookies.clear()
    response = await client.get("/healthz")
    assert response.status_code == 200


async def test_authenticated_requests_reach_all_resource_routers(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    create_file = AsyncMock(return_value=(uuid7(), "https://example.com/upload"))
    monkeypatch.setattr(files, "create", create_file)

    assert (await client.get("/v1/products", params={"first": 1})).status_code == 200
    assert (await client.get("/v1/offers", params={"first": 1})).status_code == 200
    assert (
        await client.post("/v1/files", json={"mime_type": "image/png"})
    ).status_code == 200
    create_file.assert_awaited_once()


async def test_expired_session_is_rejected(
    client: AsyncClient, session: AsyncSession
) -> None:
    token = client.cookies[SESSION_COOKIE]
    auth_session = await session.get(AuthSession, auth.hash_session_token(token))
    assert auth_session is not None
    auth_session.expires_at = utc_now() - timedelta(seconds=1)
    await session.flush()

    response = await client.get("/v1/products")
    assert response.status_code == 401
