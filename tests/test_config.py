from typing import Literal

import pytest
from sqlalchemy.engine import make_url

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
