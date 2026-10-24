from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import UUID7

from man.auth.dependencies import require_authentication
from man.exceptions import ResourceMissing
from man.kit.pagination import ListResource, PaginationParamsQuery
from man.postgres import AsyncSession, get_db_session
from man.products.schemas import ProductCreate, ProductSchema
from man.products.service import products as product_service

router = APIRouter()


class ProductMissing(ResourceMissing):
    def __init__(self, id: UUID):
        super().__init__(f"The product {id} could not be found")


@router.get("/products")
async def list_products(
    pagination_params: PaginationParamsQuery,
    session: AsyncSession = Depends(get_db_session),
) -> ListResource[ProductSchema]:
    products, total_count = await product_service.list(session, pagination_params)

    return ListResource[ProductSchema].from_paginated_results(
        [ProductSchema.model_validate(product) for product in products], total_count
    )


@router.get("/product-option-prices")
async def list_product_option_prices(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, dict[str, int]]:
    return await product_service.list_option_prices(session)


@router.get("/products/{id}")
async def retrieve_product(
    id: UUID7, session: AsyncSession = Depends(get_db_session)
) -> ProductSchema:
    product = await product_service.get(session, id)

    if not product:
        raise ProductMissing(id)

    return ProductSchema.model_validate(product)


@router.post("/products", dependencies=[Depends(require_authentication)])
async def create_product(
    create_schema: ProductCreate, session: AsyncSession = Depends(get_db_session)
) -> ProductSchema:
    product = await product_service.create(session, create_schema)
    return ProductSchema.model_validate(product)


@router.put("/products/{id}", dependencies=[Depends(require_authentication)])
async def update_product(
    id: UUID7,
    update_schema: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ProductSchema:
    product = await product_service.update(session, id, update_schema)
    if not product:
        raise ProductMissing(id)
    return ProductSchema.model_validate(product)


@router.delete(
    "/products/{id}", dependencies=[Depends(require_authentication)], status_code=204
)
async def delete_product(
    id: UUID7, session: AsyncSession = Depends(get_db_session)
) -> None:
    if not await product_service.delete(session, id):
        raise ProductMissing(id)
