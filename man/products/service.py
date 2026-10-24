from collections.abc import Sequence
from uuid import UUID

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
        )

        return await product_repository.create(product, flush=True)


products = ProductService()
