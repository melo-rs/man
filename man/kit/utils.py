from datetime import UTC, datetime
from uuid import UUID, uuid7


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> UUID:
    return uuid7()
