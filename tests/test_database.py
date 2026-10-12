import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from man.models import Product
from tests.fixtures.database import (
    ALEMBIC_CONFIG_FILE,
    Database,
    database_transaction,
    get_database_name,
)


def test_names_isolate_workers_and_runs() -> None:
    names = {
        get_database_name("man_test", run_id, worker_id)
        for run_id in ["a" * 32, "b" * 32]
        for worker_id in ["master", "gw0", "gw1"]
    }
    assert len(names) == 6
    assert "man_test" not in names


@pytest.mark.parametrize(
    ("base", "run_id", "worker"),
    [
        ("man", "a" * 32, "master"),
        ("production", "a" * 32, "gw0"),
        ('man_test"; DROP DATABASE man; --', "a" * 32, "gw0"),
        ("man_test", "invalid", "gw0"),
        ("man_test", "a" * 32, 'gw0"'),
        ("x" * 50 + "_test", "a" * 32, "gw0"),
    ],
)
def test_unsafe_database_names_are_rejected(
    base: str, run_id: str, worker: str
) -> None:
    with pytest.raises(ValueError):
        get_database_name(base, run_id, worker)


@pytest.mark.integration
@pytest.mark.anyio
async def test_connection_targets_worker_database(
    initialize_test_database: Database,
    session: AsyncSession,
    worker_id: str,
    testrun_uid: str,
) -> None:
    name = await session.scalar(text("SELECT current_database()"))
    assert name == initialize_test_database.name
    assert testrun_uid in name
    assert name.endswith(f"_{worker_id}")


@pytest.mark.integration
@pytest.mark.anyio
async def test_commits_and_rollbacks_do_not_escape_outer_transaction(
    initialize_test_database: Database,
) -> None:
    async with (
        database_transaction(initialize_test_database) as connection,
        AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session,
    ):
        product = Product(name="Committed", description="Description", price=100)
        session.add(product)
        await session.commit()
        id = product.id
        session.expunge_all()
        assert await session.scalar(select(func.count()).select_from(Product)) == 1
        await session.commit()

        session.add(
            Product(id=id, name="Duplicate", description="Description", price=100)
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()
        assert await session.get(Product, id) is not None
        await session.commit()

        session.add(Product(name="Rolled back", description="Description", price=100))
        await session.flush()
        await session.rollback()
        assert await session.scalar(select(func.count()).select_from(Product)) == 1

    # A second independent context proves teardown works without test-order assumptions.
    async with database_transaction(initialize_test_database) as connection:
        assert await connection.scalar(select(func.count()).select_from(Product)) == 0


@pytest.mark.integration
def test_migration_round_trip_and_model_drift(
    initialize_test_database: Database,
) -> None:
    config = Config(ALEMBIC_CONFIG_FILE)
    config.attributes["sqlalchemy.url"] = initialize_test_database.url
    command.check(config)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.check(config)
