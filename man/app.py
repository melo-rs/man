import contextlib
from collections.abc import AsyncGenerator
from typing import TypedDict

from fastapi import FastAPI
from man.config import settings
from man.exception_handlers import add_exception_handlers
from man.health.router import router as health_router
from man.kit.cors import CORSConfig, CORSMatcherMiddleware
from man.kit.db.postgres import (
    AsyncEngine,
    AsyncSessionMaker,
    create_async_sessionmaker,
)
from man.postgres import AsyncSessionMiddleware, create_async_engine
from man.router import router
from starlette.types import Scope


def configure_cors(app: FastAPI):
    configs: list[CORSConfig] = []

    # Man frontend CORS configuration
    if settings.CORS_ORIGINS:

        def man_frontend_matcher(origin: str, scope: Scope) -> bool:
            return origin in settings.CORS_ORIGINS

        man_frontend_config = CORSConfig(
            man_frontend_matcher,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        configs.append(man_frontend_config)

    service_config = CORSConfig(
        lambda origin, scope: True,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization"],
    )

    configs.append(service_config)

    app.add_middleware(CORSMatcherMiddleware, configs=configs)


class State(TypedDict):
    async_engine: AsyncEngine
    async_sessionmaker: AsyncSessionMaker


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[State]:
    async_engine = create_async_engine()

    async_sessionmaker = create_async_sessionmaker(async_engine)

    yield {
        "async_engine": async_engine,
        "async_sessionmaker": async_sessionmaker,
    }

    await async_engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(AsyncSessionMiddleware)

configure_cors(app)
add_exception_handlers(app)

# /healthz
app.include_router(health_router)

# /v1
app.include_router(router)
