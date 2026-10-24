import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from man.app import configure_cors


@pytest.mark.anyio
async def test_api_allows_credentialed_requests_from_other_origins() -> None:
    app = FastAPI()
    configure_cors(app)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    origin = "https://another-frontend.example"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        preflight = await client.options(
            "/ping",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        response = await client.get("/ping", headers={"Origin": origin})

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-credentials"] == "true"
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
