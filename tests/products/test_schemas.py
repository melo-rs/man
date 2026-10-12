from datetime import UTC, datetime
from typing import Any
from uuid import uuid7

import pytest
from pydantic import ValidationError

from man.products.schemas import ProductCreate, ProductSchema


def test_valid_product() -> None:
    product = ProductCreate(name="Café", description="A useful product", price=1000)
    assert product.model_dump() == {
        "name": "Café",
        "description": "A useful product",
        "price": 1000,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", ""), ("description", ""), ("price", 0), ("price", -1)],
)
def test_invalid_product(field: str, value: Any) -> None:
    payload = {"name": "Product", "description": "Description", "price": 1000}
    payload[field] = value
    with pytest.raises(ValidationError) as exc:
        ProductCreate.model_validate(payload)
    assert exc.value.errors()[0]["loc"] == (field,)


def test_product_response_serializes_uuid_and_timestamps() -> None:
    id = uuid7()
    schema = ProductSchema(
        id=id,
        name="Product",
        description="Description",
        price=1000,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        modified_at=None,
    )
    payload = schema.model_dump(mode="json")
    assert payload["id"] == str(id)
    assert payload["created_at"] == "2026-01-01T00:00:00Z"
    assert payload["modified_at"] is None
