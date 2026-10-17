import httpx

from man.config import settings


class BlobClient(httpx.AsyncClient):
    def __init__(
        self,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        token = token if token is not None else settings.VERCEL_BLOB_READ_WRITE_TOKEN
        parts = token.split("_", 4)
        if (
            len(parts) != 5
            or parts[:3] != ["vercel", "blob", "rw"]
            or not parts[3]
            or not parts[4]
        ):
            raise ValueError(
                "Vercel Blob read-write token is not configured or invalid"
            )

        super().__init__(
            base_url="https://vercel.com/api/blob/",
            headers={
                "Authorization": f"Bearer {token}",
                "x-vercel-blob-store-id": parts[3],
                "x-api-version": "13",
            },
            timeout=15.0,
            transport=transport,
        )
