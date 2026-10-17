from pydantic import field_validator

from man.kit.schemas import IDSchema, Schema, TimestampedSchema


class ProductSchema(IDSchema, TimestampedSchema):
    name: str
    description: str
    price: int
    thumb_url: str


class ProductCreate(Schema):
    name: str
    description: str
    price: int
    thumb_url: str

    @field_validator("name", "description")
    def str_fields_cannot_be_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")

        return value

    @field_validator("price")
    def price_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")

        return value
