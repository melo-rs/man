from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from man.kit.schemas import IDSchema, Schema, TimestampedSchema


class ProductSchema(IDSchema, TimestampedSchema):
    name: str
    description: str
    price: int = Field(description="Price in BRL cents.")
    thumb_url: str
    category: str
    unit: str
    gallery_urls: list[str]
    options: list[str]


class ProductCreate(Schema):
    name: str
    description: str
    price: int = Field(description="Price in BRL cents.")
    thumb_url: str
    category: str = "Produtos"
    unit: str = "unidade"
    gallery_urls: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    option_prices: dict[str, int] = Field(default_factory=dict)

    @field_validator("name", "description", "category", "unit")
    def str_fields_cannot_be_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")

        return value

    @field_validator("price")
    def price_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")

        return value

    @field_validator("thumb_url")
    def thumb_must_be_public_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("image URL must be an absolute HTTPS URL")
        return value

    @field_validator("gallery_urls")
    def gallery_must_have_public_urls(cls, values: list[str]) -> list[str]:
        for value in values:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("gallery image URLs must be absolute HTTPS URLs")
        return values

    @model_validator(mode="after")
    def validate_option_prices(self) -> ProductCreate:
        if any(not option for option in self.options):
            raise ValueError("option names must not be empty")
        if len(set(self.options)) != len(self.options):
            raise ValueError("option names must be unique")
        for name, price in self.option_prices.items():
            if name not in self.options:
                raise ValueError("option price name must match an option")
            if price <= 0:
                raise ValueError("option prices must be positive")
        return self
