# Man backend

Python 3.14, FastAPI, SQLAlchemy, PostgreSQL, and Alembic.

## Run the tests

For first-time setup, copy `.env.template` to `.env` and customize it as needed.
Install the locked development dependencies and start the shared PostgreSQL service:

```sh
uv sync --dev --locked
docker compose up -d --wait postgres
uv run task test
```

Development and tests use the same PostgreSQL 18.6 server on port `5432`.
Development uses the `man` database; tests create separate worker databases
such as `man_test_master` and `man_test_gw0`. Public test defaults live in the
tracked `.env.test`; tests select `MAN_ENV=test` before importing the app.
Environment variables override those defaults. If the server uses custom
credentials, host, or port, use matching values when running tests.

Useful commands:

```sh
# Run unit tests (the database fixture still initializes a worker database)
uv run task test_unit

# Parallel execution without coverage
uv run task test_fast

# Limit parallelism on larger machines
uv run task test_fast -n 2

# Run a file or a single case
uv run task test tests/products/test_endpoints.py
uv run task test tests/products/test_endpoints.py::test_missing_product

# Match CI's reports
uv run task test --cov-report=xml --cov-report=html --junitxml=test-results.xml

# Stop the shared service; its persistent volume retains development data
docker compose down
```

The PostgreSQL user must have permission to create and drop databases. The
Compose service's default `man` user has these permissions. Keep a separate test
database prefix in `MAN_POSTGRES_DATABASE`, such as `man_test`.

## Test conventions

Tests mirror application domains. Each domain uses `test_schemas.py`,
`test_repository.py`, and `test_endpoints.py` as needed. Mark database-backed
tests with `pytest.mark.integration` and async tests with `pytest.mark.anyio`.
AnyIO uses asyncio, matching asyncpg. Database initialization is session-scoped
and automatic for every test run, including runs that select only unit tests.

Shared fixtures live in `tests/fixtures`:

- `database`: one freshly migrated database per xdist worker, plus
  function-scoped transactions, sessions, and `save_fixture`.
- `base`: FastAPI dependency overrides and HTTPX clients that clear the test
  session's identity map before each request.
- `random_models`: typed async builders such as `create_product`, with explicit
  overrides and predictable defaults; names follow Polar's fixture conventions.

Repository tests use the real PostgreSQL database. `save_fixture` adds and
flushes models. Endpoint tests reuse the test session through a dependency
override. The HTTPX client expunges loaded objects before each request to catch
behavior that would otherwise depend on the session's identity map. Each test
starts an outer database transaction and rolls it back afterward.
The request-session lifecycle tests use a dedicated client with the real database
dependency and request savepoints to verify production commits and rollbacks.

Worker databases use the configured test prefix and worker ID: `master` for a
serial run and `gw0`, `gw1`, etc. for parallel runs. The initialization fixture
drops an existing worker database, recreates it, and applies migrations before
the suite. It drops the worker database again on normal teardown. Overlapping
test runs need different `MAN_POSTGRES_DATABASE` values because worker names are
reused. The configured base database and development database are left intact.

Routine HTTPX tests inject request state rather than starting application
lifespan.

## Migrations and checks

Schemas are built from migrations, never `metadata.create_all()`. The model
registry must import new models so Alembic can discover them. Migrate and check
the development database with:

```sh
uv run task db_migrate
uv run alembic check
uv run task lint
uv run task type_check
```

CI starts a PostgreSQL service with a `man_test` database, migrates it, and runs
`alembic check`. It sets `MAN_TEST_DATABASE_TEMPLATE=man_test`, so worker
databases are cloned from that migrated template instead of applying migrations
again. Locally, the fixture applies migrations unless
`MAN_TEST_DATABASE_TEMPLATE` names an existing migrated template. Template
cloning retries briefly when another connection is using the template, matching
Polar's fixture.

CI uploads JUnit and XML/HTML coverage reports. Coverage is reported without a
minimum threshold. Optional xdist parallelism is available locally.

The database lifecycle and shared PostgreSQL setup follow
[Polar's backend fixtures at commit a4bae2b7](https://github.com/polarsource/polar/tree/a4bae2b742befdb6dcc696a841f259aed24f2086/server/tests/fixtures).
