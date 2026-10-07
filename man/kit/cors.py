from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


class CORSMatcher(Protocol):
    def __call__(self, origin: str, scope: Scope) -> bool: ...


@dataclass
class CORSConfig:
    matcher: CORSMatcher
    allow_origins: Sequence[str] = ()
    allow_methods: Sequence[str] = ("GET",)
    allow_headers: Sequence[str] = ()
    allow_credentials: bool = False
    expose_headers: Sequence[str] = ()
    max_age: int = 600

    def get_middleware(self, app: ASGIApp) -> CORSMiddleware:
        return CORSMiddleware(
            app=app,
            allow_origins=self.allow_origins,
            allow_methods=self.allow_methods,
            allow_headers=self.allow_headers,
            allow_credentials=self.allow_credentials,
            expose_headers=self.expose_headers,
            max_age=self.max_age,
        )


class CORSMatcherMiddleware:
    def __init__(self, app: ASGIApp, *, configs: Sequence[CORSConfig]):
        self.app = app
        self.config_middlewares = tuple(
            (config, config.get_middleware(app)) for config in configs
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origin = headers.get("origin")

        if origin is None:
            await self.app(scope, receive, send)
            return

        middleware = self._get_config_middleware(origin, scope)

        if middleware is None:
            await self.app(scope, receive, send)
            return

        if scope["method"] == "OPTIONS" and "access-control-request-method" in headers:
            response = middleware.preflight_response(request_headers=headers)
            await response(scope, receive, send)

            return

        await middleware.simple_response(scope, receive, send, request_headers=headers)

    def _get_config_middleware(
        self, origin: str, scope: Scope
    ) -> CORSMiddleware | None:
        for config, middleware in self.config_middlewares:
            if config.matcher(origin, scope):
                return middleware

        return None
