import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from man.exception_handlers import add_exception_handlers
from man.exceptions import Forbidden, ManError, ResourceMissing, Unauthorized


@pytest.mark.parametrize(
    "error",
    [Unauthorized(), Forbidden(), ResourceMissing(), ManError("Unexpected error")],
)
def test_exception_response_preserves_status_and_message(error: ManError) -> None:
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/error")
    async def raise_error() -> None:
        raise error

    with TestClient(app) as client:
        response = client.get("/error")
    assert response.status_code == error.status_code
    assert response.json() == {
        "status_code": error.status_code,
        "message": error.message,
    }
