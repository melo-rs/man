import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncEngine

from man.app import configure_cors, create_app, lifespan
from man.config import settings


def test_openapi_exposes_products_and_query_pagination(app: FastAPI) -> None:
    schema = app.openapi()
    assert set(schema["paths"]) == {"/v1/products", "/v1/products/{id}"}
    list_operation = schema["paths"]["/v1/products"]["get"]
    assert "requestBody" not in list_operation
    assert {p["name"] for p in list_operation["parameters"]} == {
        "first",
        "last",
        "before",
        "after",
    }
    assert all(p["in"] == "query" for p in list_operation["parameters"])


def test_app_instances_do_not_share_dependency_overrides() -> None:
    first, second = create_app(), create_app()

    def dependency() -> str:
        return "original"

    first.dependency_overrides[dependency] = lambda: "override"
    assert dependency not in second.dependency_overrides


@pytest.mark.parametrize(
    "origin", ["http://localhost:3000", "https://external.example"]
)
def test_cors_frontend_and_external_origins(
    origin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["http://localhost:3000"])
    app = FastAPI()
    configure_cors(app)

    @app.get("/")
    async def endpoint() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        preflight = client.options(
            "/",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        response = client.get("/", headers={"Origin": origin})
        without_origin = client.get("/")
    assert preflight.status_code == response.status_code == 200
    if origin == "http://localhost:3000":
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
    else:
        assert response.headers["access-control-allow-origin"] == "*"
        assert "access-control-allow-credentials" not in response.headers
    assert "access-control-allow-origin" not in without_origin.headers


@pytest.mark.anyio
@pytest.mark.parametrize("fail", [False, True])
async def test_lifespan_always_disposes_engine(
    fail: bool, mocker: MockerFixture
) -> None:
    engine = mocker.Mock(spec=AsyncEngine)
    engine.dispose = mocker.AsyncMock()
    mocker.patch("man.app.create_async_engine", return_value=engine)
    app = create_app()
    if fail:
        with pytest.raises(RuntimeError, match="during lifespan"):
            async with lifespan(app):
                raise RuntimeError("during lifespan")
    else:
        async with lifespan(app) as state:
            assert state["async_engine"] is engine
    engine.dispose.assert_awaited_once_with()
