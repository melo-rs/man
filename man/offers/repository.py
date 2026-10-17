from man.kit.repository.base import RepositoryBase
from man.models.offer import Offer


class OfferRepository(RepositoryBase[Offer]):
    model = Offer
