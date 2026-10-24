from sqlalchemy import select
from sqlalchemy.orm import selectinload

from man.kit.repository.base import RepositoryBase
from man.models.offer import Offer


class OfferRepository(RepositoryBase[Offer]):
    model = Offer

    def get_base_statement(self):
        return select(Offer).options(selectinload(Offer.product))
