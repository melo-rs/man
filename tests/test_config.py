from typing import Literal

import pytest
from pydantic import SecretStr
from pytest import MonkeyPatch
from sqlalchemy.engine import make_url

from man.app import app, lifespan
from man.config import Environment, Settings, settings


def test_test_environment_is_selected_before_app_imports() -> None:
    assert settings.is_test()
    assert Settings.model_config.get("env_file") == ".env.test"


@pytest.mark.parametrize("environment", list(Environment))
def test_environment_helpers(environment: Environment) -> None:
    config = settings.model_copy(update={"ENV": environment})
    assert config.is_development() == (environment == Environment.development)
    assert config.is_production() == (environment == Environment.production)
    assert config.is_test() == (environment == Environment.test)


@pytest.mark.parametrize("driver", ["asyncpg", "psycopg2"])
def test_database_urls_preserve_special_password_characters(
    driver: Literal["asyncpg", "psycopg2"],
) -> None:
    config = settings.model_copy(
        update={"POSTGRES_PWD": "p@ss%word", "POSTGRES_DATABASE": "man_test"}
    )
    url = make_url(config.get_postgres_dsn(driver))
    assert url.drivername == f"postgresql+{driver}"
    assert url.password == "p@ss%word"
    assert url.database == "man_test"


def test_neon_database_urls_use_pooled_runtime_and_direct_migrations() -> None:
    config = settings.model_copy(
        update={
            "ENV": Environment.production,
            "DATABASE_URL": "postgresql://user:p%40ss@pooled.example/db?sslmode=require&channel_binding=require",
            "DATABASE_URL_UNPOOLED": "postgresql://user:p%40ss@direct.example/db?sslmode=require&channel_binding=require",
        }
    )

    runtime_url = make_url(config.get_postgres_dsn("asyncpg"))
    migration_url = make_url(config.get_postgres_dsn("asyncpg", direct=True))

    assert runtime_url.host == "pooled.example"
    assert migration_url.host == "direct.example"
    assert runtime_url.password == "p@ss"
    assert runtime_url.query == {"ssl": "require"}
    assert migration_url.query == {"ssl": "require"}


def test_neon_url_keeps_libpq_options_for_psycopg2() -> None:
    config = settings.model_copy(
        update={
            "ENV": Environment.production,
            "DATABASE_URL": "postgres://user:password@pooled.example/db?sslmode=require&channel_binding=require",
        }
    )

    url = make_url(config.get_postgres_dsn("psycopg2"))

    assert url.drivername == "postgresql+psycopg2"
    assert url.query == {"sslmode": "require", "channel_binding": "require"}


def test_neon_integration_url_is_read_from_environment(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@host.example/db")

    config = Settings()

    assert config.DATABASE_URL == "postgresql://user:password@host.example/db"


@pytest.mark.anyio
async def test_app_requires_a_configured_login_password(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "PASSWORD", SecretStr(""))
    with pytest.raises(RuntimeError, match="MAN_PASSWORD must be configured"):
        async with lifespan(app):
            pass
