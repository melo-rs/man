from typing import Literal

from man.kit.schemas import IDSchema, Schema


class FileCreate(Schema):
    mime_type: Literal["image/png"]


class FileSchema(IDSchema):
    mime_type: Literal["image/png"]
    upload_url: str
