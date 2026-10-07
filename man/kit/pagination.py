from collections.abc import Sequence
from typing import Annotated, Any, Self

from fastapi import Query
from pydantic import UUID7, Field, model_validator

from man.config import settings
from man.kit.schemas import Schema


class PaginationParams(Schema):
    after: UUID7 | None = Field(
        default=None,
        description="Cursor to be used with 'first' for forward pagination.",
    )
    before: UUID7 | None = Field(
        default=None,
        description="Cursor to be used with 'last' for backward pagination.",
    )
    first: int | None = Field(
        default=None,
        ge=1,
        le=settings.API_PAGINATION_MAX_LIMIT,
        description=(
            f"The number of items to forward paginate (used with 'after'). "
            f"Maximum is {settings.API_PAGINATION_MAX_LIMIT}."
        ),
    )
    last: int | None = Field(
        default=None,
        ge=1,
        le=settings.API_PAGINATION_MAX_LIMIT,
        description=(
            f"The number of items to backward paginate (used with 'before'). "
            f"Maximum is {settings.API_PAGINATION_MAX_LIMIT}."
        ),
    )

    @model_validator(mode="after")
    def check_cursor_order(self) -> Self:
        if self.first is None and self.last is None:
            raise ValueError("either 'first' or 'last' must be provided")

        if self.first is not None and self.last is not None:
            raise ValueError("'first' and 'last' cannot be both provided")

        if self.first is not None and self.before is not None:
            raise ValueError("'before' cannot be used with 'first'")

        if self.last is not None and self.after is not None:
            raise ValueError("'after' cannot be used with 'last'")

        return self


PaginationParamsQuery = Annotated[PaginationParams, Query()]


class Pagination(Schema):
    total_count: int


class ListResource[T: Any](Schema):
    items: list[T]
    pagination: Pagination

    @classmethod
    def from_paginated_results(cls, items: Sequence[T], total_count: int):
        return cls(items=list(items), pagination=Pagination(total_count=total_count))
