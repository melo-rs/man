from datetime import UTC, datetime

from man.kit.utils import generate_uuid, utc_now


def test_generated_ids_are_unique_uuid7s() -> None:
    ids = {generate_uuid() for _ in range(100)}
    assert len(ids) == 100
    assert all(id.version == 7 for id in ids)


def test_utc_now_is_aware_and_current() -> None:
    before = datetime.now(UTC)
    now = utc_now()
    after = datetime.now(UTC)
    assert now.tzinfo == UTC
    assert before <= now <= after
