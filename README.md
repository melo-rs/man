# Man backend

Python 3.14, FastAPI, SQLAlchemy, PostgreSQL, and Alembic.

## Run the tests

Install the locked development dependencies and start the disposable test service:

```sh
uv sync --dev --locked
docker compose -f docker-compose.test.yml up -d --wait
uv run task test
```

The test service uses PostgreSQL 18.6 on `127.0.0.1:5433`. It has a separate
Compose project and stores its data in memory. Public connection defaults live
in the tracked `.env.test`; tests select `MAN_ENV=test` before importing the app.
Environment variables override those defaults, including the port used by CI.

Useful commands:

```sh
# No PostgreSQL required
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

# Stop the service and discard all its data
docker compose -f docker-compose.test.yml down
```

For a different local port, set `MAN_TEST_POSTGRES_PORT` when starting Compose
and the same value in `MAN_POSTGRES_PORT` when running tests. An alternative
PostgreSQL server must give the test user permission to create databases and
use a `MAN_POSTGRES_DATABASE` base name ending in `_test`.

## Test conventions

Tests mirror application domains. Each domain uses `test_schemas.py`,
`test_repository.py`, and `test_endpoints.py` as needed. Mark database-backed
tests with `pytest.mark.integration` and async tests with `pytest.mark.anyio`.
AnyIO uses asyncio, matching asyncpg.

Shared fixtures live in `tests/fixtures`:

- `database`: one freshly migrated database per run and xdist worker, plus
  function-scoped connections, sessions, and `save_fixture`.
- `base`: fresh FastAPI apps and HTTPX clients using the real session middleware
  and database dependency.
- `random_objects`: typed async builders such as `create_product`, with explicit
  overrides and predictable defaults; names follow Polar's fixture conventions.

Repository tests use the real PostgreSQL database. `save_fixture` adds and
flushes models. Endpoint tests automatically release fixture setup savepoints
before each request, clear the setup session's identity map, and open a fresh
request session on the same connection. Application commits and rollbacks use
savepoints inside an outer transaction that always rolls back after the test.
Requests within one test run sequentially; this shared-connection client is not
a harness for concurrent-request or separate-connection visibility tests.

Test databases include the run ID and worker ID and are dropped on normal
teardown. The harness never drops the configured base database or reuses an
existing generated database. If a run is forcibly terminated, stopping the
disposable Compose service clears any leftover databases.

Routine HTTPX tests inject request state rather than starting application
lifespan. The health tests also use a context-managed `TestClient` to exercise
real startup, database connections, and shutdown. Schema and helper tests do
not initialize PostgreSQL.

## Migrations and checks

Schemas are built from migrations, never `metadata.create_all()`. The model
registry must import new models so Alembic can discover them. Check the base
test database explicitly with:

```sh
MAN_ENV=test uv run task db_migrate
MAN_ENV=test uv run alembic check
uv run task lint
uv run task type_check
```

CI runs those checks and the serial suite, uploading JUnit and XML/HTML coverage
reports. Coverage is reported without a minimum threshold. Optional xdist
parallelism is available locally; database templates, CI sharding, and services
such as Redis and MinIO are deferred until the application needs them.

This suite follows [Polar's backend test conventions at commit 2a1cb969](https://github.com/polarsource/polar/tree/2a1cb969fb21e2c9811c094069351089736fb172/server/tests).
