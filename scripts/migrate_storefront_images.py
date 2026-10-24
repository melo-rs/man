"""Upload the storefront's product images to the public development Blob store.

Run once after ``seed_storefront.py`` with the frontend checkout beside this
backend checkout. Safe to rerun: existing blobs and migrated records are reused.
"""

import asyncio
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import tempfile
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from man.config import settings
from man.models import Product
from man.postgres import create_async_engine

DATA_DIR = Path(__file__).parent / "data"
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "Emporio_GE"
PREFIX = "emporio-ge/products/"
MIME_TYPES = {
    ".avif": "image/avif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def blob_environment() -> dict[str, str]:
    token = settings.VERCEL_BLOB_READ_WRITE_TOKEN or os.getenv("BLOB_READ_WRITE_TOKEN")
    if not token:
        raise RuntimeError("A Vercel Blob read-write token is required")
    return {
        **os.environ,
        "BLOB_READ_WRITE_TOKEN": token,
        "XDG_CACHE_HOME": str(Path(tempfile.gettempdir()) / "emporio-vercel-cache"),
        "NO_UPDATE_NOTIFIER": "1",
    }


def vercel(*args: str, env: dict[str, str]) -> str:
    result = subprocess.run(
        ["vercel", "blob", *args, "--non-interactive"],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.replace(env["BLOB_READ_WRITE_TOKEN"], "[redacted]")
        raise RuntimeError(f"Vercel Blob command failed: {detail.strip()}")
    return result.stdout


def list_blobs(env: dict[str, str]) -> dict[str, str]:
    response = json.loads(
        vercel("list", "--json", "--prefix", PREFIX, "--limit", "1000", env=env)
    )
    if response["pagination"].get("next"):
        raise RuntimeError("Blob prefix contains more than 1000 files")
    result = {blob["pathname"]: blob["url"] for blob in response["blobs"]}
    for url in result.values():
        host = urlsplit(url).hostname or ""
        if not host.endswith(".public.blob.vercel-storage.com"):
            raise RuntimeError("Connected Blob store is not public")
    return result


def pathname_for(path: str) -> str:
    source = FRONTEND_DIR / path
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    stem = unicodedata.normalize("NFKD", source.stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return f"{PREFIX}{digest}-{stem}{source.suffix.lower()}"


def upload(path: str, pathname: str, env: dict[str, str]) -> None:
    source = FRONTEND_DIR / path
    mime_type = MIME_TYPES.get(source.suffix.lower()) or mimetypes.guess_type(source)[0]
    if not source.is_file() or not mime_type:
        raise RuntimeError(f"Missing or unsupported image: {path}")
    vercel(
        "put",
        str(source),
        "--access",
        "public",
        "--pathname",
        pathname,
        "--content-type",
        mime_type,
        env=env,
    )
    print(f"Uploaded {path}")


async def update_products(records: list[dict], urls: dict[str, str]) -> int:
    engine = create_async_engine()
    updated = 0
    try:
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        async with sessionmaker() as session:
            names = [record["name"] for record in records]
            products = (
                (await session.execute(select(Product).where(Product.name.in_(names))))
                .scalars()
                .all()
            )
            by_name = {product.name: product for product in products}
            for record in records:
                product = by_name.get(record["name"])
                if product is None:
                    continue
                gallery = record["gallery"]
                target = [urls[path] for path in gallery]
                if product.thumb_url == target[0] and product.gallery_urls == target:
                    continue
                if product.thumb_url != gallery[0] or product.gallery_urls != gallery:
                    raise RuntimeError(
                        f"Images for {product.name} were edited; review before migrating"
                    )
                product.thumb_url = target[0]
                product.gallery_urls = target
                updated += 1
            await session.commit()
    finally:
        await engine.dispose()
    return updated


def main() -> None:
    records = json.loads((DATA_DIR / "products.json").read_text())
    paths = sorted({path for record in records for path in record["gallery"]})
    for path in paths:
        if not (FRONTEND_DIR / path).is_file():
            raise RuntimeError(f"Missing storefront image: {path}")

    env = blob_environment()
    pathnames = {path: pathname_for(path) for path in paths}
    existing = list_blobs(env)
    missing = [
        (path, pathname)
        for path, pathname in pathnames.items()
        if pathname not in existing
    ]
    if missing:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(upload, path, pathname, env)
                for path, pathname in missing
            ]
            for future in as_completed(futures):
                future.result()

    for attempt in range(5):
        blobs = list_blobs(env)
        if all(pathname in blobs for pathname in pathnames.values()):
            break
        if attempt == 4:
            raise RuntimeError("Uploaded blobs did not appear in the store listing")
        time.sleep(2)

    urls = {path: blobs[pathname] for path, pathname in pathnames.items()}
    manifest = DATA_DIR / "blob_urls.json"
    manifest.write_text(json.dumps(urls, indent=2, ensure_ascii=False) + "\n")
    updated = asyncio.run(update_products(records, urls))
    print(f"Mapped {len(urls)} public image URLs; updated {updated} products")


if __name__ == "__main__":
    main()
