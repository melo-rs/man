from typing import Literal

from man.kit.schemas import IDSchema, Schema


class FileCreate(Schema):
    mime_type: Literal["image/png", "image/jpeg", "image/webp", "image/avif"]


class FileSchema(IDSchema):
    mime_type: Literal["image/png", "image/jpeg", "image/webp", "image/avif"]
    upload_url: str
