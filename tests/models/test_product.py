from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from man.models import Model, Product


def test_model_registry_includes_products() -> None:
    assert "products" in Model.metadata.tables


@pytest.mark.anyio
@pytest.mark.integration
async def test_product_defaults_and_detached_identity(session: AsyncSession) -> None:
    product = Product(name="Product", description="Description", price=100)
    assert repr(product) == "Product(id=None)"
    before = datetime.now(UTC)
    session.add(product)
    await session.flush()
    assert product.id.version == 7
    assert before <= product.created_at <= datetime.now(UTC)
    assert product.created_at.utcoffset() == UTC.utcoffset(None)
    assert product.modified_at is None

    id = product.id
    await session.commit()
    session.expunge_all()
    assert repr(product) == f"Product(id={id!r})"
    loaded = await session.get(Product, id)
    assert loaded is not None
    assert loaded is not product
    assert loaded == product
    assert hash(loaded) == hash(product)

    loaded.set_modified_at()
    await session.flush()
    assert loaded.modified_at is not None
    assert loaded.modified_at >= loaded.created_at
