import base64
import hashlib
import hmac
from time import time

from man.integrations.vercel.blob.client import client


class BlobService:
    async def issue_signed_token(
        self,
        pathname: str,
        content_type: str,
        maximum_size_bytes: int = 10 * 1024 * 1024,
        expires_in_seconds: int = 300,
    ):
        response = await client.post(
            "/signed-token",
            json={
                "pathname": pathname,
                "operations": ["put"],
                "allowedContentTypes": [content_type],
                "maximumSizeInBytes": maximum_size_bytes,
                "validUntil": (int(time()) + expires_in_seconds) * 1000,
            },
        )

        token = response.json()
        print(token)

        response.raise_for_status()

        canonical = "\n".join(
            sorted(
                ["operation=put", f"pathname={pathname}"],
                key=lambda s: s.encode("utf-8"),
            )
        )

        digest = hmac.new(
            token["clientSigningToken"].encode(),
            canonical.encode(),
            hashlib.sha256,
        ).digest()

        signature = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

        url = client.build_request(
            "PUT",
            "",
            params={
                "pathname": pathname,
                "vercel-blob-delegation": token["delegationToken"],
                "vercel-blob-signature": signature,
            },
        ).url

        return str(url)


blob = BlobService()
