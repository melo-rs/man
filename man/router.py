from fastapi import APIRouter, Depends

from man.auth.dependencies import require_authentication
from man.auth.router import router as auth_router
from man.files.router import router as files_router
from man.offers.router import router as offers_router
from man.products.router import router as products_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router)
router.include_router(products_router)
router.include_router(offers_router)
router.include_router(files_router, dependencies=[Depends(require_authentication)])
