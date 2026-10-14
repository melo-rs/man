from man.kit.repository.base import RepositoryBase
from man.models.product import Product


class ProductRepository(RepositoryBase[Product]):
    model = Product
