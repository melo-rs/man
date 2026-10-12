import json
from decimal import Decimal

import pytest

from man.kit.db.postgres import json_serializer


def test_json_serializer_handles_nested_decimals() -> None:
    assert json.loads(
        json_serializer({"values": [Decimal("1.25"), {"amount": Decimal("2.50")}]})
    ) == {"values": [1.25, {"amount": 2.5}]}


def test_json_serializer_rejects_unsupported_objects() -> None:
    with pytest.raises(TypeError, match="not JSON serializable"):
        json_serializer({"unsupported": object()})
