from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from man.models import Product

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


async def test_offer_responses_include_current_product_image(
    client: AsyncClient, product: Product, session
) -> None:
    now = datetime.now(UTC)
    response = await client.post(
        "/v1/offers",
        json={
            "product_id": str(product.id),
            "promo_price": 500,
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=7)).isoformat(),
        },
    )
    assert response.status_code == 200
    offer = response.json()
    assert offer["thumb_url"] == product.thumb_url

    current_product = await session.get(Product, product.id)
    assert current_product is not None
    current_product.thumb_url = "https://example.com/new-product.png"
    await session.flush()

    retrieved = await client.get(f"/v1/offers/{offer['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["thumb_url"] == current_product.thumb_url

    listed = await client.get("/v1/offers", params={"first": 10})
    assert listed.status_code == 200
    assert listed.json()["items"][0]["thumb_url"] == current_product.thumb_url
