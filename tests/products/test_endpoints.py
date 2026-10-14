from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID, uuid7

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.types import Receive, Scope, Send

from man.app import create_app
from man.exceptions import ManError
from man.models import Product
from man.postgres import get_db_session
from man.products.repository import ProductRepository
from tests.fixtures.database import SaveFixture
from tests.fixtures.random_models import create_product

pytestmark = [pytest.mark.anyio, pytest.mark.integration]
PAYLOAD = {"name": "Product", "description": "Description", "price": 1000}


@pytest.fixture
def request_session_app() -> FastAPI:
    return create_app()


@pytest.fixture
async def request_session_client(
    request_session_app: FastAPI, session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    """Exercise production session handling inside the test's outer transaction."""
    sessionmaker = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async def app_with_state(scope: Scope, receive: Receive, send: Send) -> None:
        await session.commit()
        session.expunge_all()
        scope.setdefault("state", {}).update(async_sessionmaker=sessionmaker)
        await request_session_app(scope, receive, send)

    async with AsyncClient(
        transport=ASGITransport(app=app_with_state), base_url="http://test"
    ) as client:
        yield client


async def test_create_then_retrieve_in_another_request(client: AsyncClient) -> None:
    response = await client.post("/v1/products", json=PAYLOAD)
    assert response.status_code == 200
    product = response.json()
    assert UUID(product["id"]).version == 7
    assert product["created_at"]
    assert product["modified_at"] is None
    assert {field: product[field] for field in PAYLOAD} == PAYLOAD

    retrieved = await client.get(f"/v1/products/{product['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == product

    listed = await client.get("/v1/products", params={"first": 1})
    assert listed.status_code == 200
    assert listed.json() == {"items": [product], "pagination": {"total_count": 1}}


async def test_retrieve_fixture_product(client: AsyncClient, product: Product) -> None:
    response = await client.get(f"/v1/products/{product.id}")
    assert response.status_code == 200
    assert response.json()["name"] == product.name
    assert response.json()["price"] == product.price


async def test_empty_list(client: AsyncClient) -> None:
    response = await client.get("/v1/products", params={"first": 10})
    assert response.status_code == 200
    assert response.json() == {"items": [], "pagination": {"total_count": 0}}


async def test_missing_product(client: AsyncClient) -> None:
    id = uuid7()
    response = await client.get(f"/v1/products/{id}")
    assert response.status_code == 404
    assert response.json() == {
        "status_code": 404,
        "message": f"The product {id} could not be found",
    }


@pytest.mark.parametrize("id", ["invalid", "00000000-0000-4000-8000-000000000001"])
async def test_invalid_product_id(client: AsyncClient, id: str) -> None:
    response = await client.get(f"/v1/products/{id}")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "id"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {**PAYLOAD, "name": ""},
        {**PAYLOAD, "description": ""},
        {**PAYLOAD, "price": 0},
        {**PAYLOAD, "price": -1},
    ],
)
async def test_invalid_creation(client: AsyncClient, payload: dict[str, Any]) -> None:
    response = await client.post("/v1/products", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]
    listed = await client.get("/v1/products", params={"first": 1})
    assert listed.json()["pagination"]["total_count"] == 0


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"first": 0},
        {"last": 101},
        {"first": 1, "last": 1},
        {"first": 1, "before": "00000000-0000-7000-8000-000000000001"},
        {"last": 1, "after": "00000000-0000-7000-8000-000000000001"},
        {"first": 1, "after": "invalid"},
    ],
)
async def test_invalid_query_pagination(
    client: AsyncClient, params: dict[str, Any]
) -> None:
    response = await client.get("/v1/products", params=params)
    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.parametrize("forward", [True, False])
async def test_pagination_queries(
    client: AsyncClient, save_fixture: SaveFixture, forward: bool
) -> None:
    products = sorted(
        [await create_product(save_fixture) for _ in range(5)],
        key=lambda product: product.id,
    )
    params = (
        {"first": 2, "after": str(products[2].id)}
        if forward
        else {"last": 2, "before": str(products[2].id)}
    )
    response = await client.get("/v1/products", params=params)
    assert response.status_code == 200
    expected = [products[1], products[0]] if forward else [products[3], products[4]]
    assert [item["id"] for item in response.json()["items"]] == [
        str(p.id) for p in expected
    ]
    assert response.json()["pagination"]["total_count"] == 5


async def test_each_request_uses_a_fresh_session(
    request_session_app: FastAPI,
    request_session_client: AsyncClient,
    session: AsyncSession,
) -> None:
    request_sessions: list[AsyncSession] = []

    @request_session_app.get("/test/session")
    async def capture_session(
        db: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> None:
        request_sessions.append(db)

    assert (await request_session_client.get("/test/session")).status_code == 200
    assert (await request_session_client.get("/test/session")).status_code == 200
    assert len(request_sessions) == 2
    assert request_sessions[0] is not request_sessions[1]
    assert all(db is not session for db in request_sessions)


async def test_failed_request_rolls_back_and_next_request_succeeds(
    request_session_app: FastAPI,
    request_session_client: AsyncClient,
    session: AsyncSession,
    product: Product,
) -> None:
    failed_id = uuid7()

    @request_session_app.post("/test/rollback")
    async def failing_endpoint(
        db: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> None:
        db.add(Product(id=failed_id, **PAYLOAD))
        await db.flush()
        raise ManError("Rollback this request", status_code=400)

    response = await request_session_client.post("/test/rollback")
    assert response.status_code == 400
    assert await ProductRepository(session).get_by_id(failed_id) is None
    assert (
        await request_session_client.get(f"/v1/products/{product.id}")
    ).status_code == 200
    assert (
        await request_session_client.post("/v1/products", json=PAYLOAD)
    ).status_code == 200
