from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from man.exceptions import ManError


async def man_exception_handler(_: Request, exc: ManError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"status_code": exc.status_code, "message": exc.message},
    )


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ManError, man_exception_handler)  # type: ignore
