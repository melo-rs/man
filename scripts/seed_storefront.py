"""Import the storefront's initial catalogue and seven-day offers.

Run after migrations with ``.venv/bin/python scripts/seed_storefront.py``.
Existing products and currently active offers are left unchanged.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from man.models import Offer, Product
from man.postgres import create_async_engine

DATA_DIR = Path(__file__).parent / "data"


def cents(reais: str) -> int:
    value = Decimal(reais) * 100
    if value != value.to_integral_value():
        raise ValueError(f"Price has fractional centavos: {reais}")
    return int(value)


async def seed() -> None:
    product_data = json.loads((DATA_DIR / "products.json").read_text())
    offer_data = json.loads((DATA_DIR / "offers.json").read_text())
    blob_manifest = DATA_DIR / "blob_urls.json"
    if not blob_manifest.is_file():
        raise RuntimeError(
            "Upload storefront images with scripts/migrate_storefront_images.py first"
        )
    blob_urls = json.loads(blob_manifest.read_text())
    engine = create_async_engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    created_products = 0
    created_offers = 0

    try:
        async with sessionmaker() as session:
            existing = (await session.execute(select(Product))).scalars().all()
            products_by_name = {product.name: product for product in existing}

            for record in product_data:
                if record["name"] in products_by_name:
                    continue
                product = Product(
                    name=record["name"],
                    description=record["description"],
                    price=cents(
                        record["original_price_reais"] or record["price_reais"]
                    ),
                    thumb_url=blob_urls[record["gallery"][0]],
                    category=record["category"],
                    unit=record["unit"],
                    gallery_urls=[blob_urls[path] for path in record["gallery"]],
                    options=record["options"],
                )
                session.add(product)
                products_by_name[product.name] = product
                created_products += 1

            await session.flush()
            now = datetime.now(UTC)
            ends_at = now + timedelta(days=7)
            existing_offers = (await session.execute(select(Offer))).scalars().all()
            active_product_ids = {
                offer.product_id
                for offer in existing_offers
                if offer.is_active and offer.starts_at <= now < offer.ends_at
            }

            for record in offer_data:
                product = products_by_name[record["name"]]
                if product.id in active_product_ids:
                    continue
                promo_price = cents(record["promo_price_reais"])
                if promo_price >= product.price:
                    raise ValueError(f"Offer must be cheaper than {product.name}")
                session.add(
                    Offer(
                        product_id=product.id,
                        promo_price=promo_price,
                        starts_at=now,
                        ends_at=ends_at,
                        is_active=True,
                    )
                )
                created_offers += 1

            await session.commit()
    finally:
        await engine.dispose()

    print(
        f"Created {created_products} products and {created_offers} offers (expires {ends_at.isoformat()})."
    )


if __name__ == "__main__":
    asyncio.run(seed())
