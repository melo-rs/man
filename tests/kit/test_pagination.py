from typing import Any
from uuid import uuid4, uuid7

import pytest
from pydantic import ValidationError

from man.config import settings
from man.kit.pagination import PaginationParams


@pytest.mark.parametrize(
    "payload",
    [
        {"first": 1},
        {"last": 1},
        {"first": settings.API_PAGINATION_MAX_LIMIT},
        {"first": 2, "after": uuid7()},
        {"last": 2, "before": uuid7()},
    ],
)
def test_valid_pagination(payload: dict[str, Any]) -> None:
    params = PaginationParams.model_validate(payload)
    assert params.model_dump(exclude_none=True) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"first": 1, "last": 1},
        {"first": 1, "before": uuid7()},
        {"last": 1, "after": uuid7()},
        {"first": 0},
        {"last": -1},
        {"first": settings.API_PAGINATION_MAX_LIMIT + 1},
        {"last": settings.API_PAGINATION_MAX_LIMIT + 1},
        {"first": 1, "after": "invalid"},
        {"last": 1, "before": uuid4()},
    ],
)
def test_invalid_pagination(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PaginationParams.model_validate(payload)
