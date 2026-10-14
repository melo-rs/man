from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import UUID7

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


@router.get("/products/{id}")
async def retrieve_product(
    id: UUID7, session: AsyncSession = Depends(get_db_session)
) -> ProductSchema:
    product = await product_service.get(session, id)

    if not product:
        raise ProductMissing(id)

    return ProductSchema.model_validate(product)


@router.post("/products")
async def create_product(
    create_schema: ProductCreate, session: AsyncSession = Depends(get_db_session)
) -> ProductSchema:
    product = await product_service.create(session, create_schema)
    return ProductSchema.model_validate(product)
