from uuid import UUID, uuid7

import pytest
from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from man.kit.pagination import PaginationParams
from man.models import Product
from man.products.repository import ProductRepository
from tests.fixtures.database import SaveFixture
from tests.fixtures.random_objects import create_product

pytestmark = [pytest.mark.anyio, pytest.mark.integration]
IDS = tuple(UUID(f"00000000-0000-7000-8000-{i:012x}") for i in range(1, 6))


async def test_retrieval_and_filtered_queries(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    product = await create_product(save_fixture, name="Visible", price=1000)
    await create_product(save_fixture, name="Hidden", price=100)
    repository = ProductRepository.from_session(session)
    assert await repository.get_by_id(product.id) == product
    assert await repository.get_by_id(uuid7()) is None
    statement = repository.get_base_statement().where(Product.price >= 1000)
    assert await repository.get_one(statement) == product
    assert await repository.get_one_or_none(statement) == product
    assert await repository.get_all(statement) == [product]
    assert (
        await repository.get_one_or_none(statement.where(Product.price > 1000)) is None
    )


async def test_get_one_enforces_cardinality(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    repository = ProductRepository(session)
    with pytest.raises(NoResultFound):
        await repository.get_one(repository.get_base_statement())
    await create_product(save_fixture)
    await create_product(save_fixture)
    with pytest.raises(MultipleResultsFound):
        await repository.get_one(repository.get_base_statement())


async def test_create_and_update_persist_values(session: AsyncSession) -> None:
    repository = ProductRepository(session)
    product = await repository.create(
        Product(name="Original", description="Description", price=100), flush=True
    )
    id = product.id
    await repository.update(
        product, update_dict={"name": "Updated", "price": 200}, flush=True
    )
    session.expunge_all()
    loaded = await repository.get_by_id(id)
    assert loaded is not None
    assert loaded.name == "Updated"
    assert loaded.price == 200
    assert loaded.modified_at is not None

    loaded.description = "Changed directly"
    await repository.update(loaded)
    await session.flush()
    session.expunge_all()
    reloaded = await repository.get_by_id(id)
    assert reloaded is not None
    assert reloaded.description == "Changed directly"


@pytest.mark.parametrize(
    ("pagination", "expected"),
    [
        (PaginationParams(first=2), [4, 3]),
        (PaginationParams(last=2), [0, 1]),
        (PaginationParams(first=2, after=IDS[2]), [1, 0]),
        (PaginationParams(last=2, before=IDS[2]), [3, 4]),
        (PaginationParams(first=2, after=IDS[0]), []),
        (PaginationParams(last=2, before=IDS[4]), []),
        (PaginationParams(first=10), [4, 3, 2, 1, 0]),
    ],
)
async def test_cursor_pagination(
    pagination: PaginationParams,
    expected: list[int],
    session: AsyncSession,
    save_fixture: SaveFixture,
) -> None:
    products = [await create_product(save_fixture, id=id) for id in IDS]
    repository = ProductRepository(session)
    items, total_count = await repository.paginate(
        repository.get_base_statement(), pagination
    )
    assert [item.id for item in items] == [products[i].id for i in expected]
    assert total_count == 5


async def test_pagination_count_respects_filters_before_cursors(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    for i, id in enumerate(IDS):
        await create_product(save_fixture, id=id, price=(i + 1) * 100)
    repository = ProductRepository(session)
    statement = select(Product).where(Product.price >= 300)
    items, count = await repository.paginate(
        statement, PaginationParams(first=1, after=IDS[4])
    )
    assert [item.id for item in items] == [IDS[3]]
    assert count == 3


async def test_empty_pagination(session: AsyncSession) -> None:
    repository = ProductRepository(session)
    assert await repository.paginate(
        repository.get_base_statement(), PaginationParams(first=10)
    ) == ([], 0)
