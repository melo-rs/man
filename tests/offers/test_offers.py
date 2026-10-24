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


async def test_offer_edit_and_delete(client: AsyncClient, product: Product) -> None:
    now = datetime.now(UTC)
    payload = {
        "product_id": str(product.id),
        "promo_price": 500,
        "starts_at": now.isoformat(),
        "ends_at": (now + timedelta(days=7)).isoformat(),
    }
    created = await client.post("/v1/offers", json=payload)
    assert created.status_code == 200
    offer = created.json()
    updated = await client.put(
        f"/v1/offers/{offer['id']}",
        json={**payload, "promo_price": 400, "is_active": False},
    )
    assert updated.status_code == 200
    assert set(updated.json()) == set(offer)
    assert updated.json()["promo_price"] == 400
    assert updated.json()["is_active"] is False
    assert updated.json()["modified_at"] is not None
    assert (await client.get(f"/v1/offers/{offer['id']}")).json()["promo_price"] == 400

    assert (await client.delete(f"/v1/offers/{offer['id']}")).status_code == 204
    assert (await client.get(f"/v1/offers/{offer['id']}")).status_code == 404
