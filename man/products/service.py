from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from man.kit.pagination import PaginationParams
from man.models import Product
from man.products.repository import ProductRepository
from man.products.schemas import ProductCreate


class ProductService:
    async def list(
        self, session: AsyncSession, pagination_params: PaginationParams
    ) -> tuple[Sequence[Product], int]:
        product_repository = ProductRepository.from_session(session)
        statement = product_repository.get_base_statement()

        return await product_repository.paginate(statement, pagination_params)

    async def get(self, session: AsyncSession, id: UUID) -> Product | None:
        product_repository = ProductRepository.from_session(session)
        return await product_repository.get_by_id(id)

    async def list_option_prices(
        self, session: AsyncSession
    ) -> dict[str, dict[str, int]]:
        rows = await session.execute(select(Product.id, Product.option_prices))
        return {str(id): prices for id, prices in rows.all()}

    async def create(
        self, session: AsyncSession, create_schema: ProductCreate
    ) -> Product:
        product_repository = ProductRepository.from_session(session)

        product = Product(
            name=create_schema.name,
            description=create_schema.description,
            price=create_schema.price,
            thumb_url=create_schema.thumb_url,
            category=create_schema.category,
            unit=create_schema.unit,
            gallery_urls=create_schema.gallery_urls,
            options=create_schema.options,
            option_prices=create_schema.option_prices,
        )

        return await product_repository.create(product, flush=True)

    async def update(
        self, session: AsyncSession, id: UUID, update_schema: ProductCreate
    ) -> Product | None:
        repository = ProductRepository.from_session(session)
        product = await repository.get_by_id(id)
        if product is None:
            return None
        product.set_modified_at()
        return await repository.update(
            product, update_dict=update_schema.model_dump(), flush=True
        )

    async def delete(self, session: AsyncSession, id: UUID) -> bool:
        product = await ProductRepository.from_session(session).get_by_id(id)
        if product is None:
            return False
        await session.delete(product)
        await session.flush()
        return True


products = ProductService()
