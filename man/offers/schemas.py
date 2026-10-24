from datetime import datetime

from pydantic import UUID7, Field, field_validator, model_validator

from man.kit.schemas import IDSchema, Schema, TimestampedSchema


class OfferSchema(IDSchema, TimestampedSchema):
    product_id: UUID7
    thumb_url: str = Field(description="Public URL of the product image.")
    promo_price: int = Field(description="Promotional price in BRL cents.")
    starts_at: datetime
    ends_at: datetime
    is_active: bool


class OfferCreate(Schema):
    product_id: UUID7
    promo_price: int = Field(description="Promotional price in BRL cents.")
    starts_at: datetime
    ends_at: datetime

    @field_validator("promo_price")
    def price_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> OfferCreate:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self
