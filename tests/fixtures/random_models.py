from uuid import UUID

import pytest

from man.models import Product
from tests.fixtures.database import SaveFixture


async def create_product(
    save_fixture: SaveFixture,
    *,
    name: str = "Product",
    description: str = "Description",
    price: int = 1000,
    id: UUID | None = None,
) -> Product:
    product = Product(
        id=id or Product.generate_id(),
        name=name,
        description=description,
        price=price,
    )
    await save_fixture(product)
    return product


@pytest.fixture
async def product(save_fixture: SaveFixture) -> Product:
    return await create_product(save_fixture)
