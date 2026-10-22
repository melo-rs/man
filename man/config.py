import os
from enum import StrEnum
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Environment(StrEnum):
    development = "development"
    production = "production"
    test = "test"


env = Environment(os.getenv("MAN_ENV", Environment.development))

if env == Environment.test:
    env_file = ".env.test"
else:
    env_file = ".env"


class Settings(BaseSettings):
    ENV: Environment = Environment.development
    SQLALCHEMY_DEBUG: bool = False

    # Database
    POSTGRES_USER: str = "man"
    POSTGRES_PWD: str = "man"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "man"
    DATABASE_URL: str = Field(default="", validation_alias="DATABASE_URL")
    DATABASE_URL_UNPOOLED: str = Field(
        default="", validation_alias="DATABASE_URL_UNPOOLED"
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_POOL_RECYCLE_SECONDS: int = 600  # 10 minutes
    DATABASE_COMMAND_TIMEOUT_SECONDS: float = 30.0
    DATABASE_STREAM_YIELD_PER: int = 100

    # Authentication
    PASSWORD: SecretStr = SecretStr("")

    # CORS
    CORS_ORIGINS: list[str] = []

    # Vercel Blob
    VERCEL_BLOB_READ_WRITE_TOKEN: str = ""

    # Pagination
    API_PAGINATION_MAX_LIMIT: int = 100

    model_config = SettingsConfigDict(
        env_prefix="man_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file=env_file,
        extra="allow",
    )

    def get_postgres_dsn(
        self, driver: Literal["asyncpg", "psycopg2"], *, direct: bool = False
    ) -> str:
        database_url = (
            self.DATABASE_URL_UNPOOLED
            if direct and self.DATABASE_URL_UNPOOLED
            else self.DATABASE_URL
        )
        if database_url and not self.is_test():
            url = make_url(database_url)
            if url.drivername not in {
                "postgres",
                "postgresql",
                "postgresql+asyncpg",
                "postgresql+psycopg2",
            }:
                raise ValueError("DATABASE_URL must be a PostgreSQL URL")

            query = dict(url.query)
            if driver == "asyncpg":
                # Neon emits libpq options that asyncpg does not accept as kwargs.
                if "sslmode" in query:
                    query["ssl"] = query.pop("sslmode")
                query.pop("channel_binding", None)

            return url.set(
                drivername=f"postgresql+{driver}", query=query
            ).render_as_string(hide_password=False)

        return str(
            PostgresDsn.build(
                scheme=f"postgresql+{driver}",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PWD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DATABASE,
            )
        )

    def is_environment(self, environments: set[Environment]) -> bool:
        return self.ENV in environments

    def is_development(self) -> bool:
        return self.is_environment({Environment.development})

    def is_production(self) -> bool:
        return self.is_environment({Environment.production})

    def is_test(self) -> bool:
        return self.is_environment({Environment.test})


settings = Settings()
