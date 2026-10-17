import httpx

from man.config import settings


class BlobClient(httpx.AsyncClient):
    def __init__(self):
        super().__init__(
            base_url="https://vercel.com/api/blob/",
            headers={
                "Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}",
                "x-vercel-blob-store-id": settings.VERCEL_BLOB_READ_WRITE_TOKEN.split("_")[3],
                "x-api-version": "13",
            },
            timeout=15.0,
        )


client = BlobClient()
