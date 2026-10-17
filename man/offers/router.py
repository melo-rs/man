from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import UUID7

from man.exceptions import ResourceMissing
from man.kit.pagination import ListResource, PaginationParamsQuery
from man.postgres import AsyncSession, get_db_session
from man.offers.schemas import OfferCreate, OfferSchema
from man.offers.service import offers as offer_service

router = APIRouter()


class OfferMissing(ResourceMissing):
    def __init__(self, id: UUID):
        super().__init__(f"The offer {id} could not be found")


@router.get("/offers")
async def list_offers(
    pagination_params: PaginationParamsQuery,
    session: AsyncSession = Depends(get_db_session),
) -> ListResource[OfferSchema]:
    offers, total_count = await offer_service.list(session, pagination_params)
    return ListResource[OfferSchema].from_paginated_results(
        [OfferSchema.model_validate(offer) for offer in offers], total_count
    )


@router.get("/offers/{id}")
async def retrieve_offer(
    id: UUID7, session: AsyncSession = Depends(get_db_session)
) -> OfferSchema:
    offer = await offer_service.get(session, id)
    if not offer:
        raise OfferMissing(id)
    return OfferSchema.model_validate(offer)


@router.post("/offers")
async def create_offer(
    create_schema: OfferCreate, session: AsyncSession = Depends(get_db_session)
) -> OfferSchema:
    offer = await offer_service.create(session, create_schema)
    return OfferSchema.model_validate(offer)