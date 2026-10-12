import asyncio
import re
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from man.config import settings
from man.kit.db.postgres import AsyncSessionMaker, create_async_engine
from man.models import Model

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_FILE = ROOT / "alembic.ini"


@dataclass(frozen=True)
class Database:
    name: str
    url: str


def get_database_name(base_name: str, testrun_uid: str, worker_id: str) -> str:
    """Only generate disposable names; never reuse or drop an existing database."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*_test", base_name):
        raise ValueError("The test database base name must end in '_test'")
    if not re.fullmatch(r"[0-9a-f]{32}", testrun_uid):
        raise ValueError("The test run ID must contain 32 lowercase hexadecimal digits")
    if not re.fullmatch(r"master|gw[0-9]+", worker_id):
        raise ValueError("Invalid pytest worker ID")
    name = f"{base_name}_{testrun_uid}_{worker_id}"
    if len(name) > 63:
        raise ValueError("The generated test database name exceeds PostgreSQL's limit")
    return name


async def _execute_admin_statement(statement: str) -> None:
    connection = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PWD,
        database="postgres",
        timeout=10,
    )
    try:
        await connection.execute(statement)
    finally:
        await connection.close()


def apply_migrations(database_url: str) -> None:
    config = Config(ALEMBIC_CONFIG_FILE)
    config.attributes["sqlalchemy.url"] = database_url
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def initialize_test_database(worker_id: str, testrun_uid: str) -> Iterator[Database]:
    if not settings.is_test():
        raise pytest.UsageError("Database tests require MAN_ENV=test")

    name = get_database_name(settings.POSTGRES_DATABASE, testrun_uid, worker_id)
    test_settings = settings.model_copy(update={"POSTGRES_DATABASE": name})
    database = Database(name=name, url=test_settings.get_postgres_dsn("asyncpg"))

    # Identifiers are validated above. A failed CREATE must not trigger a DROP.
    try:
        asyncio.run(_execute_admin_statement(f'CREATE DATABASE "{name}"'))
    except OSError as exc:
        raise RuntimeError(
            "Cannot connect to test PostgreSQL. Start it with "
            "'docker compose -f docker-compose.test.yml up -d --wait'."
        ) from exc
    try:
        apply_migrations(database.url)
        yield database
    finally:
        asyncio.run(_execute_admin_statement(f'DROP DATABASE "{name}"'))


@asynccontextmanager
async def database_transaction(database: Database) -> AsyncIterator[AsyncConnection]:
    """All session commits stay inside an outer transaction that always rolls back."""
    engine = create_async_engine(
        dsn=database.url,
        application_name=f"test.{database.name}",
        pool_size=1,
        pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
        command_timeout=settings.DATABASE_COMMAND_TIMEOUT_SECONDS,
    )
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                yield connection
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def connection(
    initialize_test_database: Database, anyio_backend: str
) -> AsyncIterator[AsyncConnection]:
    async with database_transaction(initialize_test_database) as connection:
        yield connection


@pytest.fixture
def sessionmaker(connection: AsyncConnection) -> AsyncSessionMaker:
    return async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest.fixture
async def session(sessionmaker: AsyncSessionMaker) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        yield session


type SaveFixture = Callable[[Model], Coroutine[None, None, None]]


@pytest.fixture
def save_fixture(session: AsyncSession) -> SaveFixture:
    async def save(model: Model) -> None:
        session.add(model)
        await session.flush()

    return save
