from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import UUID7

from man.exceptions import ResourceMissing
from man.kit.pagination import ListResource, PaginationParams
from man.models.product import Product
from man.postgres import AsyncSession, get_db_session
from man.products.repository import ProductRepository
from man.products.schemas import ProductCreate, ProductSchema

router = APIRouter()


class ProductMissing(ResourceMissing):
    def __init__(self, id: UUID):
        super().__init__(f"The product {id} could not be found")


@router.get("/products")
async def list_products(
    pagination_params: PaginationParams, session: AsyncSession = Depends(get_db_session)
) -> ListResource[ProductSchema]:
    product_repository = ProductRepository.from_session(session)

    statement = product_repository.get_base_statement()
    products = product_repository.paginate(statement, pagination_params)

    return ListResource[ProductSchema].model_validate(products)


@router.get("/products/{id}")
async def retrieve_product(id: UUID7, session: AsyncSession = Depends(get_db_session)) -> ProductSchema:
    product_repository = ProductRepository.from_session(session)
    product = product_repository.get_by_id(id)

    if not product:
        raise ProductMissing(id)

    return ProductSchema.model_validate(product)


@router.post("/products")
async def create_product(
    create_schema: ProductCreate, session: AsyncSession = Depends(get_db_session)
) -> ProductSchema:
    product = Product(name=create_schema.name, description=create_schema.description, price=create_schema.price)

    session.add(product)
    await session.flush()

    return ProductSchema.model_validate(product)
