from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from man.exceptions import ResourceMissing
from man.kit.pagination import PaginationParams
from man.models import Offer, Product
from man.offers.repository import OfferRepository
from man.offers.schemas import OfferCreate, OfferUpdate


class OfferService:
    async def list(
        self, session: AsyncSession, pagination_params: PaginationParams
    ) -> tuple[Sequence[Offer], int]:
        offer_repository = OfferRepository.from_session(session)
        statement = offer_repository.get_base_statement()
        return await offer_repository.paginate(statement, pagination_params)

    async def get(self, session: AsyncSession, id: UUID) -> Offer | None:
        offer_repository = OfferRepository.from_session(session)
        return await offer_repository.get_by_id(id)

    async def create(self, session: AsyncSession, create_schema: OfferCreate) -> Offer:
        # Verifica se o produto existe antes de criar a oferta
        product = await session.get(Product, create_schema.product_id)
        if not product:
            raise ResourceMissing(
                f"The product {create_schema.product_id} could not be found"
            )

        offer_repository = OfferRepository.from_session(session)
        offer = Offer(
            product=product,
            promo_price=create_schema.promo_price,
            starts_at=create_schema.starts_at,
            ends_at=create_schema.ends_at,
            is_active=True,
        )
        return await offer_repository.create(offer, flush=True)

    async def update(
        self, session: AsyncSession, id: UUID, update_schema: OfferUpdate
    ) -> Offer | None:
        repository = OfferRepository.from_session(session)
        offer = await repository.get_by_id(id)
        if offer is None:
            return None
        product = await session.get(Product, update_schema.product_id)
        if product is None:
            raise ResourceMissing(
                f"The product {update_schema.product_id} could not be found"
            )
        offer.set_modified_at()
        return await repository.update(
            offer,
            update_dict={
                **update_schema.model_dump(exclude={"product_id"}),
                "product": product,
            },
            flush=True,
        )

    async def delete(self, session: AsyncSession, id: UUID) -> bool:
        offer = await OfferRepository.from_session(session).get_by_id(id)
        if offer is None:
            return False
        await session.delete(offer)
        await session.flush()
        return True


offers = OfferService()
