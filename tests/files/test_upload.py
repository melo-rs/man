import base64
import hashlib
import hmac
import json
from time import time
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid7

import httpx
import pytest
from fastapi import FastAPI
from pytest import MonkeyPatch

from man.auth.dependencies import require_authentication
from man.config import settings
from man.files.service import files
from man.integrations.vercel.blob import service as blob_module
from man.integrations.vercel.blob.client import BlobClient
from man.router import router

pytestmark = pytest.mark.anyio


async def test_signed_upload_url_is_scoped_and_signed(monkeypatch: MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"clientSigningToken": "signing-key", "delegationToken": "delegation"},
        )

    transport = httpx.MockTransport(handle_request)
    monkeypatch.setattr(
        blob_module,
        "BlobClient",
        lambda: BlobClient(token="vercel_blob_rw_store_secret", transport=transport),
    )

    before = int(time()) * 1000
    url = await blob_module.BlobService().issue_signed_token(
        "image-id", "image/png", maximum_size_bytes=1024, expires_in_seconds=60
    )
    after = int(time()) * 1000

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://vercel.com/api/blob/signed-token"
    assert request.headers["Authorization"] == "Bearer vercel_blob_rw_store_secret"
    assert request.headers["x-vercel-blob-store-id"] == "store"
    assert request.headers["x-api-version"] == "13"
    body = json.loads(request.content)
    assert {key: value for key, value in body.items() if key != "validUntil"} == {
        "pathname": "image-id",
        "operations": ["put"],
        "allowedContentTypes": ["image/png"],
        "maximumSizeInBytes": 1024,
    }
    assert before + 60_000 <= body["validUntil"] <= after + 60_000

    parsed = urlsplit(url)
    assert (parsed.scheme, parsed.netloc, parsed.path) == (
        "https",
        "vercel.com",
        "/api/blob/",
    )
    params = parse_qs(parsed.query)
    assert params["pathname"] == ["image-id"]
    assert params["vercel-blob-delegation"] == ["delegation"]
    digest = hmac.new(
        b"signing-key", b"operation=put\npathname=image-id", hashlib.sha256
    ).digest()
    assert params["vercel-blob-signature"] == [
        base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    ]


async def test_blob_api_error_is_not_returned_as_an_upload_url(
    monkeypatch: MonkeyPatch,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": "unauthorized"})
    )
    monkeypatch.setattr(
        blob_module,
        "BlobClient",
        lambda: BlobClient(token="vercel_blob_rw_store_secret", transport=transport),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await blob_module.BlobService().issue_signed_token("image-id", "image/png")


async def test_files_endpoint_returns_a_presigned_url(monkeypatch: MonkeyPatch) -> None:
    file_id = uuid7()
    create = AsyncMock(return_value=(file_id, "https://vercel.com/api/blob/?signed=1"))
    monkeypatch.setattr(files, "create", create)
    test_app = FastAPI()
    test_app.include_router(router)

    async def allow_request() -> None:
        pass

    test_app.dependency_overrides[require_authentication] = allow_request

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/files", json={"mime_type": "image/png"})

    assert response.status_code == 200
    assert response.json() == {
        "id": str(file_id),
        "mime_type": "image/png",
        "upload_url": "https://vercel.com/api/blob/?signed=1",
    }
    create.assert_awaited_once()


def test_blob_client_requires_configuration(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VERCEL_BLOB_READ_WRITE_TOKEN", "")
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    with pytest.raises(ValueError, match="not configured or invalid"):
        BlobClient()


def test_blob_client_uses_connected_vercel_store(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VERCEL_BLOB_READ_WRITE_TOKEN", "")
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "vercel_blob_rw_store_secret")

    client = BlobClient()

    assert client.headers["Authorization"] == "Bearer vercel_blob_rw_store_secret"
    assert client.headers["x-vercel-blob-store-id"] == "store"
